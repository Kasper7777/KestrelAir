"""Which country is a point in? Real borders, not guesses.

Uses the Natural Earth outlines in web/geo/countries.json (point-in-polygon with a
bounding-box prefilter). ICAO prefixes are only a fallback for points just off a
coastline (small islands, reclaimed runways) - then the nearest country within
~30 km wins, and only after that the prefix table.
"""
import json
import math
import os

_COUNTRIES = None


def _load(path):
    global _COUNTRIES
    if _COUNTRIES is None:
        data = json.load(open(path, encoding='utf-8'))
        out = []
        for f in data['features']:
            g = f['geometry']
            polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
            for poly in polys:
                ring = poly[0]
                xs, ys = [p[0] for p in ring], [p[1] for p in ring]
                out.append({'iso': f['properties']['iso'], 'name': f['properties']['name'], 'poly': poly,
                            'bbox': (min(xs), min(ys), max(xs), max(ys))})
        _COUNTRIES = out
    return _COUNTRIES


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _in_poly(x, y, poly):
    return _in_ring(x, y, poly[0]) and not any(_in_ring(x, y, hole) for hole in poly[1:])


def _seg_km(lon, lat, ring):
    """Rough distance (km) from a point to a ring's nearest vertex/edge."""
    k = math.cos(math.radians(lat))
    best = float('inf')
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        dx, dy = (x2 - x1) * k, y2 - y1
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, (((lon - x1) * k) * dx + (lat - y1) * dy) / L))
        px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        d = math.hypot((lon - px) * k, lat - py) * 111.2
        if d < best:
            best = d
    return best


def country_at(lon, lat, countries_path, near_km=30):
    """(iso, name, how) for a point; how is 'border' or 'near'; None if nothing close."""
    cs = _load(countries_path)
    for c in cs:
        x0, y0, x1, y1 = c['bbox']
        if x0 <= lon <= x1 and y0 <= lat <= y1 and _in_poly(lon, lat, c['poly']):
            return c['iso'], c['name'], 'border'
    best = None
    for c in cs:
        x0, y0, x1, y1 = c['bbox']
        if not (x0 - 0.6 <= lon <= x1 + 0.6 and y0 - 0.4 <= lat <= y1 + 0.4):
            continue
        d = _seg_km(lon, lat, c['poly'][0])
        if d <= near_km and (best is None or d < best[0]):
            best = (d, c)
    if best:
        return best[1]['iso'], best[1]['name'], 'near'
    return None
