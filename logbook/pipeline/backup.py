"""Back up everything the logbook is built from into logbook/backup/.

  backup/neofly/std-YYYYMMDD-HHMMSS.bin   NeoFly save, taken with SQLite's online
                                          backup API (safe while NeoFly is running);
                                          a new copy only when the save has changed
  backup/neofly/flights.csv               every leg in plain text (opens in Excel)
  backup/photos/<source>/<file>           full-quality originals, never deleted here,
                                          so they survive even if Steam loses them
  backup/logbook.json, config.json, overrides.json
  backup/last-backup.json                 summary of the last run

Run from the app's Back up button, or:  uv run --no-project python pipeline/backup.py
"""
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEST = os.path.join(ROOT, 'backup')


def current_dest():
    """This pilot's own backup folder: backup/pilots/<pilot>/ (from the last build)."""
    try:
        with open(os.path.join(ROOT, 'web', 'data', 'logbook.json'), encoding='utf-8') as fh:
            slug = json.load(fh)['meta'].get('pilotSlug') or 'pilot'
    except (OSError, ValueError, KeyError):
        slug = 'pilot'
    return os.path.join(ROOT, 'backup', 'pilots', slug)
sys.path[:0] = [HERE, os.path.join(HERE, 'importers')]


def _sha(path):
    h = hashlib.sha1()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def backup_neofly(nf_dir):
    out = os.path.join(DEST, 'neofly')
    os.makedirs(out, exist_ok=True)
    src = os.path.join(nf_dir, 'std.bin')
    tmp = os.path.join(out, 'std.tmp')
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    d = sqlite3.connect(tmp)
    with d:
        s.backup(d)
    s.close()
    d.close()
    new_hash = _sha(tmp)
    existing = sorted(f for f in os.listdir(out) if re.match(r'std-\d{8}-\d{6}\.bin$', f))
    if existing and _sha(os.path.join(out, existing[-1])) == new_hash:
        os.remove(tmp)
        return {'file': existing[-1], 'new': False, 'copies': len(existing)}
    name = time.strftime('std-%Y%m%d-%H%M%S.bin')
    os.replace(tmp, os.path.join(out, name))
    return {'file': name, 'new': True, 'copies': len(existing) + 1}


def backup_photos(sources, in_logbook=frozenset()):
    import screenshots
    copied = kept = 0
    size = 0
    for src in screenshots.expand_sources(sources):
        root = os.path.expandvars(os.path.expanduser(src['path']))
        if not os.path.isdir(root):
            continue
        label = re.sub(r'[^\w() -]+', '', src.get('label', 'Screenshots')).strip() or 'Screenshots'
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() != 'thumbnails']
            for fn in files:
                if not fn.lower().endswith(screenshots.EXTS):
                    continue
                full = os.path.join(dirpath, fn)
                st = os.stat(full)
                if st.st_size < src.get('minBytes', 20000):
                    continue
                if src.get('onlyDuringJourney') and os.path.normcase(full) not in in_logbook:
                    continue  # general capture folders: only shots that made it into the logbook
                dst_dir = os.path.join(DEST, 'photos', label)
                dst = os.path.join(dst_dir, os.path.relpath(full, root))
                if os.path.exists(dst) and os.path.getsize(dst) == st.st_size:
                    kept += 1
                    continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(full, dst)
                copied += 1
                size += st.st_size
    return {'copied': copied, 'alreadyBackedUp': kept, 'copiedMB': round(size / 1e6, 1)}


def export_csv(logbook_path):
    with open(logbook_path, encoding='utf-8') as fh:
        db = json.load(fh)
    path = os.path.join(DEST, 'neofly', 'flights.csv')
    cols = ['leg', 'type', 'from', 'from_name', 'to', 'to_name', 'start', 'end', 'minutes', 'distance_nm',
            'aircraft', 'landing_fpm', 'missions', 'pay', 'photos', 'notes']
    with open(path, 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for l in db['legs']:
            ms = l.get('missions', [])
            w.writerow([
                l['id'], 'flight' if l['kind'] == 'flight' else l.get('modeLabel', 'transfer'),
                l['from'], db['airports'].get(l['from'], {}).get('name'), l['to'], db['airports'].get(l['to'], {}).get('name'),
                l['start'], l['end'], l.get('minutes'), l.get('distanceNm'),
                db['aircraft'].get(l.get('aircraft'), {}).get('name', ''), l.get('landingFpm') or '',
                '; '.join(f"{m['type']} {m['from']}-{m['to']} ({m['status']})" for m in ms),
                sum(m['reward'] or 0 for m in ms if m['status'] == 'completed'), len(l.get('photos', [])),
                ' | '.join(l.get('notes', [])) + (' recovered from job log' if l.get('inferred') else ''),
            ])
    return len(db['legs'])


def run():
    import build
    t = time.time()
    cfg = build.load_json(os.path.join(ROOT, 'config.json'), {})
    nf_dir = os.path.expandvars(cfg.get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly'))
    global DEST
    DEST = current_dest()
    os.makedirs(DEST, exist_ok=True)
    result = {'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'folder': DEST}
    if os.path.exists(os.path.join(nf_dir, 'std.bin')):
        result['neofly'] = backup_neofly(nf_dir)
    else:  # another PC without NeoFly: keep what's already backed up
        saves = sorted(f for f in os.listdir(os.path.join(DEST, 'neofly'))) if os.path.isdir(os.path.join(DEST, 'neofly')) else []
        saves = [f for f in saves if re.match(r'std-\d{8}-\d{6}\.bin$', f)]
        result['neofly'] = {'file': saves[-1] if saves else None, 'new': False, 'copies': len(saves), 'noNeoflyHere': True}
    lb = os.path.join(ROOT, 'web', 'data', 'logbook.json')
    in_logbook = set()
    if os.path.exists(lb):
        with open(lb, encoding='utf-8') as fh:
            in_logbook = {os.path.normcase(p['original']) for p in json.load(fh)['photos'].values() if p.get('original')}
    result['photos'] = backup_photos(cfg.get('photos', {}).get('sources', [{'auto': 'steam'}]), in_logbook)
    if os.path.exists(lb):
        result['legs'] = export_csv(lb)
        shutil.copy2(lb, os.path.join(DEST, 'logbook.json'))
    for f in ('config.json', 'overrides.json'):
        if os.path.exists(os.path.join(ROOT, f)):
            shutil.copy2(os.path.join(ROOT, f), os.path.join(DEST, f))
    total = 0
    for dp, _, fs in os.walk(DEST):
        total += sum(os.path.getsize(os.path.join(dp, f)) for f in fs)
    result['totalMB'] = round(total / 1e6, 1)
    result['seconds'] = round(time.time() - t, 1)
    with open(os.path.join(DEST, 'last-backup.json'), 'w', encoding='utf-8') as fh:
        json.dump(result, fh, indent=1)
    return result


def last():
    try:
        with open(os.path.join(current_dest(), 'last-backup.json'), encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


if __name__ == '__main__':
    print(json.dumps(run(), indent=1))
