"""Real places near an airport, for the layover diary.

- restaurants / cafés / pubs within ~6 km, from OpenStreetMap (Overpass API)
- sights within 10 km, from Wikipedia's geosearch (with photos and a summary)
- local dishes for the country (a small built-in list of Wikipedia articles), with photos

Everything is fetched once per airport and cached in backup/places/, so builds stay
fast and offline. The places are real; what Casper does there is imagined.
"""
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'KestrelAirLogbook/1.0 (personal flight logbook; build-time lookups)'}
OVERPASS = 'https://overpass-api.de/api/interpreter'
SKIP_SIGHT = re.compile(r'airport|air ?base|airfield|aerodrome|heliport|station|school|college|constituency|electoral|district|'
                        r'ward\b|parish|municipality|road|street|highway|motorway|bus |hospital|prison|county|province|oblast|'
                        r'raion|rural|selsoviet|okrug|list of|\(disambiguation\)', re.I)

DISHES = {
    'GB': ['Full breakfast', 'Fish and chips', 'Sunday roast', 'Cornish pasty', 'Afternoon tea', 'Sticky toffee pudding'],
    'JE': ['Jersey Royal potato', 'Fish and chips', 'Jersey wonder', 'Crab'], 'GG': ['Guernsey Gâche', 'Fish and chips', 'Crab'],
    'FK': ['Fish and chips', "Shepherd's pie", 'Full breakfast'], 'IM': ['Fish and chips', 'Kipper'],
    'FR': ['Croissant', 'Moules-frites', 'Crêpe', 'Galette', 'Coq au vin', 'Crème brûlée'],
    'ES': ['Paella', 'Spanish omelette', 'Churros', 'Tapas', 'Gazpacho'],
    'DZ': ['Couscous', 'Shakshouka', 'Maghrebi mint tea', 'Chakhchoukha'],
    'HR': ['Ćevapi', 'Burek', 'Pašticada', 'Fritule'], 'BA': ['Ćevapi', 'Burek', 'Begova čorba'],
    'TR': ['Turkish breakfast', 'Döner kebab', 'Baklava', 'Turkish coffee', 'Lahmacun', 'Pide'],
    'CY': ['Halloumi', 'Souvlaki', 'Kleftiko', 'Meze'],
    'DE': ['Bratwurst', 'Currywurst', 'Pretzel', 'Schnitzel'],
    'NO': ['Brunost', 'Fårikål', 'Waffle', 'Open sandwich'], 'FI': ['Karelian pasty', 'Lohikeitto', 'Korvapuusti'],
    'RU': ['Pelmeni', 'Borscht', 'Blini', 'Pirozhki', 'Shashlik'], 'KZ': ['Beshbarmak', 'Baursak', 'Plov'],
    'CN': ['Jiaozi', 'Hot pot', 'Lanzhou beef noodle soup', 'Xiaolongbao'],
    'IN': ['Masala chai', 'Biryani', 'Dosa', 'Momo (food)'], 'TH': ['Pad thai', 'Tom yum', 'Green curry', 'Mango sticky rice'],
    'KR': ['Bibimbap', 'Korean barbecue', 'Kimchi', 'Tteokbokki'], 'JP': ['Ramen', 'Sushi', 'Okonomiyaki', 'Onigiri', 'Tempura'],
    'US': ['Hamburger', 'Pancake', 'Buffalo wing', 'Clam chowder', 'Barbecue in the United States'],
    'CA': ['Poutine', 'Butter tart', 'Nanaimo bar', 'Peameal bacon'],
    'MX': ['Taco', 'Chilaquiles', 'Guacamole', 'Tamale'], 'JM': ['Jerk (cooking)', 'Ackee and saltfish', 'Jamaican patty', 'Rice and peas'],
    'CO': ['Arepa', 'Bandeja paisa', 'Ajiaco', 'Empanada'], 'CL': ['Empanada', 'Pastel de choclo', 'Cazuela', 'Pisco sour'],
    'MR': ['Thieboudienne', 'Couscous', 'Ataya'], '': ['Coffee', 'Sandwich', 'Pizza'],
}


def _get(url, data=None, tries=4):
    import urllib.error
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == tries - 1:
                raise
            time.sleep(4 * (i + 1) if e.code in (429, 504) else 2)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(3)


def _km(a, b, c, d):
    la1, lo1, la2, lo2 = map(math.radians, (a, b, c, d))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _image(url, dest):
    if not url:
        return None
    if not os.path.exists(dest):
        data = _get(re.sub(r'/(\d+)px-', '/640px-', url)) or _get(url)
        if not data:
            return None
        with open(dest, 'wb') as fh:
            fh.write(data)
    return os.path.basename(dest)


def restaurants(lat, lon):
    q = f'''[out:json][timeout:40];(nwr["amenity"~"^(restaurant|cafe|pub|bar|fast_food)$"]["name"](around:6000,{lat},{lon}););out center tags 60;'''
    raw = _get(OVERPASS, data=urllib.parse.urlencode({'data': q}).encode())
    out = []
    for e in json.loads(raw or b'{}').get('elements', []):
        t = e.get('tags', {})
        la, lo = e.get('lat') or e.get('center', {}).get('lat'), e.get('lon') or e.get('center', {}).get('lon')
        if not t.get('name') or la is None:
            continue
        out.append({'name': t.get('name:en') or t['name'], 'kind': t.get('amenity'), 'cuisine': (t.get('cuisine') or '').replace('_', ' ').replace(';', ', '),
                    'km': round(_km(lat, lon, la, lo), 1), 'lat': la, 'lon': lo})
    out.sort(key=lambda r: (not r['cuisine'], r['km']))
    return out[:30]


def sights(lat, lon, img_dir, ident):
    url = ('https://en.wikipedia.org/w/api.php?action=query&format=json&generator=geosearch&ggsradius=10000&ggslimit=40'
           f'&ggscoord={lat}|{lon}&prop=pageimages|description|extracts|info&piprop=thumbnail&pithumbsize=640'
           '&exintro=1&explaintext=1&exsentences=2&inprop=url')
    data = json.loads(_get(url) or b'{}')
    out = []
    for p in (data.get('query', {}).get('pages') or {}).values():
        title = p.get('title', '')
        if SKIP_SIGHT.search(title) or SKIP_SIGHT.search(p.get('description') or ''):
            continue
        thumb = (p.get('thumbnail') or {}).get('source')
        if not thumb:
            continue
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:60]
        f = _image(thumb, os.path.join(img_dir, f'sight-{ident}-{slug}.jpg'))
        if f:
            out.append({'title': title, 'description': p.get('description'), 'extract': (p.get('extract') or '')[:320],
                        'url': p.get('fullurl'), 'image': f})
        if len(out) >= 6:
            break
    return out


def dishes(iso, img_dir, cache):
    out = []
    for title in DISHES.get(iso, DISHES['']):
        if title not in cache:
            try:
                s = json.loads(_get('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(title.replace(' ', '_'), safe='')) or b'{}')
            except Exception:
                continue
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
            img = _image((s.get('thumbnail') or {}).get('source'), os.path.join(img_dir, f'dish-{slug}.jpg')) if s else None
            cache[title] = {'title': s.get('title', title) if s else title, 'description': s.get('description') if s else None, 'image': img}
            time.sleep(0.4)
        if cache[title].get('image'):
            out.append(cache[title])
    return out


OVERPASS_MIRRORS = [OVERPASS, 'https://overpass.kumi.systems/api/interpreter', 'https://overpass.private.coffee/api/interpreter']


def restaurants_many(pts, radius=5000):
    """One Overpass query for several airports at once; each place goes to its nearest airport."""
    around = ''.join(f'nwr["amenity"~"^(restaurant|cafe|pub|bar|fast_food)$"]["name"](around:{radius},{la},{lo});' for _, la, lo in pts)
    q = f'[out:json][timeout:120];({around});out center tags;'
    body = urllib.parse.urlencode({'data': q}).encode()
    raw, last = None, None
    for url in OVERPASS_MIRRORS:
        try:
            raw = _get(url, data=body, tries=2)
            if raw:
                break
        except Exception as e:
            last = e
    if raw is None:
        raise RuntimeError(f'Overpass unavailable ({last})')
    out = {i: [] for i, _, _ in pts}
    for e in json.loads(raw).get('elements', []):
        t = e.get('tags', {})
        la, lo = e.get('lat') or e.get('center', {}).get('lat'), e.get('lon') or e.get('center', {}).get('lon')
        if not t.get('name') or la is None:
            continue
        ident, km = min(((i, _km(a, b, la, lo)) for i, a, b in pts), key=lambda x: x[1])
        if km * 1000 > radius:
            continue
        out[ident].append({'name': t.get('name:en') or t['name'], 'kind': t.get('amenity'),
                           'cuisine': (t.get('cuisine') or '').replace('_', ' ').replace(';', ', '), 'km': round(km, 1)})
    for i in out:
        out[i].sort(key=lambda r: (not r['cuisine'], r['km']))
        out[i] = out[i][:30]
    return out


def for_airports(airports, cache_dir):
    """airports: {ident: airport}. Returns {ident: {restaurants, sights, dishes}}."""
    from concurrent.futures import ThreadPoolExecutor
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(cache_dir, 'places.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    dish_cache = cache.setdefault('_dishes', {})
    todo = [i for i in airports if i not in cache]
    if todo:
        print(f'  places: looking up {len(todo)} layover airport(s)')
        with ThreadPoolExecutor(4) as pool:   # Wikipedia sights, a few at a time
            sight_jobs = {i: pool.submit(sights, airports[i]['lat'], airports[i]['lon'], img_dir, i) for i in todo}
            for k in range(0, len(todo), 10):     # restaurants: one Overpass query per 10 airports
                chunk = todo[k:k + 10]
                try:
                    rest = restaurants_many([(i, airports[i]['lat'], airports[i]['lon']) for i in chunk])
                except Exception as e:
                    print(f'  ! restaurants for {", ".join(chunk)}: {e} (will retry next build)')
                    continue
                for i in chunk:
                    try:
                        sg = sight_jobs[i].result()
                    except Exception:
                        sg = []
                    cache[i] = {'restaurants': rest.get(i, []), 'sights': sg}
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump(cache, fh, ensure_ascii=False, indent=0)
                print(f'    {min(k + 10, len(todo))}/{len(todo)}')
    out = {}
    for ident in airports:
        if ident in cache:
            iso = (airports[ident].get('country') or {}).get('iso') or ''
            out[ident] = {**cache[ident], 'dishes': dishes(iso, img_dir, dish_cache)}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)
    return out
