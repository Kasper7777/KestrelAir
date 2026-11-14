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


def slugify(name):
    import re
    return re.sub(r'[^a-z0-9]+', '-', (name or 'pilot').lower()).strip('-') or 'pilot'


def pilot_dir(name):
    return os.path.join(ROOT, 'backup', 'pilots', slugify(name))


def main(fetch=True):
    """fetch=False: build only from NeoFly, screenshots and what's already saved (fast,
    offline). fetch=True: also look up anything new online (Wikipedia, places, flags)."""
    cfg = load_json(os.path.join(ROOT, 'config.json'), {})
    overrides = load_json(os.path.join(ROOT, 'overrides.json'), {})
    web = os.path.join(ROOT, 'web')
    os.makedirs(os.path.join(web, 'data'), exist_ok=True)
    pcfg = cfg.get('pilot', {})
    chosen = pcfg.get('neofly') if pcfg.get('neofly') not in (None, '', 'auto') else None

    nf_dir = os.path.expandvars(cfg.get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly'))
    print(f'NeoFly: {nf_dir}' + (f' (pilot {chosen})' if chosen else ''))
    backup = os.path.join(ROOT, 'backup')
    cache_path = os.path.join(backup, 'airports.json')
    try:
        cache = load_json(cache_path, {})
    except ValueError:
        cache = {}
    # without NeoFly on this PC, read the newest saved copy: the chosen pilot's, else any pilot's
    fallback = os.path.join(pilot_dir(chosen), 'neofly') if chosen else None
    if not fallback or not os.path.isdir(fallback):
        root = os.path.join(backup, 'pilots')
        dirs = [os.path.join(root, d, 'neofly') for d in sorted(os.listdir(root))] if os.path.isdir(root) else []
        fallback = next((d for d in dirs if os.path.isdir(d)), None)
    nf = neofly.load(nf_dir, fallback, cache, chosen)
    me = pilot_dir(nf['pilot']['name'])
    os.makedirs(me, exist_ok=True)
    print(f'  {len(nf["flights"])} flights ({sum(f["inferred"] for f in nf["flights"])} recovered from the job log), from {nf["source"]}')
    os.makedirs(backup, exist_ok=True)
    cache.update(nf['airports'])  # lets another PC without NeoFly still place airports
    with open(cache_path + '.tmp', 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(cache_path + '.tmp', cache_path)

    sources = screenshots.expand_sources(cfg.get('photos', {}).get('sources', [{'auto': 'steam'}]))
    # this pilot's originals saved by the Back up button: on another PC these are the photos
    shots = os.path.join(me, 'photos')
    if os.path.isdir(shots):
        sources += [{'label': d, 'path': os.path.join(shots, d)} for d in sorted(os.listdir(shots))
                    if os.path.isdir(os.path.join(shots, d))]
    print('Screenshots: ' + ', '.join(s['path'] for s in sources))
    photos = screenshots.scan(sources, os.path.join(web, 'media'))
    print(f'  {len(photos)} images')

    legs, stops, airports, unplaced = journey.build(nf['flights'], nf['airport'], nf['events'], photos, overrides,
                                                    nf['aircraft'], nf['aiFlights'])

    # each airport's country from the real borders it sits inside (ICAO prefixes are only a fallback)
    import geocountry
    import countries as ctab
    names = {}
    for code, (nm, iso) in ctab.PREFIXES.items():
        names.setdefault(iso, nm)
    names.update({'JE': 'Jersey', 'GG': 'Guernsey', 'US': 'United States', 'GB': 'United Kingdom'})
    cpath = os.path.join(web, 'geo', 'countries.json')
    for ident, a in airports.items():
        found = geocountry.country_at(a['lon'], a['lat'], cpath)
        if not found:
            continue
        iso, ne_name, how = found
        if how == 'near' and a['country'].get('iso'):
            continue   # just off a coast (e.g. Alderney): trust the airport's own registry country over the nearest shore
        if a['country'].get('iso') != iso:
            print(f'  country: {ident} was {a["country"].get("name")}, its location says {ne_name} ({how})')
        a['country'] = {'name': names.get(iso, ne_name), 'iso': iso}

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

    # Wikipedia (cached in backup/wiki; only new airports/aircraft are looked up)
    import wikipedia
    import shutil
    wiki_dir = os.path.join(backup, 'wiki')
    media_wiki = os.path.join(web, 'media', 'wiki')
    os.makedirs(media_wiki, exist_ok=True)

    def publish(entry):
        e = {k: v for k, v in entry.items() if k not in ('image', 'imageFile', 'fetched')}
        f = entry.get('imageFile')
        if f and os.path.exists(os.path.join(wiki_dir, 'img', f)):
            dst = os.path.join(media_wiki, f)
            if not os.path.exists(dst):
                shutil.copy2(os.path.join(wiki_dir, 'img', f), dst)
            e['image'] = f'media/wiki/{f}'
        return e

    try:
        aw = wikipedia.airports(airports, wiki_dir, fetch)
        for ident, a in airports.items():
            if aw.get(ident, {}).get('title'):
                a['wiki'] = publish(aw[ident])
        for k, w in wikipedia.aircraft(aircraft, wiki_dir, overrides.get('aircraft'), fetch).items():
            aircraft[k]['wiki'] = publish(w)
    except Exception as e:
        print(f'  ! Wikipedia step skipped: {e}')

    # aircraft dossiers: real history/specs/photos + real manuals found on this PC
    try:
        import aircraftinfo
        repo = os.path.dirname(ROOT)
        roots = cfg.get('manuals', {}).get('folders') or [
            repo, r'%USERPROFILE%\Downloads', r'%USERPROFILE%\Documents', r'%USERPROFILE%\Desktop',
            r'%APPDATA%\Microsoft Flight Simulator 2024\Packages\Community',
            r'%APPDATA%\Microsoft Flight Simulator\Packages\Community',
            r'%LOCALAPPDATA%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\Packages\Community']
        registry = {}
        for k, a in aircraft.items():
            title, rx = wikipedia.title_for({**a, 'id': k}, overrides.get('aircraft'))
            if title:
                d = aircraftinfo.details(title, wiki_dir, fetch)
                if d:
                    a['dossier'] = {'title': d.get('title'), 'url': d.get('url'), 'history': d.get('history', []),
                                    'specs': d.get('specs', []),
                                    'photos': [{'src': publish({'imageFile': ph['file']}).get('image'), 'credit': ph['credit']}
                                               for ph in d.get('photos', []) if publish({'imageFile': ph['file']}).get('image')]}
            if rx:
                mans = aircraftinfo.find_manuals([rx], roots)
                a['manuals'] = [{k2: m[k2] for k2 in ('id', 'title', 'mb')} for m in mans]
                registry.update({m['id']: m['path'] for m in mans})
        with open(os.path.join(ROOT, 'manuals-index.json'), 'w', encoding='utf-8') as fh:   # server-side only, not served
            json.dump(registry, fh, indent=1)
        print(f'Aircraft: {sum(1 for a in aircraft.values() if a.get("dossier"))} dossiers, {len(registry)} manuals found on this PC')
    except Exception as e:
        print(f'  ! aircraft dossiers skipped: {e}')

    # layover diary: real places near airports where the pilot stayed 8 h or more
    try:
        import places as places_mod
        import diary
        long_stays = {}
        for s in stops:
            if s.get('arrive'):
                end = datetime.fromisoformat(s['depart']) if s.get('depart') else datetime.now()
                if (end - datetime.fromisoformat(s['arrive'])).total_seconds() >= diary.MIN_HOURS * 3600:
                    long_stays[s['airport']] = airports[s['airport']]
        pl = places_mod.for_airports(long_stays, os.path.join(backup, 'places'), fetch)
        n = diary.build(stops, legs, airports, pl, os.path.join(web, 'media', 'places'), os.path.join(backup, 'places', 'img'),
                        places_mod, fetch)
        places_mod.save_cache(os.path.join(backup, 'places'))
        print(f'Diary: {n} layovers written up')
    except Exception as e:
        import traceback
        print(f'  ! diary skipped: {e}')
        traceback.print_exc()

    # visited countries coloured in with their flags (only new countries are drawn)
    try:
        import flagfills
        isos = sorted({a['country']['iso'] for a in airports.values() if a['country'].get('iso')})
        n = flagfills.build(isos, os.path.join(web, 'geo', 'countries.json'), os.path.join(web, 'geo', 'flags'),
                            os.path.join(backup, 'flags'), fetch)
        if n:
            print(f'  flag fills: {n} new countries')
    except Exception as e:
        print(f'  ! flag fills skipped: {e}')

    flights = [l for l in legs if l['kind'] == 'flight']
    ground = [l for l in legs if l['kind'] == 'ground']
    landings = [l['landingFpm'] for l in flights if l.get('landingFpm')]
    countries = sorted({a['country']['name'] for a in airports.values()})
    stats = {
        'flights': len(flights), 'hours': round(sum(l['minutes'] for l in flights) / 60, 1),
        'distanceNm': sum(l['distanceNm'] or 0 for l in flights), 'airports': len(airports),
        'countries': len(countries), 'countryList': countries,
        'countryIsos': sorted({a['country']['iso'] for a in airports.values() if a['country'].get('iso')}), 'aircraft': len(aircraft),
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
        'meta': {'version': 1, 'builtAt': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), 'online': fetch,
                 'sources': ['neofly', 'screenshots'], 'neofly': nf['source'], 'timezone': 'local PC time',
                 'pilots': [p['name'] for p in nf['pilots']], 'pilotSlug': slugify(nf['pilot']['name']), 'pilotChosen': chosen or ''},
        'pilot': nf['pilot'], 'aircraft': aircraft, 'airports': airports, 'legs': legs, 'stops': stops,
        'photos': {p['id']: p for p in photos},
        'unplacedPhotos': unplaced, 'stats': stats,
    }
    # flights your hired pilots flew in company aircraft (shown in the logbook's Company view)
    company = []
    for f in nf['aiFlights']:
        if not (f['start'] and f['end'] and f['end'] > f['start']):
            continue
        dep, arr = nf['airport'](f['from']), nf['airport'](f['to'])
        if not dep or not arr:
            continue
        company.append({'id': f'ai-{f["id"]}', 'pilot': f['pilot'], 'from': dep['ident'], 'to': arr['ident'],
                        'fromName': dep['name'], 'toName': arr['name'],
                        'fromPos': [dep['lon'], dep['lat']], 'toPos': [arr['lon'], arr['lat']],
                        'start': journey.iso(f['start']), 'end': journey.iso(f['end']),
                        'minutes': round((f['end'] - f['start']).total_seconds() / 60, 1), 'distanceNm': f['distanceNm'],
                        'aircraft': f['aircraft'], 'aircraftName': nf['aircraft'].get(f['aircraft'], {}).get('name'),
                        'aircraftLivery': nf['aircraft'].get(f['aircraft'], {}).get('livery'),
                        'engines': nf['aircraft'].get(f['aircraft'], {}).get('engines'),
                        'type': f['type'], 'pay': f['pay'], 'completed': f['status'] == 0})
    out['companyFlights'] = company
    print(f'Company: {len(company)} flights by hired pilots')
    # per-pilot settings: display name and photo (set from the app's Pilot settings)
    mine = pcfg.get('pilots', {}).get(nf['pilot']['name'], {})
    out['pilot']['character'] = mine.get('displayName') or nf['pilot']['name']
    candidates = [os.path.join(me, 'pilot.jpg')] + ([os.path.normpath(os.path.join(ROOT, mine['photo']))] if mine.get('photo') else [])
    src = next((c for c in candidates if os.path.exists(c)), None)
    dst = os.path.join(web, 'media', 'pilot.jpg')
    if src:
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src) or os.path.getsize(dst) != os.path.getsize(src):
            import shutil
            shutil.copy2(src, dst)
        out['pilot']['photo'] = 'media/pilot.jpg?v=' + str(int(os.path.getmtime(src)))
    elif os.path.exists(dst):
        os.remove(dst)  # another pilot's photo must not linger

    # self-check before publishing: anything inconsistent is reported (and in meta, for the app)
    try:
        import selftest
        problems = selftest.run(out, web)
    except Exception as e:
        problems = [f'self-check failed to run: {e}']
    out['meta']['checks'] = problems
    print('Self-check: ' + ('all good' if not problems else f'{len(problems)} problem(s)'))
    for p in problems[:20]:
        print(f'  ! {p}')

    # write atomically so the page never reads a half-written file
    tmp = os.path.join(web, 'data', 'logbook.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(web, 'data', 'logbook.json'))
    placed = len(photos) - len(unplaced)
    print(f'Journey: {len(flights)} flights + {len(ground)} transfers across {len(airports)} airports, '
          f'{len(countries)} countries; {placed}/{len(photos)} photos placed')
    for g in ground:
        print(f'  gap {g["from"]} -> {g["to"]}: {g["distanceKm"]} km, {g["mode"]}' + (f'  [{g["notes"][0]}]' if g['notes'] else ''))
    for f in flights:
        if f.get('unlogged'):
            print(f'  unlogged flight {f["from"]} -> {f["to"]} in {aircraft.get(f["aircraft"], {}).get("name")}: '
                  f'{f["start"]} .. {f["end"]} ({len(f.get("photos", []))} photos)')


if __name__ == '__main__':
    main()
