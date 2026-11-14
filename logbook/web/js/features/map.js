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
const ACCENT = '#ffb547';

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

  const map = new maplibregl.Map({
    container: 'map', style: styles[store.get('basemap')] || styles.satellite,
    center: [10, 30], zoom: 1.5, attributionControl: { compact: true }, maxPitch: 70,
  });

  const planeEl = document.createElement('div');
  planeEl.className = 'plane-marker';
  const plane = new maplibregl.Marker({ element: planeEl, rotationAlignment: 'map', pitchAlignment: 'map' });
  let planeShown = false, planeFor = null;

  const fc = (features) => ({ type: 'FeatureCollection', features });
  const empty = fc([]);
  const legFeatures = () => fc(db.legs.map((l) => ({
    type: 'Feature', id: l.index,
    properties: { id: l.id, kind: l.kind, color: l.color, mcolor: l.monthColor, aircraft: l.aircraft || '' },
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

  const colorExpr = () => (store.get('colorBy') === 'month' ? ['get', 'mcolor'] : ['get', 'color']);

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
    for (const [iso, f] of Object.entries(flags || {})) {
      if (!visited.has(iso)) continue;
      map.addSource(`flag-${iso}`, { type: 'image', url: `geo/flags/${iso}.png`, coordinates: f.coordinates });
      map.addLayer({ id: `flag-${iso}`, type: 'raster', source: `flag-${iso}`,
        paint: { 'raster-opacity': base === 'satellite' ? 0.78 : 0.7, 'raster-fade-duration': 0, 'raster-resampling': 'linear' } });
    }
    map.addLayer({ id: 'country-line', type: 'line', source: 'countries',
      paint: { 'line-color': onLight ? '#1d2433' : '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.5, 6, 1.4], 'line-opacity': 0.55 } });

    const flight = ['==', ['get', 'kind'], 'flight'];
    const ground = ['==', ['get', 'kind'], 'ground'];
    map.addLayer({ id: 'legs-casing', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': onLight ? '#ffffff' : '#000000', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 3, 6, 5.5], 'line-opacity': onLight ? 0.9 : 0.35, 'line-blur': 1 } });
    map.addLayer({ id: 'legs-line', type: 'line', source: 'legs', filter: flight, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': colorExpr(), 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.4, 6, 2.8] } });
    map.addLayer({ id: 'ground-line', type: 'line', source: 'legs', filter: ground, layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': onLight ? '#3b4252' : '#ffffff', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.3, 6, 2.2],
        'line-dasharray': [0.2, 2.2], 'line-opacity': 0.9 } });
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

    map.addLayer({ id: 'ap-dot', type: 'circle', source: 'airports',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, ['+', 2.2, ['*', 0.5, ['sqrt', ['get', 'visits']]]], 7, ['+', 5, ['sqrt', ['get', 'visits']]]],
        'circle-color': '#ffffff', 'circle-stroke-color': 'rgba(10,14,24,0.85)', 'circle-stroke-width': 1.6 } });
    map.addLayer({ id: 'ap-label', type: 'symbol', source: 'airports', minzoom: 3.4,
      layout: { 'text-field': ['get', 'ident'], 'text-font': [font.font], 'text-size': 11.5, 'text-offset': [0, 1.15],
        'text-anchor': 'top', 'text-letter-spacing': 0.06, 'text-optional': true },
      paint: { 'text-color': onLight ? '#1d2433' : '#ffffff', 'text-halo-color': onLight ? '#ffffff' : 'rgba(0,0,0,0.75)', 'text-halo-width': 1.4 } });
    map.addLayer({ id: 'photo-pin', type: 'circle', source: 'photos', minzoom: 2.2,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 2.2, 3, 8, 6.5], 'circle-color': ACCENT,
        'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.4 } });

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
  const tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'glass-tip', offset: 14 });
  map.on('mousemove', 'legs-hit', (e) => {
    const l = db.legById.get(e.features[0].properties.id);
    if (!l || store.get('playing')) return;
    tip.setLngLat(e.lngLat).setHTML(ui.legTooltip(l)).addTo(map);
  });
  map.on('mouseleave', 'legs-hit', () => tip.remove());
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
    for (const id of ['legs-line', 'legs-casing']) map.setFilter(id, ['all', ['==', ['get', 'kind'], 'flight'], vis]);
  }
  function applyLayers() {
    const L = store.get('layers');
    const set = (ids, on) => ids.forEach((id) => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'));
    set(['legs-line', 'legs-casing'], L.routes);
    set(['ground-line'], L.transfers);
    set(['ap-dot'], L.airports);
    set(['ap-label'], L.airports && L.labels);
    set(['photo-pin'], L.photos);
    set(['country-line', ...Object.keys(flags || {}).map((iso) => `flag-${iso}`)], L.countries);
    if (map.getLayer('legs-line')) map.setPaintProperty('legs-line', 'line-color', colorExpr());
  }
  function paintSelected(id) {
    const src = map.getSource('selected');
    if (!src) return;
    const l = id && db.legById.get(id);
    src.setData(l ? { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: l.coords } } : empty);
  }
  function fitLegs(legs, opts = {}) {
    const b = bounds(legs.map((l) => l.coords));
    const span = Math.max(b[1][0] - b[0][0], b[1][1] - b[0][1]);
    map.fitBounds(b, { padding: ui.padding(), maxZoom: span < 0.5 ? 9.5 : 8.5, duration: 1400, essential: true, ...opts });
  }

  store.on('selected', (id) => { paintSelected(id); if (id && !store.get('playing')) fitLegs([db.legById.get(id)]); });
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
      plane.setLngLat(point).setRotation(leg?.kind === 'flight' ? bearing : 0);
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
    setTrail(features) { map.getSource('trail')?.setData(fc(features)); },
    dimRoutes(on) {
      if (!map.getLayer('legs-line')) return;
      map.setPaintProperty('legs-line', 'line-opacity', on ? 0.22 : 1);
      map.setPaintProperty('legs-casing', 'line-opacity', on ? 0.1 : 0.35);
      map.setPaintProperty('ground-line', 'line-opacity', on ? 0.25 : 0.9);
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
