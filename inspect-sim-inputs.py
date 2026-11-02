import ctypes as c
import time
import json
from pathlib import Path

sim = c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
sim.SimConnect_Open.argtypes = [c.POINTER(c.c_void_p), c.c_char_p, c.c_void_p, c.c_uint32, c.c_void_p, c.c_uint32]
sim.SimConnect_GetNextDispatch.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_uint32)]
sim.SimConnect_EnumerateInputEvents.argtypes = [c.c_void_p, c.c_uint32]
sim.SimConnect_Close.argtypes = [c.c_void_p]
h = c.c_void_p()
hr = sim.SimConnect_Open(c.byref(h), b'KestrelAir read-only input audit', None, 0, None, 0)
if hr: raise RuntimeError(f'Open: {hr:#x}')
try:
    print('Enumerate:', sim.SimConnect_EnumerateInputEvents(h, 77))
    packets = []
    until = time.monotonic() + 8
    while time.monotonic() < until:
        p, size = c.c_void_p(), c.c_uint32()
        if sim.SimConnect_GetNextDispatch(h, c.byref(p), c.byref(size)) == 0:
            raw = c.string_at(p, size.value)
            packets.append(raw.hex())
            import re
            for name in re.findall(rb'[A-Za-z][A-Za-z0-9_]{5,}', raw):
                text = name.decode()
                if any(x in text.upper() for x in ('HEADING', 'GYRO', 'AVIONIC', 'BATTERY', 'COURSE', 'BARO')):
                    print(text)
        time.sleep(.01)
    Path('sim-input-packets.json').write_text(json.dumps(packets))
finally:
    sim.SimConnect_Close(h)
