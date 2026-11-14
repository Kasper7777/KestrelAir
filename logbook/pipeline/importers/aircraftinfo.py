"""The aircraft dossier: real facts about each aircraft type you fly, plus any real
manuals for it already on this PC.

- history: the Wikipedia article's opening sections (plain text)
- specs: from Wikidata (manufacturer, first flight, number built, crew, seats,
  length, wingspan, height, empty weight, top speed) - only values Wikidata has
- photos: real photos of the type from the article
- manuals: PDFs on this PC whose file name matches the aircraft (add-on manuals,
  POHs, checklists you've made) - served to the app by the local server only

Fetched once (cached in backup/wiki/), in the background like the rest.
"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request

UA = {'User-Agent': 'KestrelAirLogbook/1.0 (personal flight logbook; build-time lookups)'}
WP = 'https://en.wikipedia.org/w/api.php?format=json&action=query&redirects=1'
SPECS = [  # Wikidata property, label, kind
    ('P176', 'Manufacturer', 'item'), ('P606', 'First flight', 'date'), ('P729', 'Entered service', 'date'),
    ('P1092', 'Number built', 'qty'), ('P1029', 'Crew', 'qty'), ('P1083', 'Seats', 'qty'),
    ('P2043', 'Length', 'len'), ('P2050', 'Wingspan', 'len'), ('P2048', 'Height', 'len'),
    ('P2067', 'Empty weight', 'mass'), ('P2052', 'Top speed', 'speed'),
]
UNITS = {'Q11573': ('m', 1), 'Q174728': ('m', 0.01), 'Q3710': ('m', 0.3048), 'Q218593': ('m', 0.0254),
         'Q11570': ('kg', 1), 'Q100995': ('kg', 0.4536), 'Q180154': ('km/h', 1), 'Q128822': ('km/h', 1.852),
         'Q211256': ('km/h', 1.609), 'Q182429': ('km/h', 3.6)}


def _json(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def _download(url, dest):
    if os.path.exists(dest):
        return True
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            data = r.read()
        with open(dest, 'wb') as fh:
            fh.write(data)
        return True
    except Exception:
        return False


def _fmt(kind, v):
    if kind == 'date':
        return v['time'][1:5] if v.get('time') else None
    amount = float(v['amount'])
    unit = v.get('unit', '').rsplit('/', 1)[-1]
    if kind == 'qty':
        return f'{int(round(amount)):,}'
    sym, k = UNITS.get(unit, (None, None))
    if not sym:
        return None
    x = amount * k
    if sym == 'm':
        return f'{x:.1f} m ({x / 0.3048:.0f} ft)'
    if sym == 'kg':
        return f'{x:,.0f} kg ({x / 0.4536:,.0f} lb)'
    if sym == 'km/h':
        return f'{x:,.0f} km/h ({x / 1.852:,.0f} kt)'
    return None


def details(title, cache_dir, fetch=True):
    path = os.path.join(cache_dir, 'aircraft_details.json')
    cache = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    if title in cache or not fetch:
        return cache.get(title)
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    out = {'title': title, 'history': [], 'specs': [], 'photos': []}
    try:
        q = _json(WP + '&prop=extracts|pageprops|info&inprop=url&explaintext=1&exsectionformat=plain&titles=' + urllib.parse.quote(title))
        page = next(iter(q['query']['pages'].values()))
        out['url'] = page.get('fullurl')
        text = page.get('extract') or ''
        stop = re.search(r'\n(Specifications|See also|References|Notes|Accidents and incidents|Operators)\b', text)
        paras = [p.strip() for p in (text[:stop.start()] if stop else text).split('\n') if len(p.strip()) > 120]
        out['history'] = paras[:6]
        qid = (page.get('pageprops') or {}).get('wikibase_item')
        if qid:
            ent = _json(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json')['entities'][qid]['claims']
            items = {}
            for prop, label, kind in SPECS:
                for c in ent.get(prop, [])[:1]:
                    v = c['mainsnak'].get('datavalue', {}).get('value')
                    if v is None:
                        continue
                    if kind == 'item':
                        items[label] = v['id']
                    else:
                        val = _fmt('date' if kind == 'date' else kind, v)
                        if val:
                            out['specs'].append({'label': label, 'value': val})
            if items:
                labels = _json('https://www.wikidata.org/w/api.php?format=json&action=wbgetentities&props=labels&languages=en&ids='
                               + '|'.join(items.values()))['entities']
                for label, q2 in items.items():
                    name = labels.get(q2, {}).get('labels', {}).get('en', {}).get('value')
                    if name:
                        out['specs'].insert(0, {'label': label, 'value': name})
        imgs = _json(WP + '&generator=images&gimlimit=40&prop=imageinfo&iiprop=url|mime|size&iiurlwidth=960&titles=' + urllib.parse.quote(title))
        for p in sorted((imgs.get('query', {}).get('pages') or {}).values(), key=lambda p: p.get('title', '')):
            ii = (p.get('imageinfo') or [{}])[0]
            t = p.get('title', '')
            if ii.get('mime') != 'image/jpeg' or re.search(r'diagram|drawing|logo|map|cockpit diagram|3-view|3view|silhouette|flag', t, re.I):
                continue
            if (ii.get('width') or 0) < 600:
                continue
            f = f'acft-{slug}-{len(out["photos"])}.jpg'
            if _download(ii['thumburl'], os.path.join(img_dir, f)):
                out['photos'].append({'file': f, 'credit': ii.get('descriptionurl')})
            if len(out['photos']) >= 6:
                break
    except Exception as e:
        out['error'] = str(e)[:120]
    cache[title] = out
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1)
    return out


def find_manuals(patterns, roots, max_depth=5):
    """PDFs under the given folders whose file name matches the aircraft.
    patterns: regexes (e.g. r'citation\\s*x|c750'). Returns [{id, title, mb, path}]."""
    found, seen = [], set()
    for root in roots:
        root = os.path.expandvars(root)
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip('\\/').count(os.sep)
        for dirpath, dirnames, files in os.walk(root):
            if dirpath.count(os.sep) - base_depth >= max_depth:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if not d.startswith('.') and d.lower() not in ('node_modules', 'web', 'cache')]
            for fn in files:
                if not fn.lower().endswith('.pdf'):
                    continue
                name = re.sub(r'[_\-.]+', ' ', fn[:-4])
                if not any(re.search(p, name, re.I) for p in patterns):
                    continue
                full = os.path.join(dirpath, fn)
                key = os.path.normcase(full)
                same = (fn.lower(), os.path.getsize(full))      # the same file saved in two places
                if key in seen or same in seen:
                    continue
                seen.update((key, same))
                found.append({'id': hashlib.sha1(key.encode()).hexdigest()[:12], 'title': name.strip(),
                              'mb': round(os.path.getsize(full) / 1e6, 1), 'path': full})
    return found
