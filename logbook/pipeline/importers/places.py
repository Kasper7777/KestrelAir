"""Real places near an airport, for the layover diary.

- restaurants / cafés / pubs within ~6 km, from OpenStreetMap (Overpass API)
- sights within 10 km, from Wikipedia's geosearch (with photos and a summary)
- local dishes for the country (a small built-in list of Wikipedia articles), with photos

Everything is fetched once per airport and cached in backup/places/, so builds stay
fast and offline. The places are real; what the pilot does there is imagined.
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
                        r'raion|rural|selsoviet|okrug|list of|\(disambiguation\)|crash|accident|disaster|incident|'
                        r'flight \d|shooting|bombing|murder|massacre|explosion|collision|derailment|fire of', re.I)

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
        data = None
        # Wikimedia only serves standard thumbnail widths (250, 330, 500, 960...)
        for u in (re.sub(r'/(\d+)px-', '/500px-', url), url):
            try:
                data = _get(u, tries=2)
            except Exception:
                data = None
            if data:
                break
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
           f'&ggscoord={lat}|{lon}&prop=pageimages|description|extracts|info&piprop=thumbnail&pithumbsize=500'
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


def dishes(iso, img_dir, cache, titles=None, fetch=True):
    out = []
    for title in titles or DISHES.get(iso, DISHES['']):
        if title not in cache and not fetch:
            continue
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
    around = ''.join(f'nwr["amenity"~"^(restaurant|cafe|pub|bar|fast_food)$"]["name"](around:{radius},{la},{lo});'
                     f'nwr["tourism"~"^(hotel|guest_house|motel|hostel)$"]["name"](around:{radius + 3000},{la},{lo});' for _, la, lo in pts)
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
    hotels = {i: [] for i, _, _ in pts}
    for e in json.loads(raw).get('elements', []):
        t = e.get('tags', {})
        la, lo = e.get('lat') or e.get('center', {}).get('lat'), e.get('lon') or e.get('center', {}).get('lon')
        if not t.get('name') or la is None:
            continue
        ident, km = min(((i, _km(a, b, la, lo)) for i, a, b in pts), key=lambda x: x[1])
        if t.get('tourism'):
            if km * 1000 <= radius + 3000:
                hotels[ident].append({'name': t.get('name:en') or t['name'], 'kind': t['tourism'].replace('_', ' '), 'km': round(km, 1),
                                      'lat': la, 'lon': lo, 'commons': t.get('wikimedia_commons'),
                                      'stars': t.get('stars'), 'website': t.get('website') or t.get('contact:website'),
                                      'street': ' '.join(x for x in (t.get('addr:housenumber'), t.get('addr:street')) if x) or None})
            continue
        if km * 1000 > radius:
            continue
        out[ident].append({'name': t.get('name:en') or t['name'], 'kind': t.get('amenity'),
                           'cuisine': (t.get('cuisine') or '').replace('_', ' ').replace(';', ', '), 'km': round(km, 1),
                           'lat': la, 'lon': lo, 'commons': t.get('wikimedia_commons'),
                           'website': t.get('website') or t.get('contact:website') or t.get('url'),
                           'menu': t.get('website:menu') or t.get('menu:url') or t.get('contact:menu'),
                           'hours': t.get('opening_hours'), 'street': ' '.join(x for x in (t.get('addr:housenumber'), t.get('addr:street')) if x) or None,
                           'town': t.get('addr:city')})
    for i in out:
        # places that say what they serve (and have a website) first, then nearest
        out[i].sort(key=lambda r: (not r['cuisine'], not (r['website'] or r['menu']), r['km']))
        out[i] = out[i][:40]
        hotels[i].sort(key=lambda h: (h['kind'] != 'hotel', not h['website'], h['km']))
        hotels[i] = hotels[i][:10]
    return {i: {'restaurants': out[i], 'hotels': hotels[i]} for i in out}


# what you'd order at a place, from its OpenStreetMap cuisine tag (Wikipedia article titles)
CUISINE_DISHES = [
    (r'pizza', ['Pizza Margherita', 'Pizza']), (r'italian', ['Spaghetti alla carbonara', 'Lasagne', 'Risotto', 'Pizza Margherita']),
    (r'indian|curry|nepal', ['Chicken tikka masala', 'Butter chicken', 'Biryani', 'Naan']),
    (r'chinese|cantonese|sichuan|dim ?sum', ['Kung Pao chicken', 'Char siu', 'Dim sum', 'Fried rice']),
    (r'sushi|japanese', ['Sushi', 'Ramen', 'Tempura', 'Katsu curry']), (r'ramen|noodle', ['Ramen', 'Lanzhou beef noodle soup']),
    (r'thai', ['Pad thai', 'Green curry', 'Tom yum']), (r'vietnam', ['Pho', 'Bánh mì']), (r'korean', ['Bibimbap', 'Korean barbecue']),
    (r'burger', ['Hamburger', 'Cheeseburger']), (r'chicken', ['Fried chicken', 'Buffalo wing']),
    (r'kebab|turkish|doner|döner', ['Döner kebab', 'Shish kebab', 'Lahmacun']), (r'greek', ['Gyros', 'Moussaka', 'Souvlaki']),
    (r'lebanese|middle.?east|arab|falafel|shawarma', ['Shawarma', 'Falafel', 'Hummus']),
    (r'mexican|tex-?mex|taco|burrito', ['Taco', 'Burrito', 'Quesadilla']),
    (r'fish.?and.?chips|chippy', ['Fish and chips']), (r'seafood|fish', ['Fish and chips', 'Oyster', 'Lobster']),
    (r'steak', ['Steak', 'Steak frites']), (r'barbecue|bbq|grill', ['Barbecue', 'Steak']),
    (r'french|brasserie|bistro', ['Steak frites', 'Croque monsieur', 'Crème brûlée']), (r'crepe|crêpe', ['Crêpe', 'Galette']),
    (r'spanish|tapas', ['Tapas', 'Patatas bravas', 'Paella']), (r'portuguese', ['Pastel de nata', 'Bacalhau']),
    (r'sandwich|deli|bagel', ['Sandwich', 'Club sandwich', 'Bagel']), (r'bakery|cake|pastry', ['Croissant', 'Danish pastry']),
    (r'coffee|cafe|café|tea', ['Flat white', 'Croissant', 'Cappuccino']), (r'ice.?cream|gelato', ['Ice cream', 'Gelato']),
    (r'donut|doughnut', ['Doughnut']), (r'breakfast|brunch|diner', ['Pancake', 'Full breakfast', 'Eggs Benedict']),
    (r'vegan|vegetarian', ['Falafel', 'Buddha bowl']), (r'russian', ['Pelmeni', 'Borscht', 'Blini']),
    (r'georgian', ['Khachapuri', 'Khinkali']), (r'uzbek|central.?asian', ['Plov', 'Lagman (food)']),
    (r'american', ['Hamburger', 'Buffalo wing', 'Pancake']), (r'british|english', ['Fish and chips', 'Sunday roast', 'Full breakfast']),
    (r'regional|local', []),
]
KIND_DISHES = {'pub': ['Fish and chips', 'Steak and kidney pie', "Ploughman's lunch"], 'bar': ['Cocktail', 'Beer'],
               'cafe': ['Flat white', 'Croissant', 'Cappuccino'], 'fast_food': ['Hamburger', 'French fries']}


def menu_for(place, iso):
    """Dishes that fit this restaurant: its cuisine first, its type next, the country last."""
    c = (place or {}).get('cuisine') or ''
    for rx, dishes_ in CUISINE_DISHES:
        if c and re.search(rx, c, re.I) and dishes_:
            return dishes_
    kind = (place or {}).get('kind')
    if kind == 'pub' and iso not in ('GB', 'IE', 'JE', 'GG', 'IM', 'FK'):
        return ['Beer', 'Hamburger']
    return KIND_DISHES.get(kind) if kind in ('pub', 'bar', 'cafe') else (DISHES.get(iso) or DISHES[''])


PLACES_VERSION = 4   # bump when the saved fields change, so old entries are looked up again
CACHE, CACHE_PATH = {}, None   # set by for_airports; shared with the photo lookups the diary makes


def save_cache(cache_dir=None):
    if CACHE_PATH:
        with open(CACHE_PATH, 'w', encoding='utf-8') as fh:
            json.dump(CACHE, fh, ensure_ascii=False, indent=0)
COMMONS = 'https://commons.wikimedia.org/w/api.php?format=json&action=query'
NOT_A_PHOTO = re.compile(r'map|logo|\.svg|plan\b|diagram|sign|coat of arms|flag|locator|screenshot', re.I)


MENU_WORDS = re.compile(r'menu|carte|speisekarte|men[uú]|меню|メニュー|菜单|메뉴|price list', re.I)


def _commons_files(query_params, keep_menus=False):
    data = json.loads(_get(COMMONS + query_params + '&prop=imageinfo&iiprop=url|mime&iiurlwidth=500') or b'{}')
    pages = sorted((data.get('query', {}).get('pages') or {}).values(), key=lambda p: p.get('index', 0))
    out = []
    for p in pages:
        ii = (p.get('imageinfo') or [{}])[0]
        title = p.get('title', '')
        is_menu = bool(MENU_WORDS.search(title))
        if ii.get('mime') == 'image/jpeg' and ii.get('thumburl') and (is_menu and keep_menus or not NOT_A_PHOTO.search(title)):
            out.append({'title': title, 'url': ii['thumburl'], 'page': ii.get('descriptionurl'), 'menu': is_menu})
    return out


def place_photos(cache, place, img_dir, fetch=True):
    """Real photos of (or right beside) a restaurant / hotel, plus a photographed menu when
    Wikimedia Commons has one: its OSM-tagged image first, then Commons photos taken within
    150 m, then a Commons search for '<name> menu'. Cached per place.
    Returns {'photos': [{file, credit}], 'menu': {file, credit} | None}."""
    if not place or place.get('lat') is None:
        return {'photos': [], 'menu': None}
    key = f'{place["lat"]:.5f},{place["lon"]:.5f}'
    store = cache.setdefault('_placePhotos', {})
    if key not in store or 'photos' not in store[key]:
        if not fetch:
            return {'photos': [], 'menu': None}
        found = []
        try:
            tag = place.get('commons')
            if tag and not tag.startswith('Category:'):
                found += _commons_files('&titles=' + urllib.parse.quote(tag if tag.startswith('File:') else 'File:' + tag))
            found += _commons_files(f'&generator=geosearch&ggsnamespace=6&ggsradius=150&ggslimit=15&ggscoord={place["lat"]}|{place["lon"]}',
                                    keep_menus=True)
            if not any(f['menu'] for f in found) and place.get('name'):
                found += [f for f in _commons_files('&generator=search&gsrnamespace=6&gsrlimit=5&gsrsearch='
                                                    + urllib.parse.quote(f'"{place["name"]}" menu filetype:bitmap'), keep_menus=True) if f['menu']]
        except Exception:
            return {'photos': [], 'menu': None}
        slug = 'place-' + re.sub(r'[^0-9a-z]+', '-', key)
        photos, menu = [], None
        for n, f in enumerate([f for f in found if not f['menu']][:3]):
            fn = _image(f['url'], os.path.join(img_dir, f'{slug}-{n}.jpg'))
            if fn:
                photos.append({'file': fn, 'credit': f['page']})
        m = next((f for f in found if f['menu']), None)
        if m:
            fn = _image(m['url'], os.path.join(img_dir, f'{slug}-menu.jpg'))
            menu = {'file': fn, 'credit': m['page']} if fn else None
        store[key] = {'photos': photos, 'menu': menu}
        time.sleep(0.3)
    return store[key]


def dish_photo(cache, title, seed, img_dir, fetch=True):
    """One of several real photos of a dish (Wikimedia Commons), chosen by seed, so the
    same dish doesn't always show the same picture. Falls back to the Wikipedia lead image."""
    d = cache.setdefault('_dishPhotos', {})
    if title not in d and fetch:
        try:
            d[title] = [f['url'] for f in _commons_files('&generator=search&gsrnamespace=6&gsrlimit=12&gsrsearch='
                                                         + urllib.parse.quote(f'"{title}" filetype:bitmap'))][:8]
        except Exception:
            d[title] = []
        time.sleep(0.3)
    # only photos whose file name actually names the dish (search also returns e.g. people at a grill)
    words = [w for w in re.findall(r'[^\W\d_]{4,}', title.lower()) if w not in ('with', 'from', 'style')]
    def named(u):
        name = urllib.parse.unquote(u.rsplit('/', 1)[-1]).lower().replace('_', ' ')
        return any(w in name for w in words) and not re.search(r'people|men |women|soldier|marine|crowd|festival|shop|store|sign|logo', name)
    urls = [u for u in (d.get(title) or []) if named(u)]
    if not urls:
        return None
    url = urls[seed % len(urls)]
    name = 'dishv-' + re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') + f'-{seed % len(urls)}.jpg'
    dest = os.path.join(img_dir, name)
    if os.path.exists(dest):
        return name
    return _image(url, dest) if fetch else None


def for_airports(airports, cache_dir, fetch=True):
    """airports: {ident: airport}. Returns {ident: {restaurants, hotels, sights, dishes}}.
    fetch=False uses only what's already saved (instant, offline); fetch=True also looks up
    anything new or out of date, saving as it goes."""
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    path = os.path.join(cache_dir, 'places.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    dish_cache = cache.setdefault('_dishes', {})
    global CACHE, CACHE_PATH
    CACHE, CACHE_PATH = cache, path

    def save():
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=0)

    # restaurants + hotels: one Overpass query per 10 airports, for new or out-of-date entries
    stale = [i for i in airports if cache.get(i, {}).get('restV') != PLACES_VERSION] if fetch else []
    if stale:
        print(f'  places: looking up restaurants and hotels near {len(stale)} airport(s)')
    for k in range(0, len(stale), 10):
        chunk = stale[k:k + 10]
        try:
            found = restaurants_many([(i, airports[i]['lat'], airports[i]['lon']) for i in chunk])
        except Exception as e:
            print(f'  ! places for {", ".join(chunk)}: {e} (will retry next time)')
            continue
        for i in chunk:
            cache.setdefault(i, {}).update(found[i], restV=PLACES_VERSION)
        save()
        print(f'    {min(k + 10, len(stale))}/{len(stale)}')

    # sights near each airport (Wikipedia), one at a time - it rate-limits
    for i in [i for i in airports if i in cache and not cache[i].get('sightsChecked')] if fetch else []:
        try:
            cache[i]['sights'] = sights(airports[i]['lat'], airports[i]['lon'], img_dir, i)
            cache[i]['sightsChecked'] = True
            save()
        except Exception as e:
            print(f'  ! sights {i}: {e} (will retry next build)')
        time.sleep(1)

    out = {}
    for ident in airports:
        if ident not in cache:
            continue
        iso = (airports[ident].get('country') or {}).get('iso') or ''
        rests = []
        for r in cache[ident].get('restaurants', []):
            # what you'd actually order there, with a photo of the dish
            rests.append({**r, 'order': dishes(iso, img_dir, dish_cache, menu_for(r, iso), fetch)})
        out[ident] = {**cache[ident], 'restaurants': rests, 'hotels': cache[ident].get('hotels', []),
                      'sights': cache[ident].get('sights', []), 'dishes': dishes(iso, img_dir, dish_cache, None, fetch)}
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)
    return out
