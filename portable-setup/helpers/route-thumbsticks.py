"""Route the WarBRD MiniSticks to the vJoy camera axes. Walking/look: left walks, right looks.
Drone: real-drone "Mode 2" (left = throttle + yaw, right = forward/back + sideways).

Measured live 2026-11-03 (right-thumbstick-watch.txt): on both grips the MiniStick's HID Rx is
horizontal (right = high) and Ry is vertical (up = high). The earlier routing had the right stick's
channels crossed, so up/down looked left/right.

MSFS preset "KestrelAir SPAD Cameras v2" on vJoy (verified in the live file 2026-11-03):
X = drone translation X (sideways), Y = drone translation Z (forward/back), Z = drone rotation Y (yaw),
Rx = drone translation Y (height), Ry = look left/right and Rz = look up/down (cockpit, external, on foot).

    Grip   MiniStick axis       vJoy targets           Result
    Right  Rx (horizontal)      Ry 0x34, X 0x30        look left/right; drone slides sideways
    Right  Ry (vertical)        Rz 0x35, Y 0x31        look up/down;    drone forward/back
    Left   Rx (horizontal)      Z  0x32                drone yaw        (A/D walking keys unchanged)
    Left   Ry (vertical)        Rx 0x33                drone climb/descend (W/S walking keys unchanged)

Only the VJOY_AXIS definitions inside those four events are replaced; the left stick's walking-key
definitions stay as they are. Close SPAD first. Idempotent.
Usage: python route-thumbsticks.py <profile.xml> [...]
"""
from pathlib import Path
import re
import sys

ROUTES = {  # (DeviceIndex, BoundTo) -> vJoy HID usages
    (0, 'RX_AXIS'): (0x34, 0x30),
    (0, 'RY_AXIS'): (0x35, 0x31),
    (1, 'RX_AXIS'): (0x32,),
    (1, 'RY_AXIS'): (0x33,),
}
DEVICE_RE = r'(<Device VendorID="0x3344" ProductID="0x03F5"[^>]*DeviceIndex="{idx}"[^>]*>)(.*?)(</Device>)'
VJOY_ONLY_DEF = re.compile(
    r'\n[ \t]*<EventDefinition Trigger="VALUE">\s*<EventActions>\s*'
    r'(?:<EventActionVirtualJoyStick[^>]*JoystickAction="VJOY_AXIS"[^>]*/>\s*)+'
    r'</EventActions>\s*</EventDefinition>', re.S)


def vjoy_def(targets, indent):
    lines = ['<EventDefinition Trigger="VALUE">', '  <EventActions>']
    lines += [f'    <EventActionVirtualJoyStick JoystickAction="VJOY_AXIS" JoystickNumber="1" '
              f'JoystickTarget="{t}" JoystickMode="RESPONSECURVE" />' for t in targets]
    lines += ['  </EventActions>', '</EventDefinition>']
    return ''.join('\n' + indent + l for l in lines)


def patch(text):
    for (idx, bound), targets in ROUTES.items():
        dev = re.compile(DEVICE_RE.format(idx=idx), re.S)
        m = dev.search(text)
        if not m:
            raise ValueError(f'grip {idx} not found')
        body = m.group(2)
        ev = re.search(rf'(<Event BoundTo="{bound}">\s*<EventDefinitions>)(.*?)(\n([ \t]*)</EventDefinitions>)', body, re.S)
        if not ev:
            raise ValueError(f'grip {idx} has no {bound} event')
        defs = VJOY_ONLY_DEF.sub('', ev.group(2))
        indent = ev.group(4) + '  '
        new_event = ev.group(1) + defs + vjoy_def(targets, indent) + ev.group(3)
        body = body[:ev.start()] + new_event + body[ev.end():]
        text = text[:m.start(2)] + body + text[m.end(2):]
    return text


def main():
    for name in sys.argv[1:]:
        path = Path(name)
        raw = path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        crlf = '\r\n' in text
        new = patch(text.replace('\r\n', '\n'))
        if crlf:
            new = new.replace('\n', '\r\n')
        path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
        print(f'{path}: thumbsticks routed')


if __name__ == '__main__':
    main()
