"""Country flag fills for the map.

For every country you've landed in, draws its flag clipped exactly to the
country's outline (in Web Mercator, so it lines up with the map) and writes
web/geo/flags/<ISO>[-<n>].png plus web/geo/flags.json:

    {"version": 2, "countries": {"RU": {"name": ..., "parts": [{"file": "RU.png", "coordinates": [[w,n],[e,n],[e,s],[w,s]]}, ...]}}}

Robustness:
- countries that cross the 180° line (Russia, USA, Fiji, Kiribati) are split into a
  part on each side, so nothing is dropped and no image extends past ±180°
- the flag is fitted to each part with at most ~2x stretch, then centre-cropped,
  so stripes and emblems stay recognisable (no single-colour slivers)
- every part is validated (sane coordinates, non-empty clip, image written) before
  it goes into flags.json; anything odd is skipped and reported, never drawn
- FILL_VERSION invalidates old fills when the drawing method changes
Flags come from flagcdn.com once and are cached in backup/flags/.
"""
import json
import math
import os
import urllib.request

from PIL import Image, ImageDraw

FILL_VERSION = 3
TILE_ABOVE_PX = 900     # countries wider than this (~40° of longitude) get the flag tiled, so every part reads as that flag
WORLD_PX = 8192          # mercator width of the whole world at fill resolution
MAX_PX = 2048
MAX_STRETCH = 2.0


def _merc(lon, lat):
    lat = max(-85, min(85, lat))
    return (lon + 180) / 360, (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2


def _flag(iso, cache, fetch):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f'{iso.lower()}.png')
    if not os.path.exists(path):
        if not fetch:
            return None
        req = urllib.request.Request(f'https://flagcdn.com/w1280/{iso.lower()}.png', headers={'User-Agent': 'KestrelAirLogbook/1.0'})
        data = urllib.request.urlopen(req, timeout=30).read()
        Image.open(__import__('io').BytesIO(data)).verify()      # refuse anything that isn't an image
        with open(path, 'wb') as fh:
            fh.write(data)
    return Image.open(path).convert('RGBA')


def _split_dateline(polys):
    """Group polygons by side of the 180° line when a country straddles it."""
    lons = [p[0] for poly in polys for p in poly[0]]
    if max(lons) - min(lons) <= 300:
        return [polys]
    east = [poly for poly in polys if sum(p[0] for p in poly[0]) / len(poly[0]) >= 0]
    west = [poly for poly in polys if sum(p[0] for p in poly[0]) / len(poly[0]) < 0]
    return [g for g in (east, west) if g]


def _fit(flag, W, H):
    """Fit the flag to W x H allowing at most MAX_STRETCH distortion, cropping the rest."""
    fa, ta = flag.width / flag.height, W / H
    want = min(max(ta, fa / MAX_STRETCH), fa * MAX_STRETCH)   # aspect to crop the flag to
    if want < fa:      # crop width
        cw = int(flag.height * want)
        flag = flag.crop(((flag.width - cw) // 2, 0, (flag.width - cw) // 2 + cw, flag.height))
    else:              # crop height
        ch = int(flag.width / want)
        flag = flag.crop((0, (flag.height - ch) // 2, flag.width, (flag.height - ch) // 2 + ch))
    return flag.resize((W, H), Image.LANCZOS)


def _draw_part(polys, flag):
    pts = [p for poly in polys for ring in poly for p in ring]
    w, e = min(p[0] for p in pts), max(p[0] for p in pts)
    s, n = min(p[1] for p in pts), max(p[1] for p in pts)
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        return None, 'coordinates out of range'
    x0, y0 = _merc(w, n)
    x1, y1 = _merc(e, s)
    W = max(32, min(MAX_PX, int((x1 - x0) * WORLD_PX)))
    H = max(32, min(MAX_PX, int((y1 - y0) / (x1 - x0) * W)))
    mask = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(mask)
    for poly in polys:
        for k, ring in enumerate(poly):
            xy = []
            for lon, lat in ring:
                mx, my = _merc(lon, lat)
                xy.append(((mx - x0) / (x1 - x0) * (W - 1), (my - y0) / (y1 - y0) * (H - 1)))
            if len(xy) >= 3:
                d.polygon(xy, fill=0 if k else 255)
    if not mask.getbbox():
        return None, 'empty outline'
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if W > TILE_ABOVE_PX:
        # huge country: a brick pattern of whole flags, so wherever you look it reads as that flag
        tw = max(300, W // 4)
        th = int(tw * flag.height / flag.width)
        tile = flag.resize((tw, th), Image.LANCZOS)
        sheet = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        for row, y in enumerate(range(0, H, th)):
            for x in range(-(tw // 2) * (row % 2), W, tw):
                sheet.paste(tile, (x, y))
        out.paste(sheet, (0, 0), mask)
    else:
        out.paste(_fit(flag, W, H), (0, 0), mask)
    return (out, [[w, n], [e, n], [e, s], [w, s]]), None


def build(isos, countries_path, out_dir, cache_dir, fetch=True):
    os.makedirs(out_dir, exist_ok=True)
    index_path = os.path.join(os.path.dirname(out_dir), 'flags.json')
    try:
        index = json.load(open(index_path, encoding='utf-8'))
    except (OSError, ValueError):
        index = {}
    if index.get('version') != FILL_VERSION:       # old format / old method: redraw everything
        index = {'version': FILL_VERSION, 'countries': {}}
        for f in os.listdir(out_dir):
            if f.endswith('.png'):
                os.remove(os.path.join(out_dir, f))
    feats = {f['properties']['iso']: f for f in json.load(open(countries_path, encoding='utf-8'))['features']}
    done = 0
    for iso in isos:
        entry = index['countries'].get(iso)
        if entry and all(os.path.exists(os.path.join(out_dir, p['file'])) for p in entry['parts']):
            continue
        f = feats.get(iso)
        if not f:
            print(f'  ! flag fill {iso}: no outline for this country')
            continue
        try:
            flag = _flag(iso, cache_dir, fetch)
        except Exception as ex:
            print(f'  ! flag fill {iso}: {ex}')
            continue
        if flag is None:
            continue
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        parts = []
        for k, group in enumerate(_split_dateline(polys)):
            res, why = _draw_part(group, flag)
            if not res:
                print(f'  ! flag fill {iso} part {k}: {why} - skipped')
                continue
            img, coords = res
            name = f'{iso}.png' if k == 0 else f'{iso}-{k}.png'
            img.save(os.path.join(out_dir, name), optimize=True)
            parts.append({'file': name, 'coordinates': coords})
        if parts:
            index['countries'][iso] = {'name': f['properties'].get('name'), 'parts': parts}
            done += 1
    with open(index_path, 'w', encoding='utf-8') as fh:
        json.dump(index, fh, indent=1, sort_keys=True)
    return done


def validate(index_path, out_dir):
    """Problems with the fills on disk (empty list = all good)."""
    problems = []
    try:
        index = json.load(open(index_path, encoding='utf-8'))
    except (OSError, ValueError) as e:
        return [f'flags.json unreadable: {e}']
    for iso, c in index.get('countries', {}).items():
        for p in c['parts']:
            path = os.path.join(out_dir, p['file'])
            (w, n), (e, _), (_, s) = p['coordinates'][0], p['coordinates'][1], p['coordinates'][2]
            if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
                problems.append(f'{iso}: bad corners {p["coordinates"]}')
            if not os.path.exists(path):
                problems.append(f'{iso}: missing {p["file"]}')
            else:
                with Image.open(path) as im:
                    if not im.getbbox():
                        problems.append(f'{iso}: {p["file"]} is blank')
    return problems
