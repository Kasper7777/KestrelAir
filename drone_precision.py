"""Drone-only precision response with explicit, verified input/output units.

Inputs are SPAD LOCAL axis percentages. Outputs are vJoy raw counts 1..32767.
Existing mode conditions and all flight/cabin actions are preserved.
"""
from pathlib import Path
import re
import sys
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
ROUTES = {0: {'X_AXIS': ('Z_AXIS', 50), 'Y_AXIS': ('RZ_AXIS', 53), 'RZ_AXIS': ('DIAL', 55)},
          1: {'X_AXIS': ('X_AXIS', 48), 'Y_AXIS': ('Y_AXIS', 49), 'RZ_AXIS': ('RX_AXIS', 51)}}
DEVICE = re.compile(r'<Device\b[^>]*>.*?</Device>', re.S)
EVENT = re.compile(r'<Event BoundTo="(X_AXIS|Y_AXIS|RZ_AXIS)">.*?</Event>', re.S)


def expression(source):
    t = f'(Min(100.0, Max(0.0, [{source}])) / 50.0 - 1.0)'
    return f'16384.0 + 16383.0 * (0.35 * {t} + 0.65 * {t} * {t} * {t})'


def action(source, target):
    return (f'<EventActionChangeValue TargetDataDefinition="LOCAL:JOY_0X12340XBEAD_{target}" '
            f'SourceType="Exp" SourceDataDefinition="{expression(source)}" />')


def patch(text):
    changed = 0
    def device(m):
        nonlocal changed
        head = m.group().split('>')[0]
        if 'ProductID="0x03F5"' not in head:
            return m.group()
        index = int(re.search(r'DeviceIndex="(\d+)"', head)[1])
        def event(e):
            nonlocal changed
            bound = e[1]
            target, hid = ROUTES[index][bound]
            source = f'LOCAL:JOY_0X33440X03F5_{bound}' + ('_1' if index else '')
            old = re.compile(r'<EventActionVirtualJoyStick\b(?=[^>]*JoystickAction="VJOY_AXIS")'
                             rf'(?=[^>]*JoystickTarget="{hid}")[^>]*(?:/>|>.*?</EventActionVirtualJoyStick>)', re.S)
            new = re.compile(r'<EventActionChangeValue\b(?=[^>]*TargetDataDefinition="LOCAL:JOY_0X12340XBEAD_'
                             + target + r'")[^>]*/>')
            body, count = old.subn(lambda _: action(source, target), e.group())
            if not count:
                body, count = new.subn(lambda _: action(source, target), e.group())
            assert count == 1, (index, bound, count)
            changed += count
            return body
        return EVENT.sub(event, m.group())
    result = DEVICE.sub(device, text)
    assert changed == 6
    ET.fromstring(result)
    return result


def main():
    raise SystemExit('Disabled: unfinished changes rolled back at user request.')
    installed = '--installed' in sys.argv
    if installed:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SPAD.neXt.exe', '/NH'],
                                capture_output=True, text=True, check=True)
        assert 'spad.next.exe' not in result.stdout.lower(), 'Close SPAD before installing'
    folders = ([Path.home() / 'Documents/SPAD.neXt/profiles'] if installed else
               [ROOT / 'profiles', ROOT / 'portable-setup/profiles'])
    backup = ROOT / 'backups' / ('drone-precision-' + time.strftime('%Y%m%d-%H%M%S'))
    for folder in folders:
        for path in folder.glob('*.xml'):
            raw = path.read_bytes()
            text = raw.decode('utf-8-sig')
            updated = patch(text)
            assert patch(updated) == updated
            saved = backup / folder.parent.name / path.name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8'))
            print(f'Set six drone precision actions: {path.name}')


if __name__ == '__main__':
    main()
