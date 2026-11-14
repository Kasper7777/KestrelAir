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

const FEATURES = [header, journeyList, detail, lightbox, timeline];

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
      return { top: (r('topbar')?.bottom || 0) + 40, bottom: (r('timeline')?.height || 0) + 50, left: list + 50, right: Math.max(0, det) + 50 };
    },
    legTooltip(l) {
      const ac = db.aircraft[l.aircraft];
      return html`<b>${l.from} → ${l.to}</b><br>${l.kind === 'flight'
        ? html`${day(l.start)} · ${time(l.start)}<br>${duration(l.minutes)} · ${num(l.distanceNm)} nm<br><i style="color:${l.color}">●</i> ${ac?.name || ''}`
        : html`${l.icon} ${l.modeLabel} · ${num(l.distanceKm)} km`}`.s;
    },
    airportPopup(ident, coords) {
      const a = db.airports[ident];
      const arrivals = db.legs.filter((l) => l.to === ident && l.kind === 'flight');
      const photos = a.stops.flatMap((s) => s.photos);
      const el = document.createElement('div');
      el.className = 'ap-pop';
      el.innerHTML = html`
        <div class="ap-code">${a.ident}${a.country?.iso ? html` <img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}</div>
        <div class="ap-name">${a.name}</div>
        <div class="ap-where">${[a.city, a.country?.name].filter(Boolean).join(', ')}</div>
        <div class="ap-facts">${a.elevationFt != null ? html`<span>${num(a.elevationFt)} ft</span>` : ''}${a.longestRunwayFt ? html`<span>${num(a.longestRunwayFt)} ft rwy</span>` : ''}<span>${a.visits} visit${a.visits === 1 ? '' : 's'}</span></div>
        ${arrivals.length ? html`<div class="ap-legs">${arrivals.map((l) => html`<button data-id="${l.id}">${day(l.start)} · from ${l.from}</button>`)}</div>` : ''}
        ${photos.length ? html`<div class="ap-thumbs">${photos.map((id, i) => html`<img src="${db.photos[id].thumb}" data-i="${i}" alt="">`)}</div>` : ''}`.s;
      el.addEventListener('click', (e) => {
        if (e.target.dataset.id) { pop.remove(); store.set('selected', e.target.dataset.id); }
        if (e.target.dataset.i) ui.openPhotos(photos, +e.target.dataset.i);
      });
      const pop = new maplibregl.Popup({ className: 'airport-popup', maxWidth: '300px', offset: 10 }).setLngLat(coords).setDOMContent(el).addTo(ui.map.map);
    },
    // polaroid that pops up while the replay passes the spot a photo was taken
    flashPhoto(p) {
      const wrap = document.getElementById('flash');
      const card = document.createElement('figure');
      card.className = 'polaroid';
      card.style.setProperty('--tilt', `${(Math.random() * 8 - 4).toFixed(1)}deg`);
      card.innerHTML = html`<img src="${p.thumb}" alt=""><figcaption>${time(p.takenAt)} · ${day(p.takenAt)}</figcaption>`.s;
      card.addEventListener('click', () => { ui.stopPlayback?.(); ui.openPhotos(db.legById.get(p.leg)?.photos || [p.id], (db.legById.get(p.leg)?.photos || []).indexOf(p.id)); });
      wrap.append(card);
      while (wrap.children.length > 4) wrap.firstElementChild.remove();
      setTimeout(() => card.classList.add('out'), 3800 / Math.sqrt(store.get('speed')));
      setTimeout(() => card.remove(), 4600 / Math.sqrt(store.get('speed')));
    },
  };
  return ui;
}

start().catch((e) => {
  console.error(e);
  document.getElementById('boot').innerHTML = `<div class="boot-err"><b>Couldn't open the logbook.</b><br>${e.message}<br><small>Start it with Logbook.cmd so the data is rebuilt and served.</small></div>`;
});
