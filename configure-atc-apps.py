"""Point vPilot and BeyondATC at the vJoy buttons that SPAD drives from the WarBRD grips.

    vJoy button 1 -> vPilot push-to-talk          (grip top push button)
    vJoy button 2 -> BeyondATC PushToTalk1        (grip bottom push button)
    vJoy button 3 -> BeyondATC DoAction1          (grip trigger / flip trigger = auto respond)
    vJoy button 4 -> BeyondATC TabKey             (grip wheel up/down = next dialogue option)
    vJoy button 5 -> BeyondATC EnterKey           (grip wheel press = send selected option)

Both grips report the same USB name since the 2026-10-31 firmware repair, so neither app can
tell them apart; routing through vJoy gives each app one stable device to listen to.

Close vPilot and BeyondATC first: both write their settings back on exit.
Usage: python configure-atc-apps.py [--vjoy-guid GUID]
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import uuid
import winreg

VPILOT_CONFIG = Path.home() / 'AppData/Local/vPilot/vPilotConfig.xml'
BATC_KEY = r'Software\Skirmish Mode Games, Inc\BeyondATC'
BATC_VALUE = 'KeyBindings_h731465248'
VJOY_UNITY_DEVICE = '/Shaul Eizikovich vJoy - Virtual Joystick'
BATC_ROUTES = {'General/PushToTalk1': 2, 'General/DoAction1': 3,
               'General/TabKey': 4, 'General/EnterKey': 5}
VPILOT_BUTTON_INDEX = 0  # vPilot stores zero-based button index; 0 = vJoy button 1


def running(names):
    out = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    return [n for n in names if n.lower() in out]


def vjoy_directinput_guid() -> str:
    path = (r'System\CurrentControlSet\Control\MediaProperties\PrivateProperties'
            r'\DirectInput\VID_1234&PID_BEAD\Calibration\0')
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
        raw, _ = winreg.QueryValueEx(k, 'GUID')
    return str(uuid.UUID(bytes_le=bytes(raw)))


def configure_vpilot(guid: str) -> None:
    text = VPILOT_CONFIG.read_text(encoding='utf-8-sig')
    line = (f'<PTTConfiguration DeviceType="Joystick" Name="vJoy Device" '
            f'JoystickGuidString="{guid}" ButtonOrKey="{VPILOT_BUTTON_INDEX}" />')
    new, n = re.subn(r'<PTTConfiguration\b[^>]*/>', line, text)
    if n != 1:
        sys.exit('vPilotConfig.xml: PTTConfiguration element not found; not changed')
    VPILOT_CONFIG.write_text(new, encoding='utf-8')
    print('vPilot PTT ->', line)


def configure_beyondatc() -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, BATC_KEY, 0,
                        winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
        try:
            raw, kind = winreg.QueryValueEx(k, BATC_VALUE)
            data = json.loads(bytes(raw).rstrip(b'\0'))
        except FileNotFoundError:
            kind, data = winreg.REG_BINARY, {'bindings': []}
        bindings = data.setdefault('bindings', [])
        for action, button in BATC_ROUTES.items():
            path = f'{VJOY_UNITY_DEVICE}/button{button}'
            entry = next((b for b in bindings if b.get('action') == action), None)
            if entry is None:
                entry = {'action': action, 'id': str(uuid.uuid4()),
                         'interactions': 'null', 'processors': 'null'}
                bindings.append(entry)
            entry['path'] = path
            print(f'BeyondATC {action} -> {path}')
        blob = json.dumps(data, separators=(',', ':')).encode('utf-8') + b'\0'
        winreg.SetValueEx(k, BATC_VALUE, 0, kind, blob)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--vjoy-guid', help='override the vJoy DirectInput instance GUID')
    ap.add_argument('--skip-vpilot', action='store_true', help='leave vPilot untouched (it may stay open)')
    args = ap.parse_args()
    busy = running(['BeyondATC.exe'] + ([] if args.skip_vpilot else ['vPilot.exe']))
    if busy:
        sys.exit('Close these first (they overwrite settings on exit): ' + ', '.join(busy))
    if not args.skip_vpilot:
        configure_vpilot(args.vjoy_guid or vjoy_directinput_guid())
    configure_beyondatc()


if __name__ == '__main__':
    main()
