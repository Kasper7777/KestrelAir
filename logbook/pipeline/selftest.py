"""Self-check run at the end of every build. Returns a list of problems (empty = all good).

Checks that what the app is about to show is consistent:
- every leg points at airports that exist and have coordinates
- every airport sits inside (or right beside) the country it's labelled with
- every visited country has a valid flag fill, and every fill is sane
- every photo / picture the page references exists on disk
"""
import json
import os
import re

import flagfills
import geocountry


def run(db, web):
    problems = []
    airports = db['airports']
    cpath = os.path.join(web, 'geo', 'countries.json')
    for l in db['legs']:
        for k in ('from', 'to'):
            a = airports.get(l[k])
            if not a or a.get('lat') is None:
                problems.append(f'leg {l["id"]}: airport {l[k]} missing')
    for ident, a in airports.items():
        r = geocountry.country_at(a['lon'], a['lat'], cpath)
        if not (a.get('country') or {}).get('iso'):
            problems.append(f'{ident}: no country')
        elif r and r[2] == 'border' and r[0] != a['country']['iso']:
            problems.append(f'{ident}: labelled {a["country"]["name"]} but sits inside {r[1]} ({r[0]})')
    index_path = os.path.join(web, 'geo', 'flags.json')
    problems += flagfills.validate(index_path, os.path.join(web, 'geo', 'flags'))
    try:
        fills = json.load(open(index_path, encoding='utf-8')).get('countries', {})
    except (OSError, ValueError):
        fills = {}
    for iso in db['stats'].get('countryIsos', []):
        if iso not in fills:
            problems.append(f'{iso}: visited but has no flag fill yet')
    refs = set(re.findall(r'"((?:media|geo)/[^"?]+)', json.dumps(db)))
    for r in sorted(refs):
        if not os.path.exists(os.path.join(web, r)):
            problems.append(f'missing file {r}')
    return problems
