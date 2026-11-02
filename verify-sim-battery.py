import ctypes as c
import struct
import time
import json

d=c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
h=c.c_void_p()
d.SimConnect_Open.argtypes=[c.POINTER(c.c_void_p),c.c_char_p,c.c_void_p,c.c_uint,c.c_void_p,c.c_uint]
d.SimConnect_GetNextDispatch.argtypes=[c.c_void_p,c.POINTER(c.c_void_p),c.POINTER(c.c_uint)]
d.SimConnect_AddToDataDefinition.argtypes=[c.c_void_p,c.c_uint,c.c_char_p,c.c_char_p,c.c_uint,c.c_float,c.c_uint]
d.SimConnect_RequestDataOnSimObject.argtypes=[c.c_void_p]+[c.c_uint]*8
d.SimConnect_MapClientEventToSimEvent.argtypes=[c.c_void_p,c.c_uint,c.c_char_p]
d.SimConnect_TransmitClientEvent.argtypes=[c.c_void_p]+[c.c_uint]*5
d.SimConnect_Close.argtypes=[c.c_void_p]
d.SimConnect_GetInputEvent.argtypes=[c.c_void_p,c.c_uint,c.c_uint64]
d.SimConnect_SetInputEvent.argtypes=[c.c_void_p,c.c_uint64,c.c_uint,c.c_void_p]
assert d.SimConnect_Open(c.byref(h),b'KestrelAir battery verification',None,0,None,0)==0
names=['ELECTRICAL MASTER BATTERY:1','AVIONICS MASTER SWITCH:1','RECIP ENG COWL FLAP POSITION:1']
for name in names:
    assert d.SimConnect_AddToDataDefinition(h,1,name.encode(),b'number',4,0,0xffffffff)==0
def read():
    assert d.SimConnect_RequestDataOnSimObject(h,1,1,0,1,0,0,0,0)==0
    end=time.monotonic()+3
    while time.monotonic()<end:
        p,n=c.c_void_p(),c.c_uint()
        if d.SimConnect_GetNextDispatch(h,c.byref(p),c.byref(n))==0:
            raw=c.string_at(p,n.value)
            if struct.unpack_from('<I',raw,8)[0]==8 and len(raw)>=64:
                return struct.unpack_from('<3d',raw,40)
        time.sleep(.01)
    raise RuntimeError('No data received')
def input_hash(name):
    for packet in json.load(open('sim-input-packets.json')):
        raw=bytes.fromhex(packet)
        pos=raw.find(name.encode()+b'\0')
        if pos>=0: return struct.unpack_from('<Q',raw,pos+64)[0]
    raise ValueError(name)
def input_value(hash):
    assert d.SimConnect_GetInputEvent(h,201,hash)==0
    end=time.monotonic()+3
    while time.monotonic()<end:
        p,n=c.c_void_p(),c.c_uint()
        if d.SimConnect_GetNextDispatch(h,c.byref(p),c.byref(n))==0:
            raw=c.string_at(p,n.value)
            if len(raw)>=28 and struct.unpack_from('<I',raw,12)[0]==201:
                print('Input response packet',raw.hex())
                return struct.unpack_from('<d',raw,20)[0]
        time.sleep(.01)
    raise RuntimeError('No input value')
try:
    before=read()
    print('Before:',dict(zip(names,before)))
    assert d.SimConnect_MapClientEventToSimEvent(h,100,b'BATTERY1_SET')==0
    try:
        print('Send on:',d.SimConnect_TransmitClientEvent(h,0,100,1-int(before[0]),1,16))
        time.sleep(1)
        print('Changed:',read())
    finally:
        d.SimConnect_TransmitClientEvent(h,0,100,int(before[0]),1,16)
        time.sleep(1)
        print('Restored:',read())
    for name in ['ELECTRICAL_BATTERY_1','ELECTRICAL_AVIONICS_BUS_1','ENGINE_COWLFLAPS_LEFT','ENGINE_COWLFLAPS_RIGHT']:
        hash=input_hash(name)
        saved=input_value(hash)
        print(name,'before',saved)
        try:
            value=c.c_double(1-saved)
            print('Set native:',d.SimConnect_SetInputEvent(h,hash,8,c.byref(value)))
            time.sleep(1)
            print('After native:',input_value(hash),'simvars',read())
        finally:
            value=c.c_double(saved)
            d.SimConnect_SetInputEvent(h,hash,8,c.byref(value))
            time.sleep(.5)
finally:
    d.SimConnect_Close(h)
