"""SPAD cabin camera mode (pink): either grip flip lever DOWN disables both flight sticks, and the grip wheels
raise/lower the cockpit camera. The lever state itself is read by ka-walk-leds.exe (L:KA_WALK_MODE)."""
from pathlib import Path
import copy
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
NS = 'http://www.fsgs.com/SPAD'
N = {'s': NS}
E.register_namespace('', NS)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
WALK = 'LVAR:KA_WALK_MODE'
CAM = 'SIMCONNECT:CAMERA STATE'
HELPER = ROOT / '.tools/ka-drone-leds/ka-walk-leds.exe'
# Grip wheel up / down -> Shift+E / Shift+Q = KEY_COCKPIT_CAMERA_HEIGHT_INC / _DEC (stand up / crouch), from the
# sim defaults in Packages/fs-input-profiles/.../Keyboard_2024_Transversal.xml. Not Shift+R/F: Shift+F is
# KEY_COCKPIT_QUICKVIEW4 (looks left) and Shift+R does nothing in the cockpit.
WHEEL = {'BUTTON_22': 'E', 'BUTTON_21': 'Q'}
WHEEL_HOLD_MS = 150  # each wheel click holds the key this long; MSFS moves the camera while it is held

def sub(parent, name, **attrs):
    return E.SubElement(parent, '{'+NS+'}'+name, **{k: str(v) for k,v in attrs.items()})

def condition(definition, source, value, comparator='Equals'):
    conditions = definition.find('s:EventConditions', N)
    if conditions is None:
        conditions = E.Element('{'+NS+'}EventConditions')
        definition.insert(0, conditions)
    if any(c.get('ConditionValueSource')==source and c.get('ConditionTargetValue')==str(value)
           and c.get('ConditionComparator','Equals')==comparator for c in conditions): return
    sub(conditions, 'EventCondition', ConditionValueSource=source, ConditionTargetValue=value,
        ConditionComparator=comparator)

def key(actions, mode, *keys):
    a=sub(actions,'EventActionKeyboard',MacroType=mode,TargetWindow='__ACTIVEWINDOW__')
    macro=sub(a,'KeyboardMacro',Duration=20,Repeat=1,Pause=25)
    ks=sub(macro,'Keys')
    for k in keys: sub(ks,'Keys').text=k

def definition(defs, trigger='VALUE', conds=()):
    d=sub(defs,'EventDefinition',Trigger=trigger)
    for src,val,cmp in conds: condition(d,src,val,cmp)
    return d,sub(d,'EventActions')

def patch(root):
    grips=[d for d in root.findall('./s:Devices/s:Device',N) if d.get('ProductID')=='0x03F5']
    if len(grips)!=2: return False
    variables=root.find('s:Variables',N)
    if variables is None:
        variables=E.Element('{'+NS+'}Variables'); root.insert(0,variables)
    for axis in ('RX','RY'):
        name='PROFILE:KA_CABIN_'+axis
        v=next((v for v in variables if v.get('Name')==name),None)
        if v is None: v=sub(variables,'Variable',Name=name,Value=0,ValueType='Decimal')
        v.set('Value','0')
    for dev in grips:
        events=dev.find('s:DevicePage/s:Events',N)
        for event in events:
            bound=event.get('BoundTo')
            if bound in ('X_AXIS','Y_AXIS','RZ_AXIS'):
                for d in event.findall('s:EventDefinitions/s:EventDefinition',N):
                    condition(d,WALK,1,'Unequal')
            if dev.get('DeviceIndex')=='1' and bound in ('RX_AXIS','RY_AXIS'):
                defs=event.find('s:EventDefinitions',N)
                # Replace our camera definitions; retain the existing on-foot and drone controls.
                for d in list(defs):
                    targets=[a.get('TargetDataDefinition','') for a in d.findall('s:EventActions/*',N)]
                    if any(t.startswith('PROFILE:KA_CABIN_') for t in targets): defs.remove(d)
                    elif d.find('.//s:EventActionKeyboard',N) is not None: condition(d,CAM,2,'Unequal')
                axis=bound[:2]
                state='PROFILE:KA_CABIN_'+axis
                other='PROFILE:KA_CABIN_'+('RY' if axis=='RX' else 'RX')
                low,high=('A','D') if axis=='RX' else ('S','W')
                base=[(WALK,1,'Equals'),(CAM,2,'Equals')]
                for zone,compare,threshold,pressed,released in [(-1,'Less',12000,low,high),(1,'Greater',48000,high,low)]:
                    d,a=definition(defs,conds=base+[('EVENT:VALUE',threshold,compare),(state,zone,'Unequal')])
                    sub(a,'EventActionChangeValue',TargetDataDefinition=state,Value=zone)
                    key(a,'RELEASE',released)
                    key(a,'PRESS','LShiftKey',pressed)
                d,a=definition(defs,conds=[('EVENT:VALUE',12000,'GreaterOrEqual'),('EVENT:VALUE',48000,'LessOrEqual'),(state,0,'Unequal')])
                sub(a,'EventActionChangeValue',TargetDataDefinition=state,Value=0)
                key(a,'RELEASE',low,high)
                # Release Shift only when the other axis is centred, to allow diagonal movement.
                d,a=definition(defs,conds=[('EVENT:VALUE',12000,'GreaterOrEqual'),('EVENT:VALUE',48000,'LessOrEqual'),(other,0,'Equals')])
                # Use a state guard to avoid flooding key-up macros at rest.
                condition(d,'PROFILE:KA_CABIN_SHIFT',1)
                sub(a,'EventActionChangeValue',TargetDataDefinition='PROFILE:KA_CABIN_SHIFT',Value=0)
                key(a,'RELEASE','LShiftKey')
                for d in defs:
                    for a in d.findall('s:EventActions',N):
                        if any(x.get('MacroType')=='PRESS' for x in a.findall('s:EventActionKeyboard',N)) and any(x.get('TargetDataDefinition')==state for x in a):
                            sub(a,'EventActionChangeValue',TargetDataDefinition='PROFILE:KA_CABIN_SHIFT',Value=1)
                for source,value in [(WALK,1),(CAM,2)]:
                    d,a=definition(defs,conds=[(source,value,'Unequal'),(state,0,'Unequal')])
                    sub(a,'EventActionChangeValue',TargetDataDefinition=state,Value=0)
                    sub(a,'EventActionChangeValue',TargetDataDefinition='PROFILE:KA_CABIN_SHIFT',Value=0)
                    key(a,'RELEASE',low,high,'LShiftKey')
        # Pink mode in the cockpit camera (CAMERA STATE 2): the grip wheel raises/lowers the camera height instead
        # of driving the ATC reply menus. Pink mode in any other view: the wheel does nothing. Drone mode
        # (CAMERA STATE 4) keeps the wheel on drone speed.
        for event in events:
            hid=event.get('BoundTo')
            if hid not in WHEEL: continue
            defs=event.find('s:EventDefinitions',N)
            for d in list(defs):
                if d.find('.//s:EventActionKeyboard',N) is not None: defs.remove(d)
                elif d.find('.//s:EventActionCommand',N) is not None: condition(d,WALK,1,'Unequal')
            d,a=definition(defs,'PRESS',[(WALK,1,'Equals'),(CAM,2,'Equals')])
            a=sub(a,'EventActionKeyboard',MacroType='PRESSANDRELEASE',TargetWindow='__ACTIVEWINDOW__')
            ks=sub(sub(a,'KeyboardMacro',Duration=WHEEL_HOLD_MS,Repeat=1,Pause=25),'Keys')
            for k in ('LShiftKey',WHEEL[hid]): sub(ks,'Keys').text=k
        # Flip lever edges release any held camera keys and start the shared lighting/state helper.
        for old in list(events):
            if old.get('BoundTo')=='BUTTON_2': events.remove(old)
        event=sub(events,'Event',BoundTo='BUTTON_2'); defs=sub(event,'EventDefinitions')
        for trigger in ('PRESS','RELEASE'):
            d,a=definition(defs,trigger)
            key(a,'RELEASE','W','A','S','D','LShiftKey')
            for axis in ('RX','RY','SHIFT'):
                sub(a,'EventActionChangeValue',TargetDataDefinition='PROFILE:KA_CABIN_'+axis,Value=0)
            command=sub(a,'EventActionCommand')
            sub(command,'Parameter',Value='SPAD_neXt.RunProgram')
            sub(command,'Parameter1',Value=HELPER)
    if not any(v.get('Name')=='PROFILE:KA_CABIN_SHIFT' for v in variables):
        sub(variables,'Variable',Name='PROFILE:KA_CABIN_SHIFT',Value=0,ValueType='Decimal')
    for param in root.findall('.//s:Parameter1',N):
        value=param.get('Value','')
        if value.endswith('ka-drone-leds.exe'): param.set('Value',str(HELPER))
    return True

def main():
    installed='--installed' in sys.argv
    if installed:
        status=subprocess.run(['tasklist','/FI','IMAGENAME eq SPAD.neXt.exe','/NH'],capture_output=True,text=True)
        if 'spad.next.exe' in status.stdout.lower(): raise SystemExit('Exit SPAD completely before installation.')
    folders=[Path.home()/'Documents/SPAD.neXt/profiles'] if installed else [ROOT/'profiles',ROOT/'portable-setup/profiles']
    backup=ROOT/'backups'/('cabin-camera-'+time.strftime('%Y%m%d-%H%M%S'))
    for folder in folders:
        for path in folder.glob('*.xml'):
            tree=E.parse(path)
            if not patch(tree.getroot()): continue
            target=backup/folder.parent.name/path.name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
            E.indent(tree,space='  '); tree.write(path,encoding='utf-8')
            print('Cabin mode:',path)

if __name__=='__main__': main()
