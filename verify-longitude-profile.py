"""Validate Longitude bindings against the captured live aircraft event catalog."""
from pathlib import Path
import json
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parent
N={'s':'http://www.fsgs.com/SPAD'}
NAME='Citation Longitude - Asobo G5000.xml'
known=set((ROOT/'references/longitude-input-events.txt').read_text().splitlines())
source=E.parse(ROOT/'profiles/Citation X - FlightFX C750.xml').getroot()
results=[]
for folder in ('profiles','portable-setup/profiles'):
    root=E.parse(ROOT/folder/NAME).getroot()
    devices=root.findall('./s:Devices/s:Device',N)
    for dev in devices:
        bounds=[event.get('BoundTo') for event in dev.findall('s:DevicePage/s:Events/s:Event',N)]
        assert len(bounds)==len(set(bounds)),(dev.attrib,'duplicate bindings')
    for action in root.findall('.//s:EventActionControl',N):
        target=action.get('TargetDataDefinition','')
        if target.startswith('B:'):
            assert any(target[2:]==name or target[2:].startswith(name+'_') for name in known),target
    xml=E.tostring(root,encoding='unicode')
    assert not any(x in xml for x in ('WT21_','VTX_C750','ENG_CUTOFF_','Switch_ignition','BKSQ'))
    for index in ('0','1'):
        get=lambda tree: next(d for d in tree.findall('./s:Devices/s:Device',N) if d.get('ProductID')=='0x03F5' and d.get('DeviceIndex')==index)
        assert E.tostring(get(root))==E.tostring(get(source)),'Stick/cabin controls changed'
    pedals=lambda tree: next(d for d in tree.findall('./s:Devices/s:Device',N) if d.get('ProductID')=='0x0763')
    assert E.tostring(pedals(root))==E.tostring(pedals(source)),'Pedal controls changed'
    assert root.find('s:ProfileInformation',N).get('ProfileID')!=source.find('s:ProfileInformation',N).get('ProfileID')
    throttle=next(d for d in devices if d.get('ProductID')=='0x0194')
    for button,value in [(40,'0'),(41,'1')]:
        action=throttle.find(f'.//s:Event[@BoundTo="BUTTON_{button}"]//s:EventActionControl',N)
        assert action.get('TargetDataDefinition')=='B:LNG_BRAKES_PARKING_BRAKE_Set'
        assert action.find('s:Parameter',N).get('Value')==value
    results.append(f'PASS {folder}: unique bindings; B-event bases exist in live Longitude; no Citation X commands; sticks/cabin/pedals preserved; unique profile ID')
for line in results: print(line)
(ROOT/'verify-longitude-results.txt').write_text('\n'.join(results)+'\nLive aircraft measurements: forward throttle Set 0/0.5/1 -> input display 20/60/100; speedbrake 0..1; flap axis -16383/0/16383 -> native indices 0/1/3. Batteries, buses, fuel pumps, lighting, deice-compatible event names and standby/emergency inputs inspected. Native APU generator toggle requires index 1. Engines were not started; reverse, starter, ATS and G5000 screen response require physical validation.\n')
