// The map: satellite / dark / light basemaps on a globe or flat projection,
// countries you've landed in filled in, every leg as a great-circle arc
// (flights) or dashed line (transfers), airports sized by visits, photo pins.
import { store } from '../core/store.js';
import { bounds } from '../core/geo.js';
import { planeSvg } from '../core/planes.js';

const drops = [];

const CARTO_DARK = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const CARTO_LIGHT = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';
const FALLBACK_FONT = { glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf', font: 'Open Sans Semibold' };
const ACCENT = '#d9b45f';

export async function createMap(db, ui) {
  const [dark, light, countries, flags] = await Promise.all([
    fetch(CARTO_DARK).then((r) => r.json()).catch(() => null),
    fetch(CARTO_LIGHT).then((r) => r.json()).catch(() => null),
    fetch('geo/countries.json').then((r) => r.json()).catch(() => null),
    fetch('geo/flags.json').then((r) => r.json()).catch(() => ({})),
  ]);
  const font = pickFont(dark);
  const styles = { satellite: rasterStyle(font, 'satellite'), dark: dark || rasterStyle(font, 'dark'), light: light || rasterStyle(font, 'light') };
  const visited = new Set(db.stats.countryIsos || []);
  // flag fill pieces (a country crossing the date line has one per side); anything malformed is ignored
  const flagParts = new Map();
  for (const [iso, c] of Object.entries(flags?.countries || {})) {
    if (!visited.has(iso)) continue;
    (c.parts || []).forEach((p, k) => {
      const ok = Array.isArray(p.coordinates) && p.coordinates.length === 4 &&
        p.coordinates.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y) && x >= -180 && x <= 180 && y >= -90 && y <= 90);
      if (ok && p.file) flagParts.set(`flag-${iso}-${k}`, p);
    });
  }
  const flagLayerIds = [...flagParts.keys()];

  const map = new maplibregl.Map({
    container: 'map', style: styles[store.get('basemap')] || styles.satellite,
    center: [10, 30], zoom: 1.5, attributionControl: { compact: true }, maxPitch: 70,
  });

  const planeEl = document.createElement('div');
  planeEl.className = 'plane-marker';
  const plane = new maplibregl.Marker({ element: planeEl, rotationAlignment: 'viewport', pitchAlignment: 'viewport' });
  // aim the replay plane along its true course as seen on screen (correct on the globe, near the poles,
  // tilted or turned): project the plane and a spot 1 km ahead along its bearing
  let planeBearing = null;
  const aimPlane = () => {
    if (planeBearing == null) return;
    const [lon, lat] = plane.getLngLat().toArray(), r = (planeBearing * Math.PI) / 180;
    const ahead = [lon + ((1 / 111.2) * Math.sin(r)) / Math.max(0.01, Math.cos((lat * Math.PI) / 180)), Math.max(-89.9, Math.min(89.9, lat + (1 / 111.2) * Math.cos(r)))];
    const a = map.project([lon, lat]), b = map.project(ahead);
    if (Number.isFinite(b.x) && Math.hypot(b.x - a.x, b.y - a.y) > 1e-6) plane.setRotation((Math.atan2(b.x - a.x, -(b.y - a.y)) * 180) / Math.PI);
  };
  map.on('move', aimPlane);
  let planeShown = false, planeFor = null;

  const fc = (features) => ({ type: 'FeatureCollection', features });
  const empty = fc([]);
  // how strongly a route shows for its age: full for recent flights, easing to 35% for the oldest
  // the newest flight is the brightest; the very first is faint (30%) but never gone
  const AGE = ['coalesce', ['get', 'age'], 0];
  const fade = (base) => ['*', base, ['interpolate', ['linear'], AGE, 0, 1, 0.15, 0.95, 0.5, 0.75, 1, 0.5]];
  const ageWidth = (w1, w6) => ['interpolate', ['linear'], ['zoom'], 1, ['*', w1, ['-', 1, ['*', 0.35, ['coalesce', ['get', 'age'], 0]]]],
    6, ['*', w6, ['-', 1, ['*', 0.35, ['coalesce', ['get', 'age'], 0]]]]];
  const legFeatures = () => fc(db.legs.map((l) => ({
    type: 'Feature', id: l.index,
    // age: 0 for the newest leg, 1 for the oldest - older routes fade back, never out
    properties: { id: l.id, kind: l.kind, color: l.color, mcolor: l.monthColor, aircraft: l.aircraft || '',
      age: db.legs.length > 1 ? 1 - l.index / (db.legs.length - 1) : 0 },
    geometry: { type: 'LineString', coordinates: l.coords },
  })));
  const airportFeatures = () => fc(Object.values(db.airports).map((a) => ({
    type: 'Feature', properties: { ident: a.ident, visits: a.visits },
    geometry: { type: 'Point', coordinates: [a.lon, a.lat] },
  })));
  const photoFeatures = () => fc(db.photoList.filter((p) => p.position).map((p) => ({
    type: 'Feature', properties: { id: p.id }, geometry: { type: 'Point', coordinates: p.position },
  })));
  const countryFeatures = () => fc((countries?.features || []).filter((f) => visited.has(f.properties.iso)));

  // colour drains with age: full colour for recent flights, blending to soft silver for the oldest
  // a photo spot: a small dark-glass badge with a gold rim and a cream camera (drawn once, at 2x)
  function photoBadge() {
    const S = 52, c = document.createElement('canvas');
    c.width = c.height = S;
    const g = c.getContext('2d');
    const rr = (x, y, w, h, r) => { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); };
    g.shadowColor = 'rgba(0,0,0,.55)'; g.shadowBlur = 6; g.shadowOffsetY = 2;
    rr(6, 5, 40, 40, 12);
    const body = g.createLinearGradient(0, 5, 0, 45);
    body.addColorStop(0, 'rgba(70,76,96,.95)'); body.addColorStop(1, 'rgba(20,23,34,.95)');
    g.fillStyle = body; g.fill();
    g.shadowColor = 'transparent';
    g.lineWidth = 2; g.strokeStyle = '#d9b45f'; g.stroke();
    rr(9, 7, 34, 15, 9);                                     // glossy top
    const gloss = g.createLinearGradient(0, 7, 0, 22);
    gloss.addColorStop(0, 'rgba(255,255,255,.45)'); gloss.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gloss; g.fill();
    g.fillStyle = '#f6ebc8';                                 // camera
    rr(14, 18, 24, 17, 4); g.fill();
    g.fillRect(21, 15, 10, 4);
    g.beginPath(); g.arc(26, 26.5, 5.2, 0, Math.PI * 2); g.fillStyle = 'rgba(28,32,46,1)'; g.fill();
    g.beginPath(); g.arc(26, 26.5, 2.6, 0, Math.PI * 2); g.fillStyle = '#d9b45f'; g.fill();
    return g.getImageData(0, 0, S, S);
  }

  // ---------- route colours
  // "Age" (default): a time-heat palette - your newest flights burn white-gold, then gold and amber,
  // cooling through teal and blue to a dim violet for the oldest. History reads at a glance.
  const AGE_STOPS = [[0, '#fff4d2'], [0.03, '#ffd977'], [0.12, '#f0a646'], [0.3, '#47d3d8'], [0.55, '#3f86e8'], [0.8, '#6a5cd6'], [1, '#5c5486']];
  const ageColorExpr = ['interpolate', ['linear'], AGE, ...AGE_STOPS.flat()];
  const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  function ageColor(age) {                 // the same palette in JS, for the timeline and the replay trail
    const a = Math.max(0, Math.min(1, age));
    for (let i = 1; i < AGE_STOPS.length; i++) {
      const [x1, c1] = AGE_STOPS[i - 1], [x2, c2] = AGE_STOPS[i];
      if (a <= x2) {
        const f = (a - x1) / (x2 - x1 || 1), A = hex(c1), B = hex(c2);
        return `rgb(${A.map((v, k) => Math.round(v + (B[k] - v) * f)).join(',')})`;
      }
    }
    return AGE_STOPS[AGE_STOPS.length - 1][1];
  }
  const legAge = (l) => (db.legs.length > 1 ? 1 - l.index / (db.legs.length - 1) : 0);
  ui.routeColor = (l) => (store.get('colorBy') === 'age' ? ageColor(legAge(l)) : store.get('colorBy') === 'month' ? l.monthColor : l.color);
  const colorExpr = () => {
    if (store.get('colorBy') === 'age') return ageColorExpr;
    // each plane keeps its own colour; older flights dim towards slate (about 40% of the way at the
    // very first flight - the stop past 1 means the hue never fully goes) while glow and opacity fall away
    const c = ['to-color', store.get('colorBy') === 'month' ? ['get', 'mcolor'] : ['get', 'color']];
    return ['interpolate', ['linear'], AGE, 0, c, 0.12, c, 2.3, '#4b5262'];
  };
  const HOVER = ['boolean', ['feature-state', 'hover'], false];
  const ROUTE_LAYERS = ['legs-casing', 'legs-bloom', 'legs-glow', 'legs-line', 'legs-shine'];
  const HOT = '#fff3d6';

  function addOverlay() {
    try { map.setProjection({ type: store.get('projection') }); } catch (e) {}
    try {
      map.setSky({ 'sky-color': '#0a1a33', 'horizon-color': '#3a6ea5', 'fog-color': '#0a1a33', 'sky-horizon-blend': 0.7,
        'horizon-fog-blend': 0.5, 'fog-ground-blend': 0.3, 'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0] });
    } catch (e) {}
    const base = store.get('basemap');
    const onLight = base === 'light';

    map.addSource('countries', { type: 'geojson', data: countryFeatures() });
    map.addSource('legs', { type: 'geojson', data: legFeatures() });
    map.addSource('selected', { type: 'geojson', data: empty, lineMetrics: true });
    map.addSource('trail', { type: 'geojson', data: empty });
    map.addSource('airports', { type: 'geojson', data: airportFeatures() });
    map.addSource('photos', { type: 'geojson', data: photoFeatures() });

    // every visited country coloured in with its own flag (pre-clipped to the outline at build time)
    for (const id of flagLayerIds) {
      const part = flagParts.get(id);
      try {
        map.addSource(id, { type: 'image', url: `geo/flags/${part.file}`, coordinates: part.coordinates });
        map.addLayer({ id, type: 'raster', source: id,
          // vivid on the globe, stepping aside as you zoom in to airports and routes
          paint: { 'raster-opacity': ['interpolate', ['linear'], ['zoom'], 2, base === 'satellite' ? 0.8 : 0.72, 4.5, 0.5, 6.5, 0.18, 8, 0],
                   'raster-fade-duration': 0, 'raster-resampling': 'linear' } });
      } catch (e) { console.warn('flag fill skipped', id, e); }
    }
    // a crisp two-tone border round each visited country, so neighbours never run together
    map.addLayer({ id: 'country-casing', type: 'line', source: 'countries', layout: { 'line-join': 'round' },
      paint: { 'line-color': '#05070d', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.6, 6, 3.6], 'line-opacity': 0.55 } });
    map.addLayer({ id: 'country-line', type: 'line', source: 'countries', layout: { 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.7, 6, 1.6], 'line-opacity': 0.9 } });

    const flight = ['==', ['get', 'kind'], 'flight'];
    const ground = ['==', ['get', 'kind'], 'ground'];
    map.addLayer({ id: 'legs-casing', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': onLight ? '#ffffff' : '#000000', 'line-width': ageWidth(3, 5.5), 'line-opacity': fade(onLight ? 0.9 : 0.35), 'line-blur': 1 } });
    // bloom: a wide, soft light around each route - blazing on recent flights, all but gone on the oldest
    map.addLayer({ id: 'legs-bloom', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['case', HOVER, HOT, colorExpr()], 'line-blur': 14,
        'line-width': ['interpolate', ['linear'], ['zoom'], 1, ['case', HOVER, 26, 14], 6, ['case', HOVER, 46, 28]],
        'line-opacity': ['case', HOVER, 0.85, ['interpolate', ['linear'], AGE, 0, 0.6, 0.06, 0.45, 0.2, 0.22, 0.5, 0.07, 1, 0.02]],
        'line-opacity-transition': { duration: 250 }, 'line-width-transition': { duration: 250 } } });
    // halo: a tighter glow hugging the line
    map.addLayer({ id: 'legs-glow', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['case', HOVER, HOT, colorExpr()], 'line-blur': 4,
        'line-width': ['interpolate', ['linear'], ['zoom'], 1, ['case', HOVER, 12, 7], 6, ['case', HOVER, 22, 14]],
        'line-opacity': ['case', HOVER, 1, ['interpolate', ['linear'], AGE, 0, 0.95, 0.15, 0.7, 0.5, 0.3, 1, 0.12]] } });
    // the glass core
    map.addLayer({ id: 'legs-line', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['case', HOVER, '#fffaf0', colorExpr()],
        'line-width': ['interpolate', ['linear'], ['zoom'], 1, ['case', HOVER, 3.6, ['*', 2.1, ['-', 1, ['*', 0.35, AGE]]]],
          6, ['case', HOVER, 6, ['*', 3.8, ['-', 1, ['*', 0.35, AGE]]]]],
        'line-opacity': ['case', HOVER, 1, fade(1)] } });
    // the light catching the top of the glass rod
    map.addLayer({ id: 'legs-shine', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': ageWidth(0.6, 1.2), 'line-offset': ['interpolate', ['linear'], ['zoom'], 1, -0.35, 6, -0.7],
        'line-blur': 0.3, 'line-opacity': ['case', HOVER, 1, ['interpolate', ['linear'], AGE, 0, 0.85, 0.4, 0.45, 1, 0.2]] } });
    map.addLayer({ id: 'ground-line', type: 'line', source: 'legs', filter: ground, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': onLight ? '#3b4252' : '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.3, 6, 2.2],
        'line-dasharray': [0.2, 2.2], 'line-opacity': fade(0.9) } });
    map.addLayer({ id: 'legs-hit', type: 'line', source: 'legs', paint: { 'line-color': '#000', 'line-width': 18, 'line-opacity': 0.001 } });

    map.addSource('preview', { type: 'geojson', data: empty });
    map.addLayer({ id: 'preview-line', type: 'line', source: 'preview', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': 5, 'line-opacity': 0.85, 'line-blur': 0.5 } });
    map.addLayer({ id: 'trail-glow', type: 'line', source: 'trail', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': 12, 'line-blur': 8, 'line-opacity': 0.55 } });
    map.addLayer({ id: 'trail-line', type: 'line', source: 'trail', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': 2.6 } });

    map.addLayer({ id: 'sel-halo', type: 'line', source: 'selected', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': 12, 'line-blur': 8, 'line-opacity': 0.45 } });
    map.addLayer({ id: 'sel-line', type: 'line', source: 'selected', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-width': 4, 'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, '#ffffff', 1, ACCENT] } });

    map.addLayer({ id: 'ap-glow', type: 'circle', source: 'airports',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, ['+', 5, ['sqrt', ['get', 'visits']]], 7, ['+', 11, ['*', 1.5, ['sqrt', ['get', 'visits']]]]],
        'circle-color': '#f6ebc8', 'circle-blur': 1, 'circle-opacity': 0.35 } });
    map.addLayer({ id: 'ap-dot', type: 'circle', source: 'airports',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, ['+', 2.2, ['*', 0.5, ['sqrt', ['get', 'visits']]]], 7, ['+', 5, ['sqrt', ['get', 'visits']]]],
        'circle-color': '#ffffff', 'circle-stroke-color': 'rgba(217,180,95,0.9)', 'circle-stroke-width': 1.4 } });
    map.addLayer({ id: 'ap-label', type: 'symbol', source: 'airports', minzoom: 3.4,
      layout: { 'text-field': ['get', 'ident'], 'text-font': [font.font], 'text-size': 11.5, 'text-offset': [0, 1.15],
        'text-anchor': 'top', 'text-letter-spacing': 0.06, 'text-optional': true },
      paint: { 'text-color': onLight ? '#1d2433' : '#ffffff', 'text-halo-color': onLight ? '#ffffff' : 'rgba(0,0,0,0.75)', 'text-halo-width': 1.4 } });
    if (!map.hasImage('photo-badge')) map.addImage('photo-badge', photoBadge(), { pixelRatio: 2 });
    map.addLayer({ id: 'photo-pin', type: 'symbol', source: 'photos', minzoom: 2.2,
      layout: { 'icon-image': 'photo-badge', 'icon-size': ['interpolate', ['linear'], ['zoom'], 2.2, 0.55, 6, 0.85, 9, 1],
        'icon-allow-overlap': true, 'icon-ignore-placement': true } });

    applyLayers();
    applyFilter();
    paintSelected(store.get('selected'));
  }
  map.on('style.load', addOverlay);

  // ---------- interactions
  for (const id of ['legs-hit', 'ap-dot', 'photo-pin']) {
    map.on('mouseenter', id, () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', id, () => (map.getCanvas().style.cursor = ''));
  }
  // hover tips: a glass bubble that rises out of a blur (see .glass-tip in app.css) and dissolves
  // on the way out. Its content only changes when you move onto a different thing, so it never flickers.
  // Photos win over airports, airports over routes.
  const tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'glass-tip', offset: 14, maxWidth: '260px' });
  let tipKey = null, tipOut = 0;
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const tipFor = (f) => {
    if (f.layer.id === 'photo-pin') {
      const p = db.photos[f.properties.id];
      const lg = p && db.legById.get(p.leg);
      return p && `<img class="tip-photo" src="${esc(p.thumb)}" alt=""><div class="tip-sub">${lg ? `${esc(lg.from)} → ${esc(lg.to)} · ` : ''}${esc(p.takenAt?.slice(11, 16))}</div>`;
    }
    if (f.layer.id === 'ap-dot') {
      const a = db.airports[f.properties.ident];
      return a && `<b>${esc(a.ident)}</b><div class="tip-sub">${esc(a.name)}${a.city ? ` · ${esc(a.city)}` : ''}<br>${a.visits} visit${a.visits === 1 ? '' : 's'}</div>`;
    }
    const l = db.legById.get(f.properties.id);
    return l && ui.legTooltip(l);
  };
  // the route under the pointer lights up (bloom, halo and core all brighten)
  let hovered = null;
  const setHover = (id) => {
    if (hovered === id) return;
    if (hovered != null) map.setFeatureState({ source: 'legs', id: hovered }, { hover: false });
    hovered = id;
    if (id != null) map.setFeatureState({ source: 'legs', id }, { hover: true });
  };
  const hideTip = () => {
    setHover(null);
    if (!tipKey) return;
    tipKey = null;
    tip.getElement()?.classList.add('leaving');
    clearTimeout(tipOut);
    tipOut = setTimeout(() => { if (!tipKey) tip.remove(); }, 260);
  };
  map.on('mousemove', (e) => {
    if (store.get('playing')) { hideTip(); return; }
    const layers = ['photo-pin', 'ap-dot', 'legs-hit'].filter((l) => map.getLayer(l) && map.getLayoutProperty(l, 'visibility') !== 'none');
    const f = map.queryRenderedFeatures(e.point, { layers })[0];
    if (!f) { hideTip(); return; }
    setHover(f.layer.id === 'legs-hit' && f.id != null ? f.id : null);
    const key = `${f.layer.id}:${f.properties.id || f.properties.ident}`;
    const anchor = f.layer.id === 'legs-hit' ? e.lngLat : f.geometry.coordinates;
    if (key !== tipKey) {
      const htmlStr = tipFor(f);
      if (!htmlStr) { hideTip(); return; }
      clearTimeout(tipOut);
      tipKey = key;
      tip.remove();                                  // a fresh element, so it emerges again
      tip.setLngLat(anchor).setHTML(htmlStr).addTo(map);
    } else if (f.layer.id === 'legs-hit') tip.setLngLat(anchor);
  });
  map.getCanvas().addEventListener('mouseleave', hideTip);
  map.on('click', (e) => {
    const layers = ['photo-pin', 'ap-dot', 'legs-hit'].filter((l) => map.getLayer(l) && map.getLayoutProperty(l, 'visibility') !== 'none');
    const hits = map.queryRenderedFeatures(e.point, { layers });
    if (!hits.length) return;
    const top = hits[0];
    if (top.layer.id === 'photo-pin') {
      const p = db.photos[top.properties.id];
      const set = p.leg ? db.legById.get(p.leg).photos : db.stopById.get(p.stop)?.photos || [p.id];
      ui.openPhotos(set, set.indexOf(p.id));
    } else if (top.layer.id === 'ap-dot') ui.airportPopup(top.properties.ident, top.geometry.coordinates);
    else store.set('selected', top.properties.id);
  });

  // ---------- reactions
  function applyFilter() {
    if (!map.getLayer('legs-line')) return;
    const hidden = [...store.get('hiddenAircraft')];
    const vis = hidden.length ? ['!', ['in', ['get', 'aircraft'], ['literal', hidden]]] : true;
    for (const id of ROUTE_LAYERS) if (map.getLayer(id)) map.setFilter(id, ['all', ['==', ['get', 'kind'], 'flight'], vis]);
  }
  function applyLayers() {
    const L = store.get('layers');
    const set = (ids, on) => ids.forEach((id) => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'));
    set(ROUTE_LAYERS, L.routes);
    set(['ground-line'], L.transfers);
    set(['ap-dot', 'ap-glow'], L.airports);
    set(['ap-label'], L.airports && L.labels);
    set(['photo-pin'], L.photos);
    set(['country-line', 'country-casing', ...flagLayerIds], L.countries);
    if (map.getLayer('legs-line')) map.setPaintProperty('legs-line', 'line-color', ['case', HOVER, '#fffaf0', colorExpr()]);
    for (const id of ['legs-bloom', 'legs-glow']) if (map.getLayer(id)) map.setPaintProperty(id, 'line-color', ['case', HOVER, HOT, colorExpr()]);
  }
  function paintSelected(id) {
    const src = map.getSource('selected');
    if (!src) return;
    const l = id && db.legById.get(id);
    src.setData(l ? { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: l.coords } } : empty);
    if (l) revealSelected();
  }
  // the chosen route flows in like water: the line draws itself from departure to
  // arrival while a soft glow swells around it and settles
  let revealRaf = 0;
  function revealSelected() {
    cancelAnimationFrame(revealRaf);
    if (!map.getLayer('sel-line') || store.get('playing') || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const t0 = performance.now(), D = 1300;
    const ease = (x) => 1 - (1 - x) ** 3;
    const full = ['interpolate', ['linear'], ['line-progress'], 0, '#ffffff', 1, ACCENT];
    const step = (now) => {
      const x = Math.max(0, Math.min(1, (now - t0) / D)), e = ease(x);
      const p = Math.max(0.004, Math.min(1, e * 1.08));
      map.setPaintProperty('sel-line', 'line-gradient', p >= 0.998 ? full
        : ['interpolate', ['linear'], ['line-progress'], 0, '#ffffff', p, ACCENT, p + 0.002, 'rgba(217,180,95,0)', 1, 'rgba(217,180,95,0)']);
      map.setPaintProperty('sel-halo', 'line-opacity', Math.max(0, 0.45 * e + 0.35 * Math.sin(Math.PI * Math.min(1, x * 1.4)) * (1 - x)));
      map.setPaintProperty('sel-halo', 'line-width', 12 + 16 * Math.sin(Math.PI * x) * (1 - x * 0.5));
      map.setPaintProperty('sel-halo', 'line-blur', 8 + 8 * (1 - e));
      if (x < 1) revealRaf = requestAnimationFrame(step);
    };
    revealRaf = requestAnimationFrame(step);
  }
  function fitLegs(legs, opts = {}) {
    const b = bounds(legs.map((l) => l.coords));
    const span = Math.max(b[1][0] - b[0][0], b[1][1] - b[0][1]);
    map.fitBounds(b, { padding: ui.padding(), maxZoom: span < 0.5 ? 9.5 : 8.5, duration: 1400, essential: true, ...opts });
  }

  store.on('selected', (id) => { paintSelected(id); if (id && db.legById.has(id) && !store.get('playing') && !store.get('scrubbing') && ui.scrubbedLeg?.() !== id) fitLegs([db.legById.get(id)]); });
  store.on('hiddenAircraft', applyFilter);
  store.on('layers', applyLayers);
  store.on('colorBy', applyLayers);
  store.on('basemap', (b) => map.setStyle(styles[b]));
  store.on('projection', (p) => { try { map.setProjection({ type: p }); } catch (e) {} });

  const api = {
    map,
    fitAll: (opts) => fitLegs(db.legs, opts),
    fitLegs,
    setPlane(point, bearing, leg) {
      if (leg && planeFor !== leg.id) {
        planeFor = leg.id;
        const ac = db.aircraft[leg.aircraft];
        planeEl.innerHTML = leg.kind === 'flight' ? planeSvg(ac) : `<span class="ground-dot"></span>`;
        planeEl.style.setProperty('--c', leg.color);
        planeEl.classList.toggle('ground', leg.kind !== 'flight');
      }
      plane.setLngLat(point);
      planeBearing = leg?.kind === 'flight' && Number.isFinite(bearing) ? bearing : null;
      if (planeBearing == null) plane.setRotation(0); else aimPlane();
      if (!planeShown) { plane.addTo(map); planeShown = true; }
    },
    hidePlane() { plane.remove(); planeShown = false; planeFor = null; },
    preview(id) {
      const l = id && db.legById.get(id);
      map.getSource('preview')?.setData(l ? { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: l.coords } } : empty);
    },
    // a print that drops onto the map where the photo was taken, then fades
    dropPhoto(p, onClick) {
      if (!p.position) return;
      const el = document.createElement('div'); // MapLibre owns this element's transform
      const fig = document.createElement('figure');
      fig.className = 'map-print';
      fig.style.setProperty('--tilt', `${(Math.random() * 7 - 3.5).toFixed(1)}deg`);
      const lg = db.legById.get(p.leg);
      fig.innerHTML = `<img src="${p.thumb}" alt=""><figcaption>${lg ? `${lg.from} → ${lg.to}` : ''} · ${p.takenAt.slice(11, 16)}</figcaption><i></i>`;
      el.append(fig);
      el.addEventListener('click', (e) => { e.stopPropagation(); onClick?.(p); });
      const m = new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -16] }).setLngLat(p.position).addTo(map);
      drops.push(m);
      while (drops.length > 3) drops.shift().remove();
      setTimeout(() => fig.classList.add('out'), 4200 / Math.sqrt(store.get('speed')));
      setTimeout(() => { m.remove(); const k = drops.indexOf(m); if (k >= 0) drops.splice(k, 1); }, 5000 / Math.sqrt(store.get('speed')));
    },
    clearDrops() { drops.splice(0).forEach((m) => m.remove()); },
    // a local news story pops up over the airport as the plane lands
    dropNews(story, lngLat, onClick) {
      const el = document.createElement('div');
      const card = document.createElement('div');
      card.className = 'map-news glass-soft';
      const esc = (t) => String(t || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
      card.innerHTML = `${story.image ? `<img src="${esc(story.image)}" alt="">` : ''}<div><span>Local news · ${esc(story.source)}</span><b>${esc(story.title)}</b></div><i></i>`;
      el.append(card);
      el.addEventListener('click', (e) => { e.stopPropagation(); onClick?.(); });
      const m = new maplibregl.Marker({ element: el, anchor: 'bottom', offset: [0, -14] }).setLngLat(lngLat).addTo(map);
      drops.push(m);
      while (drops.length > 3) drops.shift().remove();
      const k = Math.sqrt(store.get('speed'));
      setTimeout(() => card.classList.add('out'), 5200 / k);
      setTimeout(() => { m.remove(); const i = drops.indexOf(m); if (i >= 0) drops.splice(i, 1); }, 6000 / k);
    },
    setTrail(features) { map.getSource('trail')?.setData(fc(features)); },
    dimRoutes(on) {
      if (!map.getLayer('legs-line')) return;
      const light = store.get('basemap') === 'light';
      map.setPaintProperty('legs-line', 'line-opacity', on ? fade(0.22) : ['case', HOVER, 1, fade(1)]);
      map.setPaintProperty('legs-casing', 'line-opacity', fade(on ? 0.1 : light ? 0.9 : 0.35));
      map.setPaintProperty('ground-line', 'line-opacity', fade(on ? 0.25 : 0.9));
      // during a replay the glow steps back so the replay trail stands out
      const L = store.get('layers');
      for (const id of ['legs-bloom', 'legs-glow', 'legs-shine']) {
        if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on || !L.routes ? 'none' : 'visible');
      }
    },
  };
  await new Promise((r) => (map.loaded() ? r() : map.once('load', r)));
  return api;
}

function pickFont(style) {
  const fonts = (style?.layers || []).map((l) => l.layout?.['text-font']).filter((f) => Array.isArray(f) && typeof f[0] === 'string').map((f) => f[0]);
  const f = fonts.find((x) => /semibold|bold|medium/i.test(x)) || fonts[0];
  return f ? { glyphs: style.glyphs, font: f } : FALLBACK_FONT;
}

function rasterStyle(font, kind) {
  const carto = (layer) => ['a', 'b', 'c'].map((s) => `https://${s}.basemaps.cartocdn.com/${layer}/{z}/{x}/{y}.png`);
  const base = {
    satellite: { type: 'raster', tileSize: 256, maxzoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] },
    dark: { type: 'raster', tileSize: 256, attribution: '© OpenStreetMap © CARTO', tiles: carto('dark_nolabels') },
    light: { type: 'raster', tileSize: 256, attribution: '© OpenStreetMap © CARTO', tiles: carto('light_nolabels') },
  }[kind];
  // place names over imagery: Esri's free reference layer (CARTO's label tiles now need a key)
  const labels = kind === 'satellite'
    ? { type: 'raster', tileSize: 256, maxzoom: 13, attribution: 'Labels © Esri',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'] }
    : { type: 'raster', tileSize: 256, attribution: '© OpenStreetMap © CARTO', tiles: carto(kind === 'light' ? 'light_only_labels' : 'dark_only_labels') };
  return {
    version: 8, glyphs: font.glyphs,
    sources: { base, labels },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#05070d' } },
      { id: 'base', type: 'raster', source: 'base', paint: kind === 'satellite' ? { 'raster-saturation': -0.1, 'raster-brightness-max': 0.92, 'raster-contrast': 0.05 } : {} },
      { id: 'labels', type: 'raster', source: 'labels', paint: { 'raster-opacity': kind === 'satellite' ? 0.85 : 1 } },
    ],
  };
}
