// Entry point: load data, create the map, then start every registered feature.
// To add a feature (e.g. the scrapbook), create js/features/<name>.js exporting a
// default feature object and add it to FEATURES below. See registry.js.
import { store } from './core/store.js';
import { loadLogbook } from './core/data.js';
import { html, day, time, duration, num, flagUrl } from './core/format.js';
import { createMap } from './features/map.js';
import { register, all } from './features/registry.js';
import header from './features/header.js';
import journeyList from './features/journey-list.js';
import detail from './features/detail.js';
import lightbox from './features/lightbox.js';
import timeline from './features/timeline.js';
import gallery from './features/gallery.js';
import insights from './features/insights.js';
import logbook from './features/logbook.js';
import layers from './features/layers.js';
import diary from './features/diary.js';
import settings from './features/settings.js';
import aircraft from './features/aircraft.js';
import glassfx from './features/glassfx.js';
import newsFeature from './features/news.js';
import docs from './features/docs.js';

const FEATURES = [header, journeyList, detail, lightbox, timeline, gallery, insights, logbook, layers, diary, settings, aircraft, newsFeature, docs, glassfx];

async function start() {
  // keep the local launcher alive while this tab is open; surface build errors
  setInterval(() => fetch('/__alive').catch(() => {}), 60000);
  fetch('/__status').then((r) => r.json()).then((s) => s.error && console.warn('Last rebuild failed, showing previous data:\n' + s.error)).catch(() => {});
  const db = await loadLogbook();
  document.title = `${db.pilot.name} · Logbook`;
  const ui = makeUi(db);
  const map = await createMap(db, ui);
  ui.fitAll = (o) => map.fitAll(o);
  ui.map = map;
  const ctx = { db, store, map, ui };
  window.logbook = ctx; // handy in the console
  FEATURES.forEach(register);
  for (const f of all()) {
    try { f.init?.(ctx); } catch (e) { console.error(`feature ${f.id} failed`, e); }
  }
  map.fitAll({ duration: 2600 });
  document.body.classList.add('ready');
  const deep = new URLSearchParams(location.hash.slice(1)).get('leg');
  if (deep && db.legById.has(deep)) setTimeout(() => store.set('selected', deep), 2700);
  store.on('selected', (id) => history.replaceState(null, '', id ? `#leg=${id}` : '#'));
}

function makeUi(db) {
  const ui = {
    // keep fitted routes clear of the floating panels
    padding() {
      const r = (id) => document.getElementById(id)?.getBoundingClientRect();
      const W = innerWidth, H = innerHeight;
      if (W < 820) return { top: 80, bottom: (r('timeline')?.height || 80) + 20 + (document.body.classList.contains('has-detail') ? H * 0.45 : 0), left: 30, right: 30 };
      const list = document.body.classList.contains('list-collapsed') ? 0 : (r('sidebar')?.right || 0);
      const det = document.body.classList.contains('has-detail') ? W - (r('detail')?.left ?? W) : 0;
      return { top: (r('titlebar')?.bottom || 0) + 50, bottom: (r('timeline')?.height || 0) + 60, left: list + 60, right: Math.max(0, det) + 60 };
    },
    legTooltip(l) {
      const ac = db.aircraft[l.aircraft];
      return html`<b>${l.from} → ${l.to}</b><div class="tip-sub">${l.kind === 'flight'
        ? html`${day(l.start)} · ${duration(l.minutes)} · ${num(l.distanceNm)} nm<br>${ac?.name || ''}`
        : html`${l.modeLabel} · ${num(l.distanceKm)} km`}</div>`.s;
    },
    airportPopup(ident, coords) {
      const a = db.airports[ident];
      const arrivals = db.legs.filter((l) => l.to === ident && l.kind === 'flight');
      const photos = a.stops.flatMap((s) => s.photos);
      const el = document.createElement('div');
      el.className = 'ap-pop';
      el.innerHTML = html`
        ${a.wiki?.image ? html`<img class="ap-img" src="${a.wiki.image}" alt="">` : ''}
        <div class="ap-code">${a.ident}${a.country?.iso ? html` <img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}</div>
        <div class="ap-name">${a.name}</div>
        <div class="ap-where">${[a.city, a.country?.name].filter(Boolean).join(', ')}</div>
        <div class="ap-facts">${a.elevationFt != null ? html`<span>${num(a.elevationFt)} ft</span>` : ''}${a.longestRunwayFt ? html`<span>${num(a.longestRunwayFt)} ft rwy</span>` : ''}<span>${a.visits} visit${a.visits === 1 ? '' : 's'}</span></div>
        ${a.wiki?.description ? html`<div class="ap-where">${a.wiki.description}</div>` : ''}
        ${arrivals.length ? html`<div class="ap-legs">${arrivals.map((l) => html`<button data-id="${l.id}">${day(l.start)} · from ${l.from}</button>`)}</div>` : ''}
        ${photos.length ? html`<div class="ap-thumbs">${photos.map((id, i) => html`<img src="${db.photos[id].thumb}" data-i="${i}" alt="">`)}</div>` : ''}`.s;
      el.addEventListener('click', (e) => {
        if (e.target.dataset.id) { pop.remove(); store.set('selected', e.target.dataset.id); }
        if (e.target.dataset.i) ui.openPhotos(photos, +e.target.dataset.i);
      });
      const pop = new maplibregl.Popup({ className: 'airport-popup', maxWidth: '300px', offset: 12 }).setLngLat(coords).setDOMContent(el).addTo(ui.map.map);
    },
    // polaroid that pops up while the replay passes the spot a photo was taken
    flashPhoto(p) {
      // drops onto the map at the spot the photo was taken
      ui.map.dropPhoto(p, (ph) => {
        ui.stopPlayback?.();
        const set = db.legById.get(ph.leg)?.photos || [ph.id];
        ui.openPhotos(set, set.indexOf(ph.id));
      });
    },
  };
  return ui;
}

start().catch((e) => {
  console.error(e);
  document.getElementById('boot').innerHTML = `<div class="boot-err"><b>Couldn't open the logbook.</b><br>${e.message}<br><small>Start it with Kestrel Air Logbook.exe so the data is rebuilt and served.</small></div>`;
});
