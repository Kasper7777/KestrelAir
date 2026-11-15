"""Soften only the six main-stick drone actions; preserve all other profile text.

Run without arguments for repository/portable profiles, or --installed with SPAD closed.
"""
from pathlib import Path
import re
import shutil
import sys
import time
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
# WarBRD axes report 0..60000. Blend linear and cubic response: a gentle centre,
# continuous slope, unchanged direction, centre and full-scale endpoints.
T = '(Min(60000, Max(0, [EVENT:VALUE])) / 30000.0 - 1)'
EXPRESSION = f'16384 + 16383 * (0.2 * {T} + 0.8 * {T} * {T} * {T})'
DEVICE = re.compile(r'<Device\b[^>]*>.*?</Device>', re.S)
EVENT = re.compile(r'<Event BoundTo="(?:X_AXIS|Y_AXIS|RZ_AXIS)">.*?</Event>', re.S)
ACTION = re.compile(r'<EventActionVirtualJoyStick\b(?=[^>]*JoystickAction="VJOY_AXIS")'
                    r'(?=[^>]*JoystickTarget="(?:48|49|50|51|53|55)")[^>]*'
                    r'(?:/>|>.*?</EventActionVirtualJoyStick>)', re.S)


def patch(text):
    count = 0
    def device(match):
        nonlocal count
        body = match.group()
        if not re.search(r'<Device\b[^>]*ProductID="0x03F5"', body):
            return body
        def event(match):
            def action(match):
                nonlocal count
                count += 1
                old = match.group()
                head = old.split('>')[0].rstrip('/')
                head = re.sub(r'JoystickMode="[^"]*"', 'JoystickMode="CUSTOM"', head)
                return head + f'><Parameter Type="Exp" Value="{EXPRESSION}" /></EventActionVirtualJoyStick>'
            return ACTION.sub(action, match.group())
        return EVENT.sub(event, body)
    result = DEVICE.sub(device, text)
    if count != 6:
        raise ValueError(f'Expected six drone actions, found {count}')
    ET.fromstring(result)
    return result


def main():
    raise SystemExit('Disabled: these custom drone curves caused control problems and were rolled back.')
    installed = '--installed' in sys.argv
    if installed:
        status = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SPAD.neXt.exe', '/NH'],
                                capture_output=True, text=True, check=True)
        if 'spad.next.exe' in status.stdout.lower():
            raise SystemExit('Close SPAD before installing; cached profiles would overwrite changes.')
    folders = ([Path.home() / 'Documents/SPAD.neXt/profiles'] if installed else
               [ROOT / 'profiles', ROOT / 'portable-setup/profiles'])
    backup = ROOT / 'backups' / ('drone-curves-' + time.strftime('%Y%m%d-%H%M%S'))
    for folder in folders:
        for path in folder.glob('*.xml'):
            raw = path.read_bytes()
            text = raw.decode('utf-8-sig')
            updated = patch(text)
            if updated == text:
                continue
            target = backup / folder.parent.name / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')
                             + updated.encode('utf-8'))
            print(f'{path}: six drone curves softened')


if __name__ == '__main__':
    main()
