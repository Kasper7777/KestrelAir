"""Wikipedia facts for airports and aircraft types.

Looked up once per airport / aircraft and cached in backup/wiki/ (with the
picture), so later builds are instant, work offline, and travel with the repo.

Airports: Wikidata by ICAO code (P239) -> English Wikipedia article, plus a few
facts (city served, opened, operator). Unofficial codes (7FL6, CEX3...) fall
back to a Wikipedia geosearch near the airport's coordinates.
Aircraft: the type's Wikipedia article (e.g. "Beechcraft Baron").
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'KestrelAirLogbook/1.0 (personal flight logbook; build-time lookups)'}
AIRPORT_WORDS = re.compile(r'airport|airfield|aerodrome|air base|airbase|airpark|air strip|airstrip|heliport|field\b', re.I)
AIRCRAFT_ALIASES = [  # NeoFly/MSFS model name -> Wikipedia article
    (r'citation\s*x|c750', 'Cessna Citation X'), (r'c152|cessna 152', 'Cessna 152'),
    (r'c172|cessna 172', 'Cessna 172'), (r'baron', 'Beechcraft Baron'), (r'comanche|pa-24', 'Piper PA-24 Comanche'),
    (r'aerostar', 'Piper PA-60 Aerostar'), (r'bonanza', 'Beechcraft Bonanza'), (r'king air', 'Beechcraft King Air'),
    (r'a320', 'Airbus A320neo family'), (r'longitude', 'Cessna Citation Longitude'), (r'tbm', 'Daher TBM'),
    (r'pc-?12', 'Pilatus PC-12'), (r'caravan|c208', 'Cessna 208 Caravan'), (r'kodiak', 'Quest Kodiak'),
    (r'h135', 'Eurocopter EC135'), (r'da62', 'Diamond DA62'), (r'da40', 'Diamond DA40'),
]


class NotFound(Exception):
    pass


def _get(url, tries=6):
    import urllib.error
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise NotFound(url)
            if i == tries - 1:
                raise
            wait = e.headers.get('Retry-After') if e.code == 429 else None
            time.sleep(min(30, float(wait)) if wait and wait.isdigit() else 2 * (i + 1))
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def _json(url):
    return json.loads(_get(url).decode('utf-8'))


def _summary(title):
    s = _json('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'), safe=''))
    if s.get('type') == 'disambiguation':
        return None
    return {
        'title': s.get('title'), 'description': s.get('description'), 'extract': s.get('extract'),
        'url': (s.get('content_urls') or {}).get('desktop', {}).get('page'),
        'image': (s.get('thumbnail') or {}).get('source'),
    }


def _save_image(url, dest):
    if not url or os.path.exists(dest):
        return os.path.exists(dest)
    big = re.sub(r'/(\d+)px-', '/960px-', url)  # a sharper version of the thumbnail
    for u in (big, url):
        try:
            data = _get(u, tries=2)
            with open(dest, 'wb') as fh:
                fh.write(data)
            return True
        except Exception:
            continue
    return False


def _wikidata(icaos):
    vals = ' '.join(f'"{i}"' for i in icaos)
    q = f'''SELECT ?icao ?article ?cityLabel ?inception ?operatorLabel WHERE {{
      VALUES ?icao {{ {vals} }}
      ?item wdt:P239 ?icao .
      OPTIONAL {{ ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }}
      OPTIONAL {{ ?item wdt:P931 ?city . }}
      OPTIONAL {{ ?item wdt:P571 ?inception . }}
      OPTIONAL {{ ?item wdt:P137 ?operator . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }} }}'''
    data = _json('https://query.wikidata.org/sparql?format=json&query=' + urllib.parse.quote(q))
    out = {}
    for b in data['results']['bindings']:
        i = b['icao']['value']
        o = out.setdefault(i, {'cities': [], 'operators': []})
        if 'article' in b:
            o['title'] = urllib.parse.unquote(b['article']['value'].rsplit('/', 1)[1]).replace('_', ' ')
        if 'cityLabel' in b and b['cityLabel']['value'] not in o['cities']:
            o['cities'].append(b['cityLabel']['value'])
        if 'operatorLabel' in b and b['operatorLabel']['value'] not in o['operators']:
            o['operators'].append(b['operatorLabel']['value'])
        if 'inception' in b:
            o['opened'] = b['inception']['value'][:4].lstrip('+')
    return out


def _geosearch(a):
    data = _json('https://en.wikipedia.org/w/api.php?action=query&list=geosearch&format=json&gslimit=20'
                 f'&gsradius=6000&gscoord={a["lat"]}|{a["lon"]}')
    hits = data.get('query', {}).get('geosearch', [])
    for h in hits:
        if AIRPORT_WORDS.search(h['title']) or a['ident'].lower() in h['title'].lower():
            return h['title'], 'airport'
    # no article for the field itself: describe the nearest town instead
    town = a.get('city')
    if town:
        return town, 'town'
    return (hits[0]['title'], 'nearby') if hits else (None, None)


def airports(airports_by_ident, cache_dir):
    os.makedirs(os.path.join(cache_dir, 'img'), exist_ok=True)
    path = os.path.join(cache_dir, 'airports.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    todo = [i for i in airports_by_ident if i not in cache]
    if todo:
        print(f'  Wikipedia: looking up {len(todo)} new airport(s)')
        try:
            wd = _wikidata(todo)
        except Exception as e:
            print(f'  ! Wikidata unavailable ({e}); will retry next build')
            wd = None
        for ident in todo:
            if wd is None:
                break
            a = airports_by_ident[ident]
            info = dict(wd.get(ident, {}))
            title, kind = info.get('title'), 'airport'
            try:
                if not title:
                    title, kind = _geosearch(a)
                try:
                    s = _summary(title) if title else None
                except NotFound:
                    s = None  # remembered as "no article", not retried
            except Exception as e:
                print(f'  ! {ident}: {e}')
                continue
            entry = {'kind': kind if s else None, 'fetched': time.strftime('%Y-%m-%d'),
                     'cities': info.get('cities', [])[:3], 'operators': info.get('operators', [])[:2], 'opened': info.get('opened')}
            if s:
                entry.update(s)
                img = os.path.join(cache_dir, 'img', f'airport-{ident}.jpg')
                entry['imageFile'] = os.path.basename(img) if _save_image(s.get('image'), img) else None
            cache[ident] = entry
            time.sleep(0.6)  # stay well inside Wikipedia's rate limits
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=1, sort_keys=True)
    return cache


def aircraft(aircraft_by_id, cache_dir, overrides=None):
    os.makedirs(os.path.join(cache_dir, 'img'), exist_ok=True)
    path = os.path.join(cache_dir, 'aircraft.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    changed = False
    for key, a in aircraft_by_id.items():
        title = (overrides or {}).get(key, {}).get('wiki')
        if not title:
            name = f'{a.get("name", "")} {a.get("livery") or ""}'.lower()
            title = next((t for rx, t in AIRCRAFT_ALIASES if re.search(rx, name)), None)
        if not title or title in cache:
            continue
        try:
            s = _summary(title)
            time.sleep(0.6)
        except NotFound:
            s = None
        except Exception as e:
            print(f'  ! aircraft {title}: {e}')
            continue
        if s:
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            img = os.path.join(cache_dir, 'img', f'aircraft-{slug}.jpg')
            s['imageFile'] = os.path.basename(img) if _save_image(s.get('image'), img) else None
        cache[title] = s or {}
        changed = True
    if changed:
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=1, sort_keys=True)
    out = {}
    for key, a in aircraft_by_id.items():
        title = (overrides or {}).get(key, {}).get('wiki') or next(
            (t for rx, t in AIRCRAFT_ALIASES if re.search(rx, f'{a.get("name", "")} {a.get("livery") or ""}'.lower())), None)
        if title and cache.get(title):
            out[key] = cache[title]
    return out
