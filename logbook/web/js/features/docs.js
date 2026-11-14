// Documents on a flight: SimBrief plans (archived automatically) and plan files you
// saved yourself. Shown as a "Documents" card on the flight (click the route line
// or the list row), with the full briefing - route, fuel, weights, navlog - on tap.
import { html, render, num } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet } from '../core/sheet.js';
import { register } from './registry.js';

const hm = (s) => (s ? `${Math.floor(s / 3600)}h ${String(Math.round((s % 3600) / 60)).padStart(2, '0')}m` : '—');

export default {
  id: 'docs',
  init({ db, ui }) {
    const briefing = (l, o) => {
      const { body } = openSheet({ id: 'briefing', title: `${o.callsign || 'Flight plan'} · ${o.origin} → ${o.destination}`, cls: 'brief-sheet',
        sub: `SimBrief briefing · ${o.aircraft || ''}${o.reg ? ` (${o.reg})` : ''} · planned ${o.out ? o.out.replace('T', ' ') + ' UTC' : ''}` });
      const u = o.units || '';
      render(body, html`<div class="brief">
        ${o.map ? html`<img class="brief-map" src="${o.map}" alt="Route map">` : ''}
        <div class="brief-route"><span>Route</span><code>${o.origin} ${o.route || ''} ${o.destination}</code></div>
        <div class="facts brief-facts">${[['Cruise', o.cruise ? `FL${String(Math.round(o.cruise / 100)).padStart(3, '0')}` : null],
          ['Distance', o.distance ? `${num(o.distance)} nm` : null], ['Time en route', hm(o.ete)], ['Alternate', o.alternate],
          ['Block fuel', o.blockFuel ? `${num(o.blockFuel)} ${u}` : null], ['Trip fuel', o.tripFuel ? `${num(o.tripFuel)} ${u}` : null],
          ['Reserve', o.reserve ? `${num(o.reserve)} ${u}` : null], ['Cost index', o.costIndex],
          ['ZFW', o.zfw ? `${num(o.zfw)} ${u}` : null], ['TOW', o.tow ? `${num(o.tow)} ${u}` : null], ['LDW', o.ldw ? `${num(o.ldw)} ${u}` : null],
          ['Passengers', o.pax], ['Cargo', o.cargo ? `${num(o.cargo)} ${u}` : null], ['Avg wind', o.windComp ? `${o.windComp} kt` : null]]
          .filter(([, v]) => v != null && v !== '').map(([k, v]) => html`<div class="fact"><span>${k}</span><b>${v}</b></div>`)}</div>
        ${o.navlog?.length ? html`<h4>Navlog</h4><div class="navlog"><table><thead><tr><th>Fix</th><th>Via</th><th>Alt</th><th>Wind</th><th>Dist</th><th>Time</th></tr></thead>
          <tbody>${o.navlog.map((f) => html`<tr><td>${f.ident}</td><td>${f.via || ''}</td><td>${f.alt || ''}</td><td>${f.wind}</td><td>${f.dist || ''}</td><td>${f.time ? hm(+f.time) : ''}</td></tr>`)}</tbody></table></div>` : ''}
        <div class="links">${o.pdf ? html`<a class="link-btn" href="${o.pdf}" target="_blank" rel="noopener">${icon('doc')}Open the OFP (PDF)</a>` : ''}</div>
      </div>`);
    };
    ui.openBriefing = (legId, i = 0) => {
      const l = db.legById.get(legId);
      const o = (l?.docs || []).filter((d) => d.kind === 'simbrief')[i];
      if (o) briefing(l, o);
    };

    register({
      id: 'docs-section',
      legSections(l) {
        if (!l.docs?.length) return [];
        const el = document.createElement('div');
        el.className = 'docs';
        render(el, html`${l.docs.map((d, i) => d.kind === 'simbrief'
          ? html`<button class="doc-card" data-brief="${l.id}" data-i="${l.docs.filter((x) => x.kind === 'simbrief').indexOf(d)}">
              <span class="doc-ico">${icon('doc')}</span><div><b>SimBrief plan · ${d.callsign || `${d.origin}-${d.destination}`}</b>
              <small>${[d.cruise ? `FL${String(Math.round(d.cruise / 100)).padStart(3, '0')}` : null, d.distance ? `${num(d.distance)} nm` : null,
                        d.blockFuel ? `${num(d.blockFuel)} ${d.units || ''} block` : null].filter(Boolean).join(' · ')}</small></div>${icon('forward')}</button>`
          : html`<a class="doc-card" href="${d.file}" target="_blank" rel="noopener"><span class="doc-ico">${icon('doc')}</span>
              <div><b>${d.title}</b><small>Saved plan file</small></div>${icon('external')}</a>`)}`);
        el.addEventListener('click', (e) => {
          const b = e.target.closest('[data-brief]');
          if (b) ui.openBriefing(b.dataset.brief, +b.dataset.i);
        });
        return [{ title: 'Documents', el }];
      },
    });
  },
};
