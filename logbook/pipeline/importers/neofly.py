"""NeoFly importer.

Reads NeoFly's save (std.bin, a SQLite file) and navdata.sqlite strictly read-only
(a temp copy is taken so a running NeoFly never sees a lock) and returns
source-neutral records:

  flights   - one per flown leg (flightlog), plus legs that only exist in the job
              log (NeoFly sometimes skips the flightlog row), flagged inferred=True
  aircraft  - hangar planes, keyed "neofly:<hangarId>"
  events    - relocations / hotel stays etc. from the finance ledger, used later to
              explain gaps between flights
  pilot     - name, rank, hours, cash
  airports  - resolver function: ident -> airport dict (navdata, then job coordinates)
"""
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta

from countries import country_for

MISSION_TYPES = {
    1: 'Cargo', 2: 'Sensitive cargo', 3: 'Express cargo', 4: 'Illicit cargo', 5: 'Tourists',
    6: 'VIP', 7: 'Skydiving drop', 8: 'Emergency', 9: 'Search & rescue', 10: 'Fire fighting',
    11: 'Advertising', 12: 'Interception', 13: 'Secret', 14: 'Humanitarian', 22: 'Passengers',
    25: 'Qualification', 26: 'Airline',
}
JOB_STATUS = {0: 'completed', 1: 'failed', 2: 'cancelled'}


def _ts(v):
    """NeoFly stores times as yyyymmddHHMMSS integers in local PC time."""
    try:
        return datetime.strptime(str(int(v)), '%Y%m%d%H%M%S')
    except (TypeError, ValueError):
        return None


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S') if dt else None


def _snapshot(path, tmp):
    dst = os.path.join(tmp, os.path.basename(path))
    shutil.copy2(path, dst)
    con = sqlite3.connect(f'file:{dst}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    return con


def _clean_aircraft_name(name):
    # aircrafts.name carries MSFS title matchers after a comma: "Asobo Cessna 152,/1670"
    return re.split(r',', name or '')[0].strip() or None


def load(neofly_dir, backup_dir=None, airports_cache=None, pilot_name=None):
    """Live NeoFly install if this PC has one, otherwise the newest save in the
    repo's backup folder (so a fresh clone on another PC still builds).
    airports_cache: {ident: airport} saved by earlier builds, used when
    navdata.sqlite isn't installed here."""
    std = os.path.join(neofly_dir, 'std.bin')
    nav = os.path.join(neofly_dir, 'navdata.sqlite')
    source = 'live'
    if not os.path.exists(std) and backup_dir and os.path.isdir(backup_dir):
        saves = sorted(f for f in os.listdir(backup_dir) if re.match(r'std-\d{8}-\d{6}\.bin$', f))
        if saves:
            std, source = os.path.join(backup_dir, saves[-1]), 'backup:' + saves[-1]
    if not os.path.exists(std):
        raise FileNotFoundError(f'NeoFly save not found: {std} (and no backup in {backup_dir})')

    with tempfile.TemporaryDirectory() as tmp:
        db = _snapshot(std, tmp)
        navdb = _snapshot(nav, tmp) if os.path.exists(nav) else None
        try:
            out = _read(db, navdb, airports_cache or {}, pilot_name)
            out['source'] = source
            return out
        finally:
            db.close()
            if navdb:
                navdb.close()


def _read(db, navdb, airports_cache, pilot_name=None):
    # which NeoFly pilot: the one named in config, else whoever is logged in to NeoFly
    pilots = [{'id': r[0], 'name': r[1]} for r in db.execute('select id, name from players order by id')]
    pid = next((p['id'] for p in pilots if pilot_name and p['name'].lower() == pilot_name.lower()), None)
    if pid is None:
        row = db.execute('select pilotID from currentpilot').fetchone()
        pid = row[0] if row else pilots[0]['id']
    p = db.execute('select * from players where id=?', (pid,)).fetchone()
    pilot = {
        'name': p['name'], 'rank': p['rank'], 'xp': p['xp'], 'cash': p['cash'],
        'neoflyHours': round((p['totalFlyTime'] or 0) / 60, 1), 'location': p['pilotCurrentICAO'],
        'reputation': round(p['reputation'] or 0, 1), 'crashes': p['nbrCrash'],
    }

    # ---- aircraft
    aircraft = {}
    for r in db.execute('''select h.id, h.tailNumber, h.Location, h.Cost, l.name livery, a.name model, a.type,
                                  a.engines, a.cruiseSpeedktas, a.Pax, a.engineType
                           from hangar h left join liveries l on l.id=h.liveryId
                           left join aircrafts a on a.id=l.aircraftId where h.ownerId=?''', (pid,)):
        aircraft[f'neofly:{r["id"]}'] = {
            'id': f'neofly:{r["id"]}', 'name': _clean_aircraft_name(r['model']) or r['livery'] or f'Aircraft {r["id"]}',
            'livery': r['livery'], 'tail': (r['tailNumber'] or '').strip() or None, 'category': r['type'],
            'engines': r['engines'], 'cruiseKt': r['cruiseSpeedktas'], 'seats': r['Pax'],
            'price': r['Cost'], 'base': r['Location'],
        }
    # purchase dates from the ledger, by model name
    bought = {}
    for r in db.execute("select date, description, expenses from finances where ownerId=? and description like 'Buying plane:%' order by date", (pid,)):
        bought.setdefault(r['description'].split(':', 1)[1].strip(), (_iso(_ts(r['date'])), r['expenses']))
    for a in aircraft.values():
        if a['name'] in bought:
            a['acquired'], a['price'] = bought[a['name']][0], bought[a['name']][1] or a['price']

    def plane_id(pl):
        key = f'neofly:{pl}'
        if key not in aircraft:
            aircraft[key] = {'id': key, 'name': f'Aircraft #{pl}', 'category': None}
        return key

    # ---- airports (navdata first, job coordinates as a fallback)
    job_coords = {}
    for r in db.execute('select departure, latDep, lonDep, arrival, latArriv, lonArriv, nameAirport from jobs'):
        if r['departure'] and r['latDep'] is not None:
            job_coords.setdefault(r['departure'], (r['latDep'], r['lonDep'], None))
        if r['arrival'] and r['latArriv'] is not None:
            job_coords.setdefault(r['arrival'], (r['latArriv'], r['lonArriv'], r['nameAirport']))
    cache = {}

    def airport(ident):
        ident = (ident or '').strip().upper()
        if ident in cache:
            return cache[ident]
        a = None
        if navdb is not None:
            r = navdb.execute('''select ident, name, city, state, country, laty, lonx, altitude, longest_runway_length,
                                        longest_runway_surface, num_runways, has_tower_object, region
                                 from airport where ident=? order by (city is null), msfs_version desc limit 1''', (ident,)).fetchone()
            if r:
                a = {'ident': ident, 'name': r['name'], 'city': r['city'], 'state': r['state'],
                     'lat': round(r['laty'], 6), 'lon': round(r['lonx'], 6), 'elevationFt': r['altitude'],
                     'longestRunwayFt': r['longest_runway_length'], 'surface': r['longest_runway_surface'],
                     'runways': r['num_runways'], 'tower': bool(r['has_tower_object']),
                     'country': country_for(ident, r['country'], r['state'], r['region'])}
        if a is None and ident in airports_cache:
            a = airports_cache[ident]
        if a is None and ident in job_coords:
            lat, lon, nm = job_coords[ident]
            a = {'ident': ident, 'name': nm or ident, 'lat': lat, 'lon': lon, 'country': country_for(ident)}
        cache[ident] = a
        return a

    # ---- jobs (missions), grouped so they can be pinned to flights
    jobs = []
    for r in db.execute('select * from joblog where ownerId=? order by date', (pid,)):
        jobs.append({
            'jobId': r['id'], 'from': r['departure'], 'to': r['arrival'], 'type': MISSION_TYPES.get(r['jobType'], f'Mission {r["jobType"]}'),
            'status': JOB_STATUS.get(r['status'], str(r['status'])), 'reward': r['reward'], 'xp': r['xp'],
            'cargoLbs': r['weight'], 'pax': r['pax'], 'completedAt': _ts(r['date']), 'plane': plane_id(r['planeId']),
            'bonus': {'security': r['bonusSecurity'], 'comfort': r['bonusComfort'], 'fly': r['bonusFly']},
        })

    # ---- flights
    flights = []
    for r in db.execute('select * from flightlog where ownerId=? order by date, id', (pid,)):
        start = _ts(r['date'])
        mins = float(r['flytime'] or 0)
        flights.append({
            'sourceId': f'neofly:flightlog:{r["id"]}', 'from': r['departure'], 'to': r['arrival'],
            'start': start, 'end': start + timedelta(minutes=mins), 'minutes': round(mins, 1),
            'distanceNm': r['dist'], 'aircraft': plane_id(r['planeId']), 'landingFpm': r['landingfpm'],
            'crash': bool(r['crash']), 'bonus': {'security': r['bonusSecurity'], 'comfort': r['bonusComfort'], 'fly': r['bonusFly']},
            'missions': [], 'inferred': False,
        })

    # attach each job to the flight it was flown on: same plane, completed during
    # or shortly after the flight. Unmatched completed jobs become inferred flights.
    # Tier 0: same route, within 6 h (NeoFly occasionally stamps jobs hours off).
    # Tier 1: one end matches, completed during or up to 75 min after the flight.
    for j in jobs:
        best, best_key = None, None
        for f in flights:
            if f['aircraft'] != j['plane'] or not j['completedAt']:
                continue
            t, dt = j['completedAt'], abs((j['completedAt'] - f['end']).total_seconds())
            if j['from'] == f['from'] and j['to'] == f['to'] and dt <= 6 * 3600:
                key = (0, dt)
            elif (j['from'] == f['from'] or j['to'] == f['to']) and \
                    f['start'] - timedelta(minutes=5) <= t <= f['end'] + timedelta(minutes=75):
                key = (1, dt)
            else:
                continue
            if best is None or key < best_key:
                best, best_key = f, key
        if best is not None:
            best['missions'].append(j)
        elif j['status'] == 'completed' and j['from'] != j['to'] and airport(j['from']) and airport(j['to']):
            dep, arr = airport(j['from']), airport(j['to'])
            nm = _nm(dep, arr)
            kt = aircraft.get(j['plane'], {}).get('cruiseKt') or 120
            mins = nm / kt * 60 + 15
            flights.append({
                'sourceId': f'neofly:joblog:{j["jobId"]}', 'from': j['from'], 'to': j['to'],
                'start': j['completedAt'] - timedelta(minutes=mins), 'end': j['completedAt'],
                'minutes': round(mins, 1), 'distanceNm': round(nm), 'aircraft': j['plane'], 'landingFpm': None,
                'crash': False, 'bonus': j['bonus'], 'missions': [j], 'inferred': True,
            })

    flights.sort(key=lambda f: f['start'])

    # ---- ledger events that explain moves between flights
    events = []
    rows = db.execute('select * from finances where ownerId=? order by date', (pid,)).fetchall()
    staff_times = {r['date'] for r in rows if (r['description'] or '').startswith('Staff pilot')}
    for r in rows:
        d = r['description'] or ''
        kind = None
        if d.startswith('Airport fees'):
            # a landing fee - unless it belongs to a hired pilot's mission (same timestamp)
            kind = None if r['date'] in staff_times else 'landing-fee'
        elif d.startswith('Buying fuel'):
            kind = 'fuel'
        elif d.startswith('Moving pilot to'):
            kind = 'pilot-move'
        elif d.startswith('Aircraft movement to'):
            kind = 'aircraft-move'
        elif d.startswith('Hotel fees'):
            kind = 'hotel'
        elif d.startswith('Restaurant fees'):
            kind = 'restaurant'
        elif d.startswith('Buying plane'):
            kind = 'aircraft-bought'
        if kind:
            m = re.search(r':\s*([A-Z0-9]{3,5})\b', d)
            events.append({'kind': kind, 'at': _ts(r['date']), 'text': d, 'cost': r['expenses'] or 0,
                           'income': r['incomes'] or 0, 'ident': m.group(1) if (m and kind.endswith('move')) else None,
                           'subject': d.split(':', 1)[1].strip() if ':' in d else None})

    # where hired (AI) pilots flew your planes - tells us where a plane really was
    ai_flights = []
    for r in db.execute('select * from aipilotflightlog where ownerId=? order by dateStart', (pid,)):
        ai_flights.append({'id': r['id'], 'aircraft': plane_id(r['aircraftID']), 'from': r['departure'], 'to': r['destination'],
                           'start': _ts(r['dateStart']), 'end': _ts(r['dateEnd']), 'pilot': r['pilotName'],
                           'status': r['status'], 'pay': r['pay'], 'distanceNm': r['distance'],
                           'type': MISSION_TYPES.get(r['missiontype'], f'Mission {r["missiontype"]}')})
        airport(r['departure']), airport(r['destination'])

    # resolve every airport now: the databases close when load() returns
    for f in flights:
        airport(f['from']), airport(f['to'])
    for e in events:
        if e['ident']:
            airport(e['ident'])
    return {'pilot': pilot, 'pilots': pilots, 'aircraft': aircraft, 'flights': flights, 'events': events, 'aiFlights': ai_flights,
            'airport': lambda ident: cache.get((ident or '').strip().upper()),
            'airports': {k: v for k, v in cache.items() if v}}


def _nm(a, b):
    from math import radians, sin, cos, asin, sqrt
    la1, lo1, la2, lo2 = map(radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 3440.065 * asin(sqrt(h))
