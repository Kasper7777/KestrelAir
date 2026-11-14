// Loads data/logbook.json (built by pipeline/build.py) and derives everything the
// UI needs: per-leg geometry, aircraft colours, airport visit counts, and a map
// position for every photo (interpolated along the flight by its timestamp).
import { greatCircle, bowed, cumulative, along, kmBetween } from './geo.js';
import { toDate } from './format.js';

// Apple-like system hues: distinct, bright enough for satellite and dark maps
export const PALETTE = ['#64d2ff', '#ff9f0a', '#bf5af2', '#30d158', '#ff375f', '#ffd60a', '#5e5ce6', '#ff6961', '#66d4cf', '#ac8e68'];
export const GROUND_COLOR = '#ffffff';
const MONTH_RAMP = ['#64d2ff', '#5e5ce6', '#bf5af2', '#ff375f', '#ff9f0a', '#ffd60a'];

function ramp(t) {
  const x = Math.max(0, Math.min(1, t)) * (MONTH_RAMP.length - 1);
  const i = Math.min(MONTH_RAMP.length - 2, Math.floor(x)), f = x - i;
  const a = MONTH_RAMP[i].match(/\w\w/g).map((h) => parseInt(h, 16)), b = MONTH_RAMP[i + 1].match(/\w\w/g).map((h) => parseInt(h, 16));
  return '#' + a.map((v, k) => Math.round(v + (b[k] - v) * f).toString(16).padStart(2, '0')).join('');
}

export async function loadLogbook(url = 'data/logbook.json') {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Could not load ${url} (${res.status}). Run the build first.`);
  return index(await res.json());
}

function index(db) {
  const { legs, airports, aircraft, photos } = db;

  // aircraft colours in order of first flight, so the palette follows the story
  let c = 0;
  for (const l of legs) {
    if (l.kind !== 'flight') continue;
    const a = aircraft[l.aircraft] || (aircraft[l.aircraft] = { id: l.aircraft, name: l.aircraft });
    if (!a.color) a.color = a.colorOverride || PALETTE[c++ % PALETTE.length];
    a.legs = (a.legs || 0) + 1;
    a.minutes = (a.minutes || 0) + l.minutes;
    a.nm = (a.nm || 0) + (l.distanceNm || 0);
    a.firstFlight = a.firstFlight || l.start;
  }

  const legById = new Map();
  legs.forEach((l, i) => {
    l.index = i;
    l.dep = airports[l.from];
    l.arr = airports[l.to];
    const a = [l.dep.lon, l.dep.lat], b = [l.arr.lon, l.arr.lat];
    if (l.kind === 'flight') l.coords = l.local ? circuit(a) : greatCircle(a, b);
    else l.coords = kmBetween(a, b) > 400 ? greatCircle(a, b) : bowed(a, b);
    l.acc = cumulative(l.coords);
    l.color = l.kind === 'flight' ? aircraft[l.aircraft].color : GROUND_COLOR;
    const months = [...new Set(legs.map((x) => x.start.slice(0, 7)))].sort();
    l.monthColor = l.kind === 'flight' ? ramp(months.indexOf(l.start.slice(0, 7)) / Math.max(1, months.length - 1)) : GROUND_COLOR;
    l.photos = l.photos || [];
    l.number = l.kind === 'flight' ? legs.slice(0, i + 1).filter((x) => x.kind === 'flight').length : null;
    legById.set(l.id, l);
  });

  // airports: visits + which stops happened there
  for (const a of Object.values(airports)) { a.visits = 0; a.stops = []; }
  for (const l of legs) if (l.kind === 'flight') airports[l.to].visits++;
  if (legs.length) airports[legs[0].from].visits++;
  const stopById = new Map();
  for (const s of db.stops) { stopById.set(s.id, s); airports[s.airport]?.stops.push(s); }

  // photo positions: along the leg by time, or at the stop's airport
  const photoList = Object.values(photos).sort((x, y) => x.takenAt.localeCompare(y.takenAt));
  for (const p of photoList) {
    if (p.leg) {
      const l = legById.get(p.leg);
      const t0 = toDate(l.start), t1 = toDate(l.end), t = toDate(p.takenAt);
      p.fraction = t1 > t0 ? Math.max(0, Math.min(1, (t - t0) / (t1 - t0))) : 0.5;
      p.position = along(l.coords, p.fraction, l.acc).point;
    } else if (p.stop) {
      const ap = airports[stopById.get(p.stop).airport];
      p.position = [ap.lon, ap.lat];
    }
  }

  return { ...db, legById, stopById, photoList, flights: legs.filter((l) => l.kind === 'flight') };
}

// a small loop for local flights (same departure and arrival)
function circuit([lon, lat], km = 9, n = 40) {
  const dLat = km / 111, dLon = km / (111 * Math.cos((lat * Math.PI) / 180));
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * Math.PI * 2;
    pts.push([lon + dLon * Math.sin(t), lat + dLat * (1 - Math.cos(t)) * 0.6]);
  }
  return pts;
}
