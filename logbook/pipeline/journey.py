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
    'reposition': {'label': 'NeoFly reposition', 'icon': '🔀', 'kmh': 1e9, 'overhead': 0},
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


def build(flights, airport, events, photos, overrides, aircraft=None, ai_flights=()):
    gap_over = overrides.get('gaps', {})
    leg_over = overrides.get('legs', {})
    legs = []
    airports = {}
    ctx = {'flights': flights, 'events': events, 'photos': photos, 'aircraft': aircraft or {}, 'ai': list(ai_flights)}

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
            legs.append(_bridge(prev, f, airports[prev['to']], dep, gap_over, ctx))
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
        prev = {'to': arr['ident'], 'end': f['end'], 'id': leg_id, 'aircraft': f['aircraft']}

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


def _bridge(prev, nxt, a, b, gap_over, ctx):
    """Decide what happened between two flights that don't join up, from evidence:

    1. Same aircraft before and after, and NeoFly never charged to move it
       -> you flew it; NeoFly just didn't log it.
    2. The aircraft you arrived in is next seen departing from where the next
       flight starts (your own flights or a hired pilot's) and wasn't paid-moved
       -> you flew it there.
    3. NeoFly charged to move an aircraft / the pilot during the gap
       -> repositioned by NeoFly / the sim.
    4. Otherwise a ground or airline transfer chosen by distance and geography.
    overrides.json 'gaps' can force any of these.
    """
    start, end = prev['end'], nxt['start']
    key = f'{a["ident"]}>{b["ident"]}'
    o = gap_over.get(key, {})
    window = lambda e: start - timedelta(minutes=30) <= e['at'] <= end + timedelta(minutes=30)
    moves = [e for e in ctx['events'] if e['kind'] in ('pilot-move', 'aircraft-move') and window(e)
             and e['ident'] in (a['ident'], b['ident'])]
    shots = [p for p in ctx['photos'] if start <= datetime.fromisoformat(p['takenAt']) <= end]
    names = {k: v.get('name') for k, v in ctx['aircraft'].items()}

    flown_in, why = None, []
    if o.get('mode') == 'flight':
        flown_in = o.get('aircraft') or prev['aircraft']
        why.append('Marked as flown in overrides.json.')
    elif not o.get('mode') and not any(e['kind'] == 'aircraft-move' and e['ident'] == b['ident'] for e in moves):
        if prev['aircraft'] == nxt['aircraft']:
            flown_in = prev['aircraft']
            why.append(f'The {names.get(flown_in, "same aircraft")} flew the leg before and the leg after, '
                       f'and NeoFly never charged to move it, so you flew it here.')
        else:
            seen = _next_departure(prev['aircraft'], start, ctx)
            if seen and seen[0] == b['ident']:
                flown_in = prev['aircraft']
                why.append(f'The {names.get(flown_in, "aircraft")} you arrived in next departs from {b["ident"]} '
                           f'({seen[1]}), with no paid move, so you flew it here.')
    if flown_in:
        if shots:
            why.append(f'{len(shots)} screenshot{"s" if len(shots) > 1 else ""} taken during this time.')
        return _unlogged_flight(prev, nxt, a, b, flown_in, why, shots, ctx, o)

    km = km_between(a, b)
    notes = [f'NeoFly ledger: {e["text"]} (${e["cost"]:,})' for e in moves]
    if o.get('mode'):
        mode = o['mode']
    elif any(e['kind'] == 'aircraft-move' for e in moves) or any(e['kind'] == 'pilot-move' for e in moves):
        mode = 'reposition'
        notes.insert(0, f'NeoFly moved the aircraft for you (no flight), and the next flight in the sim started at {b["ident"]}.')
    else:
        mode = pick_mode(a, b, km)
    m = MODES[mode]
    est = m['overhead'] + km / m['kmh'] * 60
    if o.get('note'):
        notes.insert(0, o['note'])
    return {
        'id': f'gap-{prev["id"]}', 'kind': 'ground', 'mode': mode, 'modeLabel': o.get('label', m['label']),
        'icon': m['icon'], 'from': a['ident'], 'to': b['ident'], 'start': iso(start), 'end': iso(end),
        'distanceKm': round(km, 1), 'distanceNm': round(km / 1.852), 'estimatedMinutes': round(est),
        'minutes': round((end - start).total_seconds() / 60, 1) if end and start else None,
        'notes': notes, 'auto': not o.get('mode'), 'events': [],
    }


def _next_departure(plane, after, ctx):
    """Where the plane is next seen taking off, from your flights or hired pilots'."""
    cands = [(f['start'], f['from'], 'your next flight in it') for f in ctx['flights']
             if f['aircraft'] == plane and f['start'] >= after]
    cands += [(f['start'], f['from'], f'hired pilot {f["pilot"]}, {f["start"]:%d %b}') for f in ctx['ai']
              if f['aircraft'] == plane and f['start'] and f['start'] >= after]
    if not cands:
        return None
    t, ident, what = min(cands)
    return ident, what


def _unlogged_flight(prev, nxt, a, b, plane, why, shots, ctx, o):
    """A flight you flew that NeoFly didn't record. Its times are estimated:
    landing = a NeoFly landing fee during the gap if there is one; otherwise the
    flight is centred on screenshots taken during the gap; otherwise it starts
    when that aircraft was refuelled; otherwise it lands shortly before the next flight."""
    gap0, gap1 = prev['end'], nxt['start']
    nm = km_between(a, b) / 1.852
    ac = ctx['aircraft'].get(plane, {})
    mins = nm / (ac.get('cruiseKt') or 150) * 60 + 15
    dur = timedelta(minutes=mins)
    fees = [e['at'] for e in ctx['events'] if e['kind'] == 'landing-fee'
            and gap0 + dur * 0.6 <= e['at'] <= gap1 - timedelta(minutes=2)]
    fuel = [e['at'] for e in ctx['events'] if e['kind'] == 'fuel' and e['subject'] == ac.get('name')
            and gap0 <= e['at'] <= gap1 - dur]
    if fees:
        end = fees[0]
        start = end - dur
        why.append(f'Landing time from the NeoFly landing fee at {end:%H:%M}; takeoff estimated from distance.')
    elif shots:
        ts = [datetime.fromisoformat(p['takenAt']) for p in shots]
        mid = min(ts) + (max(ts) - min(ts)) / 2
        start = mid - dur / 2
        why.append('Times estimated around your screenshots and the distance.')
    elif fuel:
        start = fuel[-1] + timedelta(minutes=5)
        why.append(f'Takeoff estimated from refuelling at {fuel[-1]:%H:%M}; landing from distance.')
    else:
        start = gap1 - timedelta(minutes=20) - dur
        why.append('Times estimated from distance (placed just before the next flight).')
    start = max(gap0, min(start, gap1 - dur))
    end = min(gap1, start + dur)
    return {
        'id': f'unlogged-{prev["id"]}', 'kind': 'flight', 'from': a['ident'], 'to': b['ident'],
        'start': iso(start), 'end': iso(end), 'minutes': round((end - start).total_seconds() / 60, 1),
        'distanceNm': round(nm), 'aircraft': plane, 'landingFpm': None, 'crash': False, 'bonus': {},
        'inferred': True, 'unlogged': True, 'source': 'evidence', 'local': False, 'missions': [],
        'evidence': why, **{k: v for k, v in o.items() if k not in ('mode', 'aircraft')},
    }


def _place_events(events, stops, legs):
    # ground legs hold the time between two flights when there was a gap, so they
    # collect events too; stops are tried first
    holders = stops + [l for l in legs if l['kind'] == 'ground']
    for e in events:
        if e['kind'] not in ('hotel', 'restaurant', 'aircraft-bought'):
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
