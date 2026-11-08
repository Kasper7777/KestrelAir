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
# Grip wheel up / down -> L:KA_CABIN_H +1 / -1. ka-walk-leds turns that into Shift+E / Shift+Q
# (KEY_COCKPIT_CAMERA_HEIGHT_INC / _DEC, sim defaults in Keyboard_2024_Transversal.xml) held for 150 ms.
WHEEL = {'BUTTON_22': 1, 'BUTTON_21': -1}
GROUND = 'SIMCONNECT:SIM ON GROUND'
ONFOOT_ALLOW = [(GROUND,1,'Equals'),(CAM,3,'Unequal'),(WALK,1,'Unequal')]
ONFOOT_RELEASE = [(GROUND,1,'Unequal'),(CAM,3,'Equals'),(WALK,1,'Equals')]
ONFOOT_RELEASE_KEYS = [(src,str(val),cmp) for src,val,cmp in ONFOOT_RELEASE]

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
                axis=bound[:2]
                stick='PROFILE:KA_STICK1_'+axis
                letters=('A','D') if axis=='RX' else ('S','W')
                for d in list(defs):
                    targets=[a.get('TargetDataDefinition','') for a in d.findall('s:EventActions/*',N)]
                    sources={(c.get('ConditionValueSource'),c.get('ConditionTargetValue'),c.get('ConditionComparator','Equals')) for c in d.iter('{'+NS+'}EventCondition')}
                    presses=[k for k in d.findall('.//s:EventActionKeyboard',N) if k.get('MacroType')!='RELEASE']
                    # Our own definitions (old keyboard cabin walk, LVAR zones, on-foot safety releases): rebuilt below.
                    if any(t.startswith(('PROFILE:KA_CABIN_','LVAR:KA_CABIN_')) for t in targets): defs.remove(d)
                    elif stick in targets and not presses and sources & set(ONFOOT_RELEASE_KEYS): defs.remove(d)
                    elif presses:
                        # On-foot walking sends BARE W/A/S/D, which are aileron/elevator keys in the air. Only allow
                        # it on the ground, outside pink mode, never in the cockpit (2), outside (3) or drone (4) views.
                        for src,val,cmp in ONFOOT_ALLOW: condition(d,src,val,cmp)
                # Release any held on-foot key as soon as one of those guards stops holding.
                for src,val,cmp in ONFOOT_RELEASE:
                    d,a=definition(defs,conds=[(stick,0,'Unequal'),(src,val,cmp)])
                    sub(a,'EventActionChangeValue',TargetDataDefinition=stick,Value=0)
                    key(a,'RELEASE',*letters)
                # Pink-mode cabin walk: SPAD only records the MiniStick zone; ka-walk-leds presses Shift+key safely.
                lvar='LVAR:KA_CABIN_'+('X' if axis=='RX' else 'Y')
                for zone,conds in [(-1,[('EVENT:VALUE',12000,'Less')]),(1,[('EVENT:VALUE',48000,'Greater')]),
                                   (0,[('EVENT:VALUE',12000,'GreaterOrEqual'),('EVENT:VALUE',48000,'LessOrEqual')])]:
                    d,a=definition(defs,conds=conds+[(lvar,zone,'Unequal')])
                    sub(a,'EventActionChangeValue',TargetDataDefinition=lvar,Value=zone)
        # Pink mode in the cockpit camera (CAMERA STATE 2): a wheel click asks ka-walk-leds for one camera-height
        # step (L:KA_CABIN_H = +1 up / -1 down) instead of the ATC reply menus. Pink mode in any other view: nothing.
        # Drone mode (CAMERA STATE 4) keeps the wheel on drone speed.
        for event in events:
            hid=event.get('BoundTo')
            if hid not in WHEEL: continue
            defs=event.find('s:EventDefinitions',N)
            for d in list(defs):
                targets=[a.get('TargetDataDefinition','') for a in d.findall('s:EventActions/*',N)]
                if d.find('.//s:EventActionKeyboard',N) is not None or 'LVAR:KA_CABIN_H' in targets: defs.remove(d)
                elif d.find('.//s:EventActionCommand',N) is not None: condition(d,WALK,1,'Unequal')
            d,a=definition(defs,'PRESS',[(WALK,1,'Equals'),(CAM,2,'Equals')])
            sub(a,'EventActionChangeValue',TargetDataDefinition='LVAR:KA_CABIN_H',Value=WHEEL[hid])
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
