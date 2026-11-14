"""One-click logbook: rebuild from NeoFly + screenshots, serve web/, open the browser.

- Rebuilds on start, and again on every page load if NeoFly's save or any
  screenshot folder changed, so refreshing the page always shows the latest flights.
- If the logbook is already running, a second launch just opens the browser.
- Exits on its own a few minutes after the last browser tab closes (the page
  sends a heartbeat), so nothing is left running in the background.
Logs to logbook/logbook.log.
"""
import http.server
import json
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, 'web')
PORT = int(os.environ.get('LOGBOOK_PORT', 8787))
URL = f'http://127.0.0.1:{PORT}/'
IDLE_EXIT = 6 * 60
LOG = os.path.join(ROOT, 'logbook.log')

sys.path[:0] = [HERE, os.path.join(HERE, 'importers')]


def log(msg):
    line = time.strftime('%Y-%m-%d %H:%M:%S  ') + msg
    try:
        print(line, flush=True)
    except Exception:
        pass  # pythonw has no console
    with open(LOG, 'a', encoding='utf-8') as fh:
        fh.write(line + '\n')


class Rebuilder:
    def __init__(self):
        self.lock = threading.Lock()
        self.sig = None
        self.error = None

    def signature(self):
        import build, screenshots
        cfg = build.load_json(os.path.join(ROOT, 'config.json'), {})
        paths = [os.path.join(os.path.expandvars(cfg.get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly')), 'std.bin'),
                 os.path.join(ROOT, 'config.json'), os.path.join(ROOT, 'overrides.json')]
        for s in screenshots.expand_sources(cfg.get('photos', {}).get('sources', [{'auto': 'steam'}])):
            paths.append(os.path.expandvars(s['path']))
        out = []
        for p in paths:
            try:
                out.append((p, os.path.getmtime(p)))
            except OSError:
                out.append((p, None))
        return out

    def ensure(self, force=False):
        """Fast offline build whenever NeoFly / screenshots / settings changed; then
        fetch anything new (Wikipedia, places, hotels, flags) in the background."""
        with self.lock:
            try:
                sig = self.signature()
                if not force and sig == self.sig and os.path.exists(os.path.join(WEB, 'data', 'logbook.json')):
                    return
                import build
                t = time.time()
                build.main(fetch=False)
                self.sig, self.error = sig, None
                log(f'rebuilt in {time.time() - t:.1f}s')
            except Exception:
                self.error = traceback.format_exc()
                log('build failed:\n' + self.error)
                return
        self.enrich()

    def enrich(self):
        if self.enriching:
            self.again = True
            return
        self.enriching = True
        threading.Thread(target=self._enrich, daemon=True).start()

    def _enrich(self):
        try:
            while True:
                self.again = False
                with self.lock:
                    import build
                    t = time.time()
                    build.main(fetch=True)
                    log(f'background details fetched in {time.time() - t:.1f}s')
                if not self.again:
                    break
        except Exception:
            log('background fetch failed:\n' + traceback.format_exc())
        finally:
            self.enriching = False

    enriching = False
    again = False


def built_at():
    try:
        with open(os.path.join(WEB, 'data', 'logbook.json'), encoding='utf-8') as fh:
            return json.load(fh)['meta'].get('builtAt')
    except (OSError, ValueError, KeyError):
        return None


rebuilder = Rebuilder()
backup_lock = threading.Lock()
last_seen = time.time()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=WEB, **kw)

    def log_message(self, *a):
        pass

    def end_headers(self):
        if self.path.endswith(('.json', '.js', '.css', '.html')) or self.path == '/':
            self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def do_GET(self):
        global last_seen
        last_seen = time.time()
        path = self.path.split('?')[0]
        if path == '/__alive':
            return self._json({'ok': True})
        if path == '/__status':
            import backup
            return self._json({'error': rebuilder.error, 'lastBackup': backup.last(),
                               'builtAt': built_at(), 'fetching': rebuilder.enriching})
        if path.startswith('/__manual/'):
            return self._manual(path.rsplit('/', 1)[-1])
        if path in ('/', '/index.html'):
            rebuilder.ensure()
        return super().do_GET()

    def _manual(self, mid):
        """Open a manual found on this PC (only files the build listed - never arbitrary paths)."""
        try:
            reg = json.load(open(os.path.join(ROOT, 'manuals-index.json'), encoding='utf-8'))
        except (OSError, ValueError):
            reg = {}
        p = reg.get(mid)
        if not p or not os.path.isfile(p) or not p.lower().endswith('.pdf'):
            return self.send_error(404)
        size = os.path.getsize(p)
        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', f'inline; filename="{os.path.basename(p)}"')
        self.end_headers()
        with open(p, 'rb') as fh:
            while True:
                chunk = fh.read(1 << 20)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def do_POST(self):
        global last_seen
        last_seen = time.time()
        path = self.path.split('?')[0]
        if self.headers.get('X-Logbook') != '1':  # only the app's own buttons
            self.send_error(403)
            return
        if path == '/__backup':
            import backup
            rebuilder.ensure()  # back up the latest flights
            with backup_lock:
                try:
                    res = backup.run()
                    log(f'backup: neofly {res["neofly"]["file"]} (new={res["neofly"]["new"]}), '
                        f'{res["photos"]["copied"]} photos copied, {res["totalMB"]} MB total')
                    return self._json({'ok': True, **res})
                except Exception:
                    err = traceback.format_exc()
                    log('backup failed:\n' + err)
                    return self._json({'ok': False, 'error': err.strip().splitlines()[-1]})
        if path == '/__open-backup':
            import backup
            d = backup.current_dest()
            os.makedirs(d, exist_ok=True)
            os.startfile(d)
            return self._json({'ok': True})
        if path == '/__settings':
            try:
                n = int(self.headers.get('Content-Length') or 0)
                if n > 25_000_000:
                    raise ValueError('photo too large')
                req = json.loads(self.rfile.read(n) or b'{}')
                save_settings(req)
                rebuilder.ensure(force=True)
                return self._json({'ok': not rebuilder.error, 'error': rebuilder.error and rebuilder.error.strip().splitlines()[-1]})
            except Exception as e:
                log('settings failed:\n' + traceback.format_exc())
                return self._json({'ok': False, 'error': str(e)})
        self.send_error(404)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def save_settings(req):
    """Pilot settings from the app: which NeoFly pilot, their display name, their photo."""
    import base64, io
    import build
    path = os.path.join(ROOT, 'config.json')
    cfg = build.load_json(path, {})
    p = cfg.setdefault('pilot', {})
    name = (req.get('pilot') or '').strip()          # '' = whoever is logged in to NeoFly
    p['neofly'] = name or 'auto'
    target = (req.get('for') or name).strip()       # whose name/photo is being edited
    if target:
        name = target
        me = p.setdefault('pilots', {}).setdefault(name, {})
        if 'displayName' in req:
            dn = (req.get('displayName') or '').strip()
            if dn and dn != name:
                me['displayName'] = dn[:40]
            else:
                me.pop('displayName', None)
        if req.get('photo'):  # data URL from the file picker
            from PIL import Image, ImageOps
            raw = base64.b64decode(req['photo'].split(',', 1)[-1])
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB')
            im.thumbnail((800, 800))
            d = build.pilot_dir(name)
            os.makedirs(d, exist_ok=True)
            im.save(os.path.join(d, 'pilot.jpg'), 'JPEG', quality=88)
            me.pop('photo', None)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, indent=2)
    log(f'settings saved: pilot={p["neofly"]}')


def auto_backup():
    """Every launch: copy any new NeoFly progress and screenshots into backup/."""
    import backup
    time.sleep(3)
    with backup_lock:
        try:
            r = backup.run()
            log(f'auto-backup: neofly {r["neofly"]["file"]} (new={r["neofly"]["new"]}), {r["photos"]["copied"]} photos copied')
        except Exception:
            log('auto-backup failed:\n' + traceback.format_exc())


def already_running():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', PORT)) == 0


def main():
    if already_running():
        webbrowser.open(URL)
        return
    log('starting')
    rebuilder.ensure()
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if not os.environ.get('LOGBOOK_NO_BROWSER'):
        webbrowser.open(URL)
    log(f'serving {URL}')
    threading.Thread(target=auto_backup, daemon=True).start()
    while time.time() - last_seen < IDLE_EXIT:
        time.sleep(5)
    log('no open tabs - stopping')
    srv.shutdown()


if __name__ == '__main__':
    main()
