// Title capsule (pilot), toolbar (View, Other shots, Back up), the View menu
// popover and the headline stats.
import { store } from '../core/store.js';
import { html, render, num, compact, money, day } from '../core/format.js';
import { icon } from '../core/icons.js';

export default {
  id: 'header',
  init({ db, ui }) {
    const s = db.stats, p = db.pilot;

    render(document.getElementById('titlebar'), html`
      <button class="icon-btn" id="side-toggle" title="Show / hide the journey">${icon('sidebar')}</button>
      <img class="app-mark" src="icon.png" alt="Kestrel Air">
      <div class="brand"><b>Kestrel Air</b><small>Logbook</small></div>
      <div class="tb-sep"></div>
      <button class="pilot-btn" title="Pilot settings: choose the NeoFly pilot, name and photo">
        ${p.photo ? html`<img class="avatar" src="${p.photo}" alt="">` : html`<span class="avatar ph">${(p.character || p.name)[0]}</span>`}
        <span class="brand pilot"><b>${p.character || p.name}</b><small>Captain · Rank ${p.rank}</small></span></button>`);
    document.getElementById('side-toggle').addEventListener('click', () => document.body.classList.toggle('list-collapsed'));
    document.querySelector('.pilot-btn').addEventListener('click', () => ui.openSettings?.());

    render(document.getElementById('stats'), html`
      <div class="stat"><b>${num(s.flights)}</b><span>Flights</span></div>
      <div class="stat"><b>${num(s.hours, 0)}</b><span>Hours</span></div>
      <div class="stat"><b>${compact(s.distanceNm)}</b><span>Nautical miles</span></div>
      <div class="stat"><b>${num(s.airports)}</b><span>Airports</span></div>
      <div class="stat" title="${s.countryList.join(', ')}"><b>${num(s.countries)}</b><span>Countries</span></div>
      <div class="stat" title="${money(s.earnings)}"><b>$${compact(s.earnings)}</b><span>Earned</span></div>`);

    const bar = document.getElementById('toolbar');
    render(bar, html`
      <button class="tb-btn" data-act="all" title="Show the whole journey">${icon('globe')}<span>Journey</span></button>
      <button class="tb-btn" data-act="view" title="Map style and layers">${icon('layers')}<span>View</span></button>
      <div class="tb-sep"></div>
      <button class="tb-btn" data-act="logbook" title="Every flight, written up in a pilot's logbook">${icon('book')}<span>Logbook</span></button>
      <button class="tb-btn" data-act="diary" title="What ${p.character || p.name} got up to on the ground between flights">${icon('diary')}<span>Diary</span></button>
      <button class="tb-btn" data-act="photos" title="Every screenshot, as prints">${icon('photo')}<span>Photos</span></button>
      <button class="tb-btn" data-act="insights" title="Records, charts and favourite airports">${icon('chart')}<span>Insights</span></button>
      <div class="tb-sep"></div>
      <button class="tb-btn primary backup-btn" data-act="backup" title="Copy your NeoFly save, original screenshots and a flight list into the logbook's backup folder">${icon('save')}<span>Back up</span></button>`);
    bar.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      const act = b.dataset.act;
      if (act === 'all') { store.set('selected', null); ui.fitAll(); }
      if (act === 'view') toggleMenu(b);
      if (act === 'photos') ui.openGallery();
      if (act === 'insights') ui.openInsights();
      if (act === 'logbook') ui.openLogbook();
      if (act === 'diary') ui.openDiary?.();
      if (act === 'backup') runBackup(b);
    });

    // ---------- View menu
    const menu = document.getElementById('viewmenu');
    const seg = (key, opts) => html`<div class="segmented" data-key="${key}">${opts.map(([v, label, ic]) =>
      html`<button data-v="${v}" class="${store.get(key) === v ? 'on' : ''}">${ic ? icon(ic) : ''}${label}</button>`)}</div>`;
    const sw = (k, label) => html`<div class="switch-row"><span>${label}</span><button class="switch ${store.get('layers')[k] ? 'on' : ''}" data-layer="${k}" aria-label="${label}"></button></div>`;
    const drawMenu = () => render(menu, html`
      <h5>Map</h5>${seg('basemap', [['satellite', 'Satellite'], ['dark', 'Dark'], ['light', 'Light']])}
      <h5>Projection</h5>${seg('projection', [['globe', 'Globe', 'globe'], ['mercator', 'Flat', 'map']])}
      <h5>Colour routes by</h5>${seg('colorBy', [['aircraft', 'Aircraft'], ['month', 'Month']])}
      <h5>Show</h5><div class="list-box">
        ${sw('countries', 'Countries visited')}${sw('routes', 'Flights')}${sw('transfers', 'Transfers')}
        ${sw('airports', 'Airports')}${sw('labels', 'Airport codes')}${sw('photos', 'Photo pins')}</div>`);
    function toggleMenu(btn) {
      if (!menu.hidden) { menu.hidden = true; btn.classList.remove('on'); return; }
      drawMenu(); menu.hidden = false; btn.classList.add('on');
    }
    menu.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.layer) store.set('layers', { ...store.get('layers'), [b.dataset.layer]: !store.get('layers')[b.dataset.layer] });
      else if (b.dataset.v) store.set(b.closest('.segmented').dataset.key, b.dataset.v);
      drawMenu();
    });
    document.addEventListener('pointerdown', (e) => {
      if (!menu.hidden && !menu.contains(e.target) && !e.target.closest('[data-act=view]')) {
        menu.hidden = true; bar.querySelector('[data-act=view]').classList.remove('on');
      }
    });

    // ---------- backup
    const toast = document.getElementById('toast');
    const say = (tpl) => { render(toast, tpl); toast.hidden = false; };
    const post = (url) => fetch(url, { method: 'POST', headers: { 'X-Logbook': '1' } }).then((r) => r.json());
    async function runBackup(btn) {
      btn.disabled = true;
      say(html`<b>Backing up…</b><small>NeoFly save, original screenshots and your flight list.</small>`);
      try {
        const r = await post('/__backup');
        if (!r.ok) throw new Error(r.error);
        const ph = r.photos;
        say(html`<b>${icon('check')}Backup complete</b>
          <small>NeoFly save: ${r.neofly.new ? 'new copy saved' : 'unchanged since the last backup'} (${r.neofly.copies} kept)</small>
          <small>Screenshots: ${ph.copied ? `${ph.copied} new, ${ph.copiedMB} MB` : 'nothing new'} · ${ph.copied + ph.alreadyBackedUp} in total</small>
          <small>Flight list: ${r.legs} legs in flights.csv · ${r.totalMB} MB altogether</small>
          <div class="toast-actions"><button data-open>${icon('folder')}Show folder</button><button class="primary" data-close>Done</button></div>`);
      } catch (e) {
        say(html`<b>Backup didn't finish</b><small>${e.message || 'Start the logbook from Kestrel Air Logbook.exe and try again.'}</small>
          <div class="toast-actions"><button class="primary" data-close>OK</button></div>`);
      } finally { btn.disabled = false; }
    }
    toast.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.open !== undefined) post('/__open-backup');
      toast.hidden = true;
    });
    fetch('/__status').then((r) => r.json()).then((st) => {
      const b = bar.querySelector('.backup-btn');
      if (b && st.lastBackup) b.title += `\nLast backup: ${day(st.lastBackup.at)}, ${st.lastBackup.at.slice(11, 16)}`;
    }).catch(() => {});
  },
};
