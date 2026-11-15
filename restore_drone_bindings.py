"""Restore only the six drone actions from before the unsuccessful curve change."""
from pathlib import Path
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import tune_drone_curves as curves

ROOT = Path(__file__).resolve().parent


def restore(current, original):
    actions = {}
    for dev in curves.DEVICE.finditer(original):
        if not re.search(r'<Device\b[^>]*ProductID="0x03F5"', dev.group()):
            continue
        for event in curves.EVENT.finditer(dev.group()):
            for action in curves.ACTION.finditer(event.group()):
                target = re.search(r'JoystickTarget="(\d+)"', action.group())[1]
                actions[target] = action.group()
    assert len(actions) == 6, 'Backup must contain all six drone axes'
    replaced = []
    target_hid = {'X_AXIS': '48', 'Y_AXIS': '49', 'Z_AXIS': '50',
                  'RX_AXIS': '51', 'RZ_AXIS': '53', 'DIAL': '55'}
    precision_action = re.compile(r'<EventActionChangeValue\b(?=[^>]*TargetDataDefinition="LOCAL:JOY_0X12340XBEAD_'
                                  r'(X_AXIS|Y_AXIS|Z_AXIS|RX_AXIS|RZ_AXIS|DIAL)")[^>]*/>')
    def device(match):
        if not re.search(r'<Device\b[^>]*ProductID="0x03F5"', match.group()):
            return match.group()
        def event(match):
            def action(match):
                target = re.search(r'JoystickTarget="(\d+)"', match.group())[1]
                replaced.append(target)
                return actions[target]
            def precision(match):
                target = target_hid[match[1]]
                replaced.append(target)
                return actions[target]
            return precision_action.sub(precision, curves.ACTION.sub(action, match.group()))
        return curves.EVENT.sub(event, match.group())
    result = curves.DEVICE.sub(device, current)
    assert len(replaced) == 6 and len(set(replaced)) == 6
    ET.fromstring(result)
    return result


def main():
    installed = '--installed' in sys.argv
    if installed:
        import subprocess
        status = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SPAD.neXt.exe', '/NH'],
                                capture_output=True, text=True, check=True)
        assert 'spad.next.exe' not in status.stdout.lower(), 'SPAD must be closed'
    folders = ([Path.home() / 'Documents/SPAD.neXt/profiles'] if installed else
               [ROOT / 'profiles', ROOT / 'portable-setup/profiles'])
    rollback_backup = ROOT / 'backups' / ('drone-rollback-' + time.strftime('%Y%m%d-%H%M%S'))
    for folder in folders:
        source = ROOT / 'backups' / ('drone-curves-20261115-000314' if installed else
                                    'drone-curves-20261114-235507') / folder.parent.name
        for path in folder.glob('*.xml'):
            raw = path.read_bytes()
            text = raw.decode('utf-8-sig')
            original = (source / path.name).read_bytes().decode('utf-8-sig')
            updated = restore(text, original)
            target = rollback_backup / folder.parent.name / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            output = (b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8')
            path.write_bytes(output)
            assert path.read_bytes() == output
            assert restore(updated, original) == updated
            print(f'Restored six original drone actions: {path.name}')


if __name__ == '__main__':
    main()
