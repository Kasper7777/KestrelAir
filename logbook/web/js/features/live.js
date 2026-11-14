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
    const glide = (m, to) => {
      cancelAnimationFrame(m.raf);
      const from = m.marker.getLngLat().toArray(), t0 = performance.now(), D = 1800;
      if (Math.abs(from[0] - to[0]) > 1 || Math.abs(from[1] - to[1]) > 1) { m.marker.setLngLat(to); return; }
      const step = (now) => {
        const x = Math.min(1, (now - t0) / D), e = 1 - (1 - x) ** 2;
        m.marker.setLngLat([from[0] + (to[0] - from[0]) * e, from[1] + (to[1] - from[1]) * e]);
        if (x < 1) m.raf = requestAnimationFrame(step);
      };
      m.raf = requestAnimationFrame(step);
    };

    // ---------- map layers (re-added if the basemap changes)
    const addLayers = () => {
      if (!M.getStyle() || M.getSource('live')) return;
      M.addSource('live', { type: 'geojson', data: empty });
      M.addLayer({ id: 'live-ahead', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'ahead'], layout: { 'line-cap': 'round' },
        paint: { 'line-color': '#f0dca4', 'line-width': 2, 'line-dasharray': [0.6, 2.2], 'line-opacity': 0.85 } });
      M.addLayer({ id: 'live-glow', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'flown'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#d9b45f', 'line-width': 12, 'line-blur': 9, 'line-opacity': 0.45 } });
      M.addLayer({ id: 'live-flown', type: 'line', source: 'live', filter: ['==', ['get', 'part'], 'flown'], layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#fff3dc', 'line-width': 3 } });
      draw();
    };

    function draw() {
      const feats = [];
      for (const f of flights) {
        const here = posOf(f), to = endPt(f.to), from = endPt(f.from);
        if (f.track?.length > 1) feats.push({ type: 'Feature', properties: { part: 'flown' }, geometry: { type: 'LineString', coordinates: f.track } });
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
          const el = document.createElement('div');
          el.className = 'live-marker';
          el.innerHTML = `<span class="lm-ring"></span><span class="lm-plane"></span><span class="lm-tag"></span>`;
          el.addEventListener('click', (e) => { e.stopPropagation(); openCard(f.id); });
          m = { el, marker: new maplibregl.Marker({ element: el }).setLngLat(here).addTo(M), shape: null };
          markers.set(f.id, m);
        }
        const ac = acOf(f);
        const shape = `${ac.name}|${f.who}`;
        if (m.shape !== shape) { m.el.querySelector('.lm-plane').innerHTML = planeSvg(ac); m.shape = shape; }
        m.el.classList.toggle('planned', f.status === 'planned');
        m.el.classList.toggle('stale', f.status === 'stale');
        m.el.classList.toggle('hired', f.who === 'hired');
        m.heading = headingOf(f, here);
        m.el.querySelector('.lm-plane').style.transform = `rotate(${m.heading - M.getBearing()}deg)`;
        const alt = f.position?.alt, spd = f.position?.speed;
        m.el.querySelector('.lm-tag').textContent = f.status === 'planned' ? `Ready · ${label(f)}` : f.status === 'ground' ? `On the ground${spd > 3 ? ` · ${num(spd)} kt` : ''}`
          : [f.who === 'hired' ? (f.pilot || 'Hired pilot') : 'Live', alt != null ? `${num(alt)} ft${vsArrow(f.position?.vs)}` : '', spd != null ? `${num(spd)} kt` : ''].filter(Boolean).join(' · ');
        m.el.classList.toggle('ground', f.status === 'ground');
        glide(m, here);
        if (following === f.id) M.easeTo({ center: here, duration: 1800, easing: (x) => x });
      }
      for (const [id, m] of markers) if (!seen.has(id)) { m.marker.remove(); markers.delete(id); }
      drawPill();
      drawNow();
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
      openCard(f.id);
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
    // keep each aircraft pointing the right way when the map is rotated
    M.on('rotate', () => { for (const m of markers.values()) m.el.querySelector('.lm-plane').style.transform = `rotate(${(m.heading || 0) - M.getBearing()}deg)`; });
    // dragging the map yourself stops following
    M.on('dragstart', () => { if (following) { following = null; if (card) openCard(card.dataset.id, true); } });
    setTimeout(poll, 1200);
    ui.liveFlights = () => flights;
    let testing = false;
    ui.setLiveForTest = (fs) => { testing = true; flights = fs; draw(); };     // handy in the console (pauses polling)
  },
};
