"""One-off: country outlines for the 'countries visited' map layer.

Downloads Natural Earth 1:50m admin-0 countries (public domain), keeps only the
ISO code and name, rounds coordinates, and writes web/geo/countries.json. The
result is committed, so the app never needs to download it.
    uv run --no-project python pipeline/make_countries.py
"""
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = 'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_50m_admin_0_countries.geojson'


def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]


def main():
    req = urllib.request.Request(SRC, headers={'User-Agent': 'KestrelAirLogbook/1.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    feats = []
    for f in data['features']:
        p = f['properties']
        iso = p.get('ISO_A2_EH') if p.get('ISO_A2_EH') not in (None, '-99') else p.get('ISO_A2')
        if iso in (None, '-99'):
            continue
        g = f['geometry']
        feats.append({'type': 'Feature', 'properties': {'iso': iso, 'name': p.get('NAME')},
                      'geometry': {'type': g['type'], 'coordinates': rnd(g['coordinates'])}})
    os.makedirs(os.path.join(ROOT, 'web', 'geo'), exist_ok=True)
    out = os.path.join(ROOT, 'web', 'geo', 'countries.json')
    with open(out, 'w', encoding='utf-8') as fh:
        json.dump({'type': 'FeatureCollection', 'features': feats}, fh, separators=(',', ':'))
    print(f'{len(feats)} countries -> {out} ({os.path.getsize(out) // 1024} KB)')


if __name__ == '__main__':
    main()
