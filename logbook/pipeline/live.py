"""Live: what's flying right now - read only from data the sim tools already keep.

Nothing is recorded here. Every source is read on demand while the logbook is
open, and each one returns flights in the same shape, so the map doesn't care
where a flight came from:

    {'id', 'who': 'you' | 'hired', 'pilot', 'aircraft': {'name', 'tail'},
     'from': {'ident', 'lat', 'lon'} | None, 'to': {...} | None,
     'position': {'lat', 'lon', 'alt', 'speed'} | None,
     'track': [[lon, lat], ...], 'status': 'planned' | 'airborne' | 'stale',
     'mission': {'type', 'pax', 'cargoLbs', 'reward'} | None, 'source'}

`from` / `to` / `mission` are optional on purpose: a future source that reads the
simulator directly (no NeoFly, no mission, just you flying) fits the same shape.
Add it to SOURCES; the web app already handles whatever comes back.

NeoFly source:
  - the jobs loaded on your current plane -> the flight you're about to fly ('planned')
  - NeoFly's own trajectory log while it tracks a flight -> where you are ('airborne')
  - hired pilots' flights with their current position (NeoFly moves them) ('airborne')
"""
import math
import os
import re
import shutil
import sqlite3
import tempfile
import threading
import time

MIN_GAP = 10              # seconds between reads, however often the page asks
STALE_AFTER = 20 * 60        # NeoFly hasn't written anything for 20 min: probably paused / sim closed


def _mission_name(code):
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'importers'))
        from neofly import MISSION_TYPES
        return MISSION_TYPES.get(code, f'Mission {code}')
    except Exception:
        return None if code is None else f'Mission {code}'


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _latlon(text):
    """NeoFly writes positions as text; take the first two numbers that look like lat, lon."""
    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', str(text or '').replace(',', '.') if ';' in str(text or '') else str(text or ''))]
    if len(nums) < 2:
        return None
    lat, lon = nums[0], nums[1]
    if abs(lat) > 90 and abs(lon) <= 90:
        lat, lon = lon, lat
    if abs(lat) > 90 or abs(lon) > 180 or (lat == 0 and lon == 0):
        return None
    return lat, lon


class NeoFlySource:
    name = 'neofly'

    def __init__(self, neofly_dir, pilot_name=None):
        self.std = os.path.join(neofly_dir, 'std.bin')
        self.pilot_name = pilot_name
        self.location = None
        self.pilot = None

    def read(self):
        if not os.path.exists(self.std):
            return []
        tmp = tempfile.mkdtemp(prefix='kalive-')
        try:
            dst = os.path.join(tmp, 'std.bin')
            shutil.copy2(self.std, dst)
            for ext in ('-wal', '-shm'):                 # include anything NeoFly hasn't checkpointed yet
                if os.path.exists(self.std + ext):
                    shutil.copy2(self.std + ext, dst + ext)
            db = sqlite3.connect(f'file:{dst}?mode=ro', uri=True)
            db.row_factory = sqlite3.Row
            try:
                return self._flights(db, os.path.getmtime(self.std))
            finally:
                db.close()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @staticmethod
    def _tables(db):
        return {r[0] for r in db.execute("select name from sqlite_master where type='table'")}

    @staticmethod
    def _cols(db, table):
        return {r[1] for r in db.execute(f'pragma table_info("{table}")')}

    def _aircraft(self, db, hangar_id):
        try:
            r = db.execute('''select h.tailNumber tail, a.name model, l.name livery from hangar h
                              left join liveries l on l.id = h.liveryId left join aircrafts a on a.id = l.aircraftId
                              where h.id = ?''', (hangar_id,)).fetchone()
        except sqlite3.Error:
            r = None
        if not r:
            return {'name': None, 'tail': None, 'hangarId': hangar_id}
        name = re.split(r',', r['model'] or '')[0].strip() or r['livery']
        return {'name': name, 'tail': (r['tail'] or '').strip() or None, 'hangarId': hangar_id}

    def _job(self, db, job_id):
        try:
            j = db.execute('select * from jobs where id = ?', (job_id,)).fetchone()
        except sqlite3.Error:
            j = None
        if not j:
            return None
        k = set(j.keys())
        def end(ident, lat, lon):
            la, lo = _num(j[lat]) if lat in k else None, _num(j[lon]) if lon in k else None
            return {'ident': j[ident] if ident in k else None, 'lat': la, 'lon': lo} if la is not None and lo is not None else (
                {'ident': j[ident], 'lat': None, 'lon': None} if ident in k and j[ident] else None)
        return {'from': end('departure', 'latDep', 'lonDep'), 'to': end('arrival', 'latArriv', 'lonArriv'),
                'mission': {'type': _mission_name(j['missionType']) if 'missionType' in k else None, 'pax': j['pax'] if 'pax' in k else None,
                            'cargoLbs': j['weight'] if 'weight' in k else None, 'reward': j['reward'] if 'reward' in k else None}}

    def _flights(self, db, mtime):
        tables = self._tables(db)
        if 'players' not in tables:
            return []
        players = list(db.execute('select * from players'))
        if not players:
            return []
        me = next((p for p in players if self.pilot_name and (p['name'] or '').lower() == self.pilot_name.lower()), None)
        if me is None and 'currentpilot' in tables:
            row = db.execute('select pilotID from currentpilot').fetchone()
            me = next((p for p in players if row and p['id'] == row[0]), None)
        me = me or players[0]
        self.pilot = me['name']
        stale = time.time() - mtime > STALE_AFTER
        self.location = me['pilotCurrentICAO'] if 'pilotCurrentICAO' in me.keys() else None     # where you last landed
        out = []

        # ---- you: NeoFly's trajectory log while it's tracking a flight
        track, pos = [], None
        if 'trajectoryLog' in tables:
            cols = self._cols(db, 'trajectoryLog')
            if 'location' in cols:
                last = db.execute('select max(flightID) from trajectoryLog').fetchone()[0] if 'flightID' in cols else None
                q = 'select * from trajectoryLog' + (' where flightID = ?' if last is not None else '') + ' order by id'
                for r in db.execute(q, (last,) if last is not None else ()):
                    ll = _latlon(r['location'])
                    if ll:
                        track.append([round(ll[1], 5), round(ll[0], 5)])
                        pos = {'lat': ll[0], 'lon': ll[1], 'alt': r['altitude'] if 'altitude' in cols else None,
                               'speed': r['speed'] if 'speed' in cols else None}
        # ---- you: the jobs loaded on your current plane
        plane = me['currentPlane'] if 'currentPlane' in me.keys() else None
        job = None
        if plane and 'planeJobs' in tables:
            for r in db.execute('select jobId from planeJobs where planeId = ?', (plane,)):
                job = self._job(db, r['jobId'])
                if job:
                    break
        if pos or job:
            out.append({'id': f'you-{plane or 0}', 'who': 'you', 'pilot': me['name'], 'aircraft': self._aircraft(db, plane),
                        'from': (job or {}).get('from') or ({'ident': me['pilotCurrentICAO'], 'lat': None, 'lon': None}
                                                            if 'pilotCurrentICAO' in me.keys() and not track else None),
                        'to': (job or {}).get('to'), 'mission': (job or {}).get('mission'),
                        'position': pos, 'track': track[-2000:],
                        'status': ('stale' if stale else 'airborne') if pos else 'planned', 'source': self.name})

        # ---- hired pilots in the air (NeoFly moves them along their route)
        if 'aipilotflight' in tables:
            names = {}
            if 'aipilots' in tables:
                names = {r['id']: r['name'] for r in db.execute('select id, name from aipilots')}
            for r in db.execute('select * from aipilotflight'):
                k = set(r.keys())
                if 'ownerId' in k and r['ownerId'] not in (None, me['id']):
                    continue
                la, lo = _num(r['currentLat']) if 'currentLat' in k else None, _num(r['currentLon']) if 'currentLon' in k else None
                job = self._job(db, r['jobId']) if 'jobId' in k else None
                out.append({'id': f'hired-{r["id"]}', 'who': 'hired', 'pilot': names.get(r['aipilotId'] if 'aipilotId' in k else None),
                            'aircraft': self._aircraft(db, r['aircraftID']) if 'aircraftID' in k else {'name': None},
                            'from': (job or {}).get('from'), 'to': (job or {}).get('to'), 'mission': (job or {}).get('mission'),
                            'position': {'lat': la, 'lon': lo, 'alt': None, 'speed': None} if la is not None and lo is not None else None,
                            'track': [], 'status': 'airborne', 'started': r['dateStart'] if 'dateStart' in k else None, 'source': self.name})
        return out


class SimSource:
    """Microsoft Flight Simulator itself, over SimConnect (the sim's own add-on interface).

    Light by design: one small read every 2 s (position, altitude, heading, speeds,
    on-ground, aircraft), only while the logbook page is open and the sim is running;
    it disconnects a minute after the page stops asking. The trail of the current
    flight is kept in memory only - nothing is written anywhere.
    Needs no NeoFly and no mission: free flights show up too."""
    name = 'sim'
    EVERY = 2.0
    VARS = ('PLANE_LATITUDE', 'PLANE_LONGITUDE', 'PLANE_ALTITUDE', 'PLANE_ALT_ABOVE_GROUND', 'PLANE_HEADING_DEGREES_TRUE',
            'GROUND_VELOCITY', 'AIRSPEED_INDICATED', 'VERTICAL_SPEED', 'SIM_ON_GROUND', 'TITLE', 'ATC_ID')

    def __init__(self):
        self.lock = threading.Lock()
        self.thread = None
        self.last_ask = 0.0
        self.snap = None
        self.track = []
        self.started = None
        self.status = 'idle'

    def read(self):
        self.last_ask = time.time()
        if not (self.thread and self.thread.is_alive()):
            self.thread = threading.Thread(target=self._run, daemon=True, name='simconnect')
            self.thread.start()
        with self.lock:
            s = self.snap
            if not s or time.time() - s['at'] > 15:
                return []
            heading = s['heading']
            return [{'id': 'sim', 'who': 'you', 'pilot': None, 'source': self.name,
                     'aircraft': {'name': s['title'], 'tail': s['tail']},
                     'from': {'ident': None, 'lat': self.track[0][1], 'lon': self.track[0][0]} if self.track else None,
                     'to': None, 'mission': None,
                     'position': {'lat': s['lat'], 'lon': s['lon'], 'alt': round(s['alt']), 'agl': round(s['agl']),
                                  'speed': round(s['gs']), 'ias': round(s['ias']), 'vs': round(s['vs']), 'heading': round(heading),
                                  'onGround': s['ground']},
                     'track': list(self.track[-3000:]), 'status': 'ground' if s['ground'] else 'airborne', 'started': self.started}]

    def _run(self):
        sm = aq = None
        try:
            while time.time() - self.last_ask < 60:            # the page is still looking
                if sm is None:
                    try:
                        from SimConnect import SimConnect, AircraftRequests
                        sm = SimConnect()
                        aq = AircraftRequests(sm, _time=int(self.EVERY * 1000) - 200)
                        self.status = 'connected'
                    except Exception:
                        sm = None
                        self.status = 'waiting for the sim'
                        time.sleep(15)
                        continue
                try:
                    v = {k: aq.get(k) for k in self.VARS}
                    lat, lon = _num(v['PLANE_LATITUDE']), _num(v['PLANE_LONGITUDE'])
                    if lat is None or lon is None or (abs(lat) < 0.01 and abs(lon) < 0.01):
                        time.sleep(self.EVERY)                   # in the menus: no aircraft yet
                        continue
                    dec = lambda b: b.decode('utf-8', 'replace').strip() if isinstance(b, (bytes, bytearray)) else (str(b) if b else None)
                    snap = {'lat': lat, 'lon': lon, 'alt': _num(v['PLANE_ALTITUDE']) or 0, 'agl': _num(v['PLANE_ALT_ABOVE_GROUND']) or 0,
                            'heading': (math.degrees(_num(v['PLANE_HEADING_DEGREES_TRUE']) or 0)) % 360,
                            'gs': _num(v['GROUND_VELOCITY']) or 0, 'ias': _num(v['AIRSPEED_INDICATED']) or 0,
                            'vs': _num(v['VERTICAL_SPEED']) or 0, 'ground': bool(_num(v['SIM_ON_GROUND'])),
                            'title': dec(v['TITLE']), 'tail': dec(v['ATC_ID']), 'at': time.time()}
                    with self.lock:
                        prev = self.snap
                        jumped = prev and (_km(prev['lat'], prev['lon'], lat, lon) > 40 or prev['title'] != snap['title'])
                        if jumped or not self.track:            # a new flight / aircraft / teleport: start a fresh trail
                            self.track, self.started = [], time.strftime('%Y-%m-%dT%H:%M:%S')
                        last = self.track[-1] if self.track else None
                        if not last or _km(last[1], last[0], lat, lon) > 0.25:
                            self.track.append([round(lon, 5), round(lat, 5)])
                        self.snap = snap
                except Exception:
                    try:
                        sm.exit()
                    except Exception:
                        pass
                    sm = None
                    self.status = 'lost the sim'
                    time.sleep(10)
                    continue
                time.sleep(self.EVERY)
        finally:
            if sm is not None:
                try:
                    sm.exit()
                except Exception:
                    pass
            self.status = 'idle'


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(a)))


class Live:
    """NeoFly is read only when its file changed (at most every 10 s); the sim's
    position comes from memory every time. When both know about your flight they're
    merged: the sim's position and trail, NeoFly's mission, origin and destination."""

    def __init__(self, sources, sim=None):
        self.sources = sources
        self.sim = sim
        self.lock = threading.Lock()
        self.cache = {'flights': [], 'at': None}
        self.sig = None
        self.checked = 0

    def _sig(self):
        out = []
        for s in self.sources:
            for p in (getattr(s, 'std', ''), getattr(s, 'std', '') + '-wal'):
                try:
                    out.append(os.path.getmtime(p))
                except OSError:
                    out.append(None)
        return out

    def _neofly(self):
        sig = self._sig()
        # never more than one read per 10 s, and none at all while nothing changed (light on the PC and the sim)
        if time.time() - self.checked < MIN_GAP or (sig == self.sig and time.time() - self.checked < 30):
            return self.cache
        flights, errors = [], []
        for s in self.sources:
            try:
                flights += s.read()
            except Exception as e:                  # a locked or half-written file: keep what we had
                errors.append(f'{s.name}: {e}')
                flights += [f for f in self.cache.get('flights', []) if f.get('source') == s.name]
        self.cache = {'flights': flights, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'errors': errors}
        self.sig, self.checked = sig, time.time()
        return self.cache

    def state(self):
        with self.lock:
            base = self._neofly()
            flights = list(base['flights'])
            sim_status = None
            if self.sim:
                try:
                    sim = self.sim.read()
                except Exception as e:
                    sim = []
                    base.setdefault('errors', []).append(f'sim: {e}')
                sim_status = self.sim.status
                if sim:
                    s = sim[0]
                    mine = next((f for f in flights if f.get('who') == 'you'), None)
                    if mine:                                  # NeoFly's mission + the sim's live position
                        flights.remove(mine)
                        s = {**s, 'from': mine.get('from') or s['from'], 'to': mine.get('to'), 'mission': mine.get('mission'),
                             'pilot': mine.get('pilot'), 'aircraft': {**mine.get('aircraft', {}), **{k: v for k, v in s['aircraft'].items() if v}},
                             'id': mine['id']}
                    elif not s.get('to'):                       # no mission: it left from where NeoFly last saw you land
                        loc = next((getattr(src, 'location', None) for src in self.sources if getattr(src, 'location', None)), None)
                        who = next((getattr(src, 'pilot', None) for src in self.sources if getattr(src, 'pilot', None)), None)
                        if loc and s['status'] != 'ground':
                            s = {**s, 'from': {'ident': loc, 'lat': None, 'lon': None}}
                        s = {**s, 'pilot': who}
                    flights.insert(0, s)
            return {'flights': flights, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'errors': base.get('errors', []), 'sim': sim_status}