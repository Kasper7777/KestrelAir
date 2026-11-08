"""Parked-only check of heading, altitude and baro actions; restore original values."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
source=(ROOT/'verify-citation-x.py').read_text().replace("'Citation X - FlightFX C750.xml'","'Citation Longitude - Asobo G5000.xml'")
# The original check evaluator predates SPAD's increment/decrement value actions.
source=source.replace("                if tgt.startswith('PROFILE:'):",
    "                if a.get('ValueOperation') in ('Increment', 'Decrement'):\n"
    "                    val = read([tgt])[tgt] + (val if a.get('ValueOperation') == 'Increment' else -val)\n"
    "                if tgt.startswith('PROFILE:'):")
ctx={'__file__':str(ROOT/'verify-citation-x.py')}
exec(source[:source.index('SAVE =')],ctx)
read,fire,calc,write,pump=(ctx[k] for k in ('read','fire','calc','write','pump'))
assert read(['SIMCONNECT:SIM ON GROUND'])['SIMCONNECT:SIM ON GROUND']==1
assert read(['LVAR:KA_SFS_MONITOR'])['LVAR:KA_SFS_MONITOR']==0,'Close SFS Monitor first'
results=[]
for product,button,key in [('0x1290','BUTTON_11','SIMCONNECT:AUTOPILOT HEADING LOCK DIR'),
                           ('0x1290','BUTTON_15','SIMCONNECT:AUTOPILOT ALTITUDE LOCK VAR'),
                           ('0x13E4','BUTTON_19','SIMCONNECT:KOHLSMAN SETTING MB:1')]:
    before=read([key])[key]
    try:
        sent=fire(product,button)
        after=read([key])[key]
        assert after!=before,(button,sent,before,after)
    finally:
        if 'HEADING' in key: calc(f'{before} (>K:HEADING_BUG_SET)')
        elif 'KOHLSMAN' in key: fire(product,'BUTTON_20')
        else: write(key,before)
        list(pump(.3))
    restored=read([key])[key]
    assert abs(restored-before)<.01,(key,'restore failed',restored,before)
    results.append(f'PASS live {key}: {before} -> {after}; original restored')
print('\n'.join(results))
with (ROOT/'verify-longitude-results.txt').open('a') as out:
    out.write('\n'+'\n'.join(results)+'\n')
