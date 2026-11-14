// Right panel: a boarding-pass style card for the selected leg, with times,
// distance, aircraft, landing rate, missions, photos, the stop that followed,
// and any sections other features register (scrapbook etc.).
import { store } from '../core/store.js';
import { html, raw, render, day, time, duration, num, money, landing, flagUrl, compact } from '../core/format.js';
import { sectionsFor } from './registry.js';

export default {
  id: 'detail',
  init(ctx) {
    const { db, ui } = ctx;
    const el = document.getElementById('detail');

    const place = (a) => html`
      <div class="place">
        <div class="code">${a.ident}</div>
        <div class="name">${a.name}</div>
        <div class="where">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}${[a.city, a.state, a.country?.name].filter(Boolean).filter((x, i, arr) => arr.indexOf(x) === i).join(', ')}</div>
      </div>`;

    const photosBlock = (ids, title = 'Photos') => ids.length ? html`
      <section><h4>${title} <small>${ids.length}</small></h4>
        <div class="thumbs">${ids.map((id, i) => html`<button class="thumb" data-photos="${ids.join(',')}" data-i="${i}">
          <img src="${db.photos[id].thumb}" loading="lazy" alt=""><span>${time(db.photos[id].takenAt)}</span></button>`)}</div>
      </section>` : '';

    const flightCard = (l) => {
      const ac = db.aircraft[l.aircraft] || {};
      const land = landing(l.landingFpm, l.crash);
      const b = l.bonus || {};
      const bonuses = [b.comfort && 'Comfort', b.fly && 'Smooth flying', b.security && 'Safety'].filter(Boolean);
      return html`
        <div class="pass" style="--leg:${l.color}">
          <div class="pass-top">
            <span>Flight ${l.number} · ${day(l.start)}</span>
            ${l.inferred ? html`<span class="badge" title="NeoFly completed this job but wrote no flight-log row; times are estimated from the job.">recovered</span>` : ''}
          </div>
          <div class="pass-route">
            ${place(l.dep)}
            <div class="pass-mid">
              <svg viewBox="0 0 24 24"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>
              <div class="dash"></div>
              <small>${duration(l.minutes)}</small>
            </div>
            ${place(l.arr)}
          </div>
          <div class="pass-grid">
            <div><span>Departed</span><b>${time(l.start)}</b></div>
            <div><span>Arrived</span><b>${time(l.end)}</b></div>
            <div><span>Block time</span><b>${duration(l.minutes)}</b></div>
            <div><span>Distance</span><b>${num(l.distanceNm)} nm</b></div>
          </div>
          <div class="pass-ac">
            <i style="background:${l.color}"></i>
            <div><b>${ac.name || 'Unknown aircraft'}</b><small>${[ac.livery !== ac.name && ac.livery, ac.category, ac.cruiseKt && `${ac.cruiseKt} kt cruise`].filter(Boolean).join(' · ')}</small></div>
          </div>
        </div>
        ${land ? html`<section><h4>Landing</h4>
          <div class="landing ${land.tone}"><b>${l.crash ? 'CRASH' : `${num(l.landingFpm)} fpm`}</b><span>${land.label}</span></div>
          <div class="meter"><i style="left:calc(${Math.round(land.pct * 100)}% - 2px)"></i></div>
          ${bonuses.length ? html`<div class="tags">${bonuses.map((x) => html`<span class="tag">★ ${x} bonus</span>`)}</div>` : ''}
        </section>` : ''}
        ${l.missions.length ? html`<section><h4>Mission${l.missions.length > 1 ? 's' : ''}</h4>
          ${l.missions.map((m) => html`<div class="mission ${m.status}">
            <div><b>${m.type}</b><small>${m.from} → ${m.to}</small></div>
            <div class="mission-meta">${m.pax ? html`<span>👤 ${m.pax}</span>` : ''}${m.cargoLbs ? html`<span>📦 ${num(m.cargoLbs)} lb</span>` : ''}
              <span class="money">${m.status === 'completed' ? money(m.reward) : m.status}</span></div>
          </div>`)}
        </section>` : ''}
        ${photosBlock(l.photos, 'Photos from this flight')}`;
    };

    const groundCard = (l) => html`
      <div class="pass ground">
        <div class="pass-top"><span>Transfer · ${day(l.start)}</span><span class="badge" title="NeoFly has no record of how you got here, so this leg links the journey up. Change the mode in overrides.json.">${l.auto ? 'auto-linked' : 'edited'}</span></div>
        <div class="pass-route">
          ${place(l.dep)}
          <div class="pass-mid"><div class="mode-big">${l.icon}</div><div class="dash"></div><small>${l.modeLabel}</small></div>
          ${place(l.arr)}
        </div>
        <div class="pass-grid">
          <div><span>Distance</span><b>${num(l.distanceKm)} km</b></div>
          <div><span>Est. travel</span><b>${duration(l.estimatedMinutes)}</b></div>
          <div><span>Left</span><b>${time(l.start)}</b><small>${day(l.start)}</small></div>
          <div><span>Next flight</span><b>${time(l.end)}</b><small>${day(l.end)}</small></div>
        </div>
      </div>
      <section><p class="note">The flight log jumps from <b>${l.from}</b> to <b>${l.to}</b>, so this ${l.modeLabel.toLowerCase()} connection links the journey (${duration(l.minutes)} between flights).</p>
        ${l.notes.map((n) => html`<p class="note">${n}</p>`)}</section>
      ${photosBlock(l.photos)}`;

    const stopBlock = (l) => {
      const s = db.stopById.get(`stop-${l.id}`);
      if (!s || (!s.photos.length && !s.events.length)) return '';
      return html`<section class="stop"><h4>On the ground at ${s.airport}</h4>
        ${s.events.map((e) => html`<p class="note">${e.text}${e.cost ? ` · ${money(e.cost)}` : ''}</p>`)}
        ${photosBlock(s.photos, 'Photos at ' + s.airport)}</section>`;
    };

    const show = (id) => {
      const l = id && db.legById.get(id);
      document.body.classList.toggle('has-detail', !!l);
      if (!l) { el.innerHTML = ''; return; }
      const prev = db.legs[l.index - 1], next = db.legs[l.index + 1];
      render(el, html`
        <button class="close" title="Close (Esc)">✕</button>
        ${l.kind === 'flight' ? flightCard(l) : groundCard(l)}
        ${stopBlock(l)}
        <div class="extra"></div>
        <nav class="pager">
          <button data-go="${prev?.id || ''}" ${prev ? '' : 'disabled'}>← ${prev ? `${prev.from}–${prev.to}` : ''}</button>
          <button data-go="${next?.id || ''}" ${next ? '' : 'disabled'}>${next ? `${next.from}–${next.to}` : ''} →</button>
        </nav>`);
      const extra = el.querySelector('.extra');
      for (const s of sectionsFor('legSections', l, ctx)) {
        const sec = document.createElement('section');
        if (s.title) sec.innerHTML = `<h4>${s.title}</h4>`;
        sec.append(s.el);
        extra.append(sec);
      }
      el.scrollTop = 0;
    };

    el.addEventListener('click', (e) => {
      const t = e.target.closest('button');
      if (!t) return;
      if (t.classList.contains('close')) store.set('selected', null);
      else if (t.dataset.go) store.set('selected', t.dataset.go);
      else if (t.dataset.photos) ui.openPhotos(t.dataset.photos.split(','), +t.dataset.i);
    });
    document.addEventListener('keydown', (e) => {
      if (e.target.matches('input') || document.body.classList.contains('lightbox-open')) return;
      const cur = db.legById.get(store.get('selected'));
      if (e.key === 'Escape') store.set('selected', null);
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); store.set('selected', db.legs[cur ? Math.min(db.legs.length - 1, cur.index + 1) : 0].id); }
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); store.set('selected', db.legs[cur ? Math.max(0, cur.index - 1) : 0].id); }
    });
    store.on('selected', show);
  },
};
