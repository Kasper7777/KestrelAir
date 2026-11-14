// Aircraft dossier: tap an aircraft (Fleet tab, or the aircraft card on a flight)
// for the real thing - Wikipedia history, Wikidata specifications, real photos,
// any manuals for it found on this PC, and your own record in it.
import { html, raw, render, duration, num, compact, day } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';
import { store } from '../core/store.js';
import { typeCode, registration, planeSvg } from '../core/planes.js';

export default {
  id: 'aircraft',
  init({ db, ui }) {
    ui.openAircraft = (id) => {
      const a = db.aircraft[id];
      if (!a) return;
      const d = a.dossier || {};
      const legs = db.flights.filter((l) => l.aircraft === id);
      const landed = legs.filter((l) => l.landingFpm < 0);
      const best = landed.reduce((x, y) => (!x || y.landingFpm > x.landingFpm ? y : x), null);
      const longest = legs.reduce((x, y) => (!x || y.minutes > x.minutes ? y : x), null);
      const airports = new Set(legs.flatMap((l) => [l.from, l.to]));
      // lead with a photo of the whole aircraft, not an engine or cockpit close-up
      const detail = /engine|cockpit|interior|panel|instrument|wheel|detail|cabin|seat|nacelle|propeller/i;
      const photos = [...(d.photos || [])].sort((x, y) => detail.test(x.credit || '') - detail.test(y.credit || ''));
      const { body } = openSheet({ id: 'aircraft', title: a.name, cls: 'dossier-sheet',
        sub: [a.livery && a.livery !== a.name ? a.livery : null, typeCode(a), registration(a)].filter(Boolean).join(' · ') });
      render(body, html`
        <div class="dossier">
          <div class="ds-hero">
            ${photos[0] ? html`<img src="${photos[0].src}" alt="">` : ''}
            <div class="ds-hero-glass glass-soft">
              <span class="ds-sil" style="color:${a.color}">${raw(planeSvg(a))}</span>
              <div><b>${d.title || a.name}</b><small>${a.wiki?.description || a.category || ''}</small></div>
            </div>
          </div>
          <div class="ds-grid">
            <section class="ds-col">
              <h4>Your record</h4>
              <div class="ds-stats">
                <div><b>${legs.length}</b><span>flights</span></div>
                <div><b>${duration(a.minutes)}</b><span>flown</span></div>
                <div><b>${compact(a.nm)}</b><span>nm</span></div>
                <div><b>${airports.size}</b><span>airports</span></div>
              </div>
              <ul class="ds-facts">
                ${longest ? html`<li><span>Longest flight</span><button data-leg="${longest.id}">${longest.from} → ${longest.to} · ${duration(longest.minutes)}</button></li>` : ''}
                ${best ? html`<li><span>Softest landing</span><button data-leg="${best.id}">${num(best.landingFpm)} fpm at ${best.to}</button></li>` : ''}
                ${a.acquired ? html`<li><span>In your hangar since</span><b>${day(a.acquired)}</b></li>` : ''}
                ${a.price ? html`<li><span>Paid</span><b>$${num(a.price)}</b></li>` : ''}
                ${a.cruiseKt ? html`<li><span>Cruise (NeoFly)</span><b>${a.cruiseKt} kt</b></li>` : ''}
                ${a.seats ? html`<li><span>Seats (NeoFly)</span><b>${a.seats}</b></li>` : ''}
              </ul>
              ${d.specs?.length ? html`<h4>Specifications <small>Wikidata</small></h4>
                <ul class="ds-facts">${d.specs.map((s) => html`<li><span>${s.label}</span><b>${s.value}</b></li>`)}</ul>` : ''}
              <h4>Manuals <small>${a.manuals?.length ? 'found on this PC' : ''}</small></h4>
              ${a.manuals?.length ? html`<div class="ds-books">${a.manuals.map((m) => html`<a class="ds-book" href="/__manual/${m.id}" target="_blank" rel="noopener">
                  <span class="spine" style="--c:${a.color}"></span><div><b>${m.title}</b><small>PDF · ${m.mb} MB</small></div>${icon('external')}</a>`)}</div>`
                : html`<p class="note">No manuals for this aircraft on this PC yet. Drop a PDF anywhere in Downloads or Documents (with the aircraft's name in the file name) and it'll appear here.</p>`}
            </section>
            <section class="ds-col">
              <h4>History <small>Wikipedia</small></h4>
              <div class="ds-history">${(d.history || []).map((p) => html`<p>${p}</p>`)}</div>
              ${d.url ? html`<a class="link-btn" href="${d.url}" target="_blank" rel="noopener">Read the full article ${icon('external')}</a>` : ''}
              ${photos.length > 1 ? html`<h4>Photos</h4><div class="ds-photos">${photos.slice(1).map((p) => html`<a href="${p.credit || p.src}" target="_blank" rel="noopener"><img src="${p.src}" alt="" loading="lazy"></a>`)}</div>` : ''}
            </section>
          </div>
        </div>`);
      body.addEventListener('click', (e) => {
        const b = e.target.closest('[data-leg]');
        if (b) { closeSheet(); store.set('selected', b.dataset.leg); }
      });
    };
  },
};
