"""Build the KestrelAir vJoy preset for MSFS from the live "KestrelAir SPAD Cameras v2" preset.

Everything already working is copied unchanged (look bindings and their inversion flags, confirmed
2026-11-03). On top of that:

  * Always: camera zoom on vJoy Slider X (MSFS input 514, format copied from Asobo's own presets).
    SPAD feeds Slider X from the CM3 throttle's Rz lever (bind-sticks-and-pedals.py).
        COCKPIT_GLOBAL_CAMERA  KEY_COCKPIT_CAMERA_ZOOM_AXIS
        EXTERNAL_CAMERA        KEY_CHASE_ZOOM_AXIS
  * With --fpv: FPV drone layout instead of Mode 2 (see thumbstick-keys.md):
        Rx (left up/down)   DRONE_AXIS_TRANSLATION_Z  throttle, along the view
        Y  (right up/down)  DRONE_AXIS_ROTATION_X     pitch
        X  (right l/r)      DRONE_AXIS_ROTATION_Z     roll
        Z  (left l/r)       DRONE_AXIS_ROTATION_Y     yaw (unchanged)

Outputs (import in MSFS: Controls > vJoy Device > General controls > gear > Import, then select it):
    portable-setup/KestrelAir-vJoy-GeneralControls-v2.1-Zoom.xml   "KestrelAir SPAD Cameras v2.1 Zoom"
    portable-setup/KestrelAir-vJoy-GeneralControls-v3-FPV.xml      "KestrelAir SPAD Cameras v3 FPV" (--fpv)
Flag 4 = axis, 132 = inverted axis; add an action to INVERT if it tests backwards and rebuild.
Usage: python build-vjoy-preset.py [--fpv]
"""
from pathlib import Path
import re
import sys

SOURCE = Path(r'C:\Program Files (x86)\Steam\userdata\86580337\2537590\remote'
              r'\inputprofile_kestrelair-vjoy-generalcontrols-v2.xml')
OUT = Path(__file__).resolve().parent / 'portable-setup'
AXES = {'X': (1026, 'Joystick L-Axis X '), 'Y': (1042, 'Joystick L-Axis Y '), 'Z': (1058, 'Joystick L-Axis Z '),
        'rX': (770, 'Joystick R-Axis X '), 'rY': (786, 'Joystick R-Axis Y '), 'rZ': (802, 'Joystick R-Axis Z '),
        'SliderX': (514, 'Slider X')}
ZOOM = [('COCKPIT_GLOBAL_CAMERA', 'KEY_COCKPIT_CAMERA_ZOOM_AXIS', 'SliderX'),
        ('EXTERNAL_CAMERA', 'KEY_CHASE_ZOOM_AXIS', 'SliderX')]
FPV_UNBIND = [('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_X'), ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Y'),
              ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Z')]
FPV_BIND = [('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Z', 'rX'),
            ('DRONE_GLOBAL', 'DRONE_AXIS_ROTATION_X', 'Y'),
            ('DRONE', 'DRONE_AXIS_ROTATION_Z', 'X')]
INVERT = set()  # e.g. {'KEY_COCKPIT_CAMERA_ZOOM_AXIS'} if the lever zooms the wrong way


def action_re(context, name):
    return re.compile(rf'(<Context ContextName="{context}">.*?)(\t*<Action ActionName="{name}"[^>]*?(?:/>|>.*?</Action>))', re.S)


def opening_tag(element):
    return re.match(r'\t*<Action [^>]*?(?=/?>)', element).group(0)


def unbind(text, context, name):
    m = action_re(context, name).search(text)
    assert m, name
    tag = re.sub(r'Flag="\d+"', 'Flag="2"', opening_tag(m.group(2)))
    return text[:m.start(2)] + tag + '/>' + text[m.end(2):]


def bind(text, context, name, axis):
    m = action_re(context, name).search(text)
    assert m, name
    indent = re.match(r'\t*', m.group(2)).group(0)
    tag = re.sub(r'Flag="\d+"', 'Flag="%d"' % (132 if name in INVERT else 4), opening_tag(m.group(2)))
    key_id, label = AXES[axis]
    block = (f'{tag}>\n{indent}\t<Primary>\n{indent}\t\t<KEY Information="{label}">{key_id}</KEY>\n'
             f'{indent}\t</Primary>\n{indent}</Action>')
    return text[:m.start(2)] + block + text[m.end(2):]


def main():
    fpv = '--fpv' in sys.argv
    name, target = (('KestrelAir SPAD Cameras v3 FPV', 'KestrelAir-vJoy-GeneralControls-v3-FPV.xml') if fpv else
                    ('KestrelAir SPAD Cameras v2.1 Zoom', 'KestrelAir-vJoy-GeneralControls-v2.1-Zoom.xml'))
    text = SOURCE.read_text(encoding='utf-8')
    text = re.sub(r'(<FriendlyName[^>]*>)[^<]*', lambda m: m.group(1) + name, text, count=1)
    text = re.sub(r'(<FriendlyName[^>]*?)Locked="true"', r'\1Locked="false"', text, count=1)  # editable in MSFS
    for context, action, axis in ZOOM:
        text = bind(text, context, action, axis)
    if fpv:
        for context, action in FPV_UNBIND:
            text = unbind(text, context, action)
        for context, action, axis in FPV_BIND:
            text = bind(text, context, action, axis)
    (OUT / target).write_text(text, encoding='utf-8')
    print('wrote', OUT / target)


if __name__ == '__main__':
    main()
