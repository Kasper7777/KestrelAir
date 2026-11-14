// Left panel: the whole journey as a list grouped by day. Flights and ground
// transfers alternate exactly as they happened.
import { store } from '../core/store.js';
import { html, render, day, dayKey, time, duration, num } from '../core/format.js';

export default {
  id: 'journey-list',
  init({ db }) {
    const el = document.getElementById('legs');
    const search = document.getElementById('leg-search');

    const groups = [];
    for (const l of db.legs) {
      const k = dayKey(l.start);
      if (!groups.length || groups[groups.length - 1].key !== k) groups.push({ key: k, legs: [] });
      groups[groups.length - 1].legs.push(l);
    }

    const row = (l) => {
      const ac = db.aircraft[l.aircraft];
      const n = l.photos.length;
      if (l.kind === 'ground') return html`
        <li class="leg ground" data-id="${l.id}">
          <span class="when">${time(l.start)}</span>
          <span class="mode">${l.icon}</span>
          <span class="route"><b>${l.from}</b><em>${l.modeLabel}</em><b>${l.to}</b></span>
          <span class="meta">${num(l.distanceKm)} km${n ? html` · <span class="cam">📷${n}</span>` : ''}</span>
        </li>`;
      return html`
        <li class="leg" data-id="${l.id}" data-aircraft="${l.aircraft}">
          <span class="when">${time(l.start)}</span>
          <span class="dot" style="background:${l.color};color:${l.color}"></span>
          <span class="route"><b>${l.from}</b><i class="arrow">${l.local ? '↺' : '→'}</i><b>${l.to}</b>
            <small>${l.arr.city || l.arr.name}</small></span>
          <span class="meta">${duration(l.minutes)} · ${num(l.distanceNm)} nm${n ? html` · <span class="cam">📷${n}</span>` : ''}
            <small>${ac?.name || ''}${l.inferred ? ' · recovered' : ''}</small></span>
        </li>`;
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
        return html`<li class="day"><div class="day-head"><span>${day(g.legs[0].start)}</span>
          <small>${fl.length} flight${fl.length === 1 ? '' : 's'} · ${duration(fl.reduce((a, l) => a + l.minutes, 0))}</small></div>
          <ol>${legs.map(row)}</ol></li>`;
      })}`);
      mark(store.get('selected'), false);
    };

    const mark = (id, scroll = true) => {
      el.querySelectorAll('.leg.active').forEach((x) => x.classList.remove('active'));
      const li = id && el.querySelector(`.leg[data-id="${CSS.escape(id)}"]`);
      if (li) {
        li.classList.add('active');
        if (scroll) li.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    };

    el.addEventListener('click', (e) => {
      const li = e.target.closest('.leg');
      if (li) store.set('selected', li.dataset.id);
    });
    search.addEventListener('input', draw);
    store.on('selected', (id) => mark(id));
    store.on('hiddenAircraft', draw);
    draw();

    if (innerWidth < 820) document.body.classList.add('list-collapsed');
    document.getElementById('panel-toggle').addEventListener('click', () => document.body.classList.toggle('list-collapsed'));
  },
};
