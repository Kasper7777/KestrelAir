"""Turns imported flights into one continuous journey.

- Orders flights by takeoff time.
- Wherever one flight ends somewhere other than where the next starts, inserts a
  ground/transfer leg (taxi, train, ferry or airline seat) so the line on the map
  never breaks. Mode comes from distance + geography, and can be forced per gap
  in overrides.json.
- Builds "stops" (time spent at an airport between legs).
- Places every photo on the flight it was taken during, else on the stop / transfer
  it falls in, else in "unplaced".

Leg ids are derived from the source record (e.g. nf-fl-12), so anything attached to
a leg later (scrapbook notes, captions) survives rebuilds.
"""
from datetime import datetime, timedelta
from math import radians, sin, cos, asin, sqrt

ISLANDS = {'JE', 'GG', 'IM', 'CY', 'MT', 'JM', 'FK', 'IS', 'JP', 'GB', 'IE', 'NZ', 'CU', 'BS', 'TT', 'BB',
           'KY', 'CV', 'TW', 'PH', 'ID', 'SG', 'LK', 'GU', 'FJ', 'PR', 'DO', 'HT', 'BM', 'GL', 'AU'}
# rough door-to-door speeds (km/h) and fixed overhead (min) for estimating transfer times
MODES = {
    'walk':    {'label': 'On foot',          'icon': '🚶', 'kmh': 4.5, 'overhead': 0},
    'taxi':    {'label': 'Taxi',             'icon': '🚕', 'kmh': 55,  'overhead': 10},
    'train':   {'label': 'Train / coach',    'icon': '🚆', 'kmh': 95,  'overhead': 40},
    'ferry':   {'label': 'Ferry',            'icon': '⛴️', 'kmh': 35,  'overhead': 60},
    'airline': {'label': 'Airline (as pax)', 'icon': '🎫', 'kmh': 720, 'overhead': 150},
}


def km_between(a, b):
    la1, lo1, la2, lo2 = map(radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def pick_mode(a, b, km):
    if km < 3:
        return 'walk'
    ia, ib = a['country'].get('iso'), b['country'].get('iso')
    water = (ia != ib) and (ia in ISLANDS or ib in ISLANDS)
    if km <= 90 and not water:
        return 'taxi'
    if km <= 500 and water:
        return 'ferry'
    if km <= 700 and not water:
        return 'train'
    return 'airline'


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S') if dt else None


def build(flights, airport, events, photos, overrides):
    gap_over = overrides.get('gaps', {})
    leg_over = overrides.get('legs', {})
    legs = []
    airports = {}

    def ap(ident):
        a = airport(ident)
        if a:
            airports[a['ident']] = a
        return a

    prev = None
    for f in flights:
        dep, arr = ap(f['from']), ap(f['to'])
        if not dep or not arr:
            print(f'  ! skipping {f["sourceId"]}: unknown airport {f["from"]}/{f["to"]}')
            continue
        if prev and prev['to'] != f['from']:
            legs.append(_ground(prev, f, airports[prev['to']], dep, gap_over, events))
        leg_id = _leg_id(f['sourceId'])
        legs.append({
            'id': leg_id, 'kind': 'flight', 'from': dep['ident'], 'to': arr['ident'],
            'start': iso(f['start']), 'end': iso(f['end']), 'minutes': f['minutes'],
            'distanceNm': f['distanceNm'] if f['distanceNm'] else round(km_between(dep, arr) / 1.852),
            'aircraft': f['aircraft'], 'landingFpm': f['landingFpm'] or None, 'crash': f['crash'],
            'bonus': f['bonus'], 'inferred': f['inferred'], 'source': f['sourceId'],
            'local': dep['ident'] == arr['ident'],
            'missions': [_mission(m) for m in f['missions']],
            **leg_over.get(leg_id, {}),
        })
        prev = {'to': arr['ident'], 'end': f['end'], 'id': leg_id}

    # stops: time on the ground at an airport between two legs
    stops = []
    for i, leg in enumerate(legs):
        nxt = legs[i + 1] if i + 1 < len(legs) else None
        stops.append({
            'id': f'stop-{leg["id"]}', 'airport': leg['to'], 'arrive': leg['end'],
            'depart': nxt['start'] if nxt else None, 'after': leg['id'], 'before': nxt['id'] if nxt else None,
            'events': [], 'photos': [],
        })
    if legs:
        stops.insert(0, {'id': 'stop-origin', 'airport': legs[0]['from'], 'arrive': None, 'depart': legs[0]['start'],
                         'after': None, 'before': legs[0]['id'], 'events': [], 'photos': []})

    for leg in legs:
        leg.setdefault('photos', [])
    _place_events(events, stops, legs)
    unplaced = _place_photos(photos, legs, stops)
    return legs, stops, airports, unplaced


def _leg_id(source):
    _, table, num = source.split(':')
    return f'nf-{"fl" if table == "flightlog" else "job"}-{num}'


def _mission(m):
    return {k: (iso(v) if isinstance(v, datetime) else v) for k, v in m.items() if k != 'plane'}


def _ground(prev, nxt, a, b, gap_over, events):
    km = km_between(a, b)
    key = f'{a["ident"]}>{b["ident"]}'
    o = gap_over.get(key, {})
    mode = o.get('mode') or pick_mode(a, b, km)
    m = MODES[mode]
    est = m['overhead'] + km / m['kmh'] * 60
    start, end = prev['end'], nxt['start']
    notes = []
    for e in events:
        if e['kind'] in ('pilot-move', 'aircraft-move') and e['ident'] == b['ident'] and \
                start - timedelta(minutes=30) <= e['at'] <= end + timedelta(minutes=30):
            notes.append(f'NeoFly ledger: {e["text"]} (${e["cost"]:,})')
    if o.get('note'):
        notes.insert(0, o['note'])
    return {
        'id': f'gap-{prev["id"]}', 'kind': 'ground', 'mode': mode, 'modeLabel': o.get('label', m['label']),
        'icon': m['icon'], 'from': a['ident'], 'to': b['ident'], 'start': iso(start), 'end': iso(end),
        'distanceKm': round(km, 1), 'distanceNm': round(km / 1.852), 'estimatedMinutes': round(est),
        'minutes': round((end - start).total_seconds() / 60, 1) if end and start else None,
        'notes': notes, 'auto': not o.get('mode'), 'events': [],
    }


def _place_events(events, stops, legs):
    # ground legs hold the time between two flights when there was a gap, so they
    # collect events too; stops are tried first
    holders = stops + [l for l in legs if l['kind'] == 'ground']
    for e in events:
        if e['kind'] in ('pilot-move', 'aircraft-move'):
            continue
        for s in holders:
            lo = datetime.fromisoformat(s.get('arrive', s.get('start')) or '1900-01-01T00:00:00')
            hi = datetime.fromisoformat(s.get('depart', s.get('end')) or '9000-01-01T00:00:00')
            if lo - timedelta(minutes=10) <= e['at'] <= hi + timedelta(minutes=5):
                s['events'].append({'kind': e['kind'], 'at': iso(e['at']), 'text': e['text'],
                                    'cost': e['cost'], 'income': e['income']})
                break


def _place_photos(photos, legs, stops, before=40, after=20):
    unplaced = []
    spans = [(l, datetime.fromisoformat(l['start']), datetime.fromisoformat(l['end'])) for l in legs if l['kind'] == 'flight']
    for p in photos:
        t = datetime.fromisoformat(p['takenAt'])
        hit = next((l for l, s, e in spans if s <= t <= e), None)
        if hit is None:
            near = [(min(abs((t - s).total_seconds()), abs((t - e).total_seconds())), l) for l, s, e in spans
                    if s - timedelta(minutes=before) <= t <= e + timedelta(minutes=after)]
            hit = min(near, key=lambda x: x[0])[1] if near else None
        if hit is not None:
            hit['photos'].append(p['id'])
            p['leg'] = hit['id']
            continue
        gl = next((l for l in legs if l['kind'] == 'ground'
                   and datetime.fromisoformat(l['start']) <= t <= datetime.fromisoformat(l['end'])), None)
        if gl is not None:
            gl['photos'].append(p['id'])
            p['leg'] = gl['id']
            continue
        stop = None
        for s in stops:
            lo = datetime.fromisoformat(s['arrive']) if s['arrive'] else None
            hi = datetime.fromisoformat(s['depart']) if s['depart'] else datetime.max
            if lo is None:
                continue  # nothing before the first takeoff counts
            if lo <= t <= hi:
                stop = s
                break
        if stop is not None:
            stop['photos'].append(p['id'])
            p['stop'] = stop['id']
        else:
            unplaced.append(p['id'])
    return unplaced
