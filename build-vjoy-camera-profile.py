"""Build the camera-only General Controls preset from this MSFS installation's export."""
from pathlib import Path
import re
import xml.etree.ElementTree as E

folder = Path(__file__).resolve().parent / 'portable-setup'
raw = (folder / 'vjoy-camera-empty.xml').read_text(encoding='utf-8-sig')
root = E.fromstring('<Root>' + re.sub(r'<\?xml[^>]*\?>', '', raw) + '</Root>')
root.find('FriendlyName').text = 'KestrelAir SPAD Cameras v2'
device = root.find('Device')
for axis in device.findall('Axes/Axis'):
    axis.set('AxisSensitivy', '0')
    axis.set('AxisSensitivyMinus', '0')
    axis.set('AxisDeadZone', '6')

# Native joystick input IDs: linear XYZ and rotational XYZ, respectively.
axes = {'X': (1026, 'Joystick L-Axis X '), 'Y': (1042, 'Joystick L-Axis Y '),
        'Z': (1058, 'Joystick L-Axis Z '), 'rX': (770, 'Joystick R-Axis X '),
        'rY': (786, 'Joystick R-Axis Y '), 'rZ': (802, 'Joystick R-Axis Z ')}
bindings = [
    ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_X', 'X', False),
    ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Z', 'Y', False),
    ('DRONE_GLOBAL', 'DRONE_AXIS_ROTATION_Y', 'Z', False),
    ('DRONE_GLOBAL', 'DRONE_AXIS_TRANSLATION_Y', 'rX', False),
    ('COCKPIT_GLOBAL_CAMERA', 'KEY_COCKPIT_FREELOOK_HRZ_SET', 'rY', False),
    ('COCKPIT_GLOBAL_CAMERA', 'KEY_COCKPIT_FREELOOK_VRTC_SET', 'rZ', True),
    ('EXTERNAL_CAMERA', 'KEY_CHASE_FREELOOK_HRZ_SET', 'rY', False),
    ('EXTERNAL_CAMERA', 'KEY_CHASE_FREELOOK_VRTC_SET', 'rZ', True),
    ('PLAYER_CHARACTER_FPV', 'KEY_AXIS_PC_FPV_ROTATION_Y', 'rY', False),
    ('PLAYER_CHARACTER_FPV', 'KEY_AXIS_PC_FPV_ROTATION_X', 'rZ', True),
]
assert not device.findall('.//Primary'), 'Expected an empty exported camera template'
for context, name, axis, invert in bindings:
    action = device.find(f'Context[@ContextName="{context}"]/Action[@ActionName="{name}"]')
    assert action is not None, name
    action.set('Flag', '132' if invert else '4')
    key_id, label = axes[axis]
    E.SubElement(E.SubElement(action, 'Primary'), 'KEY', Information=label).text = str(key_id)
assert len(device.findall('.//Primary')) == len(bindings)
result = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(E.tostring(x, encoding='unicode') for x in root)
target = folder / 'KestrelAir-vJoy-GeneralControls.xml'
target.write_text(result, encoding='utf-8')
print(f'Prepared {len(bindings)} camera bindings: {target}')
