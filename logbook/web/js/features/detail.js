// Inspector: the selected leg. Hero picture (your own screenshot if you took one,
// else the destination's Wikipedia photo), route, times, aircraft, landing,
// missions, photos, and Wikipedia about the airports. Other features can add
// sections through the registry (legSections).
import { store } from '../core/store.js';
import { html, raw, render, day, time, duration, num, money, landing, flagUrl } from '../core/format.js';
import { icon, MODE_ICON } from '../core/icons.js';
import { sectionsFor } from './registry.js';

// skip Wikipedia entries that are list/disambiguation pages rather than real articles
const useful = (w) => !!w && !!w.extract && !/may refer to|is the name of several|can refer to/i.test(w.extract);

// navdata runway surface codes
const SURFACE = { A: 'asphalt', B: 'bitumen', C: 'concrete', CE: 'cement', G: 'grass', GR: 'gravel', T: 'tarmac', D: 'dirt',
  W: 'water', S: 'sand', SN: 'snow', I: 'ice', M: 'macadam', OT: 'oil-treated', CR: 'coral', SH: 'shale', TR: 'treated', U: '' };

export default {
  id: 'detail',
  init(ctx) {
    const { db, ui } = ctx;
    const el = document.getElementById('detail');

    const where = (a) => [a.city, a.state, a.country?.name].filter(Boolean).filter((x, i, arr) => arr.indexOf(x) === i).join(', ');
    const end = (a) => html`<div class="end"><div class="code">${a.ident}</div><div class="name">${a.name}</div>
      <div class="where">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}${where(a)}</div></div>`;

    const hero = (l, badge) => {
      const shot = l.photos[0] && db.photos[l.photos[0]];
      const wiki = l.arr.wiki?.image || (useful(l.dep.wiki) && l.dep.wiki.image);
      const src = shot ? shot.src : wiki;
      const cap = shot ? `Your screenshot · ${time(shot.takenAt)}` : wiki ? `${(l.arr.wiki?.image ? l.arr : l.dep).wiki.title} · Wikipedia` : '';
      return html`<div class="hero ${src ? '' : 'empty'}">
        ${src ? html`<img src="${src}" alt="" ${shot ? html`data-photos="${l.photos.join(',')}" data-i="0" style="cursor:zoom-in"` : ''}>` : ''}
        <div class="hero-top"><span class="chip ${badge ? 'warn' : ''}">${badge || (l.kind === 'flight' ? `Flight ${l.number}` : 'Transfer')}</span>
          <button class="close" title="Close (Esc)">${icon('close')}</button></div>
        ${cap ? html`<div class="hero-caption">${cap}</div>` : ''}</div>`;
    };

    const photos = (ids, title) => ids.length ? html`<div class="card"><h4>${title}<small>${ids.length}</small></h4>
      <div class="thumbs">${ids.map((id, i) => html`<button class="thumb" data-photos="${ids.join(',')}" data-i="${i}">
        <img src="${db.photos[id].thumb}" loading="lazy" alt=""><span>${time(db.photos[id].takenAt)}</span></button>`)}</div></div>` : '';

    const wikiCard = (a, heading) => {
      const w = a.wiki;
      if (!useful(w)) return '';
      const label = (xs) => (xs || []).filter((x) => !/^Q\d+$/.test(x)); // drop untranslated Wikidata ids
      const cities = label(w.cities), ops = label(w.operators);
      const surf = SURFACE[(a.surface || '').toUpperCase()] || (a.surface && a.surface.length > 2 ? a.surface.toLowerCase() : '');
      const facts = [
        cities.length && ['Serves', cities.slice(0, 2).join(', ')], w.opened && ['Opened', w.opened],
        ops.length && ['Operator', ops[0]], a.elevationFt != null && ['Elevation', `${num(a.elevationFt)} ft`],
        a.longestRunwayFt && ['Longest runway', `${num(a.longestRunwayFt)} ft${surf ? ' · ' + surf : ''}`],
        a.visits && ['Your visits', `${a.visits}`],
      ].filter(Boolean);
      return html`<div class="card wiki">
        ${heading ? html`<h4>${heading}</h4>` : ''}
        ${w.image ? html`<img class="wiki-img" src="${w.image}" alt="" loading="lazy">` : ''}
        <h3>${w.title}</h3>
        <div class="desc">${w.kind === 'town' ? `No article for the airfield itself, so here's the nearby town` : w.description || ''}</div>
        <p>${w.extract || ''}</p>
        ${facts.length ? html`<div class="facts">${facts.map(([k, v]) => html`<div class="fact"><span>${k}</span><b>${v}</b></div>`)}</div>` : ''}
        <div class="links">${w.extract && w.extract.length > 320 ? html`<button class="link-btn" data-more>Read more</button>` : ''}
          ${w.url ? html`<a class="link-btn" href="${w.url}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div>
      </div>`;
    };

    const flightCard = (l) => {
      const ac = db.aircraft[l.aircraft] || {};
      const land = landing(l.landingFpm, l.crash);
      const b = l.bonus || {};
      const bonuses = [b.comfort && 'Comfort bonus', b.fly && 'Smooth-flying bonus', b.security && 'Safety bonus'].filter(Boolean);
      const badge = l.unlogged ? 'Not in NeoFly log' : l.inferred ? 'Recovered from job log' : '';
      return html`
        ${hero(l, badge)}
        <div class="body">
          <div class="route" style="--c:${l.color}">${end(l.dep)}
            <div class="mid">${icon('plane', 'rot')}<div class="line"></div><small>${duration(l.minutes)}</small></div>${end(l.arr)}</div>
          <div class="tiles">
            <div class="tile"><span>Departed</span><b>${time(l.start)}</b><small>${day(l.start).replace(/ \d{4}$/, '')}</small></div>
            <div class="tile"><span>Arrived</span><b>${time(l.end)}</b><small>${l.unlogged || l.inferred ? 'estimated' : 'local time'}</small></div>
            <div class="tile"><span>Flight time</span><b>${duration(l.minutes)}</b></div>
            <div class="tile"><span>Distance</span><b>${num(l.distanceNm)}</b><small>nm direct</small></div>
          </div>
          <div class="card aircraft" style="--c:${l.color}">
            <div class="ph">${ac.wiki?.image ? html`<img src="${ac.wiki.image}" alt="">` : ''}</div>
            <div><b>${ac.name || 'Unknown aircraft'}</b><small>${[ac.livery && ac.livery !== ac.name && ac.livery].filter(Boolean).join('')}</small>
              <small>${[ac.wiki?.description, ac.cruiseKt && `${ac.cruiseKt} kt cruise`].filter(Boolean).join(' · ')}</small></div>
          </div>
          ${l.evidence?.length ? html`<div class="card"><h4>Why this flight is here</h4>
            <p class="note">NeoFly didn't record this flight, but its own records show you flew it.</p>
            <ul class="evidence">${l.evidence.map((e) => html`<li>${icon('check')}${e}</li>`)}</ul></div>` : ''}
          ${land ? html`<div class="card"><h4>Landing</h4>
            <div class="landing-row"><b>${l.crash ? 'Crash' : html`${num(l.landingFpm)}<small>fpm</small>`}</b><span class="grade ${land.tone}">${land.label}</span></div>
            <div class="meter"><i style="left:${Math.round(land.pct * 100)}%"></i></div>
            <div class="meter-scale"><span>Butter</span><span>Firm</span><span>Hard</span></div>
            ${bonuses.length ? html`<div class="tags">${bonuses.map((x) => html`<span class="tag gold">${x}</span>`)}</div>` : ''}</div>` : ''}
          ${l.missions.length ? html`<div class="card"><h4>Mission${l.missions.length > 1 ? 's' : ''}</h4>
            ${l.missions.map((m) => html`<div class="mission ${m.status}"><div><b>${m.type}</b>
              <small>${[m.pax && `${m.pax} passenger${m.pax > 1 ? 's' : ''}`, m.cargoLbs && `${num(m.cargoLbs)} lb`, `${m.from} → ${m.to}`].filter(Boolean).join(' · ')}</small></div>
              <span class="money">${m.status === 'completed' ? money(m.reward) : m.status}</span></div>`)}</div>` : ''}
          ${photos(l.photos, 'Your photos')}
          ${stopCard(l)}
          ${ui.diaryPreview?.(db.stopById.get(`stop-${l.id}`)) || ''}
          ${wikiCard(l.arr, l.local ? 'About the airport' : `About ${l.arr.ident}`)}
          ${!l.local && useful(l.dep.wiki) ? html`<details class="more"><summary>About ${l.dep.ident}, where you departed</summary>${wikiCard(l.dep)}</details>` : ''}
          <div class="extra"></div>
          ${pager(l)}
        </div>`;
    };

    const groundCard = (l) => html`
      ${hero(l, l.modeLabel)}
      <div class="body">
        <div class="route" style="--c:#fff">${end(l.dep)}
          <div class="mid">${icon(MODE_ICON[l.mode] || 'pin')}<div class="line"></div><small>${l.modeLabel}</small></div>${end(l.arr)}</div>
        <div class="tiles">
          <div class="tile"><span>Distance</span><b>${num(l.distanceKm)}</b><small>km</small></div>
          <div class="tile"><span>Travel</span><b>${l.mode === 'reposition' ? '—' : duration(l.estimatedMinutes)}</b><small>${l.mode === 'reposition' ? 'no travel' : 'estimated'}</small></div>
          <div class="tile"><span>Left</span><b>${time(l.start)}</b><small>${day(l.start).replace(/ \d{4}$/, '')}</small></div>
          <div class="tile"><span>Next flight</span><b>${time(l.end)}</b><small>${day(l.end).replace(/ \d{4}$/, '')}</small></div>
        </div>
        <div class="card"><h4>What happened here</h4>
          ${l.mode === 'reposition' ? '' : html`<p class="note">None of your aircraft made this trip, so a ${l.modeLabel.toLowerCase()} links the journey. You had ${duration(l.minutes)} between flights.</p>`}
          ${l.notes.map((n) => html`<p class="note">${n}</p>`)}</div>
        ${photos(l.photos, 'Your photos')}
        ${wikiCard(l.arr, `About ${l.arr.ident}`)}
        <div class="extra"></div>
        ${pager(l)}
      </div>`;

    const stopCard = (l) => {
      const s = db.stopById.get(`stop-${l.id}`);
      if (!s || (!s.photos.length && !s.events.length)) return '';
      return html`<div class="card"><h4>On the ground at ${s.airport}</h4>
        ${s.events.map((e) => html`<p class="note">${e.text}${e.cost ? ` · ${money(e.cost)}` : ''}</p>`)}
        ${s.photos.length ? html`<div class="thumbs" style="margin-top:8px">${s.photos.map((id, i) => html`<button class="thumb" data-photos="${s.photos.join(',')}" data-i="${i}">
          <img src="${db.photos[id].thumb}" loading="lazy" alt=""><span>${time(db.photos[id].takenAt)}</span></button>`)}</div>` : ''}</div>`;
    };

    const pager = (l) => {
      const prev = db.legs[l.index - 1], next = db.legs[l.index + 1];
      return html`<nav class="pager">
        <button data-go="${prev?.id || ''}" ${prev ? '' : 'disabled'}>${icon('back')}${prev ? `${prev.from} – ${prev.to}` : 'Start'}</button>
        <button data-go="${next?.id || ''}" ${next ? '' : 'disabled'}>${next ? `${next.from} – ${next.to}` : 'Latest'}${icon('forward')}</button></nav>`;
    };

    const show = (id) => {
      const l = id && db.legById.get(id);
      document.body.classList.toggle('has-detail', !!l);
      if (!l) return;
      render(el, l.kind === 'flight' ? flightCard(l) : groundCard(l));
      const extra = el.querySelector('.extra');
      for (const s of sectionsFor('legSections', l, ctx)) {
        const card = document.createElement('div');
        card.className = 'card';
        if (s.title) card.innerHTML = `<h4>${s.title}</h4>`;
        card.append(s.el);
        extra.append(card);
      }
      el.scrollTop = 0;
    };

    el.addEventListener('click', (e) => {
      const t = e.target.closest('button, img[data-photos]');
      if (!t) return;
      if (t.classList.contains('close')) store.set('selected', null);
      else if (t.dataset.go) store.set('selected', t.dataset.go);
      else if (t.dataset.diary) ui.openDiary(t.dataset.diary);
      else if (t.dataset.photos) ui.openPhotos(t.dataset.photos.split(','), +t.dataset.i);
      else if (t.dataset.more !== undefined) { const w = t.closest('.wiki'); w.classList.toggle('open'); t.textContent = w.classList.contains('open') ? 'Show less' : 'Read more'; }
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
