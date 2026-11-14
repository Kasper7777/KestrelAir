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

    def ensure(self):
        with self.lock:
            try:
                sig = self.signature()
                if sig == self.sig and os.path.exists(os.path.join(WEB, 'data', 'logbook.json')):
                    return
                import build
                t = time.time()
                build.main()
                self.sig, self.error = sig, None
                log(f'rebuilt in {time.time() - t:.1f}s')
            except Exception:
                self.error = traceback.format_exc()
                log('build failed:\n' + self.error)


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
            return self._json({'error': rebuilder.error, 'lastBackup': backup.last()})
        if path in ('/', '/index.html'):
            rebuilder.ensure()
        return super().do_GET()

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
            os.makedirs(backup.DEST, exist_ok=True)
            os.startfile(backup.DEST)
            return self._json({'ok': True})
        self.send_error(404)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


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
