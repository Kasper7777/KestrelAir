// Insights: personal records, hours flown per month, landing-rate spread and
// your most-visited airports. Every record jumps to its leg on the map.
import { store } from '../core/store.js';
import { html, raw, render, num, money, duration, compact } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';

const monthShort = new Intl.DateTimeFormat('en-GB', { month: 'short' });
const dayFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });

export default {
  id: 'insights',
  init({ db, ui }) {
    ui.openInsights = () => {
      const fl = db.flights;
      const by = (f) => fl.reduce((a, b) => (f(b) > f(a) ? b : a), fl[0]);
      const longest = by((l) => l.minutes);
      const farthest = by((l) => l.distanceNm || 0);
      const landed = fl.filter((l) => l.landingFpm && l.landingFpm < 0);
      const softest = landed.reduce((a, b) => (b.landingFpm > a.landingFpm ? b : a), landed[0]);
      const missions = fl.flatMap((l) => l.missions.filter((m) => m.status === 'completed').map((m) => ({ ...m, leg: l })));
      const richest = missions.reduce((a, b) => (b.reward > (a?.reward || 0) ? b : a), null);
      const days = new Map();
      for (const l of fl) { const k = l.start.slice(0, 10); days.set(k, (days.get(k) || []).concat(l)); }
      const busiest = [...days.entries()].sort((a, b) => b[1].length - a[1].length || b[1].reduce((s, x) => s + x.minutes, 0) - a[1].reduce((s, x) => s + x.minutes, 0))[0];
      const fav = Object.values(db.aircraft).sort((a, b) => b.minutes - a.minutes)[0];
      const top = Object.values(db.airports).sort((a, b) => b.visits - a.visits || (b.wiki?.image ? 1 : 0) - (a.wiki?.image ? 1 : 0)).slice(0, 4);
      const northmost = Object.values(db.airports).reduce((a, b) => (b.lat > a.lat ? b : a));
      const southmost = Object.values(db.airports).reduce((a, b) => (b.lat < a.lat ? b : a));

      const rec = (ic, label, value, sub, leg) => html`<${raw(leg ? 'button' : 'div')} class="record" ${leg ? html`data-leg="${leg}"` : ''}>
        <span>${icon(ic)}${label}</span><b>${value}</b><small>${sub}</small></${raw(leg ? 'button' : 'div')}>`;

      const { body } = openSheet({ id: 'insights', title: 'Insights',
        sub: `${num(db.stats.flights)} flights · ${num(db.stats.hours, 1)} hours · ${compact(db.stats.distanceNm)} nm since ${dayFmt.format(new Date(db.stats.first))}` });
      render(body, html`
        <div class="records">
          ${rec('clock', 'Longest flight', duration(longest.minutes), `${longest.from} → ${longest.to} · ${db.aircraft[longest.aircraft]?.name || ''}`, longest.id)}
          ${rec('globe', 'Farthest leg', `${num(farthest.distanceNm)} nm`, `${farthest.from} → ${farthest.to}`, farthest.id)}
          ${softest ? rec('feather', 'Softest landing', `${num(softest.landingFpm)} fpm`, `${softest.to} · ${softest.arr.name}`, softest.id) : ''}
          ${richest ? rec('moneybag', 'Best-paid job', money(richest.reward), `${richest.type} · ${richest.from} → ${richest.to}`, richest.leg.id) : ''}
          ${rec('calendar', 'Busiest day', `${busiest[1].length} flights`, `${dayFmt.format(new Date(busiest[0]))} · ${duration(busiest[1].reduce((s, x) => s + x.minutes, 0))}`, busiest[1][0].id)}
          ${rec('plane', 'Favourite aircraft', duration(fav.minutes), `${fav.name} · ${fav.legs} flights`)}
          ${rec('pin', 'Farthest north', `${northmost.lat.toFixed(1)}°N`, `${northmost.ident} · ${northmost.city || northmost.name}`)}
          ${rec('pin', 'Farthest south', `${Math.abs(southmost.lat).toFixed(1)}°S`, `${southmost.ident} · ${southmost.city || southmost.name}`)}
        </div>
        <div class="charts">
          <div class="chart-card" id="ch-months"><h4>Hours flown per month</h4><p>Every flight, including ones NeoFly didn't log</p></div>
          <div class="chart-card" id="ch-landing"><h4>How you land</h4><p>Touchdown rate, fpm</p></div>
        </div>
        <h3 class="section-title">Most-visited airports</h3>
        <div class="top-airports">${top.map((a) => html`<button class="top-ap" data-ap="${a.ident}">
          ${a.wiki?.image ? html`<img src="${a.wiki.image}" alt="" loading="lazy">` : ''}<em>${a.visits}×</em>
          <div><b>${a.ident}</b><small>${a.name}${a.city && a.city !== a.name ? `, ${a.city}` : ''}</small></div></button>`)}</div>`);

      // ---- hours per month
      const months = new Map();
      for (const l of fl) { const k = l.start.slice(0, 7); months.set(k, (months.get(k) || 0) + l.minutes / 60); }
      const mrows = [...months.entries()].sort().map(([k, h]) => ({ label: monthShort.format(new Date(k + '-01')), value: h,
        tip: `${monthShort.format(new Date(k + '-01'))} ${k.slice(0, 4)}: ${num(h, 1)} h` }));
      barChart(body.querySelector('#ch-months'), mrows, (v) => num(v, 0));
      // ---- landing spread
      const buckets = [['0–100', 0, 100], ['100–200', 100, 200], ['200–350', 200, 350], ['350–600', 350, 600], ['600+', 600, 1e9]];
      const lrows = buckets.map(([label, lo, hi]) => {
        const n = landed.filter((l) => -l.landingFpm >= lo && -l.landingFpm < hi).length;
        return { label, value: n, tip: `${n} landing${n === 1 ? '' : 's'} at ${label} fpm` };
      });
      barChart(body.querySelector('#ch-landing'), lrows, (v) => num(v));

      body.addEventListener('click', (e) => {
        const r = e.target.closest('[data-leg]');
        if (r) { closeSheet(); store.set('selected', r.dataset.leg); return; }
        const a = e.target.closest('[data-ap]');
        if (a) { closeSheet(); const ap = db.airports[a.dataset.ap]; ui.map.map.flyTo({ center: [ap.lon, ap.lat], zoom: 8, duration: 1800 }); }
      });
    };
  },
};

// Single-series bar chart: thin rounded bars, recessive grid, value labels on
// the ends, per-bar hover tooltip. One hue (the accent), so no legend.
function barChart(card, rows, fmt) {
  const W = Math.max(280, Math.round(card.clientWidth - 36)), H = 200, pad = { l: 8, r: 8, t: 18, b: 22 }; // 1:1 so text stays crisp
  const max = Math.max(1, ...rows.map((r) => r.value));
  const step = (W - pad.l - pad.r) / rows.length;
  const bw = Math.min(42, step - 6);
  const y = (v) => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${card.querySelector('h4').textContent}">
    ${[0.5, 1].map((f) => `<line class="grid" x1="${pad.l}" x2="${W - pad.r}" y1="${y(max * f)}" y2="${y(max * f)}"/>`).join('')}
    <line class="grid" x1="${pad.l}" x2="${W - pad.r}" y1="${y(0)}" y2="${y(0)}" style="stroke:rgba(255,255,255,.18)"/>
    ${rows.map((r, i) => {
      const x = pad.l + step * i + (step - bw) / 2, top = y(r.value), h = Math.max(0, y(0) - top);
      const rr = Math.min(4, h / 2, bw / 2);
      const path = h > 0 ? `M${x},${y(0)} V${top + rr} Q${x},${top} ${x + rr},${top} H${x + bw - rr} Q${x + bw},${top} ${x + bw},${top + rr} V${y(0)} Z` : '';
      return `<g class="col" data-tip="${r.tip}" data-x="${x + bw / 2}" data-y="${top}">
        <rect class="bar-hit" x="${pad.l + step * i}" y="${pad.t}" width="${step}" height="${H - pad.t - pad.b}"/>
        <path class="bar" d="${path}"/>
        ${r.value ? `<text class="val" x="${x + bw / 2}" y="${top - 5}" text-anchor="middle">${fmt(r.value)}</text>` : ''}
        <text class="axis" x="${x + bw / 2}" y="${H - 6}" text-anchor="middle">${r.label}</text></g>`;
    }).join('')}</svg><div class="chart-tip" hidden></div>`;
  card.insertAdjacentHTML('beforeend', svg);
  const tip = card.querySelector('.chart-tip');
  const s = card.querySelector('svg');
  s.addEventListener('mousemove', (e) => {
    const g = e.target.closest('g.col');
    if (!g) { tip.hidden = true; return; }
    const box = s.getBoundingClientRect(), k = box.width / W, cb = card.getBoundingClientRect();
    tip.textContent = g.dataset.tip;
    tip.style.left = `${box.left - cb.left + g.dataset.x * k}px`;
    tip.style.top = `${box.top - cb.top + g.dataset.y * k}px`;
    tip.hidden = false;
  });
  s.addEventListener('mouseleave', () => (tip.hidden = true));
}
