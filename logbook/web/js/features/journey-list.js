// Sidebar: Journey (every leg by day), Fleet (your aircraft, tap to hide/show)
// and Countries (where you've landed).
import { store } from '../core/store.js';
import { html, render, shortDay, dayKey, time, duration, num, flagUrl, compact } from '../core/format.js';
import { icon, MODE_ICON } from '../core/icons.js';

const dayFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });

export default {
  id: 'journey-list',
  init({ db, ui }) {
    const el = document.getElementById('legs');
    const search = document.getElementById('leg-search');
    document.querySelector('.search-ico').replaceWith(document.createRange().createContextualFragment(icon('search').s));

    // ---------- tabs
    const tabs = document.getElementById('tabs');
    const panes = { journey: 'pane-journey', fleet: 'pane-fleet', countries: 'pane-countries' };
    render(tabs, html`<button data-tab="journey" class="on">Journey</button><button data-tab="fleet">Fleet</button><button data-tab="countries">Countries</button>`);
    tabs.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      tabs.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
      for (const [k, id] of Object.entries(panes)) document.getElementById(id).hidden = k !== b.dataset.tab;
    });

    const badge = (l) => {
      if (l.kind === 'ground') return html`<span class="ac-badge">${icon(MODE_ICON[l.mode] || 'pin')}</span>`;
      const img = db.aircraft[l.aircraft]?.wiki?.image;
      return html`<span class="ac-badge" style="--c:${l.color}">${img ? html`<img src="${img}" alt="" loading="lazy">` : icon('plane')}</span>`;
    };

    // ---------- journey
    const groups = [];
    for (const l of db.legs) {
      const k = dayKey(l.start);
      if (!groups.length || groups[groups.length - 1].key !== k) groups.push({ key: k, legs: [] });
      groups[groups.length - 1].legs.push(l);
    }
    const row = (l) => {
      const n = l.photos.length;
      const cam = html`${n ? html` · <span class="cam">${icon('photo')}${n}</span>` : ''}${l.docs?.length ? html` · <span class="cam doc" title="Flight plan attached">${icon('doc')}</span>` : ''}${l.news?.some((x) => db.news?.[x]) ? html` · <span class="cam news" title="Local news from that day">${icon('news')}</span>` : ''}`;
      if (l.kind === 'ground') return html`
        <li class="leg ground" data-id="${l.id}">${badge(l)}
          <div class="leg-main"><div class="leg-route">${l.from}<span class="to-arrow">→</span>${l.to}</div>
            <div class="leg-sub">${l.modeLabel} · ${num(l.distanceKm)} km</div></div>
          <div class="leg-meta">${time(l.start)}<small>transfer${cam}</small></div></li>`;
      const ac = db.aircraft[l.aircraft];
      return html`
        <li class="leg" data-id="${l.id}">${badge(l)}
          <div class="leg-main"><div class="leg-route">${l.from}<span class="to-arrow">${l.local ? '↺' : '→'}</span>${l.to}
              ${l.unlogged ? html`<span class="pill">unlogged</span>` : ''}</div>
            <div class="leg-sub">${l.arr.city || l.arr.name} · ${ac?.name || ''}</div></div>
          <div class="leg-meta">${duration(l.minutes)}<small>${time(l.start)}${cam}</small></div></li>`;
    };
    const draw = () => {
      const q = search.value.trim().toLowerCase();
      const hidden = store.get('hiddenAircraft');
      const match = (l) => (!l.aircraft || !hidden.has(l.aircraft)) && (!q || [l.from, l.to, l.dep.name, l.arr.name, l.dep.city, l.arr.city,
        l.dep.country?.name, l.arr.country?.name, db.aircraft[l.aircraft]?.name, l.modeLabel].join(' ').toLowerCase().includes(q));
      render(el, html`${groups.map((g) => {
        const legs = g.legs.filter(match);
        if (!legs.length) return '';
        const fl = legs.filter((l) => l.kind === 'flight');
        return html`<li><div class="day-head"><span>${dayFmt.format(new Date(g.legs[0].start))}</span>
          <small>${fl.length ? `${fl.length} flight${fl.length === 1 ? '' : 's'} · ${duration(fl.reduce((a, l) => a + l.minutes, 0))}` : 'transfer'}</small></div>
          <ol>${legs.map(row)}</ol></li>`;
      })}`);
      mark(store.get('selected'), false);
    };
    const mark = (id, scroll = true) => {
      el.querySelectorAll('.leg.active').forEach((x) => x.classList.remove('active'));
      const li = id && el.querySelector(`.leg[data-id="${CSS.escape(id)}"]`);
      if (li) { li.classList.add('active'); if (scroll) li.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
    };
    el.addEventListener('click', (e) => { const li = e.target.closest('.leg'); if (li) store.set('selected', li.dataset.id); });
    // hovering a row lights its route up on the map
    let hov = null;
    el.addEventListener('mouseover', (e) => {
      const id = e.target.closest('.leg')?.dataset.id || null;
      if (id !== hov) { hov = id; if (!store.get('playing')) ui.map.preview(id !== store.get('selected') ? id : null); }
    });
    el.addEventListener('mouseleave', () => { hov = null; ui.map.preview(null); });
    search.addEventListener('input', draw);
    store.on('selected', (id) => mark(id));
    store.on('hiddenAircraft', draw);
    draw();

    // ---------- fleet
    const fleetEl = document.getElementById('pane-fleet');
    const fleet = Object.values(db.aircraft).sort((a, b) => (a.firstFlight || '').localeCompare(b.firstFlight || ''));
    const drawFleet = () => render(fleetEl, html`<div class="pane-note">Tap an aircraft for its dossier: history, specs, photos and manuals. The eye hides its routes.</div>
      ${fleet.map((a) => html`<div class="fleet-card ${store.get('hiddenAircraft').has(a.id) ? 'off' : ''}" data-id="${a.id}" role="button" tabindex="0">
        <div class="ph">${a.wiki?.image ? html`<img src="${a.wiki.image}" alt="" loading="lazy">` : ''}<i style="background:${a.color}"></i></div>
        <div><b>${a.name}</b><small>${a.wiki?.description || a.category || ''}</small>
          <div class="nums"><span>${a.legs} <em>flights</em></span><span>${duration(a.minutes)} <em>flown</em></span><span>${compact(a.nm)} <em>nm</em></span>
            ${a.manuals?.length ? html`<span class="has-book">${icon('book')}${a.manuals.length}</span>` : ''}</div></div>
        <button class="eye ${store.get('hiddenAircraft').has(a.id) ? '' : 'on'}" data-eye="${a.id}" title="Show / hide this aircraft's routes">${icon('globe')}</button>
      </div>`)}`);
    drawFleet();
    fleetEl.addEventListener('click', (e) => {
      const eye = e.target.closest('[data-eye]');
      if (eye) {
        const set = new Set(store.get('hiddenAircraft'));
        set.has(eye.dataset.eye) ? set.delete(eye.dataset.eye) : set.add(eye.dataset.eye);
        store.set('hiddenAircraft', set);
        drawFleet();
        return;
      }
      const b = e.target.closest('.fleet-card');
      if (b) ui.openAircraft(b.dataset.id);
    });

    // ---------- countries
    const byCountry = new Map();
    for (const a of Object.values(db.airports)) {
      const c = a.country || { name: 'Unknown' };
      const e = byCountry.get(c.name) || { ...c, airports: [], first: null };
      e.airports.push(a.ident);
      const firstLeg = db.legs.find((l) => l.to === a.ident || l.from === a.ident);
      if (firstLeg && (!e.first || firstLeg.start < e.first)) e.first = firstLeg.start;
      byCountry.set(c.name, e);
    }
    const countries = [...byCountry.values()].sort((a, b) => (a.first || '').localeCompare(b.first || ''));
    render(document.getElementById('pane-countries'), html`<div class="pane-note">${countries.length} countries, in the order you first reached them. They're shaded on the map.</div>
      ${countries.map((c) => html`<button class="country" data-ap="${c.airports[0]}" style="width:100%;text-align:left">
        ${c.iso ? html`<img src="${flagUrl(c.iso)}" alt="" onerror="this.style.visibility='hidden'">` : html`<span style="width:30px"></span>`}
        <b>${c.name}</b><small>${c.airports.length} airport${c.airports.length === 1 ? '' : 's'} · ${shortDay(c.first)}</small></button>`)}`);
    document.getElementById('pane-countries').addEventListener('click', (e) => {
      const b = e.target.closest('.country');
      if (!b) return;
      const a = db.airports[b.dataset.ap];
      ui.map.map.flyTo({ center: [a.lon, a.lat], zoom: 5, duration: 1600 });
    });

    if (innerWidth < 820) document.body.classList.add('list-collapsed');
  },
};
