"""Read cabin light states through the existing local SimConnect bridge."""
from pathlib import Path
import sys, json
import time
root = Path(__file__).resolve().parent
ctx = {'__file__': str(root / 'verify-citation-x.py')}
source = (root / 'verify-citation-x.py').read_text()
exec(source[:source.index('# ---- SPAD semantics')], ctx)
names = ['LVAR:cabin_overhead_brightness', 'LVAR:c750_cabin_emis']
names += [f'SIMCONNECT:LIGHT CABIN:{i}' for i in range(0, 11)]
names += [f'SIMCONNECT:LIGHT POTENTIOMETER:{i}' for i in range(1, 31)]
if '--watch' in sys.argv:
    previous = None
    end = time.monotonic() + 180
    while time.monotonic() < end:
        values = ctx['read'](names)
        changed = {k: v for k, v in values.items() if previous is None or previous[k] != v}
        if changed:
            line = time.strftime('%H:%M:%S') + ' ' + json.dumps(changed)
            print(line, flush=True)
            with (root / 'citation-cabin-state-watch.txt').open('a') as f:
                f.write(line + '\n')
        previous = values
        time.sleep(.25)
    sys.exit()
if len(sys.argv) > 1 and sys.argv[1] == '--set':
    ctx['write'](sys.argv[2], float(sys.argv[3]))
    list(ctx['pump'](.5))
elif len(sys.argv) > 1:
    ctx['calc'](sys.argv[1])
    list(ctx['pump'](.5))
print(json.dumps(ctx['read'](names), indent=2))
