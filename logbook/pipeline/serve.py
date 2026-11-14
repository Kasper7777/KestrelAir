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
import shutil
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
RETRY_SECONDS = 120          # how often the background top-up runs while something is still missing
ARCHIVES = {                 # what Settings can show and wipe (relative to logbook/)
    'news': ('Local news', 'backup/news'),
    'places': ('Restaurants, hotels, menus & venue photos', 'backup/places'),
    'wiki': ('Wikipedia: airports & aircraft', 'backup/wiki'),
    'flags': ('Flag fills', 'web/geo/flags'),
    'media': ('Display copies (rebuilt from the archives)', 'web/media'),
}
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

    def ensure(self, force=False, wait=True):
        """Fast offline build whenever NeoFly / screenshots / settings changed; then
        fetch anything new (Wikipedia, places, hotels, flags, news) in the background.
        wait=False (page loads): if a build is already running, serve what's there now
        rather than making the page wait - the background fetch can take minutes."""
        if not self.lock.acquire(blocking=wait):
            return
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
        finally:
            self.lock.release()
        self.enrich()

    def enrich(self):
        self.pictures()
        if self.enriching:
            self.again = True
            return
        self.enriching = True
        threading.Thread(target=self._enrich, daemon=True).start()

    def _enrich(self):
        """Fetch anything new, then keep topping up the archive every 2 minutes while
        something is still missing (e.g. news pictures GDELT throttled) - adding to
        what's archived, never re-downloading it."""
        import news
        try:
            while True:
                self.again = False
                wait_for_sim(self)
                with self.lock:
                    import build
                    t = time.time()
                    build.main(fetch=True)
                    self.last_run = time.strftime('%Y-%m-%dT%H:%M:%S')
                    log(f'background details fetched in {time.time() - t:.1f}s')
                self.pictures()
                self.pending = news.pending_arrivals(os.path.join(ROOT, 'backup', 'news'))
                if self.again:
                    continue
                if not self.pending or self.stop_retry:
                    break
                self.next_check = time.time() + RETRY_SECONDS
                while time.time() < self.next_check and not self.again and not self.stop_retry:
                    time.sleep(2)
                self.next_check = None
        except Exception:
            log('background fetch failed:\n' + traceback.format_exc())
        finally:
            self.enriching = False

    def pictures(self):
        """Start the news picture finder (once): it keeps looking up each story's real
        article - one search every few seconds - and republishes the logbook whenever
        it has found new pictures, so they appear without waiting for a full refresh."""
        if self.finding:
            return
        self.finding = True
        threading.Thread(target=self._pictures, daemon=True).start()

    def _pictures(self):
        import news
        news_dir = os.path.join(ROOT, 'backup', 'news')
        try:
            unpublished = 0
            while not self.stop_retry:
                wait_for_sim(self)
                self.pictures_left = news.pending(news_dir)
                if not self.pictures_left and not unpublished:
                    break
                found = news.resolve(news_dir, budget_s=60, log=log) if self.pictures_left else 0
                unpublished += found
                if unpublished and self.lock.acquire(timeout=1):      # a full fetch run will publish them anyway
                    try:
                        import build
                        build.main(fetch=False)
                        log(f'news: published {unpublished} new story pictures')
                        unpublished = 0
                    finally:
                        self.lock.release()
                if not found:
                    time.sleep(20)          # nothing due right now (search resting, or retries not due yet)
        except Exception:
            log('news picture finder failed:\n' + traceback.format_exc())
        finally:
            self.finding = False

    paused_for_sim = False
    finding = False
    pictures_left = 0
    enriching = False
    again = False
    stop_retry = False
    last_run = None
    next_check = None
    pending = 0


def built_at():
    try:
        with open(os.path.join(WEB, 'data', 'logbook.json'), encoding='utf-8') as fh:
            return json.load(fh)['meta'].get('builtAt')
    except (OSError, ValueError, KeyError):
        return None


_live = [None, None]     # (config signature, Live)
_simsrc = []


def _sim_source(live):
    if not _simsrc:
        _simsrc.append(live.SimSource())
    return _simsrc[0]


def live_state():
    """What's flying right now (see live.py). Never raises: the page just shows nothing."""
    try:
        import build
        import live
        cfg = build.load_json(os.path.join(ROOT, 'config.json'), {})
        nf_dir = os.path.expandvars(cfg.get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly'))
        pilot = (cfg.get('pilot') or {}).get('neofly')
        pilot = None if pilot in (None, '', 'auto') else pilot
        sig = (nf_dir, pilot)
        if _live[0] != sig:
            _live[0], _live[1] = sig, live.Live([live.NeoFlySource(nf_dir, pilot)], sim=_sim_source(live))
        return _live[1].state()
    except Exception as e:
        return {'flights': [], 'at': None, 'errors': [str(e)]}


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
                               'builtAt': built_at(), 'fetching': rebuilder.enriching and rebuilder.next_check is None and not rebuilder.paused_for_sim,
                               'simRunning': sim_running(), 'pausedForSim': rebuilder.paused_for_sim})
        if path == '/__datainfo':
            return self._json(data_info())
        if path == '/__live':
            return self._json(live_state())
        if path.startswith('/__manual/'):
            return self._manual(path.rsplit('/', 1)[-1])
        if path in ('/', '/index.html'):
            rebuilder.ensure(wait=False)     # never make the page wait on a background fetch
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
            rebuilder.ensure(wait=False)  # back up the latest flights (don't wait on a background fetch)
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
        if path == '/__refresh':
            rebuilder.again = True
            if not rebuilder.enriching:
                rebuilder.enrich()
            elif rebuilder.next_check:
                rebuilder.next_check = time.time()
            return self._json({'ok': True})
        if path == '/__wipe':
            try:
                n = int(self.headers.get('Content-Length') or 0)
                req = json.loads(self.rfile.read(n) or b'{}')
                what = req.get('what')
                if what == 'pilot':
                    import backup
                    target = backup.current_dest()
                    if (req.get('confirm') or '').strip().lower() != os.path.basename(target).lower():
                        return self._json({'ok': False, 'error': 'Type the pilot name to confirm'})
                elif what in ARCHIVES:
                    target = os.path.join(ROOT, *ARCHIVES[what][1].split('/'))
                else:
                    return self._json({'ok': False, 'error': 'Unknown archive'})
                if not rebuilder.lock.acquire(timeout=15):
                    return self._json({'ok': False, 'error': 'A background update is busy - try again in a moment'})
                try:
                    if os.path.isdir(target):
                        shutil.rmtree(target)
                    if what == 'flags':
                        try:
                            os.remove(os.path.join(WEB, 'geo', 'flags.json'))
                        except OSError:
                            pass
                finally:
                    rebuilder.lock.release()
                log(f'wiped {what}: {target}')
                rebuilder.ensure(force=True)          # rebuild from what's left; the background fetch refills it
                return self._json({'ok': True})
            except Exception as e:
                log('wipe failed:\n' + traceback.format_exc())
                return self._json({'ok': False, 'error': str(e)})
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


def _size(path):
    total = files = 0
    for dp, _, fs in os.walk(path):
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(dp, f))
                files += 1
            except OSError:
                pass
    return total, files


def data_info():
    """Archive sizes, background-update status and the last self-check, for Settings."""
    import backup
    import news
    out = {'archives': []}
    for key, (label, rel) in ARCHIVES.items():
        b, n = _size(os.path.join(ROOT, *rel.split('/')))
        out['archives'].append({'key': key, 'label': label, 'mb': round(b / 1e6, 1), 'files': n})
    pdir = backup.current_dest()
    b, n = _size(pdir)
    out['pilot'] = {'name': os.path.basename(pdir), 'mb': round(b / 1e6, 1), 'files': n}
    try:
        cache = json.load(open(os.path.join(ROOT, 'backup', 'news', 'news.json'), encoding='utf-8'))
        out['newsStories'] = sum(len(v) for k, v in cache.items() if not k.startswith('_') and isinstance(v, list))
    except (OSError, ValueError):
        out['newsStories'] = 0
    out['background'] = {'running': rebuilder.enriching and rebuilder.next_check is None,
                         'nextCheckIn': max(0, round(rebuilder.next_check - time.time())) if rebuilder.next_check else None,
                         'lastRun': rebuilder.last_run, 'pending': news.pending(os.path.join(ROOT, 'backup', 'news')),
                         'retrySeconds': RETRY_SECONDS}
    try:
        with open(os.path.join(WEB, 'data', 'logbook.json'), encoding='utf-8') as fh:
            out['checks'] = json.load(fh)['meta'].get('checks', [])
    except (OSError, ValueError, KeyError):
        out['checks'] = []
    return out


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
        if 'simbrief' in req:
            sb = (req.get('simbrief') or '').strip()
            if sb:
                me['simbrief'] = sb[:60]
            else:
                me.pop('simbrief', None)
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


# ---------- stay out of the simulator's way
SIM_EXES = ('flightsimulator.exe', 'flightsimulator2024.exe')
_sim = [False, 0.0]


def sim_running():
    """Is Microsoft Flight Simulator open? (checked at most every 30 s; cheap)"""
    if time.time() - _sim[1] > 30:
        _sim[1] = time.time()
        try:
            import subprocess
            out = subprocess.run(['tasklist', '/NH', '/FO', 'CSV'], capture_output=True, text=True, timeout=10,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.lower()
            _sim[0] = any(f'"{exe}"' in out for exe in SIM_EXES)
        except Exception:
            pass
    return _sim[0]


def wait_for_sim(rb):
    """Heavy background work (downloads, image processing) waits while the sim is running."""
    while sim_running() and not rb.stop_retry:
        rb.paused_for_sim = True
        time.sleep(30)
    rb.paused_for_sim = False


def background_priority():
    """Run the whole logbook at background priority (CPU, disk and memory), so the
    simulator always comes first - on Windows; elsewhere, a lower nice value."""
    try:
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            k.GetCurrentProcess.restype = wintypes.HANDLE
            k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            h = k.GetCurrentProcess()
            k.SetPriorityClass(h, 0x00100000)          # PROCESS_MODE_BACKGROUND_BEGIN (low disk + memory priority)
            k.SetPriorityClass(h, 0x00000040)          # then IDLE_PRIORITY_CLASS for the CPU (order matters)
        else:
            os.nice(10)
    except Exception:
        pass


def already_running():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', PORT)) == 0


def main():
    if already_running():
        webbrowser.open(URL)
        return
    log('starting')
    background_priority()
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
