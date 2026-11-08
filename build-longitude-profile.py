"""Build an Asobo/Working Title Longitude profile using its live-enumerated controls."""
from pathlib import Path
import copy
import csv
import datetime
import importlib.util
import os
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('citation_helpers', ROOT / 'build-citation-x-profile.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
N, NS = c.N, c.NS
NAME = 'Citation Longitude - Asobo G5000.xml'
INSTALLED = Path.home() / 'Documents/SPAD.neXt/profiles'
CONF = Path(os.environ['APPDATA']) / 'SPAD.neXt/conf'

def control(name, value=None, expr=None):
    return ('ctl', 'B:' + name, value, expr)

def set_(name, value=None, expr=None): return control(name + '_Set', value, expr)

def switch(root, product, on, off, *names):
    c.put(root, product, f'BUTTON_{on}', c.press(*[set_(n, 1) for n in names]))
    c.put(root, product, f'BUTTON_{off}', c.press(*[set_(n, 0) for n in names]))

def toggle(root, product, button, name):
    c.put(root, product, f'BUTTON_{button}', c.press(control(name + '_Toggle')))

def nose_wheel(up):
    flc='SIMCONNECT:AUTOPILOT FLIGHT LEVEL CHANGE'
    mach='SIMCONNECT:AUTOPILOT MANAGED SPEED IN MACH'
    return [c.press(c.k('AP_MACH_VAR_DEC' if up else 'AP_MACH_VAR_INC'),conds=[c.eq(flc,1),c.eq(mach,1)]),
            c.press(c.k('AP_SPD_VAR_DEC' if up else 'AP_SPD_VAR_INC'),conds=[c.eq(flc,1),c.ne(mach,1)]),
            *c.pitch_wheel(up)[1:]]

def build():
    root = copy.deepcopy(E.parse(ROOT / 'profiles/Citation X - FlightFX C750.xml').getroot())
    # Retain common hardware events; remove aircraft-specific definitions everywhere.
    for device in root.findall('./s:Devices/s:Device', N):
        for events in device.findall('s:DevicePage/s:Events', N):
            for event in list(events):
                defs = event.find('s:EventDefinitions', N)
                for definition in list(defs):
                    targets = [a.get('TargetDataDefinition', '') for a in definition.findall('s:EventActions/*', N)]
                    if any(t.startswith('LVAR:') and not t.startswith('LVAR:KA_') or t.startswith('H:WT21_')
                           or t.startswith('B:AS3000_UPPER_') or t.startswith('B:ENGINE_THROTTLE_') for t in targets):
                        defs.remove(definition)
                if len(defs) == 0: events.remove(event)
    for var in root.find('s:Variables', N):
        if var.get('Name') == 'PROFILE:KA_AVIONICS_FOCUS': var.set('Value', '1') # MFD range by default
        if var.get('Name', '').startswith('PROFILE:KA_CABIN_'): var.set('Value', '0')
    # The Longitude overwrites the generic PARKING_BRAKE_SET event. Drive its own handle.
    switch(root,c.THR,41,40,'LNG_BRAKES_PARKING_BRAKE')
    # Throttle: same idle detent, using the Longitude's measured normalized input event.
    for axis, engine, buttons in [('X', 1, {5: -.125, 7: -.25, 6: -.025}), ('Y', 2, {8: -.125, 11: -.25, 9: -.025})]:
        target = f'LNG_ENGINE_THROTTLE_{engine}'
        raw = 'Min(1.0, Max(0.0, ([EVENT:VALUE] - 20040.0) / 39960.0))'
        local = f'Min(1.0, Max(0.0, ([LOCAL:JOY_0X33440X0194_{axis}_AXIS] - 33.4) / 66.6))'
        released = [c.eq(f'LOCAL:JOY_0X33440X0194_BUTTON_{b}', 0) for b in buttons]
        c.put(root, c.THR, f'{axis}_AXIS', c.D('VALUE', [set_(target, expr=raw)], *released))
        for button, amount in buttons.items():
            c.put(root, c.THR, f'BUTTON_{button}',
                  c.D('PRESS', [set_(target, amount)], c.eq(f'SIMCONNECT:GENERAL ENG COMBUSTION:{engine}', 1)),
                  c.D('RELEASE', [set_(target, expr=local)]))
    # Standard flap axis spans the aircraft's native handle indices (measured 0..3).
    c.put(root, c.THR, 'Z_AXIS', c.D('VALUE', [c.k('AXIS_FLAPS_SET', expr='16383 - Round([LOCAL:JOY_0X33440X0194_Z_AXIS] * 327.66, 0)')]))
    for on,off,name,minimum in [(48,49,'LNG_LIGHTING_COCKPIT_FLOOD_LIGHT',0),(50,51,'LNG_LIGHTING_PANEL_LIGHT',5)]:
        c.put(root,c.THR,f'BUTTON_{on}',c.press(set_(name,70)))
        c.put(root,c.THR,f'BUTTON_{off}',c.press(set_(name,minimum)))
    c.remove(root, c.THR, 'BUTTON_52', 'BUTTON_53', 'BUTTON_55', 'BUTTON_56') # no fan sync or Citation-X pressurization knob
    # OFF = fuel stop; other positions = RUN; START also presses the corresponding starter.
    for product, engine, positions in [(c.THR, 1, (60,61,62,63,64)), (c.CP3, 2, (47,46,45,44,43))]:
        for index, button in enumerate(positions):
            acts = [set_(f'LNG_ENGINE_RUN_SWITCH_{engine}', 0 if index == 0 else 1)]
            if index == 4:
                acts.append(control(f'LNG_ENGINE_STARTER_{engine}_Push', 1))
            definitions = [c.press(*acts)]
            if index == 4: definitions.append(c.D('RELEASE', [control(f'LNG_ENGINE_STARTER_{engine}_Release', 0)]))
            c.put(root, product, f'BUTTON_{button}', *definitions)
    # CP3 engine/electrical controls.
    for button, name in [(1,'LNG_ELECTRICAL_BATTERY_L'),(2,'LNG_ELECTRICAL_BATTERY_R'),
                         (3,'LNG_ELECTRICAL_BUS_L_ELEC'),(4,'LNG_ELECTRICAL_BUS_R_ELEC')]:
        toggle(root,c.CP3,button,name)
    # Fuel pump switches are ON/OFF on the Longitude: both outer hardware positions select ON.
    for buttons, engine in [((14,15,16),1),((34,35,36),2)]:
        for button,value in zip(buttons,(1,0,1)):
            c.put(root,c.CP3,f'BUTTON_{button}',c.press(set_(f'FUEL_BOOST_PUMP_{engine}',value)))
    switch(root,c.CP3,17,18,'LNG_DEICE_PITOT')
    switch(root,c.CP3,19,20,'LNG_DEICE_ENGINE_2')
    switch(root,c.CP3,21,22,'LNG_DEICE_ENGINE_1','LNG_DEICE_ENGINE_2')
    switch(root,c.CP3,23,24,'LNG_DEICE_WING')
    switch(root,c.CP3,25,26,'LNG_DEICE_STAB')
    c.remove(root,c.CP3,'BUTTON_27','BUTTON_28') # no confirmed windshield control
    switch(root,c.CP3,29,30,'LNG_LIGHTING_SEATBELTS_PUSH')
    c.put(root,c.CP3,'BUTTON_6',c.press(control('AUTOPILOT_AUTOTHROTTLE_1_Push',1)))
    c.put(root,c.CP3,'BUTTON_41',c.press(control('LNG_ENGINE_STARTER_1_Push',1)),c.D('RELEASE',[control('LNG_ENGINE_STARTER_1_Release',0)]))
    c.put(root,c.CP3,'BUTTON_42',c.press(control('LNG_ENGINE_STARTER_2_Push',1)),c.D('RELEASE',[control('LNG_ENGINE_STARTER_2_Release',0)]))
    c.put(root,c.CP3,'X_AXIS',c.D('VALUE',[set_('LNG_HANDLING_SPEEDBRAKES',expr='1.0 - [LOCAL:JOY_0X33440X025C_X_AXIS] / 100.0')]))
    # CP2: lights, generators and APU.
    for on,off,names in [(23,24,['LNG_LIGHTING_TAXI']),(25,26,['LNG_LIGHTING_LANDING_1']),
                        (27,28,['LNG_LIGHTING_LANDING_2']),(29,30,['LNG_ELECTRICAL_MAIN_GENERATOR_L']),
                        (31,32,['LNG_ELECTRICAL_MAIN_GENERATOR_R']),(33,34,['LNG_LIGHTING_RECOGNITION']),
                        (35,36,['LNG_LIGHTING_LOGO'])]:
        switch(root,c.CP2,on,off,*names)
    for on,off,event in [(17,18,'STROBES_SET'),(19,20,'BEACON_LIGHTS_SET')]:
        c.put(root,c.CP2,f'BUTTON_{on}',c.press(c.k(event,1)))
        c.put(root,c.CP2,f'BUTTON_{off}',c.press(c.k(event,0)))
    # Navigation lights have no separate Longitude input event; use the standard simulator event.
    c.put(root,c.CP2,'BUTTON_21',c.press(c.k('NAV_LIGHTS_SET',1)))
    c.put(root,c.CP2,'BUTTON_22',c.press(c.k('NAV_LIGHTS_SET',0)))
    c.put(root,c.CP2,'BUTTON_4',c.press(c.k('APU_OFF_SWITCH')))
    c.put(root,c.CP2,'BUTTON_5',c.press(c.k('APU_STARTER')))
    c.put(root,c.CP2,'BUTTON_6',c.press(c.k('APU_GENERATOR_SWITCH_TOGGLE',1)))
    c.put(root,c.CP2,'BUTTON_37',c.press(set_('LNG_ELECTRICAL_STBY_POWER',1)))
    c.put(root,c.CP2,'BUTTON_38',c.press(set_('LNG_LIGHTING_EMERGENCY',1)))
    for button,name in [(7,'LNG_PNEUMATICS_APU_BLEED'),
                        (39,'LNG_PNEUMATICS_ENGINE_BLEED_L'),(40,'LNG_PNEUMATICS_ENGINE_BLEED_R')]:
        toggle(root,c.CP2,button,name)
    # G5000 physical events from Microsoft's GTC and PFD interaction maps.
    focus = 'PROFILE:KA_AVIONICS_FOCUS'
    for product in (c.BOT,c.BOT_ANA):
        for button,direction in [(13,'INC'),(21,'INC'),(29,'INC'),(14,'DEC'),(22,'DEC'),(30,'DEC')]:
            c.put(root,product,f'BUTTON_{button}',
                  c.press(c.h(f'AS3000_PFD_1_RANGE_{direction}'),conds=[c.eq(focus,0)]),
                  c.press(c.h(f'AS3000_TSC_Vertical_2_Joystick_{direction}'),conds=[c.eq(focus,1)]),sfs=True)
        for button,suffix in [(15,'RightKnob_Small_INC'),(16,'RightKnob_Small_DEC'),
                              (23,'RightKnob_Large_INC'),(24,'RightKnob_Large_DEC'),
                              (4,'RightKnob_Push'),(3,'MiddleKnob_Push')]:
            c.put(root,product,f'BUTTON_{button}',c.press(c.h('AS3000_TSC_Vertical_2_'+suffix)),sfs=True)
        for button in (19,20):
            c.put(root,product,f'BUTTON_{button}',c.press(c.k('KOHLSMAN_INC' if button==19 else 'KOHLSMAN_DEC',1)),sfs=True)
    # Keep the page-labelled buttons unassigned rather than send another aircraft's FMC events.
    c.events(root,c.DISP).clear()
    for button,value in [(4,0),(10,1)]:
        c.put(root,c.DISP,f'BUTTON_{button}',c.press(c.pv('KA_AVIONICS_FOCUS',value)),sfs=True)
    for button,suffix in [(9,'RightKnob_Push'),(3,'RightKnob_Push_Long'),(7,'MiddleKnob_Push')]:
        c.put(root,c.DISP,f'BUTTON_{button}',c.press(c.h('AS3000_TSC_Vertical_2_'+suffix)),sfs=True)
    # Mode-aware nose wheel on CM3 and PulsAIR; other autopilot buttons retain native MSFS commands.
    for product,up,down in [(c.THR,2,3),(c.AP,11,12)]:
        c.put(root,product,f'BUTTON_{up}',*nose_wheel(True),sfs=product==c.AP)
        c.put(root,product,f'BUTTON_{down}',*nose_wheel(False),sfs=product==c.AP)
    c.put(root,c.AP,'BUTTON_9',c.press(control('AUTOPILOT_VNAV_MODE_Push',1)),sfs=True)
    info=root.find('s:ProfileInformation',N)
    info.set('ProfileID',str(uuid.uuid5(uuid.NAMESPACE_URL,'kestrelair:asobo-longitude-g5000')))
    info.set('Version','1.0')
    info.find('s:Description',N).text='<HTML><BODY><P>Asobo Cessna Citation Longitude / Working Title G5000. KestrelAir hardware layout; see longitude-profile.md.</P></BODY></HTML>'
    info.find('s:LastChanged',N).text=datetime.datetime.now(datetime.timezone.utc).isoformat()
    xml=E.tostring(root,encoding='unicode')
    for forbidden in ('WT21_','VTX_C750','ENG_CUTOFF_','Switch_ignition','BKSQ','C750_THROTTLE'):
        assert forbidden not in xml,forbidden
    E.indent(root,space='  ')
    return root

def aircraft_names():
    names=[]
    for entry in E.parse(CONF/'aircraftlist.xml').findall('.//s:AircraftEntry',N):
        name=entry.text or ''
        if 'longitude' in name.lower() and 'passive' not in name.lower(): names.append(name)
    assert names,'No installed Longitude aircraft in SPAD aircraft list'
    return sorted(set(names))

def install():
    status=subprocess.run(['tasklist','/FI','IMAGENAME eq SPAD.neXt.exe','/NH'],capture_output=True,text=True)
    if 'spad.next.exe' in status.stdout.lower(): raise SystemExit('Exit SPAD completely before installation.')
    backup=ROOT/'backups'/('longitude-install-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True,exist_ok=True)
    target=INSTALLED/NAME
    if target.exists(): shutil.copy2(target,backup/NAME)
    shutil.copy2(ROOT/'profiles'/NAME,target)
    assignments=CONF/'AircraftAssignments_MSFS24.xml'
    shutil.copy2(assignments,backup/assignments.name)
    root=E.parse(assignments).getroot()
    for name in aircraft_names():
        matches=[a for a in root.findall('s:AircraftAssignment',N) if a.findtext('s:Key',namespaces=N)==name]
        assert len(matches)<=1
        a=matches[0] if matches else E.SubElement(root,c.tag('AircraftAssignment'))
        if not matches:
            E.SubElement(a,c.tag('Key')).text=name
            E.SubElement(a,c.tag('Profile'))
        a.find('s:Profile',N).text=NAME
    E.indent(root,space='  ');E.ElementTree(root).write(assignments,encoding='utf-8',xml_declaration=True)
    print('Installed',target,'and assigned',aircraft_names())

if __name__=='__main__':
    for folder in ('profiles','portable-setup/profiles'):
        out=ROOT/folder/NAME
        E.ElementTree(build()).write(out,encoding='utf-8')
        print('Created',out)
    # Merge only Longitude rows into the portable assignment table.
    path=ROOT/'portable-setup/aircraft-assignments.csv'
    lines=path.read_text(encoding='utf-8').splitlines()
    lines=[line for line in lines if 'longitude' not in line.lower()]
    import io
    extra=io.StringIO();writer=csv.writer(extra,lineterminator='\n')
    for name in aircraft_names(): writer.writerow([name,NAME])
    path.write_text('\n'.join(lines)+'\n'+extra.getvalue(),encoding='utf-8')
    if '--install' in sys.argv: install()
