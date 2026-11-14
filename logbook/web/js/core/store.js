// Tiny shared state + event bus. Every feature talks through this, never to each
// other directly, so features can be added or removed without touching the rest.
//
//   store.get('selected')            -> current value
//   store.set('selected', 'nf-fl-3') -> updates and emits 'selected'
//   store.on('selected', fn)         -> fn(value, previous); returns an unsubscribe
//   store.emit('photo:open', {...})  -> one-off events (no stored value)

const state = {
  selected: null,        // leg id
  hiddenAircraft: new Set(),
  basemap: pref('basemap', 'satellite'),     // satellite | dark | light
  projection: pref('projection', 'globe'),   // globe | mercator
  colorBy: pref('colorBy', 'aircraft'),      // aircraft | month
  layers: pref('layers', { routes: true, transfers: true, airports: true, labels: true, photos: true, countries: true }),
  playing: false,
  follow: pref('follow', false),
  speed: 1,
};
const handlers = new Map();
const PREFS = ['basemap', 'projection', 'colorBy', 'layers', 'follow'];

// view preferences are remembered per browser (nice-to-have; falls back silently)
function pref(k, dflt) {
  try {
    const v = JSON.parse(localStorage.getItem('logbook.' + k));
    return v == null ? dflt : (typeof dflt === 'object' ? { ...dflt, ...v } : v);
  } catch { return dflt; }
}

export const store = {
  get: (k) => state[k],
  set(k, v) {
    const prev = state[k];
    if (prev === v && !(v instanceof Set)) return;
    state[k] = v;
    if (PREFS.includes(k)) { try { localStorage.setItem('logbook.' + k, JSON.stringify(v)); } catch {} }
    this.emit(k, v, prev);
  },
  on(evt, fn) {
    if (!handlers.has(evt)) handlers.set(evt, new Set());
    handlers.get(evt).add(fn);
    return () => handlers.get(evt).delete(fn);
  },
  emit(evt, ...args) {
    for (const fn of handlers.get(evt) || []) {
      try { fn(...args); } catch (e) { console.error(`[${evt}]`, e); }
    }
  },
};
