"""Exercise the actual SPAD expression and vJoy output without moving flight axes."""
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.parse import urlencode

BASE = 'http://127.0.0.1:28001'


def get(route, **params):
    with urlopen(BASE + route + '?' + urlencode(dict(params, format='json')), timeout=3) as r:
        response = json.load(r)
    assert response['Success'], response
    return response.get('Result')


def set_value(name, value):
    request = Request(BASE + '/data/set?format=json',
                      data=json.dumps({'Name': name, 'Value': value}).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=3) as r:
        response = json.load(r)
    assert response['Success'], response


def trigger():
    assert get('/data/get', Name='SIMCONNECT:CAMERA STATE')['Value'] == 2, 'Cockpit camera required'
    get('/data/emulateevent', Device='3344:03F5:0', Event='BUTTON_32', Trigger='PRESS', Parameter=1)
    time.sleep(.15)


samples = []
previous_camera = get('/data/get', Name='SIMCONNECT:CAMERA STATE')['Value']
set_value('SIMCONNECT:CAMERA STATE', 2)
time.sleep(.5)
try:
    for value in (0, 25, 37.5, 45, 50, 55, 62.5, 75, 100):
        set_value('PROFILE:KA_DRONE_TEST', value)
        trigger()
        observed = get('/data/get', Name='LOCAL:JOY_0X12340XBEAD_DIAL')['Value']
        t = value / 50 - 1
        expected = 50 + 50 * (.35*t + .65*t*t*t)
        samples.append({'input_percent': value, 'expected_percent': expected, 'actual_percent': observed})
        print(samples[-1], flush=True)
        assert abs(observed - expected) <= 1, 'Live SPAD/vJoy output does not match curve'
finally:
    set_value('PROFILE:KA_DRONE_TEST', 50)
    set_value('LOCAL:JOY_0X12340XBEAD_DIAL', 16384)
    set_value('SIMCONNECT:CAMERA STATE', previous_camera)
    Path('.tools/drone-precision-live-results.json').write_text(json.dumps(samples, indent=2))

print('PASS: live SPAD expression, centre, both directions, endpoints and fine movements')
