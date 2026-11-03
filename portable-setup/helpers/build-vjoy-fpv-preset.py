"""Build the FPV-drone version of the KestrelAir vJoy preset from the live MSFS preset.

Source: the "KestrelAir SPAD Cameras v2" preset MSFS saved (inputprofile_kestrelair-vjoy-generalcontrols-v2.xml).
Everything outside the drone is copied unchanged, including the look bindings and their inversion flags
that you confirmed correct on 2026-11-03. Only the drone axes change, to an FPV layout:

    vJoy axis   SPAD feeds it from          old drone action          new drone action
    Rx          left stick up/down          translation Y (height)    DRONE_AXIS_TRANSLATION_Z (throttle: along the view)
    Z           left stick left/right       rotation Y (yaw)          unchanged
    Y           right stick up/down         translation Z (forward)   DRONE_AXIS_ROTATION_X (pitch)
    X           right stick left/right      translation X (sideways)  DRONE_AXIS_ROTATION_Z (roll, DRONE context)

Flag 4 = axis, 132 = inverted axis. INVERT below flips a drone axis if a direction tests backwards.
Writes portable-setup/KestrelAir-vJoy-GeneralControls-v3-FPV.xml for import in MSFS
(Controls > vJoy Device > General controls > gear > Import), then select "KestrelAir SPAD Cameras v3 FPV".
"""
from pathlib import Path
import re

SOURCE = Path(r'C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote'
              r'\inputprofile_kestrelair-vjoy-generalcontrols-v2.xml')
TARGET = Path(__file__).resolve().parent / 'portable-setup' / 'KestrelAir-vJoy-GeneralControls-v3-FPV.xml'
AXES = {'X': (1026, 'Joystick L-Axis X '), 'Y': (1042, 'Joystick L-Axis Y '), 'Z': (1058, 'Joystick L-Axis Z '),
        'rX': (770, 'Joystick R-Axis X '), 'rY': (786, 'Joystick R-Axis Y '), 'rZ': (802, 'Joystick R-Axis Z ')}
UNBIND = [('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_X'), ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Y'),
          ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Z')]
BIND = [  # context, action, vJoy axis
    ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Z', 'rX'),
    ('DRONE_GLOBAL', 'DRONE_AXIS_ROTATION_X', 'Y'),
    ('DRONE', 'DRONE_AXIS_ROTATION_Z', 'X'),
]
INVERT = set()  # e.g. {'DRONE_AXIS_ROTATION_X'} if pitch tests backwards


def action_re(context, name):
    return re.compile(rf'(<Context ContextName="{context}">.*?)(\t*<Action ActionName="{name}"[^>]*?(?:/>|>.*?</Action>))', re.S)


def main():
    text = SOURCE.read_text(encoding='utf-8')
    text = re.sub(r'(<FriendlyName[^>]*>)[^<]*', r'\1KestrelAir SPAD Cameras v3 FPV', text, count=1)
    text = re.sub(r'(<FriendlyName[^>]*?)Locked="true"', r'\1Locked="false"', text, count=1)  # editable in MSFS
    for context, name in UNBIND:
        m = action_re(context, name).search(text)
        assert m, name
        tag = re.match(r'\t*<Action [^>]*?(?=/?>)', m.group(2)).group(0).replace('Flag="4"', 'Flag="2"').replace('Flag="132"', 'Flag="2"')
        text = text[:m.start(2)] + tag + '/>' + text[m.end(2):]
    for context, name, axis in BIND:
        m = action_re(context, name).search(text)
        assert m, name
        indent = re.match(r'\t*', m.group(2)).group(0)
        tag = re.match(r'\t*<Action [^>]*?(?=/?>)', m.group(2)).group(0)
        tag = re.sub(r'Flag="\d+"', 'Flag="%d"' % (132 if name in INVERT else 4), tag)
        key_id, label = AXES[axis]
        block = (f'{tag}>\n{indent}\t<Primary>\n{indent}\t\t<KEY Information="{label}">{key_id}</KEY>\n'
                 f'{indent}\t</Primary>\n{indent}</Action>')
        text = text[:m.start(2)] + block + text[m.end(2):]
    TARGET.write_text(text, encoding='utf-8')
    print('wrote', TARGET)


if __name__ == '__main__':
    main()
