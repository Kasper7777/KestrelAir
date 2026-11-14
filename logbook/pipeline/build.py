"""Build web/data/logbook.json from every configured source.

    uv run --no-project --with pillow python pipeline/build.py

Output schema (version 1) - the web app only ever reads this file:
  meta      {version, builtAt, sources[]}
  pilot     {name, rank, ...}
  aircraft  {id: {...}}
  airports  {ident: {...}}
  legs      [{id, kind: flight|ground, from, to, start, end, ...}]
  stops     [{id, airport, arrive, depart, photos[], events[]}]
  photos    {id: {src, thumb, takenAt, leg|stop}}
  unplacedPhotos [id]
  stats     {...}

New sources (another sim, a CSV logbook, a scrapbook folder) go in pipeline/importers
and are merged here; the web side doesn't need to change for new data.
"""
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(HERE, 'importers')]

import journey  # noqa: E402
import neofly  # noqa: E402
import screenshots  # noqa: E402


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def main():
    cfg = load_json(os.path.join(ROOT, 'config.json'), {})
    overrides = load_json(os.path.join(ROOT, 'overrides.json'), {})
    web = os.path.join(ROOT, 'web')
    os.makedirs(os.path.join(web, 'data'), exist_ok=True)

    nf_dir = os.path.expandvars(cfg.get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly'))
    print(f'NeoFly: {nf_dir}')
    nf = neofly.load(nf_dir)
    print(f'  {len(nf["flights"])} flights ({sum(f["inferred"] for f in nf["flights"])} recovered from the job log)')

    sources = screenshots.expand_sources(cfg.get('photos', {}).get('sources', [{'auto': 'steam'}]))
    print('Screenshots: ' + ', '.join(s['path'] for s in sources))
    photos = screenshots.scan(sources, os.path.join(web, 'media'))
    print(f'  {len(photos)} images')

    legs, stops, airports, unplaced = journey.build(nf['flights'], nf['airport'], nf['events'], photos, overrides)

    # general-purpose capture folders (Windows/Game Bar/NVIDIA) also hold non-sim
    # shots: keep those only when they were taken during the journey
    strict = {s.get('label') for s in sources if s.get('onlyDuringJourney')}
    drop = {pid for pid in unplaced if next(p for p in photos if p['id'] == pid)['source'] in strict}
    for p in photos:
        if p['id'] in drop:
            for rel in (p['src'], p['thumb']):
                try:
                    os.remove(os.path.join(web, rel))
                except OSError:
                    pass
    photos = [p for p in photos if p['id'] not in drop]
    unplaced = [pid for pid in unplaced if pid not in drop]
    # forget copies of images that were deleted from the source folders
    keep = {p['id'] + '.jpg' for p in photos}
    for sub in ('photos', 'thumbs'):
        d = os.path.join(web, 'media', sub)
        for fn in os.listdir(d) if os.path.isdir(d) else []:
            if fn not in keep:
                os.remove(os.path.join(d, fn))

    used = {l['aircraft'] for l in legs if l['kind'] == 'flight'}
    aircraft = {k: v for k, v in nf['aircraft'].items() if k in used}
    for k, v in overrides.get('aircraft', {}).items():
        aircraft.setdefault(k, {}).update(v)

    flights = [l for l in legs if l['kind'] == 'flight']
    ground = [l for l in legs if l['kind'] == 'ground']
    landings = [l['landingFpm'] for l in flights if l.get('landingFpm')]
    countries = sorted({a['country']['name'] for a in airports.values()})
    stats = {
        'flights': len(flights), 'hours': round(sum(l['minutes'] for l in flights) / 60, 1),
        'distanceNm': sum(l['distanceNm'] or 0 for l in flights), 'airports': len(airports),
        'countries': len(countries), 'countryList': countries, 'aircraft': len(aircraft),
        'transfers': len(ground), 'transferKm': round(sum(l['distanceKm'] for l in ground)),
        'earnings': sum(m['reward'] or 0 for l in flights for m in l['missions'] if m['status'] == 'completed'),
        'passengers': sum(m['pax'] or 0 for l in flights for m in l['missions'] if m['status'] == 'completed'),
        'cargoLbs': sum(m['cargoLbs'] or 0 for l in flights for m in l['missions']
                        if m['status'] == 'completed' and m['type'] != 'Passengers'),
        'softestLanding': max(landings) if landings else None, 'averageLanding': round(sum(landings) / len(landings)) if landings else None,
        'longestFlight': max(flights, key=lambda l: l['minutes'])['id'] if flights else None,
        'photos': len(photos), 'first': flights[0]['start'] if flights else None, 'last': flights[-1]['end'] if flights else None,
    }

    out = {
        'meta': {'version': 1, 'builtAt': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                 'sources': ['neofly', 'screenshots'], 'timezone': 'local PC time'},
        'pilot': nf['pilot'], 'aircraft': aircraft, 'airports': airports, 'legs': legs, 'stops': stops,
        'photos': {p['id']: p for p in photos},
        'unplacedPhotos': unplaced, 'stats': stats,
    }
    avatar = cfg.get('pilot', {}).get('photo')
    if avatar:
        src = os.path.normpath(os.path.join(ROOT, avatar))
        if os.path.exists(src):
            dst = os.path.join(web, 'media', 'pilot.jpg')
            if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
                import shutil
                shutil.copy2(src, dst)
            out['pilot']['photo'] = 'media/pilot.jpg'

    with open(os.path.join(web, 'data', 'logbook.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    placed = len(photos) - len(unplaced)
    print(f'Journey: {len(flights)} flights + {len(ground)} transfers across {len(airports)} airports, '
          f'{len(countries)} countries; {placed}/{len(photos)} photos placed')
    for g in ground:
        print(f'  gap {g["from"]} -> {g["to"]}: {g["distanceKm"]} km, {g["mode"]}' + (f'  [{g["notes"][0]}]' if g['notes'] else ''))


if __name__ == '__main__':
    main()
