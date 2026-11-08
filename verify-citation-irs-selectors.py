"""Exercise only the installed selector LVAR actions and restore both IRS modes."""
from pathlib import Path
import xml.etree.ElementTree as E
import json
root = Path(__file__).resolve().parent
context = {'__file__': str(root / 'verify-citation-x.py')}
source = (root / 'verify-citation-x.py').read_text()
exec(source[:source.index('# ---- SPAD semantics')], context)
n = {'s': 'http://www.fsgs.com/SPAD'}
profile = E.parse(Path.home() / 'Documents/SPAD.neXt/profiles/Citation X - FlightFX C750.xml').getroot()
names = ['LVAR:knob_irs_l', 'LVAR:knob_irs_r', 'LVAR:Switch_ignition_l', 'LVAR:Switch_ignition_r',
         'SIMCONNECT:GENERAL ENG STARTER:1', 'SIMCONNECT:GENERAL ENG STARTER:2']
saved = context['read'](names)
results = []
try:
    for product, buttons, side in [('0x0194', range(60, 65), 'l'), ('0x025C', range(47, 42, -1), 'r')]:
        for button in buttons:
            action = profile.find(f".//s:Device[@ProductID='{product}']/s:DevicePage/s:Events/s:Event[@BoundTo='BUTTON_{button}']//s:EventActions", n)
            assert action is not None and len(action) == 1
            action = action[0]
            target = action.get('TargetDataDefinition')
            assert target == f'LVAR:knob_irs_{side}'
            value = float(action.get('Value'))
            before = context['read'](names)
            context['write'](target, value)
            list(context['pump'](.2))
            after = context['read'](names)
            assert after[target] == value, (target, value, after)
            assert all(after[k] == before[k] for k in names if k != target), after
            results.append({'device': product, 'button': button, 'IRS': side, 'mode': value, 'passed': True})
finally:
    for target in names[:2]: context['write'](target, saved[target])
    list(context['pump'](.3))
    restored = context['read'](names)
    assert restored == saved, (saved, restored)
(root / 'citation-irs-verification.json').write_text(json.dumps({'checks': results, 'restored': restored}, indent=2))
print('PASS: all ten installed selector positions; opposite IRS, ignition and starters unchanged; original IRS states restored.')
