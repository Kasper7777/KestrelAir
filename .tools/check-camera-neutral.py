"""Read-only check of the current camera and the virtual controller's cached position."""
import ctypes as c
import struct
import time
import json
from pathlib import Path

v = c.CDLL(r'C:\Program Files\vJoy\x64\vJoyInterface.dll')
v.GetPosition.argtypes = [c.c_uint, c.c_void_p]
v.GetPosition.restype = c.c_uint
axes = {}
if v.AcquireVJD(1):
    try:
        data = c.create_string_buffer(4096)
        result = v.GetPosition(1, data)
        if result == 0:
            names = ['Throttle','Rudder','Aileron','X','Y','Z','Rx','Ry','Rz','Slider0','Slider1','Wheel']
            axes = dict(zip(names, struct.unpack_from('<12i', data.raw, 4)))
    finally:
        v.RelinquishVJD(1)

d = c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
h = c.c_void_p()
d.SimConnect_Open.argtypes = [c.POINTER(c.c_void_p),c.c_char_p,c.c_void_p,c.c_uint,c.c_void_p,c.c_uint]
d.SimConnect_AddToDataDefinition.argtypes = [c.c_void_p,c.c_uint,c.c_char_p,c.c_char_p,c.c_uint,c.c_float,c.c_uint]
d.SimConnect_RequestDataOnSimObject.argtypes = [c.c_void_p]+[c.c_uint]*8
d.SimConnect_GetNextDispatch.argtypes = [c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_uint)]
d.SimConnect_Close.argtypes = [c.c_void_p]
assert d.SimConnect_Open(c.byref(h),b'KestrelAir read-only camera check',None,0,None,0)==0
samples=[]
try:
    for name, unit in [(b'CAMERA STATE',b'number'),(b'CAMERA GAMEPLAY PITCH YAW:0',b'radians'),(b'CAMERA GAMEPLAY PITCH YAW:1',b'radians')]:
        assert d.SimConnect_AddToDataDefinition(h,1,name,unit,4,0,0xffffffff)==0
    assert d.SimConnect_RequestDataOnSimObject(h,1,1,0,4,0,0,0,0)==0
    end=time.monotonic()+5
    while time.monotonic()<end:
        pointer,size=c.c_void_p(),c.c_uint()
        if d.SimConnect_GetNextDispatch(h,c.byref(pointer),c.byref(size))==0:
            raw=c.string_at(pointer,size.value)
            if len(raw)>=64 and struct.unpack_from('<I',raw,8)[0]==8:
                samples.append(struct.unpack_from('<3d',raw,40))
        time.sleep(.01)
finally:
    d.SimConnect_Close(h)
report={'axes':axes,'camera_samples':samples}
if samples:
    report['pitch_span']=max(s[1] for s in samples)-min(s[1] for s in samples)
    report['yaw_span']=max(s[2] for s in samples)-min(s[2] for s in samples)
Path('camera-neutral-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
