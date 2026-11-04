"""Drone mode on the main WarBRD sticks, laid out like the user's Star Citizen twin-stick setup (2026-11-04).

When MSFS is in the drone camera (SIMCONNECT:CAMERA STATE = 4, toggled by throttle B4), the stick bases and
twists drive the drone through vJoy, and stop moving the aircraft's ailerons/elevator. Outside drone mode the
existing flight-control definitions run exactly as before; they just gain a "CAMERA STATE Unequal 4" condition.

Star Citizen (SC_Bak layout): left X = strafe lateral, left Y = strafe longitudinal, left twist = strafe
vertical; right stick = SC default pitch (Y), roll (X), yaw (twist).

    Grip   Axis          vJoy (HID)      MSFS drone action (vJoy preset)
    Left   X             X   0x30        DRONE_AXIS_TRANSLATION_X  slide left/right
    Left   Y             Y   0x31        DRONE_AXIS_TRANSLATION_Z  forward/back
    Left   Rz (twist)    Rx  0x33        DRONE_AXIS_TRANSLATION_Y  up/down
    Right  Y             Rz  0x35        DRONE_AXIS_ROTATION_X     pitch  (Rz is also cockpit look up/down,
                                                                           which is inactive in drone mode)
    Right  X             Z   0x32        DRONE_AXIS_ROTATION_Y     yaw   (user wants X = yaw, twist = roll)
    Right  Rz (twist)    Dial 0x37       DRONE_AXIS_ROTATION_Z     roll  (preset flag 132 = inverted)

The mini-sticks keep their own drone axes (they share these vJoy axes; whichever moves last wins).
Close SPAD first. Idempotent: re-running replaces the drone definitions it added.
Usage: python drone-sticks.py <profile.xml> [...]
"""
from pathlib import Path
import importlib.util
import re
import sys

_spec = importlib.util.spec_from_file_location('bsp', Path(__file__).resolve().parent / 'bind-sticks-and-pedals.py')
bsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsp)

ROUTES = {0: {'X_AXIS': 0x32, 'Y_AXIS': 0x35, 'RZ_AXIS': 0x37},  # right: X = yaw, twist = roll (user, 2026-11-04)
          1: {'X_AXIS': 0x30, 'Y_AXIS': 0x31, 'RZ_AXIS': 0x33}}
CAM = 'SIMCONNECT:CAMERA STATE'
DEF_RE = re.compile(r'\n[ \t]*<EventDefinition\b.*?</EventDefinition>', re.S)


def condition(comparator, indent):
    return (f'{indent}<EventCondition ConditionComparator="{comparator}" ConditionTargetValue="4" '
            f'ConditionValueSource="{CAM}" />')


# vJoy axes used by nothing but the drone in MSFS: SPAD feeds them all the time, so they sit at the stick's real
# position (centre) when drone mode starts. 2026-11-04: Dial was only written in drone mode, so it entered drone
# mode at a stale value and the drone rolled/rotated on entry.
ALWAYS = {0x37}


def drone_def(target, indent):
    cond = [] if target in ALWAYS else [
        '  <EventConditions>',
        condition('Equals', '    '),  # SPAD's comparator name (not "Equal")
        '  </EventConditions>']
    return bsp.block([
        '<EventDefinition Trigger="VALUE">',
        *cond,
        '  <EventActions>',
        f'    <EventActionVirtualJoyStick JoystickAction="VJOY_AXIS" JoystickNumber="1" '
        f'JoystickTarget="{target}" JoystickMode="RESPONSECURVE" />',
        '  </EventActions>',
        '</EventDefinition>',
    ], indent)


def is_ours(d):
    # In the X/Y/twist events, a definition whose only actions are vJoy axes is one this script added.
    return ('JoystickAction="VJOY_AXIS"' in d and 'EventActionRangedAxis' not in d
            and 'EventActionKeyboard' not in d and 'EventActionChangeValue' not in d)


def gate_plane(d):
    """Add CAMERA STATE Unequal 4 to an existing (flight-control) definition that has no camera condition."""
    if CAM in d:
        return d
    indent = re.match(r'\n([ \t]*)', d).group(1)
    if '<EventConditions>' in d:
        return re.sub(r'(\n[ \t]*)</EventConditions>',
                      lambda m: '\n' + condition('Unequal', indent + '    ') + m.group(0), d, count=1)
    return re.sub(r'(<EventDefinition\b[^>]*>)', lambda m: m.group(1) + '\n' + indent + '  <EventConditions>\n'
                  + condition('Unequal', indent + '    ') + '\n' + indent + '  </EventConditions>', d, count=1)


def grip_builder(routes):
    def build(body, indent):
        for bound, target in routes.items():
            ev = re.search(rf'(<Event BoundTo="{bound}">\s*<EventDefinitions>)(.*?)(\n[ \t]*</EventDefinitions>)',
                           body, re.S)
            if not ev:
                body += bsp.block([f'<Event BoundTo="{bound}">', '  <EventDefinitions>'], indent)
                body += drone_def(target, indent + '    ')
                body += bsp.block(['  </EventDefinitions>', '</Event>'], indent)
                continue
            defs = DEF_RE.sub(lambda m: '' if is_ours(m.group(0)) else gate_plane(m.group(0)), ev.group(2))
            def_indent = ev.group(3)[1:].replace('</EventDefinitions>', '') + '  '
            body = body[:ev.start()] + ev.group(1) + defs + drone_def(target, def_indent) + ev.group(3) + body[ev.end():]
        return body
    return build


def main():
    for name in sys.argv[1:]:
        path = Path(name)
        raw = path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        crlf = '\r\n' in text
        text = text.replace('\r\n', '\n')
        for index, routes in ROUTES.items():
            text = bsp.ensure_device(text, '0x3344', '0x03F5', index, bsp.GRIPS[index])
            text = bsp.edit_events(text, '0x3344', '0x03F5', index, grip_builder(routes))
        if crlf:
            text = text.replace('\n', '\r\n')
        path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8'))
        print(f'{path}: drone sticks set')


if __name__ == '__main__':
    main()
