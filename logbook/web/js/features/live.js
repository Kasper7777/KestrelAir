// Live: what's flying right now, read on demand from what NeoFly already keeps
// (the jobs on your plane, NeoFly's own track while it follows a flight, your hired
// pilots' positions). Nothing is recorded - this only looks while the page is open.
//
// The server answers /__live with flights in one shape (see pipeline/live.py), so a
// future source - e.g. reading the simulator directly, with no NeoFly and no mission -
// shows up here without changes. Every field may be missing; nothing here assumes one.
//
//   map:      the route ahead (dashed), the track flown (glowing), a pulsing aircraft
//   pill:     "Live" capsule under the toolbar - click to fly to it / cycle flights
//   timeline: a "Now" mark after the last logged leg
//   card:     pilot, aircraft, mission, altitude, speed, progress, time to go
import { html, render, num } from '../core/format.js';
import { icon } from '../core/icons.js';
import { greatCircle, kmBetween, bearing } from '../core/geo.js';
import { planeSvg } from '../core/planes.js';
import { store } from '../core/store.js';

const POLL_MS = 10000;
const empty = { type: 'FeatureCollection', features: [] };

export default {
  id: 'live',
  init({ db, map, ui }) {
    const M = map.map;
    let flights = [], focusIdx = 0, timer = 0, failures = 0, card = null, following = null;
    const markers = new Map();

    // ---------- helpers (all tolerant of missing data)
    const pt = (p) => (p && Number.isFinite(p.lon) && Number.isFinite(p.lat) ? [p.lon, p.lat] : null);
    const endPt = (e) => {
      if (!e) return null;
      const direct = pt(e);
      if (direct) return direct;
      const a = e.ident && db.airports[e.ident];
      return a && Number.isFinite(a.lon) ? [a.lon, a.lat] : null;
    };
    const posOf = (f) => pt(f.position) || (f.track?.length ? f.track[f.track.length - 1] : null) || (f.status === 'planned' ? endPt(f.from) : null);
    const nm = (a, b) => (a && b ? kmBetween(a, b) / 1.852 : null);
    const acOf = (f) => (f.aircraft?.hangarId != null && db.aircraft[`neofly:${f.aircraft.hangarId}`]) || { name: f.aircraft?.name };
    const headingOf = (f, here) => {
      if (Number.isFinite(f.position?.heading)) return f.position.heading;      // straight from the sim
      const t = f.track || [];
      if (t.length > 1) return bearing(t[t.length - 2], t[t.length - 1]);
      const to = endPt(f.to);
      return here && to ? bearing(here, to) : 0;
    };
    const progress = (f) => {
      const a = endPt(f.from), b = endPt(f.to), here = posOf(f);
      if (!a || !b || !here || f.status === 'planned') return f.status === 'planned' ? 0 : null;
      const done = nm(a, here), left = nm(here, b);
      return done + left > 0 ? Math.max(0, Math.min(1, done / (done + left))) : null;
    };
    // the airport a sim flight started from (nearest known airport within 15 km of where the trail began)
    const nearestIdent = (p) => {
      if (!p) return null;
      let best = null, bd = 15;
      for (const a of Object.values(db.airports)) {
        if (!Number.isFinite(a.lon)) continue;
        const d = kmBetween(p, [a.lon, a.lat]);
        if (d < bd) { bd = d; best = a.ident; }
      }
      return best;
    };
    const fromIdent = (f) => f.from?.ident || nearestIdent(endPt(f.from));
    const label = (f) => `${fromIdent(f) || '…'} → ${f.to?.ident || (f.status === 'planned' ? '…' : f.status === 'ground' ? 'on the ground' : 'en route')}`;
    const statusText = (f) => (f.status === 'planned' ? 'Mission loaded - ready to go' : f.status === 'stale' ? 'No update for a while (paused?)'
      : f.who === 'hired' ? 'Hired pilot in the air' : f.status === 'ground' ? 'On the ground' : f.source === 'sim' ? 'Live from Flight Simulator' : 'In the air');
    const vsArrow = (vs) => (!Number.isFinite(vs) || Math.abs(vs) < 150 ? '' : vs > 0 ? ` ↑${num(Math.round(vs / 10) * 10)}` : ` ↓${num(Math.round(-vs / 10) * 10)}`);
    // glide a marker to its new spot instead of jumping (updates arrive every few seconds)
    // point the icon along the aircraft's TRUE heading as it appears on screen: project the aircraft and a
    // spot 1 km ahead along its heading, and aim at that. Correct on a globe (even near the poles), tilted
    // or turned - moving the camera never changes which way the aircraft points.
    const ahead = ([lon, lat], hdg, km = 1) => {
      const r = (hdg * Math.PI) / 180, dLat = (km / 111.2) * Math.cos(r);
      const dLon = ((km / 111.2) * Math.sin(r)) / Math.max(0.01, Math.cos((lat * Math.PI) / 180));
      return [lon + dLon, Math.max(-89.9, Math.min(89.9, lat + dLat))];
    };
    const orient = (m) => {
      if (!Number.isFinite(m.heading)) return;
      const p = m.marker.getLngLat().toArray();
      const a = M.project(p), b = M.project(ahead(p, m.heading));
      if (!Number.isFinite(b.x) || Math.hypot(b.x - a.x, b.y - a.y) < 1e-6) return;
      m.marker.setRotation((Math.atan2(b.x - a.x, -(b.y - a.y)) * 180) / Math.PI);
    };
    M.on('move', () => { for (const m of markers.values()) orient(m); });
    const glide = (m, to) => {
      cancelAnimationFrame(m.raf);
      const from = m.marker.getLngLat().toArray(), t0 = performance.now(), D = 1800;
      if (Math.abs(from[0] - to[0]) > 1 || Math.abs(from[1] - to[1]) > 1) { m.marker.setLngLat(to); m.tag?.setLngLat(to); return; }
      const step = (now) => {
        const x = Math.min(1, (now - t0) / D), e = 1 - (1 - x) ** 2;
        const p = [from[0] + (to[0] - from[0]) * e, from[1] + (to[1] - from[1]) * e];
        m.marker.setLngLat(p);
        m.tag?.setLngLat(p);
        orient(m);
        if (x < 1) m.raf = requestAnimationFrame(step);
      };
      m.raf = requestAnimationFrame(step);
    };

    // ---------- map layers (re-added if the basemap changes)
    const addLayers = () => {
      if (!M.getStyle() || M.getSource('live')) return;
      M.addSource('live', { type: 'geojson', data: empty, lineMetrics: true });
      // the way ahead: a faint, solid thread to the destination
      M.addLayer({ id: 'live-ahead', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'ahead'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#f6ebc8', 'line-width': 1.6, 'line-opacity': 0.35, 'line-blur': 0.5 } });
      // the whole way since departure as ONE glass line: soft at the start, brightening smoothly
      // all the way to the aircraft (no seams, no dashes)
      M.addLayer({ id: 'live-glow', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'flown'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-width': 16, 'line-blur': 10,
          'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, 'rgba(217,180,95,0.15)', 0.7, 'rgba(217,180,95,0.4)', 1, 'rgba(232,205,140,0.7)'] } });
      M.addLayer({ id: 'live-flown', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'flown'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-width': 4,
          'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, 'rgba(240,220,164,0.55)', 0.6, 'rgba(244,228,182,0.85)', 1, 'rgba(255,250,235,1)'] } });
      M.addLayer({ id: 'live-shine', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'flown'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-width': 1.2, 'line-offset': -0.8, 'line-blur': 0.3,
          'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, 'rgba(255,255,255,0.2)', 1, 'rgba(255,255,255,0.85)'] } });
      draw();
    };

    function draw() {
      const feats = [];
      for (const f of flights) {
        const here = posOf(f), to = endPt(f.to), from = endPt(f.from);
        // one line: departure -> (before the logbook was open) -> the live trail -> the aircraft now
        if (f.status !== 'planned') {
          const first = f.track?.[0] || here;
          const before = from && first && kmBetween(from, first) > 2 ? greatCircle(from, first).slice(0, -1) : [];
          const line = [...before, ...(f.track || []), ...(here ? [here] : [])];
          if (line.length > 1) feats.push({ type: 'Feature', properties: { part: 'flown' }, geometry: { type: 'LineString', coordinates: line } });
        }
        const start = f.status === 'planned' ? from : here;
        if (start && to && kmBetween(start, to) > 1) feats.push({ type: 'Feature', properties: { part: 'ahead' }, geometry: { type: 'LineString', coordinates: greatCircle(start, to) } });
      }
      M.getSource('live')?.setData({ type: 'FeatureCollection', features: feats });

      // aircraft markers: one per flight, updated in place
      const seen = new Set();
      for (const f of flights) {
        const here = posOf(f);
        if (!here) continue;
        seen.add(f.id);
        let m = markers.get(f.id);
        if (!m) {
          // the aircraft is pinned to the map's surface (rotationAlignment 'map'), so it points along its
          // true heading however the globe is turned or tilted - MapLibre does the maths, not us.
          // The label is a separate marker that stays upright and readable.
          const el = document.createElement('div');
          el.className = 'live-marker';
          el.innerHTML = `<span class="lm-ring"></span><span class="lm-plane"></span>`;
          el.addEventListener('click', (e) => { e.stopPropagation(); store.set('selected', 'live'); });
          const tagEl = document.createElement('div');
          tagEl.className = 'live-tag';
          tagEl.innerHTML = '<span class="lm-tag"></span>';
          tagEl.addEventListener('click', (e) => { e.stopPropagation(); store.set('selected', 'live'); });
          m = { el, tagEl, shape: null,
            marker: new maplibregl.Marker({ element: el, rotationAlignment: 'viewport', pitchAlignment: 'viewport' }).setLngLat(here).addTo(M),
            tag: new maplibregl.Marker({ element: tagEl, anchor: 'top', offset: [0, 26] }).setLngLat(here).addTo(M) };
          markers.set(f.id, m);
        }
        const ac = acOf(f);
        const shape = `${ac.name}|${f.who}`;
        if (m.shape !== shape) { m.el.querySelector('.lm-plane').innerHTML = planeSvg(ac); m.shape = shape; }
        m.el.classList.toggle('planned', f.status === 'planned');
        m.el.classList.toggle('stale', f.status === 'stale');
        m.el.classList.toggle('hired', f.who === 'hired');
        m.heading = headingOf(f, here);
        orient(m);
        const alt = f.position?.alt, spd = f.position?.speed;
        m.tagEl.classList.toggle('ground', f.status === 'ground');
        m.tagEl.querySelector('.lm-tag').textContent = f.status === 'planned' ? `Ready · ${label(f)}` : f.status === 'ground' ? `On the ground${spd > 3 ? ` · ${num(spd)} kt` : ''}`
          : [f.who === 'hired' ? (f.pilot || 'Hired pilot') : 'Live', alt != null ? `${num(alt)} ft${vsArrow(f.position?.vs)}` : '', spd != null ? `${num(spd)} kt` : ''].filter(Boolean).join(' · ');
        m.el.classList.toggle('ground', f.status === 'ground');
        glide(m, here);
        if (following === f.id) M.easeTo({ center: here, duration: 1800, easing: (x) => x });
      }
      for (const [id, m] of markers) if (!seen.has(id)) { m.marker.remove(); m.tag.remove(); markers.delete(id); }
      drawPill();
      drawNow();
      updateHandle();
      refreshLivePanel();
      if (card) openCard(card.dataset.id, true);
    }

    // ---------- the Live pill under the toolbar
    const pill = document.createElement('button');
    pill.id = 'livepill';
    pill.className = 'live-pill';
    pill.hidden = true;
    document.body.append(pill);
    function drawPill() {
      const live = flights.filter((f) => posOf(f));
      if (!live.length) { pill.hidden = true; return; }
      const f = live[focusIdx % live.length];
      const p = progress(f);
      render(pill, html`<span class="lp-dot ${f.status}"></span><b>${f.status === 'planned' ? 'Ready' : 'Live'}</b>
        <span>${label(f)}${acOf(f).name ? ` · ${acOf(f).name}` : ''}</span>
        ${p != null && f.status !== 'planned' ? html`<i class="lp-bar"><i style="width:${Math.round(p * 100)}%"></i></i>` : ''}
        ${live.length > 1 ? html`<em>${focusIdx % live.length + 1}/${live.length}</em>` : ''}`);
      pill.dataset.id = f.id;
      pill.hidden = false;
    }
    pill.addEventListener('click', () => {
      const live = flights.filter((f) => posOf(f));
      if (!live.length) return;
      const f = live[focusIdx % live.length];
      focus(f);
      store.set('selected', 'live');
      if (live.length > 1) focusIdx++;
    });
    function focus(f) {
      const here = posOf(f), to = endPt(f.to);
      ui.stopPlayback?.();
      if (here && to && kmBetween(here, to) > 5) {
        const lons = [here[0], to[0]], lats = [here[1], to[1]];
        M.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: ui.padding(), maxZoom: 8, duration: 1400 });
      } else if (here) M.flyTo({ center: here, zoom: Math.max(M.getZoom(), 7), duration: 1400 });
    }

    // ---------- "Now" on the timeline, after the last logged leg
    function drawNow() {
      const segs = ui.timelineSegs?.();
      if (!segs) return;
      let now = segs.querySelector('.seg.live');
      const live = flights.filter((f) => posOf(f));
      if (!live.length) { now?.remove(); return; }
      if (!now) {
        now = document.createElement('button');
        now.className = 'seg live';
        now.innerHTML = '<span class="tl-month">Now</span>';
        now.addEventListener('pointerdown', (e) => e.stopPropagation());
        now.addEventListener('click', (e) => { e.stopPropagation(); pill.click(); });
        segs.append(now);
      }
      now.title = live.map((f) => `${f.status === 'planned' ? 'Ready' : 'Live'}: ${label(f)}`).join('\n');
    }

    // ---------- the card
    function openCard(id, refresh = false) {
      const f = flights.find((x) => x.id === id);
      if (!f) { card?.remove(); card = null; return; }
      const here = posOf(f), to = endPt(f.to), from = endPt(f.from);
      const left = nm(here, to), p = progress(f), spd = f.position?.speed;
      const eta = left != null && spd > 30 ? Math.round((left / spd) * 60) : null;
      const ac = acOf(f), mis = f.mission;
      const fresh = !card;
      if (!card) {
        card = document.createElement('div');
        card.className = 'glass tagcard live-card';
        document.body.append(card);
      }
      card.dataset.id = id;
      const ap = (e) => (e?.ident && db.airports[e.ident]?.name) || '';
      render(card, html`<button class="tc-close" aria-label="Close">${icon('close')}</button>
        <div class="tc-body">
          <div class="tc-kind"><span class="lp-dot ${f.status}"></span>${statusText(f)}</div>
          <h3>${label(f)}</h3>
          <div class="tc-sub">${[f.who === 'hired' ? `${f.pilot || 'Hired pilot'} (hired)` : f.pilot, ac.name, f.aircraft?.tail].filter(Boolean).join(' · ')}</div>
          ${(ap(f.from) || ap(f.to)) ? html`<p class="lc-route">${ap(f.from) || f.from?.ident || ''}${to ? html` <span>→</span> ${ap(f.to) || f.to?.ident}` : ''}</p>` : ''}
          ${p != null && f.status !== 'planned' ? html`<div class="lc-prog"><i style="width:${Math.round(p * 100)}%"></i></div>` : ''}
          <div class="facts">
            ${f.position?.alt != null ? html`<div class="fact"><span>Altitude</span><b>${num(f.position.alt)} ft</b></div>` : ''}
            ${spd != null ? html`<div class="fact"><span>Ground speed</span><b>${num(spd)} kt</b></div>` : ''}
            ${f.position?.ias != null && f.status !== 'ground' ? html`<div class="fact"><span>Airspeed</span><b>${num(f.position.ias)} kt</b></div>` : ''}
            ${f.position?.vs != null && f.status !== 'ground' ? html`<div class="fact"><span>Climb / descent</span><b>${f.position.vs > 0 ? '+' : ''}${num(f.position.vs)} fpm</b></div>` : ''}
            ${f.position?.agl != null && f.status !== 'ground' && f.position.agl < 5000 ? html`<div class="fact"><span>Above ground</span><b>${num(f.position.agl)} ft</b></div>` : ''}
            ${f.position?.heading != null ? html`<div class="fact"><span>Heading</span><b>${String(Math.round(f.position.heading) % 360).padStart(3, '0')}°</b></div>` : ''}
            ${left != null ? html`<div class="fact"><span>${f.status === 'planned' ? 'Distance' : 'To go'}</span><b>${num(f.status === 'planned' ? nm(from, to) || left : left)} nm</b></div>` : ''}
            ${eta != null ? html`<div class="fact"><span>Arriving in</span><b>${eta >= 60 ? `${Math.floor(eta / 60)} h ${eta % 60} min` : `${eta} min`}</b></div>` : ''}
            ${mis?.type ? html`<div class="fact"><span>Mission</span><b>${mis.type}</b></div>` : ''}
            ${mis?.pax ? html`<div class="fact"><span>Passengers</span><b>${mis.pax}</b></div>` : ''}
            ${mis?.cargoLbs ? html`<div class="fact"><span>Cargo</span><b>${num(mis.cargoLbs)} lb</b></div>` : ''}
            ${mis?.reward ? html`<div class="fact"><span>Pays</span><b>$${num(mis.reward)}</b></div>` : ''}
          </div>
          <p class="note lc-note">${f.source === 'sim'
            ? 'Straight from Microsoft Flight Simulator while the logbook is open. The trail is kept in memory only - nothing is saved.'
            : 'Read from NeoFly while the logbook is open - nothing is recorded.'} It joins the logbook as a flight once NeoFly logs the landing.</p>
          <div class="links"><button class="link-btn" data-focus>${icon('pin')}Show on map</button>
            <button class="link-btn ${following === id ? 'on' : ''}" data-follow>${icon('follow')}${following === id ? 'Following' : 'Follow'}</button></div>
        </div>`);
      card.querySelector('.tc-close').onclick = () => { card.remove(); card = null; };
      card.querySelector('[data-focus]').onclick = () => focus(f);
      card.querySelector('[data-follow]').onclick = () => {
        following = following === id ? null : id;
        if (following && here) M.easeTo({ center: here, zoom: Math.max(M.getZoom(), 7), duration: 1200 });
        openCard(id, true);
      };
      if (fresh && !refresh) { card.style.right = '24px'; card.style.top = '146px'; }
    }
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && card) { card.remove(); card = null; } });

    // ---------- the live flight in the right-hand panel (store 'selected' = 'live')
    // route, live numbers, aircraft, mission, and TODAY's local news from where you've just left
    // and where you're heading. The numbers refresh in place; the rest only redraws when it changes.
    const current = () => flights.find((f) => f.who === 'you' && posOf(f)) || flights.find((f) => posOf(f));
    const newsFor = new Map();                       // ident -> {stories, pending, tries}
    function loadNews(ident) {
      if (!ident) return;
      const n = newsFor.get(ident) || { pending: true, tries: 0 };
      if (!n.pending || n.tries > 24) return;
      n.tries++;
      newsFor.set(ident, n);
      fetch(`/__livenews?ident=${encodeURIComponent(ident)}`).then((r) => r.json()).then((s) => {
        if (s.pending) { setTimeout(() => loadNews(ident), 5000); return; }
        newsFor.set(ident, { pending: false, stories: s.stories || [], city: s.city });
        if (store.get('selected') === 'live') drawLiveNews();
      }).catch(() => setTimeout(() => loadNews(ident), 10000));
    }
    const fmtMin = (m) => (m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, '0')}` : `${m} min`);
    const airportBits = (ident) => {
      const a = ident && db.airports[ident];
      return { ident, name: a?.name || '', city: a?.city || newsFor.get(ident)?.city || '', iso: a?.country?.iso, img: a?.wiki?.image };
    };
    const tilesFor = (f) => {
      const here = posOf(f), to = endPt(f.to), P = f.position || {};
      const left = nm(here, to);
      const ete = P.ete ? Math.round(P.ete / 60) : left != null && P.speed > 30 ? Math.round((left / P.speed) * 60) : null;
      const t = [
        P.alt != null && ['Altitude', `${num(P.alt)}`, 'ft'], P.speed != null && ['Ground speed', `${num(P.speed)}`, 'kt'],
        P.heading != null && ['Heading', `${String(Math.round(P.heading) % 360).padStart(3, '0')}°`, 'true'],
        P.vs != null && f.status !== 'ground' && ['Climb', `${P.vs > 0 ? '+' : ''}${num(P.vs)}`, 'fpm'],
        P.ias != null && f.status !== 'ground' && ['Airspeed', `${num(P.ias)}`, 'kt'],
        left != null && ['To go', `${num(left)}`, 'nm'], ete != null && ['Time left', fmtMin(ete), P.ete ? 'flight plan' : 'estimate'],
        P.agl != null && P.agl < 5000 && f.status !== 'ground' && ['Above ground', `${num(P.agl)}`, 'ft'],
      ].filter(Boolean);
      return html`${t.map(([k, v, s]) => html`<div class="tile"><span>${k}</span><b>${v}</b><small>${s}</small></div>`)}`;
    };
    const storyList = (ident, role) => {
      const n = newsFor.get(ident), a = airportBits(ident);
      const place = a.city || a.name || ident;
      if (!n || n.pending) return html`<div class="card live-news"><h4>${role} · ${place}</h4><p class="note"><span class="spinner"></span>Looking up today's local news…</p></div>`;
      if (!n.stories?.length) return html`<div class="card live-news"><h4>${role} · ${place}</h4><p class="note">No local stories found for today yet.</p></div>`;
      return html`<div class="card live-news"><h4>${role} · ${place}<small>today</small></h4>
        ${n.stories.map((s) => html`<a class="story compact" href="${s.url}" target="_blank" rel="noopener">
          <div class="st-img">${s.image ? html`<img src="${s.image}" alt="" loading="lazy">` : html`<div class="cutting"><span class="ct-mast">${s.source || ''}</span><span class="ct-cols"><i></i><i></i></span></div>`}</div>
          <div class="st-body"><div class="st-meta"><b>${s.source || ''}</b></div><h4>${s.title}</h4></div></a>`)}</div>`;
    };
    function drawLiveNews() {
      const el = document.querySelector('#detail .live-news-wrap');
      const f = current();
      if (!el || !f) return;
      const dep = fromIdent(f), dest = f.to?.ident;
      render(el, html`${dep ? storyList(dep, 'Where you\'ve just left') : ''}${dest ? storyList(dest, 'Where you\'re heading') : ''}`);
    }
    ui.renderLiveDetail = (el) => {
      const f = current();
      if (!f) {
        render(el, html`<div class="body"><div class="card"><h4>No live flight</h4><p class="note">Nothing is flying right now. Start a flight in Microsoft Flight Simulator (or load a NeoFly mission) and it appears here.</p></div></div>`);
        return;
      }
      const dep = airportBits(fromIdent(f)), dest = airportBits(f.to?.ident);
      const ac = acOf(f);
      loadNews(dep.ident); loadNews(dest.ident);
      render(el, html`
        <div class="hero live-hero">${dep.img ? html`<img src="${dep.img}" alt="">` : ''}
          <div class="hero-top"><span class="chip live-chip"><span class="lp-dot ${f.status}"></span>${statusText(f)}</span>
            <button class="close" title="Close (Esc)">${icon('close')}</button></div>
          <div class="hero-caption">${dep.name ? `Departed ${dep.name}` : ''}</div></div>
        <div class="body">
          <div class="route" style="--c:#d9b45f">
            <div class="end"><div class="code">${dep.ident || '—'}</div><div class="name">${dep.city || dep.name || 'Departure'}</div></div>
            <div class="mid">${icon('plane', 'rot')}<div class="line"></div><small>${f.status === 'ground' ? 'on the ground' : 'in the air'}</small></div>
            <div class="end"><div class="code">${dest.ident || '…'}</div><div class="name">${dest.city || dest.name || 'En route'}</div></div></div>
          ${progress(f) != null ? html`<div class="lc-prog"><i style="width:${Math.round(progress(f) * 100)}%"></i></div>` : ''}
          <div class="tiles live-tiles">${tilesFor(f)}</div>
          <div class="card aircraft"><div class="ph">${ac.wiki?.image ? html`<img src="${ac.wiki.image}" alt="">` : ''}</div>
            <div><b>${ac.name || f.aircraft?.name || 'Aircraft'}</b><small>${[f.aircraft?.tail, f.pilot].filter(Boolean).join(' · ')}</small>
              <small>${f.source === 'sim' ? 'Live from Microsoft Flight Simulator' : 'From NeoFly'}</small></div></div>
          ${f.mission?.type ? html`<div class="card"><h4>Mission</h4><div class="mission"><div><b>${f.mission.type}</b>
            <small>${[f.mission.pax && `${f.mission.pax} passengers`, f.mission.cargoLbs && `${num(f.mission.cargoLbs)} lb`].filter(Boolean).join(' · ')}</small></div>
            <span class="money">${f.mission.reward ? `$${num(f.mission.reward)}` : ''}</span></div></div>` : ''}
          <div class="live-news-wrap"></div>
          <div class="links live-actions"><button class="link-btn" data-live-focus>${icon('pin')}Show on map</button>
            <button class="link-btn ${following === f.id ? 'on' : ''}" data-live-follow>${icon('follow')}${following === f.id ? 'Following' : 'Follow'}</button></div>
          <p class="note lc-note">Read live while the logbook is open - nothing is recorded. The flight joins your logbook once NeoFly logs the landing.</p>
        </div>`);
      drawLiveNews();
      el.querySelector('[data-live-focus]').onclick = () => focus(f);
      el.querySelector('[data-live-follow]').onclick = () => {
        following = following === f.id ? null : f.id;
        if (following) { const here = posOf(f); if (here) M.easeTo({ center: here, zoom: Math.max(M.getZoom(), 7), duration: 1200 }); }
        ui.renderLiveDetail(el);
      };
    };
    // keep the live panel's numbers current without redrawing (or re-animating) the rest
    const refreshLivePanel = () => {
      if (store.get('selected') !== 'live') return;
      const f = current(), el = document.getElementById('detail');
      const tiles = el?.querySelector('.live-tiles');
      if (!f || !tiles) { if (el && !f) ui.renderLiveDetail(el); return; }
      render(tiles, tilesFor(f));
      const bar = el.querySelector('.lc-prog i'), p = progress(f);
      if (bar && p != null) bar.style.width = `${Math.round(p * 100)}%`;
    };
    // the right-edge tab says "Live flight" while you're flying
    const updateHandle = () => {
      const h = document.getElementById('detail-handle');
      if (!h) return;
      const live = !!current();
      h.dataset.live = live ? '1' : '';
      h.classList.toggle('is-live', live);
      const span = h.querySelector('span');
      if (span) span.textContent = live ? 'Live flight' : 'Flight';
    };
    ui.liveInfo = () => {
      const f = current();
      if (!f) return null;
      return { f, label: label(f), status: statusText(f), dep: airportBits(fromIdent(f)), dest: airportBits(f.to?.ident), aircraft: acOf(f).name || f.aircraft?.name };
    };

    // ---------- polling (only while the tab is visible; backs off if the server is gone)
    async function poll() {
      clearTimeout(timer);
      if (document.hidden || testing) return;
      try {
        const r = await fetch('/__live', { cache: 'no-store' });
        const s = await r.json();
        flights = Array.isArray(s.flights) ? s.flights.filter((f) => f && f.id) : [];
        failures = 0;
        draw();
      } catch {
        failures++;
      }
      // every 3 s while the sim is sending a flight (it's only a memory read on the server), else every 10 s
      const fast = flights.some((f) => f.source === 'sim');
      timer = setTimeout(poll, failures ? Math.min(120000, POLL_MS * 2 ** failures) : fast ? 3000 : POLL_MS);
    }
    document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); else clearTimeout(timer); });
    // set up last, once everything above exists
    if (M.isStyleLoaded()) addLayers();
    M.on('style.load', addLayers);
    // dragging the map yourself stops following
    M.on('dragstart', () => { if (following) { following = null; if (card) openCard(card.dataset.id, true); } });
    setTimeout(poll, 1200);
    ui.liveFlights = () => flights;
    let testing = false;
    ui.setLiveForTest = (fs) => { testing = true; flights = fs; draw(); };     // handy in the console (pauses polling)
  },
};
