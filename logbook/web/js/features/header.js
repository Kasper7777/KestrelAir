// Top bar: pilot card, headline stats, fleet legend (click to hide an aircraft)
// and the map toggles.
import { store } from '../core/store.js';
import { html, render, num, compact, money, day, duration, flagUrl } from '../core/format.js';

export default {
  id: 'header',
  init({ db, ui }) {
    const s = db.stats, p = db.pilot;
    const flags = Object.values(db.airports).reduce((m, a) => (a.country?.iso && m.set(a.country.name, a.country.iso), m), new Map());

    render(document.getElementById('pilot'), html`
      <div class="pilot">
        ${p.photo ? html`<img class="pilot-photo" src="${p.photo}" alt="">` : ''}
        <div>
          <div class="eyebrow">Kestrel Air · Logbook</div>
          <div class="pilot-name">${p.name}</div>
          <div class="pilot-sub">Rank ${p.rank} · ${day(s.first)} – ${day(s.last)}</div>
        </div>
      </div>`);

    const stat = (v, label, title = '') => html`<div class="stat" title="${title}"><b>${v}</b><span>${label}</span></div>`;
    render(document.getElementById('stats'), html`
      ${stat(num(s.flights), 'flights')}
      ${stat(num(s.hours, 1), 'hours')}
      ${stat(compact(s.distanceNm), 'nm flown')}
      ${stat(num(s.airports), 'airports')}
      ${stat(num(s.countries), 'countries', s.countryList.join(', '))}
      ${stat(num(s.photos), 'photos')}
      ${stat('$' + compact(s.earnings), 'earned', money(s.earnings))}`);

    const fleet = Object.values(db.aircraft).sort((a, b) => (a.firstFlight || '').localeCompare(b.firstFlight || ''));
    const legend = document.getElementById('fleet');
    const draw = () => render(legend, html`${fleet.map((a) => html`
      <button class="chip ${store.get('hiddenAircraft').has(a.id) ? 'off' : ''}" data-id="${a.id}"
        title="${a.livery || a.name} · ${a.legs} flights · ${duration(a.minutes)}">
        <i style="background:${a.color};color:${a.color}"></i>${a.name}<small>${a.legs}</small>
      </button>`)}
      <span class="chip ground"><i></i>Transfer</span>`);
    draw();
    legend.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-id]');
      if (!b) return;
      const set = new Set(store.get('hiddenAircraft'));
      set.has(b.dataset.id) ? set.delete(b.dataset.id) : set.add(b.dataset.id);
      store.set('hiddenAircraft', set);
      draw();
    });

    // countries strip (hover the stat to see names; this gives flags)
    const cs = document.getElementById('countries');
    render(cs, html`${[...flags].map(([name, iso]) => html`<img src="${flagUrl(iso)}" title="${name}" alt="${iso}" loading="lazy">`)}`);
    cs.querySelectorAll('img').forEach((i) => i.addEventListener('error', () => i.remove()));

    // toggles
    const tog = document.getElementById('toggles');
    const drawTog = () => render(tog, html`
      <button data-k="basemap" data-v="${store.get('basemap') === 'dark' ? 'satellite' : 'dark'}">${store.get('basemap') === 'dark' ? '🛰 Satellite' : '🌑 Dark map'}</button>
      <button data-k="projection" data-v="${store.get('projection') === 'globe' ? 'mercator' : 'globe'}">${store.get('projection') === 'globe' ? '🗺 Flat' : '🌍 Globe'}</button>
      <button data-act="all">⤢ Whole journey</button>
      <button data-act="backup" class="backup-btn" title="Copy your NeoFly save, all original screenshots and a flight list into the logbook's backup folder">💾 Back up</button>
      ${db.unplacedPhotos.length ? html`<button data-act="archive">🗂 Other shots (${db.unplacedPhotos.length})</button>` : ''}`);
    drawTog();
    tog.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.k) { store.set(b.dataset.k, b.dataset.v); drawTog(); }
      if (b.dataset.act === 'all') { store.set('selected', null); ui.fitAll(); }
      if (b.dataset.act === 'archive') ui.openPhotos(db.unplacedPhotos, 0, 'Shots from before this logbook started');
      if (b.dataset.act === 'backup') runBackup(b);
    });

    // ---------- backup
    const toast = document.getElementById('toast');
    const say = (tpl, ms = 0) => {
      render(toast, tpl);
      toast.hidden = false;
      clearTimeout(say.t);
      if (ms) say.t = setTimeout(() => (toast.hidden = true), ms);
    };
    const post = (url) => fetch(url, { method: 'POST', headers: { 'X-Logbook': '1' } }).then((r) => r.json());
    async function runBackup(btn) {
      btn.disabled = true;
      btn.textContent = '⏳ Backing up…';
      say(html`<b>Backing up…</b><small>NeoFly save, original screenshots and your flight list</small>`);
      try {
        const r = await post('/__backup');
        if (!r.ok) throw new Error(r.error);
        const p = r.photos;
        say(html`<b>✅ Backup done</b>
          <small>NeoFly save: ${r.neofly.new ? 'new copy saved' : 'no changes since last backup'} · ${r.neofly.copies} copies kept</small>
          <small>Photos: ${p.copied ? `${p.copied} new (${p.copiedMB} MB)` : 'none new'} · ${p.copied + p.alreadyBackedUp} backed up in total</small>
          <small>Flight list: ${r.legs} legs (flights.csv) · backup folder ${r.totalMB} MB</small>
          <div class="toast-actions"><button data-open>📂 Open backup folder</button><button data-close>OK</button></div>`);
      } catch (e) {
        say(html`<b>⚠️ Backup failed</b><small>${e.message || 'Is the logbook running from the desktop shortcut?'}</small>
          <div class="toast-actions"><button data-close>OK</button></div>`);
      } finally {
        btn.disabled = false;
        btn.textContent = '💾 Back up';
      }
    }
    toast.addEventListener('click', (e) => {
      if (e.target.dataset.open !== undefined) post('/__open-backup');
      if (e.target.dataset.close !== undefined || e.target.dataset.open !== undefined) toast.hidden = true;
    });
    fetch('/__status').then((r) => r.json()).then((s) => {
      const b = tog.querySelector('.backup-btn');
      if (b && s.lastBackup) b.title += `\nLast backup: ${day(s.lastBackup.at)} ${s.lastBackup.at.slice(11, 16)}`;
    }).catch(() => {});
  },
};
