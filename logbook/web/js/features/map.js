// The map: globe/flat projection, dark or satellite basemap, every leg drawn as a
// glowing great-circle arc (flights) or a dashed line (ground transfers), airports
// sized by visits, and photo pins placed where each shot was taken.
import { store } from '../core/store.js';
import { bounds } from '../core/geo.js';
import { GROUND_COLOR } from '../core/data.js';

const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const LABELS_FALLBACK = { glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf', font: 'Open Sans Semibold' };

export async function createMap(db, ui) {
  const dark = await fetch(DARK_STYLE).then((r) => r.json()).catch(() => null);
  const font = pickFont(dark);
  const styles = {
    dark: dark || satelliteStyle(font, false),
    satellite: satelliteStyle(font, true),
  };

  const map = new maplibregl.Map({
    container: 'map',
    style: styles[store.get('basemap')],
    center: [10, 35], zoom: 1.6,
    attributionControl: { compact: true },
    maxPitch: 70,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');

  const planeEl = document.createElement('div');
  planeEl.className = 'plane-marker';
  planeEl.innerHTML = `<svg viewBox="0 0 24 24"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>`;
  const plane = new maplibregl.Marker({ element: planeEl, rotationAlignment: 'map', pitchAlignment: 'map' });
  let planeShown = false;

  const legFeatures = () => ({
    type: 'FeatureCollection',
    features: db.legs.map((l) => ({
      type: 'Feature', id: l.index,
      properties: { id: l.id, kind: l.kind, color: l.color, aircraft: l.aircraft || '' },
      geometry: { type: 'LineString', coordinates: l.coords },
    })),
  });
  const airportFeatures = () => ({
    type: 'FeatureCollection',
    features: Object.values(db.airports).map((a) => ({
      type: 'Feature', properties: { ident: a.ident, visits: a.visits, name: a.name },
      geometry: { type: 'Point', coordinates: [a.lon, a.lat] },
    })),
  });
  const photoFeatures = () => ({
    type: 'FeatureCollection',
    features: db.photoList.filter((p) => p.position).map((p) => ({
      type: 'Feature', properties: { id: p.id, leg: p.leg || '' },
      geometry: { type: 'Point', coordinates: p.position },
    })),
  });
  const empty = { type: 'FeatureCollection', features: [] };

  function addOverlay() {
    try {
      map.setProjection({ type: store.get('projection') });
    } catch (e) { /* older engine: flat only */ }
    try {
      map.setSky({
        'sky-color': '#0b1430', 'horizon-color': '#1d3b6b', 'fog-color': '#0b1430',
        'sky-horizon-blend': 0.6, 'horizon-fog-blend': 0.6, 'fog-ground-blend': 0.2,
        'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0],
      });
    } catch (e) { /* sky unsupported */ }

    map.addSource('legs', { type: 'geojson', data: legFeatures(), lineMetrics: true });
    map.addSource('selected', { type: 'geojson', data: empty, lineMetrics: true });
    map.addSource('trail', { type: 'geojson', data: empty, lineMetrics: true });
    map.addSource('airports', { type: 'geojson', data: airportFeatures() });
    map.addSource('photos', { type: 'geojson', data: photoFeatures() });

    const flight = ['==', ['get', 'kind'], 'flight'];
    const ground = ['==', ['get', 'kind'], 'ground'];
    map.addLayer({ id: 'legs-glow', type: 'line', source: 'legs', filter: flight,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 5, 6, 10], 'line-blur': 6, 'line-opacity': 0.28 } });
    map.addLayer({ id: 'legs-line', type: 'line', source: 'legs', filter: flight,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.3, 6, 2.6], 'line-opacity': 0.95 } });
    map.addLayer({ id: 'ground-line', type: 'line', source: 'legs', filter: ground,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': GROUND_COLOR, 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 1.4, 6, 2.4], 'line-dasharray': [0.6, 2.2], 'line-opacity': 0.85 } });
    map.addLayer({ id: 'legs-hit', type: 'line', source: 'legs', paint: { 'line-color': '#000', 'line-width': 16, 'line-opacity': 0.001 } });

    map.addLayer({ id: 'trail-line', type: 'line', source: 'trail',
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.95 } });

    map.addLayer({ id: 'sel-glow', type: 'line', source: 'selected', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': 16, 'line-blur': 10, 'line-opacity': 0.55 } });
    map.addLayer({ id: 'sel-line', type: 'line', source: 'selected', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-width': 4, 'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, '#ffffff', 1, '#ffffff'] } });
    map.addLayer({ id: 'sel-ants', type: 'line', source: 'selected', layout: { 'line-cap': 'butt' },
      paint: { 'line-color': '#0b1020', 'line-width': 2, 'line-dasharray': [0, 4, 3], 'line-opacity': 0.55 } });

    map.addLayer({ id: 'ap-halo', type: 'circle', source: 'airports',
      paint: { 'circle-radius': ['+', 6, ['*', 2.2, ['sqrt', ['get', 'visits']]]], 'circle-color': '#7dd3fc', 'circle-opacity': 0.12, 'circle-blur': 0.6 } });
    map.addLayer({ id: 'ap-dot', type: 'circle', source: 'airports',
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 1, 2.6, 7, 5.5], 'circle-color': '#0b1020',
        'circle-stroke-color': '#e6f4ff', 'circle-stroke-width': 1.6 } });
    map.addLayer({ id: 'ap-label', type: 'symbol', source: 'airports', minzoom: 3.2,
      layout: { 'text-field': ['get', 'ident'], 'text-font': [font.font], 'text-size': 11, 'text-offset': [0, 1.1],
        'text-anchor': 'top', 'text-letter-spacing': 0.08, 'text-optional': true },
      paint: { 'text-color': '#e6f4ff', 'text-halo-color': '#05070f', 'text-halo-width': 1.4 } });

    map.addLayer({ id: 'photo-pin', type: 'circle', source: 'photos', minzoom: 2.5,
      paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 2.5, 3, 8, 6.5], 'circle-color': '#ffd166',
        'circle-stroke-color': '#1a1200', 'circle-stroke-width': 1.2, 'circle-opacity': 0.95 } });

    applyFilter();
    paintSelected(store.get('selected'));
  }

  map.on('style.load', addOverlay);

  // ---------- interactions
  const hoverable = ['legs-hit', 'ap-dot', 'photo-pin'];
  for (const id of hoverable) {
    map.on('mouseenter', id, () => (map.getCanvas().style.cursor = 'pointer'));
    map.on('mouseleave', id, () => (map.getCanvas().style.cursor = ''));
  }
  const tip = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'hover-tip', offset: 12 });
  map.on('mousemove', 'legs-hit', (e) => {
    const l = db.legById.get(e.features[0].properties.id);
    if (!l || store.get('playing')) return;
    tip.setLngLat(e.lngLat).setHTML(ui.legTooltip(l)).addTo(map);
  });
  map.on('mouseleave', 'legs-hit', () => tip.remove());

  map.on('click', (e) => {
    const hits = map.queryRenderedFeatures(e.point, { layers: ['photo-pin', 'ap-dot', 'legs-hit'].filter((l) => map.getLayer(l)) });
    if (!hits.length) return;
    const top = hits[0];
    if (top.layer.id === 'photo-pin') {
      const p = db.photos[top.properties.id];
      const set = p.leg ? db.legById.get(p.leg).photos : [p.id];
      ui.openPhotos(set, set.indexOf(p.id));
    } else if (top.layer.id === 'ap-dot') {
      ui.airportPopup(top.properties.ident, top.geometry.coordinates);
    } else {
      store.set('selected', top.properties.id);
    }
  });

  // ---------- reactions
  function applyFilter() {
    if (!map.getLayer('legs-line')) return;
    const hidden = [...store.get('hiddenAircraft')];
    const visible = hidden.length ? ['!', ['in', ['get', 'aircraft'], ['literal', hidden]]] : true;
    map.setFilter('legs-glow', ['all', ['==', ['get', 'kind'], 'flight'], visible]);
    map.setFilter('legs-line', ['all', ['==', ['get', 'kind'], 'flight'], visible]);
  }

  function paintSelected(id) {
    const src = map.getSource('selected');
    if (!src) return;
    const l = id && db.legById.get(id);
    src.setData(l ? { type: 'Feature', properties: { color: l.color }, geometry: { type: 'LineString', coordinates: l.coords } } : empty);
    if (l && map.getLayer('sel-line')) {
      map.setPaintProperty('sel-line', 'line-gradient',
        ['interpolate', ['linear'], ['line-progress'], 0, '#ffffff', 0.5, l.color, 1, '#ffffff']);
    }
  }

  function fitLegs(legs, opts = {}) {
    const b = bounds(legs.map((l) => l.coords));
    const span = Math.max(b[1][0] - b[0][0], b[1][1] - b[0][1]);
    map.fitBounds(b, { padding: ui.padding(), maxZoom: span < 0.5 ? 9 : 8.5, duration: 1400, essential: true, ...opts });
  }

  store.on('selected', (id) => {
    paintSelected(id);
    if (id && !store.get('playing')) fitLegs([db.legById.get(id)]);
  });
  store.on('hiddenAircraft', applyFilter);
  store.on('basemap', (b) => map.setStyle(styles[b]));
  store.on('projection', (p) => { try { map.setProjection({ type: p }); } catch (e) {} });

  // marching ants on the selected leg
  const seq = [[0, 4, 3], [0.5, 4, 2.5], [1, 4, 2], [1.5, 4, 1.5], [2, 4, 1], [2.5, 4, 0.5], [3, 4, 0],
    [0, 0.5, 3, 3.5], [0, 1, 3, 3], [0, 1.5, 3, 2.5], [0, 2, 3, 2], [0, 2.5, 3, 1.5], [0, 3, 3, 1], [0, 3.5, 3, 0.5]];
  let step = 0;
  setInterval(() => {
    if (!store.get('selected') || !map.getLayer('sel-ants') || document.hidden) return;
    step = (step + 1) % seq.length;
    map.setPaintProperty('sel-ants', 'line-dasharray', seq[step]);
  }, 70);

  // ---------- API used by the player and other features
  const api = {
    map,
    fitAll: (opts) => fitLegs(db.legs, opts),
    fitLegs,
    setPlane(point, bearingDeg) {
      plane.setLngLat(point).setRotation(bearingDeg);
      if (!planeShown) { plane.addTo(map); planeShown = true; }
    },
    hidePlane() { plane.remove(); planeShown = false; },
    setTrail(features) { map.getSource('trail')?.setData({ type: 'FeatureCollection', features }); },
    dimRoutes(on) {
      if (!map.getLayer('legs-line')) return;
      map.setPaintProperty('legs-line', 'line-opacity', on ? 0.18 : 0.95);
      map.setPaintProperty('legs-glow', 'line-opacity', on ? 0.06 : 0.28);
      map.setPaintProperty('ground-line', 'line-opacity', on ? 0.2 : 0.85);
    },
  };
  await new Promise((r) => (map.loaded() ? r() : map.once('load', r)));
  return api;
}

function pickFont(style) {
  for (const l of style?.layers || []) {
    const f = l.layout?.['text-font'];
    if (Array.isArray(f) && typeof f[0] === 'string' && /semibold|bold|medium/i.test(f[0])) return { glyphs: style.glyphs, font: f[0] };
  }
  for (const l of style?.layers || []) {
    const f = l.layout?.['text-font'];
    if (Array.isArray(f) && typeof f[0] === 'string') return { glyphs: style.glyphs, font: f[0] };
  }
  return LABELS_FALLBACK;
}

function satelliteStyle(font, imagery) {
  return {
    version: 8,
    glyphs: font.glyphs,
    sources: {
      base: imagery
        ? { type: 'raster', tileSize: 256, maxzoom: 18, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics',
            tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'] }
        : { type: 'raster', tileSize: 256, attribution: '© OpenStreetMap © CARTO',
            tiles: ['a', 'b', 'c'].map((s) => `https://${s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png`) },
      labels: { type: 'raster', tileSize: 256, attribution: '© OpenStreetMap © CARTO',
        tiles: ['a', 'b', 'c'].map((s) => `https://${s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png`) },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#05070f' } },
      { id: 'base', type: 'raster', source: 'base', paint: imagery ? { 'raster-saturation': -0.15, 'raster-brightness-max': 0.85 } : {} },
      { id: 'labels', type: 'raster', source: 'labels', paint: { 'raster-opacity': 0.9 } },
    ],
  };
}
