// The paper logbook: every flight written up EASA-style across a two-page
// spread, page totals carried forward like a real pilot's logbook.
// Night time and night landings come from the sun's position along each flight
// (sun below -6°, i.e. after civil twilight). IFR isn't recorded anywhere, so it stays blank.
import { html, raw, render } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';
import { typeCode, registration } from '../core/planes.js';
import { along, greatCircle, cumulative } from '../core/geo.js';
import { store } from '../core/store.js';

const ROWS = 14;
const pad = (n) => String(n).padStart(2, '0');
const hm = (mins) => (mins > 0.5 ? `${Math.floor(Math.round(mins) / 60)}:${pad(Math.round(mins) % 60)}` : '');
const dmy = (s) => { const d = new Date(s); return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${String(d.getFullYear()).slice(2)}`; };
const hhmm = (s) => { const d = new Date(s); return `${pad(d.getHours())}${pad(d.getMinutes())}`; };

function sunElevation(lat, lon, date) {
  const R = Math.PI / 180, d = (date.getTime() - Date.UTC(2000, 0, 1, 12)) / 864e5;
  const g = (357.529 + 0.98560028 * d) * R, q = 280.459 + 0.98564736 * d;
  const L = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * R, e = (23.439 - 0.00000036 * d) * R;
  const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L)), dec = Math.asin(Math.sin(e) * Math.sin(L));
  const gmst = ((18.697374558 + 24.06570982441908 * d) % 24) * 15;
  const H = (gmst + lon) * R - ra;
  return Math.asin(Math.sin(lat * R) * Math.sin(dec) + Math.cos(lat * R) * Math.cos(dec) * Math.cos(H)) / R;
}

function nightTime(coords, acc, start, end, arrPos) {
  const t0 = new Date(start).getTime(), t1 = new Date(end).getTime();
  let night = 0;
  const N = 24;
  for (let i = 0; i < N; i++) {
    const f = (i + 0.5) / N, [lon, lat] = along(coords, f, acc).point;
    if (sunElevation(lat, ((lon + 540) % 360) - 180, new Date(t0 + (t1 - t0) * f)) < -6) night++;
  }
  return { fraction: night / N, landing: sunElevation(arrPos[1], arrPos[0], new Date(t1)) < -6 };
}

// a hired pilot's flight in a company aircraft
function companyEntry(f) {
  const coords = greatCircle(f.fromPos, f.toPos);
  const n = nightTime(coords, cumulative(coords), f.start, f.end, f.toPos);
  const ac = { name: f.aircraftName, livery: f.aircraftLivery, engines: f.engines };
  const me = (f.engines || 1) > 1;
  return {
    id: null, date: dmy(f.start), dep: f.from, depT: hhmm(f.start), arr: f.to, arrT: hhmm(f.end),
    type: typeCode(ac), reg: registration(ac) || '—', se: me ? 0 : f.minutes, me: me ? f.minutes : 0, total: f.minutes,
    ldgDay: n.landing ? 0 : 1, ldgNight: n.landing ? 1 : 0, night: n.fraction * f.minutes, pic: f.minutes,
    picName: (f.pilot || 'Hired pilot').toUpperCase(), remarks: [f.type, f.completed ? (f.pay ? `$${f.pay.toLocaleString('en-GB')}` : '') : 'not completed'].filter(Boolean).join(' · '),
    estimated: false, company: true,
  };
}

function entry(l, db, picName) {
  const ac = db.aircraft[l.aircraft] || {};
  const n = nightTime(l.coords, l.acc, l.start, l.end, [l.arr.lon, l.arr.lat]);
  const night = n.fraction * 24, N = 24, nightLdg = n.landing;
  const me = (ac.engines || 1) > 1;
  const remarks = [];
  for (const m of l.missions) if (m.status === 'completed') remarks.push(`${m.type}${m.pax ? ` ${m.pax} pax` : m.cargoLbs ? ` ${m.cargoLbs} lb` : ''}`);
  if (l.landingFpm) remarks.push(`ldg ${l.landingFpm} fpm`);
  if (l.local) remarks.push('local');
  if (l.unlogged) remarks.push('not in NeoFly log');
  else if (l.inferred) remarks.push('from job log');
  return {
    id: l.id, date: dmy(l.start), dep: l.from, depT: hhmm(l.start), arr: l.to, arrT: hhmm(l.end),
    type: typeCode(ac), reg: registration(ac) || '—', se: me ? 0 : l.minutes, me: me ? l.minutes : 0, total: l.minutes,
    ldgDay: nightLdg ? 0 : 1, ldgNight: nightLdg ? 1 : 0, night: (night / N) * l.minutes, pic: l.minutes,
    remarks: remarks.join(' · '), estimated: l.unlogged || l.inferred, picName,
  };
}

export default {
  id: 'logbook',
  init({ db, ui }) {
    const captain = db.pilot.character || db.pilot.name;
    const own = db.flights.map((l) => entry(l, db, captain.toUpperCase()));
    const company = (db.companyFlights || []).map(companyEntry);
    const sum = (rows, k) => rows.reduce((a, r) => a + r[k], 0);
    const paginate = (list) => { const out = []; for (let i = 0; i < list.length; i += ROWS) out.push(list.slice(i, i + ROWS)); return out; };
    const fromLog = db.flights.filter((l) => !l.inferred).length;
    const fromJobs = db.flights.filter((l) => l.inferred && !l.unlogged).length;
    const fromEvidence = db.flights.filter((l) => l.unlogged).length;
    const pilots = [...new Set((db.companyFlights || []).map((f) => f.pilot))];
    const subs = {
      own: `${own.length} flights flown by ${captain}: ${fromLog} from NeoFly's flight log, ${fromJobs} recovered from its job log, ${fromEvidence} proven by its other records`,
      company: `${company.length} flights flown by your hired pilots (${pilots.join(', ')}) in company aircraft`,
    };

    ui.openLogbook = (start, startMode = 'own') => {
      let mode = startMode, entries = mode === 'own' ? own : company, pages = paginate(entries);
      let page = start ?? 0;
      const { el, body } = openSheet({ id: 'logbook', title: 'Logbook', cls: 'logbook-sheet', sub: subs[mode],
        head: html`${company.length ? html`<div class="segmented lb-mode"><button data-mode="own" class="on">${captain}</button><button data-mode="company">Company</button></div>` : ''}
          <div class="lb-pager"><button class="icon-btn" data-p="-1" title="Previous page (←)">${icon('back')}</button>
          <span class="lb-pageno"></span><button class="icon-btn" data-p="1" title="Next page (→)">${icon('forward')}</button></div>` });
      el.querySelector('.lb-mode')?.addEventListener('click', (e) => {
        const b = e.target.closest('[data-mode]');
        if (!b || b.dataset.mode === mode) return;
        mode = b.dataset.mode;
        el.querySelectorAll('.lb-mode button').forEach((x) => x.classList.toggle('on', x === b));
        el.querySelector('.sheet-head p').textContent = subs[mode];
        entries = mode === 'own' ? own : company; pages = paginate(entries); page = 0;
        draw();
      });

      const draw = (dir = 0) => {
        const rows = pages[page];
        const before = pages.slice(0, page).flat();
        const t = (k) => sum(rows, k), p = (k) => sum(before, k), tt = (k) => t(k) + p(k);
        const blank = Array.from({ length: ROWS - rows.length });
        const cellT = (v) => hm(v);
        const left = html`<table class="paper left"><colgroup><col style="width:14%"><col style="width:10%"><col style="width:9%"><col style="width:10%"><col style="width:9%"><col style="width:10%"><col style="width:14%"><col style="width:24%"></colgroup>
          <thead><tr><th rowspan="2">1<br>Date<small>dd/mm/yy</small></th><th colspan="2">2 · Departure</th><th colspan="2">3 · Arrival</th><th colspan="2">4 · Aircraft</th><th rowspan="2">5 · Single pilot<small>SE / ME</small></th></tr>
          <tr><th>Place</th><th>Time</th><th>Place</th><th>Time</th><th>Type</th><th>Registration</th></tr></thead>
          <tbody>${rows.map((r) => html`<tr data-leg="${r.id}" class="${r.estimated ? 'est' : ''}"><td>${r.date}</td><td>${r.dep}</td><td>${r.depT}</td><td>${r.arr}</td><td>${r.arrT}</td>
            <td>${r.type}</td><td>${r.reg}</td><td class="split"><span>${cellT(r.se)}</span><span>${cellT(r.me)}</span></td></tr>`)}
            ${blank.map(() => html`<tr class="blank"><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td class="split"><span></span><span></span></td></tr>`)}</tbody>
          <tfoot>
            ${[['Total this page', t], ['Total from previous pages', p], ['Total time', tt]].map(([label, f]) => html`<tr><td colspan="7" class="lbl">${label}</td>
              <td class="split"><span>${hm(f('se'))}</span><span>${hm(f('me'))}</span></td></tr>`)}
          </tfoot></table>`;
        const right = html`<table class="paper right"><colgroup><col style="width:11%"><col style="width:12%"><col style="width:9%"><col style="width:9%"><col style="width:9%"><col style="width:9%"><col style="width:11%"><col style="width:30%"></colgroup>
          <thead><tr><th rowspan="2">6<br>Total time<small>of flight</small></th><th rowspan="2">7<br>Name PIC</th><th colspan="2">8 · Landings</th><th colspan="2">9 · Conditions</th><th rowspan="2">10<br>PIC<small>function</small></th><th rowspan="2">11 · Remarks<small>and endorsements</small></th></tr>
          <tr><th>Day</th><th>Night</th><th>Night</th><th>IFR</th></tr></thead>
          <tbody>${rows.map((r) => html`<tr data-leg="${r.id}" class="${r.estimated ? 'est' : ''}"><td>${hm(r.total)}</td><td>${r.picName}</td><td>${r.ldgDay || ''}</td><td>${r.ldgNight || ''}</td>
            <td>${hm(r.night)}</td><td></td><td>${hm(r.pic)}</td><td class="rmk">${r.remarks}</td></tr>`)}
            ${blank.map(() => html`<tr class="blank"><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`)}</tbody>
          <tfoot>
            ${[['', t], ['', p], ['', tt]].map(([, f], i) => html`<tr><td>${hm(f('total'))}</td><td></td><td>${f('ldgDay')}</td><td>${f('ldgNight')}</td><td>${hm(f('night'))}</td><td></td><td>${hm(f('pic'))}</td>
              <td class="rmk sig">${i === 2 ? html`I certify that the entries in this log are true.<span>${db.pilot.character || db.pilot.name}</span>` : ''}</td></tr>`)}
          </tfoot></table>`;
        render(body, html`<div class="spread ${dir > 0 ? 'turn-fwd' : dir < 0 ? 'turn-back' : ''}">
          <div class="page pl">${left}<div class="folio">${page * 2 + 1}</div></div><div class="gutter"></div>
          <div class="page pr">${right}<div class="folio">${page * 2 + 2}</div></div></div>
          <nav class="lb-tabs">${pages.map((pg, i) => html`<button data-page="${i}" class="${i === page ? 'on' : ''}" title="${pg[0].date} – ${pg[pg.length - 1].date}">
            <b>${i * 2 + 1}–${i * 2 + 2}</b><small>${pg[0].date.slice(0, 5)}</small></button>`)}</nav>
          <p class="lb-note">Times are local. Night = sun more than 6° below the horizon along the route. Lighter ink = rebuilt from NeoFly's records rather than its flight log. Click an entry to see it on the map.</p>`);
        // facing pages must rule up: give both header blocks the taller one's height
        const heads = [...body.querySelectorAll('.paper thead')];
        const h = Math.max(...heads.map((x) => x.offsetHeight));
        heads.forEach((x) => { x.rows[0].style.height = `${h - x.rows[1].offsetHeight}px`; });
        el.querySelector('.lb-pageno').textContent = `Page ${page + 1} of ${pages.length}`;
        el.querySelector('[data-p="-1"]').disabled = page === 0;
        el.querySelector('[data-p="1"]').disabled = page === pages.length - 1;
      };
      el.querySelector('.lb-pager').addEventListener('click', (e) => {
        const b = e.target.closest('[data-p]');
        if (!b || b.disabled) return;
        page = Math.max(0, Math.min(pages.length - 1, page + +b.dataset.p));
        draw(+b.dataset.p);
      });
      body.addEventListener('click', (e) => {
        const tab = e.target.closest('[data-page]');
        if (tab) { const np = +tab.dataset.page; if (np !== page) { const d = np > page ? 1 : -1; page = np; draw(d); } return; }
        const r = e.target.closest('tr[data-leg]');
        if (r) { closeSheet(); store.set('selected', r.dataset.leg); }
      });
      const keys = (e) => {
        if (!document.body.contains(el)) return document.removeEventListener('keydown', keys, true);
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault(); e.stopImmediatePropagation();
          const d = e.key === 'ArrowRight' ? 1 : -1;
          const np = Math.max(0, Math.min(pages.length - 1, page + d));
          if (np !== page) { page = np; draw(d); }
        }
      };
      document.addEventListener('keydown', keys, true);
      draw();
    };
  },
};
