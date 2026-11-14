"""Country flag fills for the map.

For every country you've landed in, draws its flag clipped to the country's
outline (in Web Mercator, so it lines up with the map) and writes
web/geo/flags/<ISO>.png plus web/geo/flags.json with each image's corners.
The map lays these on as image layers - each visited country is coloured in
with its own flag. Flags come from flagcdn.com once and are cached in
backup/flags/, so later builds are offline and instant.
"""
import io
import json
import math
import os
import urllib.request

from PIL import Image, ImageDraw

WORLD_PX = 8192          # mercator width of the whole world at fill resolution
MAX_PX = 2048


def _merc(lon, lat):
    lat = max(-85, min(85, lat))
    return (lon + 180) / 360, (1 - math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / math.pi) / 2


def _flag(iso, cache):
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, f'{iso.lower()}.png')
    if not os.path.exists(path):
        req = urllib.request.Request(f'https://flagcdn.com/w1280/{iso.lower()}.png', headers={'User-Agent': 'KestrelAirLogbook/1.0'})
        with open(path, 'wb') as fh:
            fh.write(urllib.request.urlopen(req, timeout=30).read())
    return Image.open(path).convert('RGBA')


def build(isos, countries_path, out_dir, cache_dir):
    os.makedirs(out_dir, exist_ok=True)
    index_path = os.path.join(os.path.dirname(out_dir), 'flags.json')
    index = json.load(open(index_path, encoding='utf-8')) if os.path.exists(index_path) else {}
    feats = {f['properties']['iso']: f for f in json.load(open(countries_path, encoding='utf-8'))['features']}
    done = 0
    for iso in isos:
        if iso in index and os.path.exists(os.path.join(out_dir, f'{iso}.png')):
            continue
        f = feats.get(iso)
        if not f:
            continue
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        lons = [p[0] for poly in polys for ring in poly for p in ring]
        wrap = max(lons) - min(lons) > 300            # straddles the date line (Russia, USA, Fiji)
        fix = (lambda lon: lon + 360 if wrap and lon < 0 else lon)
        polys = [[[(fix(x), y) for x, y in ring] for ring in poly] for poly in polys]
        pts = [p for poly in polys for ring in poly for p in ring]
        w, e = min(p[0] for p in pts), max(p[0] for p in pts)
        s, n = min(p[1] for p in pts), max(p[1] for p in pts)
        x0, y0 = _merc(w, n)
        x1, y1 = _merc(e, s)
        W = max(48, min(MAX_PX, int((x1 - x0) * WORLD_PX)))
        H = max(48, min(MAX_PX, int((y1 - y0) / (x1 - x0) * W))) if x1 > x0 else W
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
        try:
            flag = _flag(iso, cache_dir)
        except Exception as ex:
            print(f'  ! flag {iso}: {ex}')
            continue
        # cover the country's box without distorting the flag, centred
        k = max(W / flag.width, H / flag.height)
        fw, fh = max(1, int(flag.width * k)), max(1, int(flag.height * k))
        flag = flag.resize((fw, fh), Image.LANCZOS).crop(((fw - W) // 2, (fh - H) // 2, (fw - W) // 2 + W, (fh - H) // 2 + H))
        out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        out.paste(flag, (0, 0), mask)
        out.save(os.path.join(out_dir, f'{iso}.png'), optimize=True)
        index[iso] = {'name': f['properties'].get('name'), 'coordinates': [[w, n], [e, n], [e, s], [w, s]]}
        done += 1
    with open(index_path, 'w', encoding='utf-8') as fh:
        json.dump(index, fh, indent=1, sort_keys=True)
    return done
