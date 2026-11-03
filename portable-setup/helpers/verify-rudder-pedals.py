"""Read-only SimConnect monitor: log the sim's rudder pedal and toe-brake positions.

Used on 2026-11-03 to confirm the Saitek pedals work through SPAD alone (after importing
portable-setup/KestrelAir-RudderPedals-SPAD.xml in MSFS): full left rudder should read near -1,
full right near +1, each toe brake 0 released .. 1 fully pressed.

Usage: python verify-rudder-pedals.py [seconds] [logfile]
"""
import ctypes as c
import struct
import sys
import time

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 120
LOG = sys.argv[2] if len(sys.argv) > 2 else 'rudder-pedals-sim.txt'
VARS = ['RUDDER PEDAL POSITION', 'RUDDER POSITION', 'BRAKE LEFT POSITION', 'BRAKE RIGHT POSITION']

d = c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
h = c.c_void_p()
d.SimConnect_Open.argtypes = [c.POINTER(c.c_void_p), c.c_char_p, c.c_void_p, c.c_uint, c.c_void_p, c.c_uint]
d.SimConnect_GetNextDispatch.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_uint)]
d.SimConnect_AddToDataDefinition.argtypes = [c.c_void_p, c.c_uint, c.c_char_p, c.c_char_p, c.c_uint, c.c_float, c.c_uint]
d.SimConnect_RequestDataOnSimObject.argtypes = [c.c_void_p] + [c.c_uint] * 8
d.SimConnect_Close.argtypes = [c.c_void_p]
assert d.SimConnect_Open(c.byref(h), b'KestrelAir pedal verification', None, 0, None, 0) == 0
for name in VARS:
    assert d.SimConnect_AddToDataDefinition(h, 1, name.encode(), b'position', 4, 0, 0xffffffff) == 0


def read():
    assert d.SimConnect_RequestDataOnSimObject(h, 1, 1, 0, 1, 0, 0, 0, 0) == 0
    end = time.monotonic() + 3
    while time.monotonic() < end:
        p, n = c.c_void_p(), c.c_uint()
        if d.SimConnect_GetNextDispatch(h, c.byref(p), c.byref(n)) == 0:
            raw = c.string_at(p, n.value)
            if struct.unpack_from('<I', raw, 8)[0] == 8 and len(raw) >= 40 + 8 * len(VARS):
                return struct.unpack_from(f'<{len(VARS)}d', raw, 40)
        time.sleep(.01)
    raise RuntimeError('No data received')


last = None
lo = [9.0] * len(VARS)
hi = [-9.0] * len(VARS)
with open(LOG, 'w', encoding='utf-8') as log:
    log.write('time ' + ' | '.join(VARS) + '\n')
    end = time.monotonic() + SECONDS
    while time.monotonic() < end:
        vals = read()
        lo = [min(a, b) for a, b in zip(lo, vals)]
        hi = [max(a, b) for a, b in zip(hi, vals)]
        text = ' '.join(f'{v:+.3f}' for v in vals)
        if text != last:
            log.write(time.strftime('%H:%M:%S ') + text + '\n')
            log.flush()
            last = text
        time.sleep(.2)
    log.write('min ' + ' '.join(f'{v:+.3f}' for v in lo) + '\n')
    log.write('max ' + ' '.join(f'{v:+.3f}' for v in hi) + '\n')
d.SimConnect_Close(h)
