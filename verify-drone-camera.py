"""Briefly enter drone view, verify state feedback, then restore the camera."""
import ctypes as c
import struct
import time

d = c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
h = c.c_void_p()
d.SimConnect_Open.argtypes = [c.POINTER(c.c_void_p), c.c_char_p, c.c_void_p, c.c_uint, c.c_void_p, c.c_uint]
d.SimConnect_AddToDataDefinition.argtypes = [c.c_void_p, c.c_uint, c.c_char_p, c.c_char_p, c.c_uint, c.c_float, c.c_uint]
d.SimConnect_RequestDataOnSimObject.argtypes = [c.c_void_p] + [c.c_uint] * 8
d.SimConnect_GetNextDispatch.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_uint)]
d.SimConnect_SetDataOnSimObject.argtypes = [c.c_void_p] + [c.c_uint] * 5 + [c.c_void_p]
d.SimConnect_Close.argtypes = [c.c_void_p]
assert d.SimConnect_Open(c.byref(h), b'KestrelAir drone verification', None, 0, None, 0) == 0

def read():
    assert d.SimConnect_RequestDataOnSimObject(h, 1, 1, 0, 1, 0, 0, 0, 0) == 0
    end = time.monotonic() + 3
    while time.monotonic() < end:
        p, n = c.c_void_p(), c.c_uint()
        if d.SimConnect_GetNextDispatch(h, c.byref(p), c.byref(n)) == 0:
            raw = c.string_at(p, n.value)
            if len(raw) >= 44 and struct.unpack_from('<I', raw, 8)[0] == 8:
                return struct.unpack_from('<i', raw, 40)[0]
        time.sleep(.01)
    raise RuntimeError('No camera state received')

def set_state(value):
    value = c.c_int(value)
    assert d.SimConnect_SetDataOnSimObject(h, 1, 0, 0, 0, c.sizeof(value), c.byref(value)) == 0
    time.sleep(1)

try:
    assert d.SimConnect_AddToDataDefinition(h, 1, b'CAMERA STATE', b'enum', 1, 0, 0xffffffff) == 0
    before = read()
    print('Initial camera state:', before)
    if before not in (2, 3, 4, 24):
        raise RuntimeError('Camera is not in an interactive flight view')
    try:
        target = 2 if before == 4 else 4
        set_state(target)
        actual = read()
        print('Temporary camera state:', actual)
        assert actual == target
    finally:
        set_state(before)
        restored = read()
        print('Restored camera state:', restored)
        assert restored == before
finally:
    d.SimConnect_Close(h)
