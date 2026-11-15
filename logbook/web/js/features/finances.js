// Finances: the company's money, read from NeoFly's ledger. Only shown when
// "Finances" is switched on in Settings (the build then includes db.finances).
// - Cash, this month, earned, fuel, owed
// - Cash over time (crosshair), month-by-month result (above / below zero)
// - Where the money comes from and goes, by category
// - Fuel: spend per aircraft and what's in each tank; fleet condition
// - Loans, and the full ledger (filter by category, search)
// Money in is always the gold accent, money out always the cool blue - and every
// mark carries its own label, so colour is never the only cue.
import { html, raw, render, num, money, compact } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet } from '../core/sheet.js';

const IN = 'var(--accent)';
const OUT = 'var(--money-out)';
// investment and financing, kept out of the running result so a $25M jet doesn't swamp a month of flying
const NOT_TRADING = new Set(['capital', 'loans', 'aircraft']);
const dShort = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const mShort = new Intl.DateTimeFormat('en-GB', { month: 'short' });
const signed = (n) => (n < 0 ? '−' : '+') + money(Math.abs(n));
const sum = (rows, f) => rows.reduce((s, r) => s + f(r), 0);

export default {
  id: 'finances',
  init({ db, ui }) {
    // its own toolbar button, beside Insights; hidden while the feature is off
    const bar = document.getElementById('toolbar');
    const btn = document.createElement('button');
    btn.className = 'tb-btn';
    btn.dataset.act = 'finances';
    btn.title = 'Cash, income and costs, fuel and the fleet - from NeoFly';
    btn.innerHTML = html`${icon('moneybag')}<span>Finances</span>`.s;
    bar.querySelector('[data-act=insights]')?.after(btn);
    const sync = () => { btn.hidden = !db.finances; };
    sync();
    btn.addEventListener('click', () => ui.openFinances());

    // Settings switched it on/off: pick up the rebuilt data without reloading the page
    ui.reloadFinances = async () => {
      const j = await fetch('data/logbook.json', { cache: 'no-store' }).then((r) => r.json());
      db.finances = j.finances || null;
      db.meta.features = j.meta.features;
      sync();
    };

    ui.openFinances = () => {
      const f = db.finances;
      if (!f) return;
      const cats = f.categories;
      const ledger = f.ledger;
      const trading = ledger.filter((r) => !NOT_TRADING.has(r.cat));
      const cash = ledger.length ? ledger[ledger.length - 1].balance : db.pilot.cash;
      const thisMonth = new Date().toISOString().slice(0, 7);
      const monthRows = trading.filter((r) => r.at?.startsWith(thisMonth));
      const monthNet = sum(monthRows, (r) => r.in - r.out);
      const earned = sum(trading, (r) => r.in);
      const fuelRows = ledger.filter((r) => r.cat === 'fuel');
      const fuelSpent = sum(fuelRows, (r) => r.out);
      const owed = sum(f.loans, (l) => l.remaining || 0);

      const { body } = openSheet({ id: 'finances', title: 'Finances', cls: 'finances-sheet',
        sub: `${db.pilot.character || db.pilot.name}'s company, from NeoFly's ledger · ${num(ledger.length)} entries since ${ledger[0] ? dShort.format(new Date(ledger[0].at)) : '—'}` });

      const tile = (ic, label, value, sub, cls = '') => html`<div class="record ${cls}"><span>${icon(ic)}${label}</span><b>${value}</b><small>${sub}</small></div>`;
      render(body, html`
        <div class="records fin-tiles">
          ${tile('moneybag', 'Cash', money(cash), `Rank ${db.pilot.rank ?? '—'} · reputation ${db.pilot.reputation ?? '—'}`, 'hero')}
          ${tile('calendar', 'This month', signed(monthNet), `From flying and trading · ${mShort.format(new Date())}`, monthNet < 0 ? 'neg' : 'pos')}
          ${tile('trophy', 'Earned', '$' + compact(earned), 'Missions, hired pilots and trading')}
          ${tile('speed', 'Fuel bought', '$' + compact(fuelSpent), `${fuelRows.length} fill-ups · avg ${money(fuelSpent / (fuelRows.length || 1))}`)}
          ${owed ? tile('doc', 'Owed', money(owed), `${f.loans.length} loan${f.loans.length === 1 ? '' : 's'} · ${money(sum(f.loans, (l) => l.weekly || 0))}/week`) : ''}
        </div>
        <div class="charts">
          <div class="chart-card" id="fin-cash"><h4>Cash over time</h4><p>The balance after every entry in the ledger</p></div>
          <div class="chart-card" id="fin-months"><h4>Month by month</h4><p>Earned minus spent - aircraft, capital and loans shown separately</p></div>
        </div>
        <div class="fin-split">
          <div class="chart-card"><h4>Where it comes from</h4><p>Money in, by kind</p><div id="fin-in"></div></div>
          <div class="chart-card"><h4>Where it goes</h4><p>Money out, by kind</p><div id="fin-out"></div></div>
        </div>
        <h3 class="section-title">${icon('speed')}Fuel &amp; fleet</h3>
        <div class="fin-fleet">${f.fleet.map((a) => fleetCard(a, fuelRows, db))}</div>
        ${f.loans.length ? html`<h3 class="section-title">${icon('doc')}Loans</h3>
          <div class="fin-loans">${f.loans.map((l) => html`<div class="set-row"><div>
            <b>${money(l.remaining)} left${l.amount ? html` <small class="muted">of ${money(l.amount)}</small>` : ''}</b>
            <small>${money(l.weekly)} a week · ${num((l.rate || 0) * 100, 1)}% interest${l.lastPaid ? ` · last paid ${dShort.format(new Date(l.lastPaid))}` : ''}</small></div>
            ${l.amount ? html`<div class="fin-meter" title="${num(100 - (l.remaining / l.amount) * 100)}% paid off"><i style="width:${Math.max(0, 100 - (l.remaining / l.amount) * 100)}%"></i></div>` : ''}</div>`)}</div>` : ''}
        <h3 class="section-title">${icon('book')}Ledger</h3>
        <div class="fin-filter">
          <div class="fin-chips"><button class="on" data-cat="">All</button>${Object.keys(cats).filter((k) => ledger.some((r) => r.cat === k))
            .map((k) => html`<button data-cat="${k}">${cats[k]}</button>`)}</div>
          <label class="search"><span class="search-ico"></span><input type="search" placeholder="Search the ledger" autocomplete="off"></label>
        </div>
        <div class="fin-ledger"></div>`);

      lineChart(body.querySelector('#fin-cash'), ledger);
      monthChart(body.querySelector('#fin-months'), trading);
      splitBars(body.querySelector('#fin-in'), ledger, cats, 'in');
      splitBars(body.querySelector('#fin-out'), ledger, cats, 'out');

      // ---- ledger: newest first, filter + search, 80 at a time
      let cat = '', q = '', shown = 80;
      const list = body.querySelector('.fin-ledger');
      const drawLedger = () => {
        const rows = ledger.filter((r) => (!cat || r.cat === cat) && (!q || r.text.toLowerCase().includes(q))).reverse();
        const net = sum(rows, (r) => r.in - r.out);
        render(list, html`<div class="fin-row head"><span>Date</span><span>Entry</span><span>Amount</span><span>Balance</span></div>
          ${rows.slice(0, shown).map((r) => html`<div class="fin-row">
            <span class="d">${r.at ? dShort.format(new Date(r.at)) : ''}<small>${r.at?.slice(11, 16) || ''}</small></span>
            <span class="t">${r.text}<small>${cats[r.cat] || ''}</small></span>
            <span class="a ${r.in - r.out < 0 ? 'out' : 'in'}">${signed(r.in - r.out)}</span>
            <span class="b">${money(r.balance)}</span></div>`)}
          <div class="fin-foot">${num(rows.length)} entr${rows.length === 1 ? 'y' : 'ies'} · net ${signed(net)}
            ${rows.length > shown ? html`<button class="link-btn" data-more>Show more</button>` : ''}</div>`);
      };
      drawLedger();
      body.querySelector('.fin-chips').addEventListener('click', (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        body.querySelectorAll('.fin-chips button').forEach((x) => x.classList.toggle('on', x === b));
        cat = b.dataset.cat; shown = 80; drawLedger();
      });
      body.querySelector('.fin-filter input').addEventListener('input', (e) => { q = e.target.value.trim().toLowerCase(); shown = 80; drawLedger(); });
      list.addEventListener('click', (e) => { if (e.target.closest('[data-more]')) { shown += 200; drawLedger(); } });
    };
  },
};

function fleetCard(a, fuelRows, db) {
  const name = a.name || 'Aircraft';
  const spent = sum(fuelRows.filter((r) => r.text.slice(r.text.indexOf(':') + 1).trim() === name), (r) => r.out);
  const pct = a.fuelCapacity ? Math.min(100, (a.fuel / a.fuelCapacity) * 100) : null;
  const ap = db.airports[a.location];
  const meter = (label, v, warnBelow) => html`<div class="fin-gauge ${v < warnBelow ? 'warn' : ''}"><span>${label}</span>
    <div class="fin-meter"><i style="width:${Math.max(0, Math.min(100, v))}%"></i></div><b>${num(v, 0)}%</b></div>`;
  return html`<div class="fin-plane">
    <div class="fp-head"><div><b>${name}</b><small>${a.tail || a.livery || ''}</small></div>
      <span class="pill">${icon('pin')}${a.location || '—'}</span></div>
    ${ap ? html`<small class="fp-where">${ap.name}${ap.country?.name ? `, ${ap.country.name}` : ''}</small>` : ''}
    <div class="fin-gauge fuel"><span>Fuel</span><div class="fin-meter"><i style="width:${pct ?? 0}%"></i></div>
      <b>${num(a.fuel)}${a.fuelCapacity ? html`<small> / ${num(a.fuelCapacity)} lb</small>` : ' lb'}</b></div>
    ${meter('Engine', a.engine, 60)}
    ${meter('Hull', a.hull, 60)}
    <div class="fp-foot">
      ${a.hull < 60 || a.engine < 60 ? html`<span class="fin-warn">${icon('feather')}Needs repair</span>` : ''}
      <span>${a.insured ? html`${icon('check')}Insured` : 'Not insured'}</span>
      <span>${num(a.airframeHours, 0)} h airframe</span>
      ${spent ? html`<span>${money(spent)} on fuel</span>` : ''}</div></div>`;
}

// Cash balance: 2px line with a soft fill, crosshair + tooltip on hover.
function lineChart(card, ledger) {
  const pts = ledger.filter((r) => r.at && r.balance != null).map((r) => ({ t: +new Date(r.at), v: r.balance, r }));
  if (pts.length < 2) return;
  const W = Math.max(300, Math.round(card.clientWidth - 36)), H = 210, pad = { l: 46, r: 10, t: 12, b: 22 };
  const t0 = pts[0].t, t1 = pts[pts.length - 1].t;
  const vmax = Math.max(...pts.map((p) => p.v)), vmin = Math.min(0, ...pts.map((p) => p.v));
  const x = (t) => pad.l + (W - pad.l - pad.r) * ((t - t0) / (t1 - t0 || 1));
  const y = (v) => pad.t + (H - pad.t - pad.b) * (1 - (v - vmin) / (vmax - vmin || 1));
  // stepped: the balance holds until the next entry
  let d = `M${x(pts[0].t)},${y(pts[0].v)}`;
  for (let i = 1; i < pts.length; i++) d += ` H${x(pts[i].t)} V${y(pts[i].v)}`;
  const area = `${d} V${y(vmin)} H${x(pts[0].t)} Z`;
  const ticks = [vmax, vmax / 2].map((v) => `<line class="grid" x1="${pad.l}" x2="${W - pad.r}" y1="${y(v)}" y2="${y(v)}"/>
    <text class="axis" x="${pad.l - 6}" y="${y(v) + 3}" text-anchor="end">$${compact(v)}</text>`).join('');
  const months = [];
  for (let m = new Date(new Date(t0).getFullYear(), new Date(t0).getMonth() + 1, 1); +m < t1; m.setMonth(m.getMonth() + 1)) months.push(+m);
  const every = Math.ceil(months.length / 8) || 1;
  card.insertAdjacentHTML('beforeend', `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Cash balance over time">
    <defs><linearGradient id="fin-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#d9b45f" stop-opacity=".32"/><stop offset="1" stop-color="#d9b45f" stop-opacity="0"/></linearGradient></defs>
    ${ticks}<line class="grid" x1="${pad.l}" x2="${W - pad.r}" y1="${y(vmin)}" y2="${y(vmin)}" style="stroke:rgba(255,255,255,.18)"/>
    ${months.filter((_, i) => i % every === 0).map((m) => `<text class="axis" x="${x(m)}" y="${H - 6}" text-anchor="middle">${mShort.format(new Date(m))}</text>`).join('')}
    <path d="${area}" fill="url(#fin-fill)"/><path d="${d}" class="fin-line"/>
    <line class="fin-cross" y1="${pad.t}" y2="${y(vmin)}" hidden/><circle class="fin-dot" r="4.5" hidden/>
    <rect x="${pad.l}" y="${pad.t}" width="${W - pad.l - pad.r}" height="${H - pad.t - pad.b}" fill="transparent"/></svg><div class="chart-tip" hidden></div>`);
  const svg = card.querySelector('svg'), tip = card.querySelector('.chart-tip');
  const cross = svg.querySelector('.fin-cross'), dot = svg.querySelector('.fin-dot');
  svg.addEventListener('mousemove', (e) => {
    const box = svg.getBoundingClientRect(), k = box.width / W;
    const t = t0 + ((e.clientX - box.left) / k - pad.l) / (W - pad.l - pad.r) * (t1 - t0);
    let p = pts[0];
    for (const q of pts) { if (q.t <= t) p = q; else break; }
    const px = x(Math.max(t0, Math.min(t1, t))), py = y(p.v);
    cross.setAttribute('x1', px); cross.setAttribute('x2', px); cross.hidden = false;
    dot.setAttribute('cx', px); dot.setAttribute('cy', py); dot.hidden = false;
    tip.innerHTML = html`<b>${money(p.v)}</b>${dShort.format(new Date(p.t))} · ${p.r.text.length > 42 ? p.r.text.slice(0, 41) + '…' : p.r.text}`.s;
    const cb = card.getBoundingClientRect();
    tip.style.left = `${box.left - cb.left + px * k}px`;
    tip.style.top = `${box.top - cb.top + py * k}px`;
    tip.hidden = false;
  });
  svg.addEventListener('mouseleave', () => { tip.hidden = true; cross.hidden = true; dot.hidden = true; });
}

// Net result per month: bars up from zero in gold, down in blue, value on each end.
function monthChart(card, rows) {
  const by = new Map();
  for (const r of rows) { if (!r.at) continue; const k = r.at.slice(0, 7); by.set(k, (by.get(k) || 0) + r.in - r.out); }
  const data = [...by.entries()].sort().slice(-12);
  if (!data.length) return;
  const W = Math.max(260, Math.round(card.clientWidth - 36)), H = 210, pad = { l: 6, r: 6, t: 18, b: 22 };
  const hi = Math.max(0, ...data.map((d) => d[1])), lo = Math.min(0, ...data.map((d) => d[1]));
  const y = (v) => pad.t + (H - pad.t - pad.b - 14) * (1 - (v - lo) / (hi - lo || 1));
  const step = (W - pad.l - pad.r) / data.length, bw = Math.min(40, step - 6);
  const bars = data.map(([k, v], i) => {
    const x0 = pad.l + step * i + (step - bw) / 2, top = y(Math.max(v, 0)), bot = y(Math.min(v, 0)), h = Math.max(1, bot - top);
    const r = Math.min(4, h / 2, bw / 2), up = v >= 0;
    // rounded only at the data end, square at zero
    const path = up
      ? `M${x0},${bot} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top + r} V${bot} Z`
      : `M${x0},${top} V${bot - r} Q${x0},${bot} ${x0 + r},${bot} H${x0 + bw - r} Q${x0 + bw},${bot} ${x0 + bw},${bot - r} V${top} Z`;
    const label = new Date(k + '-01');
    return `<g class="col" data-tip="${mShort.format(label)} ${k.slice(0, 4)}: ${signed(v)}" data-x="${x0 + bw / 2}" data-y="${up ? top : bot}">
      <rect class="bar-hit" x="${pad.l + step * i}" y="${pad.t}" width="${step}" height="${H - pad.t - pad.b}"/>
      <path class="bar" d="${path}" style="fill:${up ? IN : OUT}"/>
      <text class="val" x="${x0 + bw / 2}" y="${up ? top - 5 : bot + 12}" text-anchor="middle">${v < 0 ? '−' : ''}${compact(Math.abs(v))}</text>
      <text class="axis" x="${x0 + bw / 2}" y="${H - 6}" text-anchor="middle">${mShort.format(label)}</text></g>`;
  }).join('');
  card.insertAdjacentHTML('beforeend', `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Net result per month">
    <line class="grid" x1="${pad.l}" x2="${W - pad.r}" y1="${y(0)}" y2="${y(0)}" style="stroke:rgba(255,255,255,.22)"/>${bars}</svg><div class="chart-tip" hidden></div>`);
  const svg = card.querySelector('svg'), tip = card.querySelector('.chart-tip');
  svg.addEventListener('mousemove', (e) => {
    const g = e.target.closest('g.col');
    if (!g) { tip.hidden = true; return; }
    const box = svg.getBoundingClientRect(), k = box.width / W, cb = card.getBoundingClientRect();
    tip.textContent = g.dataset.tip;
    tip.style.left = `${box.left - cb.left + g.dataset.x * k}px`;
    tip.style.top = `${box.top - cb.top + g.dataset.y * k}px`;
    tip.hidden = false;
  });
  svg.addEventListener('mouseleave', () => (tip.hidden = true));
}

// Money in or out by category: labelled horizontal bars, biggest first.
function splitBars(el, ledger, cats, side) {
  const by = new Map();
  for (const r of ledger) {
    if (NOT_TRADING.has(r.cat) || !r[side]) continue;
    by.set(r.cat, (by.get(r.cat) || 0) + r[side]);
  }
  const rows = [...by.entries()].sort((a, b) => b[1] - a[1]);
  const total = sum(rows, (r) => r[1]) || 1, max = rows[0]?.[1] || 1;
  const left = [...NOT_TRADING].map((k) => [k, sum(ledger.filter((r) => r.cat === k), (r) => r[side])]).filter((x) => x[1]);
  render(el, html`${rows.map(([k, v]) => html`<div class="fin-hbar" title="${cats[k]}: ${money(v)} (${num((v / total) * 100, 1)}%)">
      <span>${cats[k] || k}</span><div><i style="width:${(v / max) * 100}%;background:${raw(side === 'in' ? IN : OUT)}"></i></div>
      <b>$${compact(v)}</b><small>${num((v / total) * 100, 0)}%</small></div>`)}
    <p class="note fin-total">Total ${money(total)}${left.length ? ` · kept apart: ${left.map(([k, v]) => `${cats[k].toLowerCase()} ${money(v)}`).join(', ')}` : ''}</p>`);
}
