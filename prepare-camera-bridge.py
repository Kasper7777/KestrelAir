"""Stage SPAD vJoy routes; activate only after native camera mappings are verified."""
from pathlib import Path
import copy
import xml.etree.ElementTree as E

base = Path(__file__).resolve().parent
out = base / 'portable-setup' / 'camera-profiles-pending'
out.mkdir(parents=True, exist_ok=True)
ns = 'http://www.fsgs.com/SPAD'
n = {'s': ns}
E.register_namespace('', ns)
def tag(x): return '{'+ns+'}'+x
def output(actions, usage):
    action = E.SubElement(actions, tag('EventActionVirtualJoyStick'), JoystickAction='VJOY_AXIS', JoystickNumber='1', JoystickTarget=str(usage))
    E.SubElement(action, tag('Parameter'), Type='Exp', Value='Round(Min(60000, Max(0, [EVENT:VALUE])) * 32767 / 60000, 0)')

for file in (base/'profiles').glob('*.xml'):
    root = E.parse(file).getroot()
    for d in root.findall('s:Devices/s:Device', n):
        if d.get('ProductID') != '0x03F5': continue
        index = int(d.get('DeviceIndex'))
        for axis in ['RX_AXIS','RY_AXIS']:
            event = d.find('.//s:Event[@BoundTo="'+axis+'"]', n)
            if index == 0:
                # Right grip: drone strafe/forward plus separate contextual look axes.
                for child in list(event): event.remove(child)
                defs = E.SubElement(event, tag('EventDefinitions'))
            else:
                # Left grip: keep existing walking keys, excluded from drone mode.
                defs = event.find('s:EventDefinitions', n)
            actions = E.SubElement(E.SubElement(defs, tag('EventDefinition'), Trigger='VALUE'), tag('EventActions'))
            if index == 0:
                for usage in ([0x30,0x34] if axis=='RX_AXIS' else [0x31,0x35]): output(actions, usage)
            else:
                output(actions, 0x32 if axis=='RX_AXIS' else 0x33)
    E.indent(root, space='  ')
    E.ElementTree(root).write(out/file.name, encoding='utf-8')
    assert len(root.findall('.//s:EventActionVirtualJoyStick', n)) == 6
    print('Staged camera routes:', file.name)
