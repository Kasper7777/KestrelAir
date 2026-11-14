"""SimBrief flight plans (OFPs) as documents on each flight.

SimBrief's public API returns only your *latest* OFP, so every logbook run archives
it (if new) into backup/pilots/<pilot>/simbrief/: the full OFP JSON, the PDF and the
route map. Over time every flight gets its plan. Plans you saved yourself also count:
any PDF / flight-plan file on this PC whose name contains the route (SimBrief
names them like EGOSGQPP_PDF_1699999999.pdf) is matched to that flight.

Matching: same origin and destination, and the planned departure within 2 days of
the flight (nearest wins).
"""
import glob
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

UA = {'User-Agent': 'KestrelAirLogbook/1.0'}
API = 'https://www.simbrief.com/api/xml.fetcher.php'


def _get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def archive_latest(username, folder, fetch=True):
    """Save the latest OFP (JSON + PDF + map) if it isn't archived yet. Returns its id or None."""
    if not username or not fetch:
        return None
    os.makedirs(folder, exist_ok=True)
    key = 'userid' if str(username).isdigit() else 'username'
    try:
        ofp = json.loads(_get(f'{API}?{key}={urllib.parse.quote(str(username))}&json=1'))
    except Exception as e:
        print(f'  ! SimBrief: {e}')
        return None
    if (ofp.get('fetch') or {}).get('status', 'Success') != 'Success':
        print(f'  ! SimBrief: {(ofp.get("fetch") or {}).get("status")}')
        return None
    rid = str((ofp.get('params') or {}).get('request_id') or (ofp.get('params') or {}).get('time_generated') or '')
    if not rid:
        return None
    path = os.path.join(folder, f'{rid}.json')
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(ofp, fh)
        files = ofp.get('files') or {}
        try:
            pdf = (files.get('pdf') or {}).get('link')
            if pdf:
                with open(os.path.join(folder, f'{rid}.pdf'), 'wb') as fh:
                    fh.write(_get(files['directory'] + pdf, 60))
        except Exception:
            pass
        try:
            maps = (ofp.get('images') or {}).get('map') or []
            first = maps[0] if isinstance(maps, list) and maps else maps
            if isinstance(first, dict) and first.get('link'):
                ext = os.path.splitext(first['link'])[1] or '.gif'
                with open(os.path.join(folder, f'{rid}-map{ext}'), 'wb') as fh:
                    fh.write(_get(ofp['images']['directory'] + first['link'], 60))
        except Exception:
            pass
        print(f'  SimBrief: archived plan {rid}')
    return rid


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summaries(folder):
    """Every archived OFP, boiled down to what the app shows."""
    out = []
    for path in sorted(glob.glob(os.path.join(folder, '*.json'))):
        try:
            o = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError):
            continue
        rid = os.path.splitext(os.path.basename(path))[0]
        g, t, w, f, p = (o.get(k) or {} for k in ('general', 'times', 'weights', 'fuel', 'params'))
        out_t = _num(t.get('sched_out')) or _num(p.get('time_generated'))
        fixes = (o.get('navlog') or {}).get('fix') or []
        if isinstance(fixes, dict):
            fixes = [fixes]
        out.append({
            'id': rid, 'kind': 'simbrief', 'origin': (o.get('origin') or {}).get('icao_code'),
            'destination': (o.get('destination') or {}).get('icao_code'), 'alternate': (o.get('alternate') or {}).get('icao_code'),
            'out': datetime.utcfromtimestamp(out_t).strftime('%Y-%m-%dT%H:%M') if out_t else None,
            'callsign': (o.get('atc') or {}).get('callsign'), 'aircraft': (o.get('aircraft') or {}).get('name'),
            'reg': (o.get('aircraft') or {}).get('reg'), 'route': g.get('route'), 'cruise': g.get('initial_altitude'),
            'distance': g.get('route_distance') or g.get('air_distance'), 'ete': _num(t.get('est_time_enroute')),
            'units': p.get('units'), 'blockFuel': f.get('plan_ramp'), 'tripFuel': f.get('enroute_burn'), 'reserve': f.get('reserve'),
            'zfw': w.get('est_zfw'), 'tow': w.get('est_tow'), 'ldw': w.get('est_ldw'), 'pax': w.get('pax_count'), 'cargo': w.get('cargo'),
            'costIndex': g.get('costindex'), 'windComp': g.get('avg_wind_comp'),
            'navlog': [{'ident': x.get('ident'), 'type': x.get('type'), 'via': x.get('via_airway'), 'alt': x.get('altitude_feet'),
                        'wind': f'{x.get("wind_dir", "")}/{x.get("wind_spd", "")}', 'dist': x.get('distance'),
                        'time': x.get('time_total')} for x in fixes][:60],
            'pdf': f'{rid}.pdf' if os.path.exists(os.path.join(folder, f'{rid}.pdf')) else None,
            'map': next((os.path.basename(m) for m in glob.glob(os.path.join(folder, f'{rid}-map.*'))), None),
        })
    return out


def find_saved_plans(legs, roots, max_depth=4):
    """Plan files you saved yourself, named with a flight's route (e.g. EGOSGQPP..., EGOS-GQPP...)."""
    routes = {(l['from'], l['to']) for l in legs if l['kind'] == 'flight'}
    found = []
    for root in roots:
        root = os.path.expandvars(root)
        if not os.path.isdir(root):
            continue
        base = root.rstrip('\\/').count(os.sep)
        for dirpath, dirnames, files in os.walk(root):
            if dirpath.count(os.sep) - base >= max_depth:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if not d.startswith('.') and d.lower() not in ('node_modules', 'web', 'cache', 'backup')]
            for fn in files:
                if not re.search(r'\.(pdf|pln|fms|flp|txt|xml|json|html?)$', fn, re.I):
                    continue
                name = fn.upper()
                for a, b in routes:
                    if re.search(rf'{a}[\W_]*{b}', name):
                        full = os.path.join(dirpath, fn)
                        found.append({'from': a, 'to': b, 'path': full, 'title': fn,
                                      'mtime': datetime.fromtimestamp(os.path.getmtime(full)).strftime('%Y-%m-%dT%H:%M')})
                        break
    return found


def attach(legs, ofps, saved, folder, media_dir):
    """Put matching documents on each flight; copy their files where the page can open them."""
    os.makedirs(media_dir, exist_ok=True)
    def best_leg(a, b, when):
        cands = [l for l in legs if l['kind'] == 'flight' and l['from'] == a and l['to'] == b]
        if not cands:
            return None
        if not when:
            return cands[-1]
        t = datetime.fromisoformat(when)
        l = min(cands, key=lambda l: abs(datetime.fromisoformat(l['start']) - t))
        return l if abs(datetime.fromisoformat(l['start']) - t) <= timedelta(days=2) else None
    n = 0
    for o in ofps:
        l = best_leg(o['origin'], o['destination'], o['out'])
        if not l:
            continue
        for k in ('pdf', 'map'):
            if o.get(k):
                src = os.path.join(folder, o[k])
                dst = os.path.join(media_dir, o[k])
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
                o[k] = f'media/docs/{o[k]}'
        l.setdefault('docs', []).append(o)
        n += 1
    for s in saved:
        l = best_leg(s['from'], s['to'], None if s['path'].lower().endswith('.pdf') else s['mtime']) or best_leg(s['from'], s['to'], None)
        if not l:
            continue
        safe = re.sub(r'[^\w.\-]+', '_', s['title'])
        dst = os.path.join(media_dir, safe)
        if not os.path.exists(dst):
            shutil.copy2(s['path'], dst)
        l.setdefault('docs', []).append({'kind': 'file', 'title': s['title'], 'file': f'media/docs/{safe}'})
        n += 1
    return n
