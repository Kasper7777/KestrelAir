"""Read loaded Longitude input events through SimConnect; imported by its validation script."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
context = {'__file__': str(ROOT / 'verify-citation-x.py')}
source = (ROOT / 'verify-citation-x.py').read_text()
exec(source[:source.index('# ---- SPAD semantics')], context)
c, struct, d, h = (context[k] for k in ('c', 'struct', 'd', 'h'))
read, calc, pump = (context[k] for k in ('read', 'calc', 'pump'))
d.SimConnect_GetInputEvent.argtypes = [c.c_void_p, c.c_uint, c.c_uint64]
EVENTS = {}
for packet in json.loads((ROOT / 'references/longitude-input-packets.json').read_text()):
    packet = bytes.fromhex(packet)
    if struct.unpack_from('<I', packet, 8)[0] != 34:
        continue
    for offset in range(28, len(packet) - 75, 76):
        name = packet[offset:offset+64].split(b'\0')[0].decode()
        EVENTS[name] = struct.unpack_from('<Q', packet, offset+64)[0]
_request = 700

def get(name):
    global _request
    _request += 1
    assert d.SimConnect_GetInputEvent(h, _request, EVENTS[name]) == 0
    for packet in pump(2):
        if struct.unpack_from('<I', packet, 8)[0] == 35 and struct.unpack_from('<I', packet, 12)[0] == _request:
            return struct.unpack_from('<d', packet, 20)[0]
    raise RuntimeError('No input-event response: ' + name)

if __name__ == '__main__':
    import sys
    for name in sys.argv[1:]:
        print(name, get(name))
