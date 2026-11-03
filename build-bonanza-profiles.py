"""Create single-engine Bonanza variants without changing the Baron source."""
from pathlib import Path
import copy
import uuid
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
NS = 'http://www.fsgs.com/SPAD'
E.register_namespace('', NS)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
N = {'s': NS}
source = Path.home() / 'Documents/SPAD.neXt/profiles/Baron - GNS 530 + TDS GTNxi 650.xml'
base = E.parse(source).getroot()
def tag(name): return '{' + NS + '}' + name
def device(root, product):
    return next(d for d in root.findall('./s:Devices/s:Device', N) if d.get('ProductID') == product)
def events(root, product): return device(root, product).find('s:DevicePage/s:Events', N)
def remove(root, product, *bounds):
    parent = events(root, product)
    for event in list(parent):
        if event.get('BoundTo') in bounds: parent.remove(event)
def replace(root, product, bound, target, value=None, expression=None, release=None):
    remove(root, product, bound)
    event = E.SubElement(events(root, product), tag('Event'), BoundTo=bound)
    defs = E.SubElement(event, tag('EventDefinitions'))
    for trigger, val in [('PRESS', value)] + ([('RELEASE', release)] if release is not None else []):
        actions = E.SubElement(E.SubElement(defs, tag('EventDefinition'), Trigger=trigger), tag('EventActions'))
        if target.startswith(('SIMCONNECT:', 'H:')):
            action = E.SubElement(actions, tag('EventActionControl'), TargetDataDefinition=target)
            if expression and trigger == 'PRESS': E.SubElement(action, tag('Parameter'), Type='Exp', Value=expression)
            elif val is not None: E.SubElement(action, tag('Parameter'), Type='Static', Value=str(val))
        else:
            attrs = {'TargetDataDefinition': target}
            if expression and trigger == 'PRESS': attrs.update(SourceType='Exp', SourceDataDefinition=expression)
            else: attrs['Value'] = str(val)
            E.SubElement(actions, tag('EventActionChangeValue'), attrs)
def single_axis(root, product, bound):
    action = device(root, product).find('.//s:Event[@BoundTo="'+bound+'"]//s:EventActionRangedAxis', N)
    options = action.find('s:Options', N)
    for opt in list(options):
        if opt.get('Key', '').startswith('OPTION'): options.remove(opt)
    E.SubElement(options, tag('Option'), Key='OPTION1', Value='True')

for variant in ['A36', 'A36TC', 'B36TP']:
    root = copy.deepcopy(base)
    # Keep the left throttle, propeller and mixture/condition levers as engine 1.
    remove(root, '0x0194', 'Y_AXIS', 'BUTTON_52', 'BUTTON_53', 'BUTTON_55', 'BUTTON_56', 'BUTTON_58', 'BUTTON_59')
    single_axis(root, '0x0194', 'X_AXIS')
    remove(root, '0x025C', 'Y_AXIS', 'RY_AXIS', *('BUTTON_'+str(i) for i in [2,4,19,20,34,35,36,43,44,45,46,47]))
    remove(root, '0x025C', *('BUTTON_'+str(i) for i in [23,24,25,26,27,28,29,30]))
    single_axis(root, '0x025C', 'X_AXIS')
    # No second engine cowl, second landing light, pressurization or door seal tests.
    remove(root, '0x025A', *('BUTTON_'+str(i) for i in [5,27,28,37,38,39,40]))
    replace(root, '0x025C', 'BUTTON_1', 'SIMCONNECT:BATTERY1_SET', expression='1 - [SIMCONNECT:ELECTRICAL MASTER BATTERY:1]')
    replace(root, '0x025C', 'BUTTON_3', 'SIMCONNECT:AVIONICS_MASTER_1_SET', expression='1 - [SIMCONNECT:AVIONICS MASTER SWITCH:1]')
    # Both Bonanza alternators remain assigned: main and standby are documented.
    for b, engine, val in [(29,1,1),(30,1,0),(31,2,1),(32,2,0)]:
        replace(root, '0x025A', 'BUTTON_'+str(b), 'SIMCONNECT:TOGGLE_ALTERNATOR'+str(engine))
        definition = events(root, '0x025A').find('s:Event[@BoundTo="BUTTON_'+str(b)+'"]/s:EventDefinitions/s:EventDefinition', N)
        conditions = E.Element(tag('EventConditions'))
        E.SubElement(conditions, tag('EventCondition'), ConditionComparator='Equals', ConditionTargetValue=str(1-val), ConditionValueSource='SIMCONNECT:GENERAL ENG MASTER ALTERNATOR:'+str(engine))
        definition.insert(0, conditions)
    replace(root, '0x025A', 'BUTTON_4', 'SIMCONNECT:COWLFLAP1_SET', expression='If([SIMCONNECT:RECIP ENG COWL FLAP POSITION:1] > 0.5, 0, 16383)')
    if variant == 'B36TP':
        remove(root, '0x025C', 'RX_AXIS', 'BUTTON_25', 'BUTTON_26')
        event = E.SubElement(events(root, '0x025C'), tag('Event'), BoundTo='RX_AXIS')
        actions = E.SubElement(E.SubElement(E.SubElement(event, tag('EventDefinitions')), tag('EventDefinition'), Trigger='VALUE'), tag('EventActions'))
        E.SubElement(actions, tag('EventActionChangeValue'), SourceType='Exp', TargetDataDefinition='LVAR:BKSQ_ConditionLever_1', SourceDataDefinition='If([LOCAL:JOY_0X33440X025C_RX_AXIS] < 10, 0, 1)')
        remove(root, '0x0194', *('BUTTON_'+str(i) for i in range(60,65)))
        replace(root, '0x0194', 'BUTTON_60', 'LVAR:var_StarterGenSwitch', 0)
        replace(root, '0x0194', 'BUTTON_61', 'LVAR:var_IgnitionSwitch', 2)
        replace(root, '0x0194', 'BUTTON_62', 'LVAR:var_IgnitionSwitch', 0)
        replace(root, '0x0194', 'BUTTON_63', 'LVAR:var_StarterGenSwitch', 0)
        replace(root, '0x0194', 'BUTTON_64', 'LVAR:var_StarterGenSwitch', 2, release=0)
        for b, val in [(14,2),(15,1),(16,0)]: replace(root, '0x025C', 'BUTTON_'+str(b), 'LVAR:var_FuelPumpSwitch', val)
        replace(root, '0x025C', 'BUTTON_6', 'H:Etm_EnterTest', 1)
        replace(root, '0x025C', 'BUTTON_25', 'LVAR:var_IceDeflectorSwitch', 1)
        replace(root, '0x025C', 'BUTTON_26', 'LVAR:var_IceDeflectorSwitch', 0)
        replace(root, '0x025A', 'BUTTON_4', 'LVAR:var_OilDoorHandle', expression='100 - [LVAR:var_OilDoorHandle]')
        replace(root, '0x025A', 'BUTTON_38', 'LVAR:var_DoorSealSwitch', expression='1 - [LVAR:var_DoorSealSwitch]')
    info = root.find('s:ProfileInformation', N)
    info.set('ProfileID', str(uuid.uuid4()))
    info.set('Version', '1.0')
    info.find('s:Description', N).text = f'Black Square Bonanza {variant}; derived from Baron GNS530/TDS650 layout. Single-engine controls. Manual-based conversion; live aircraft verification required. See bonanza-profiles.md.'
    # Catch twin-engine and Baron-only controls that must never survive conversion.
    xml = E.tostring(root, encoding='unicode')
    for forbidden in ['BKSQ_MixtureLeverPosition_2','BKSQ_IgnitionPosition_2','var_pressurization','var_PropSyncSwitch','var_FUEL_Switch_Pump_2','ENGINE_COWLFLAPS_RIGHT']:
        assert forbidden not in xml, forbidden
    if variant == 'B36TP': assert 'BKSQ_IgnitionPosition_' not in xml and 'BKSQ_MixtureLeverPosition_' not in xml
    path = ROOT / 'profiles' / f'Bonanza {variant} - GNS 530 + TDS GTNxi 650.xml'
    E.indent(root, space='  ')
    E.ElementTree(root).write(path, encoding='utf-8', xml_declaration=False)
    print('Created', path.name)
