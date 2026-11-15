"""Verify all six installed drone event paths using the actual centred stick readings."""
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drone_precision import ROUTES
BASE = 'http://127.0.0.1:28001'

def get(route, **params):
    with urlopen(BASE + route + '?' + urlencode(dict(params, format='json')), timeout=3) as response:
        result = json.load(response)
    assert result['Success'], result
    return result.get('Result')

def set_value(name, value):
    request = Request(BASE+'/data/set?format=json', data=json.dumps({'Name':name,'Value':value}).encode(),
                      headers={'Content-Type':'application/json'})
    with urlopen(request, timeout=3) as response:
        assert json.load(response)['Success']

samples = []
camera = get('/data/get', Name='SIMCONNECT:CAMERA STATE')['Value']
# Only exercise the live event paths with centred hardware; do not move flight controls.
for index, routes in ROUTES.items():
    for bound in routes:
        source = 'LOCAL:JOY_0X33440X03F5_'+bound+('_1' if index else '')
        assert get('/data/get', Name=source)['Value']==50, 'Leave sticks centred for this check'
try:
    set_value('SIMCONNECT:CAMERA STATE',4)
    time.sleep(.5)
    assert get('/data/get', Name='SIMCONNECT:CAMERA STATE')['Value']==4
    for index,routes in ROUTES.items():
        for bound,(target,_) in routes.items():
            assert get('/data/get', Name='SIMCONNECT:CAMERA STATE')['Value']==4
            get('/data/emulateevent',Device=f'3344:03F5:{index}',Event=bound,Trigger='VALUE',Parameter=30000)
            time.sleep(.15)
            value=get('/data/get',Name='LOCAL:JOY_0X12340XBEAD_'+target)['Value']
            samples.append({'grip':index,'axis':bound,'output':target,'percent':value})
            assert value==50, samples[-1]
finally:
    set_value('SIMCONNECT:CAMERA STATE',camera)
    Path('.tools/drone-precision-final-results.json').write_text(json.dumps(samples,indent=2))
print(json.dumps(samples))
print('PASS: all six deployed drone event paths produce centred vJoy output')
