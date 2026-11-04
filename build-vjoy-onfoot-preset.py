"""Build "KestrelAir SPAD Cameras v2.2" from the vJoy preset MSFS currently has selected ("Look").

Problem (2026-11-04): on foot, right MiniStick up/down turned left/right and left/right looked up/down,
while cockpit/external look was correct. SPAD sends the right stick's horizontal channel to vJoy Ry and the
vertical channel to vJoy Rz (route-thumbsticks.py). Cockpit/chase freelook use HRZ<-Ry, VRTC<-Rz and are
right. The on-foot actions were bound KEY_AXIS_PC_FPV_ROTATION_X<-Rz and _Y<-Ry, but in MSFS 2024 on foot
ROTATION_X is the turn (left/right) and ROTATION_Y is the up/down look. This swaps only those two bindings.
Everything else (cockpit, chase, drone) is copied unchanged. SPAD cannot fix this on its own: the same vJoy
axes drive cockpit look, which is already correct.

Usage: python build-vjoy-onfoot-preset.py   (writes portable-setup/KestrelAir-vJoy-GeneralControls-v2.2-OnFoot.xml)
If one on-foot direction then tests backwards, add its action to INVERT and rebuild.
"""
from pathlib import Path
import re
import sys

# The untouched "Look" preset as MSFS had it before 2026-11-04 (the live file now holds this script's output).
SOURCE = Path(__file__).resolve().parent / 'backups' / 'msfs-look-preset-20261104' / 'inputprofile_ka-look.xml'
LIVE = Path(r'C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote\inputprofile_ka-look.xml')
TARGET = Path(__file__).resolve().parent / 'portable-setup' / 'KestrelAir-vJoy-GeneralControls-v2.2-OnFoot.xml'
NAME = 'KestrelAir SPAD Cameras v2.2'
SWAP = {  # action -> (KEY Information, code) it should listen to
    'KEY_AXIS_PC_FPV_ROTATION_X': ('Joystick R-Axis Y ', '786'),  # stick left/right -> turn
    'KEY_AXIS_PC_FPV_ROTATION_Y': ('Joystick R-Axis Z ', '802'),  # stick up/down -> look up/down
}
INVERT = set()  # e.g. {'KEY_AXIS_PC_FPV_ROTATION_Y'}
# Cockpit look: user (2026-11-04) wants left/right NOT inverted, but keeps up/down inverted (VRTC stays 132).
FLAGS = {'KEY_COCKPIT_FREELOOK_HRZ_SET': 4}
# Drone tilt for the Star Citizen-style main sticks (drone-sticks.py): right stick Y -> vJoy Rz -> pitch,
# right stick X -> vJoy Dial (MSFS "Slider Y", 0x212) -> roll. Both were unbound in "Look".
BIND = {'DRONE_AXIS_ROTATION_X': ('Joystick R-Axis Z ', '802'),
        'DRONE_AXIS_ROTATION_Z': ('Slider Y', '530')}


def main():
    raw = SOURCE.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig')
    text, n = re.subn(r'(<FriendlyName[^>]*>)[^<]*(</FriendlyName>)', rf'\g<1>{NAME}\g<2>', text, count=1)
    assert n == 1, 'FriendlyName not found'
    for action, (info, code) in SWAP.items():
        pat = re.compile(r'(<Action ActionName="%s"[^>]*?Flag=")(\d+)("[^>]*>\s*<Primary>\s*<KEY Information=")'
                         r'[^"]*(">)\d+(</KEY>)' % action)
        flag = 132 if action in INVERT else 4
        text, n = pat.subn(lambda m: f'{m.group(1)}{flag}{m.group(3)}{info}{m.group(4)}{code}{m.group(5)}', text)
        assert n == 1, f'{action}: expected one bound action, found {n}'
    for action, flag in FLAGS.items():
        text, n = re.subn(r'(<Action ActionName="%s"[^>]*?Flag=")\d+(">\s*<Primary>)' % action,
                          rf'\g<1>{flag}\g<2>', text)
        assert n == 1, f'{action}: expected one bound action, found {n}'
    nl = '\r\n' if '\r\n' in text else '\n'
    for action, (info, code) in BIND.items():
        bound = (f'<Action ActionName="{action}" ValueEvent="0.000000" Delay="0.000000" Flag="4">{nl}'
                 f'\t\t\t<Primary>{nl}\t\t\t\t<KEY Information="{info}">{code}</KEY>{nl}\t\t\t</Primary>{nl}\t\t</Action>')
        text, n = re.subn(r'<Action ActionName="%s" ValueEvent="[^"]*" Delay="[^"]*" Flag="\d+"/>' % action,
                          lambda m: bound, text)
        assert n == 1, f'{action}: expected one unbound action, found {n}'
    body = (b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8')
    TARGET.write_bytes(body)
    print(f'wrote {TARGET}')
    if '--live' in sys.argv:  # also overwrite the preset MSFS has selected, keeping its name "Look"
        LIVE.write_bytes(body.replace(f'>{NAME}<'.encode(), b'>Look<', 1))
        print(f'wrote {LIVE} (takes effect next MSFS start)')


if __name__ == '__main__':
    main()
