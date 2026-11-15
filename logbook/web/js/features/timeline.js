// Dock: every leg as a segment in order (click to jump), plus the replay that
// flies a plane along the whole journey, drawing the trail behind it and
// popping up your photos where they were taken.
import { store } from '../core/store.js';
import { html, render, shortDay, month, day, time } from '../core/format.js';
import { along } from '../core/geo.js';
import { icon } from '../core/icons.js';

const speedLabel = (s) => (s === 0.25 ? '¼×' : s === 0.5 ? '½×' : `${s}×`);

export default {
  id: 'timeline',
  init({ db, map, ui }) {
    const bar = document.getElementById('timeline');
    const legs = db.legs;
    let lastMonth = '';
    render(bar, html`
      <button id="play" class="play" title="Replay the journey (Space)">${icon('play')}</button>
      <button id="speed" class="speed" title="Replay speed and news (- / + to change speed)">${speedLabel(store.get('speed'))}</button>
      <button id="follow" class="follow ${store.get('follow') ? 'on' : ''}" title="Follow camera: ride along behind the aircraft during the replay">${icon('follow')}</button>
      <div class="tl-track">
        <div class="tl-segs">${legs.map((l) => {
          const m = month(l.start), label = m !== lastMonth ? m : '';
          lastMonth = m;
          return html`<button class="seg ${l.kind}" data-id="${l.id}" style="--c:${ui.routeColor?.(l) || l.color}" title="${l.from} → ${l.to} · ${shortDay(l.start)}">
            ${label ? html`<span class="tl-month">${label}</span>` : ''}${l.photos.length ? html`<em></em>` : ''}</button>`;
        })}</div>
        <div class="tl-now" title="Drag to move through the journey"></div>
        <div class="tl-tip" hidden></div>
      </div>
      <div class="tl-label" id="tl-label"></div>`);

    const segs = [...bar.querySelectorAll('.seg')];
    // the dots share the map's route colours (by age, aircraft or month)
    store.on('colorBy', () => segs.forEach((s, i) => s.style.setProperty('--c', ui.routeColor?.(legs[i]) || legs[i].color)));
    const now = bar.querySelector('.tl-now');
    const label = bar.querySelector('#tl-label');
    const playBtn = bar.querySelector('#play');
    const speedBtn = bar.querySelector('#speed');
    const followBtn = bar.querySelector('#follow');
    followBtn.addEventListener('click', () => {
      store.set('follow', !store.get('follow'));
      followBtn.classList.toggle('on', store.get('follow'));
      if (!store.get('follow') && store.get('playing')) map.map.easeTo({ pitch: 0, bearing: 0, duration: 800 });
    });

    const setLabel = (l) => render(label, l
      ? html`${l.from} → ${l.to}<small>${day(l.start)} · ${time(l.start)}</small>`
      : html`${legs.length} legs<small>${shortDay(legs[0]?.start)} – ${shortDay(legs[legs.length - 1]?.end)}</small>`);
    setLabel(null);
    const markSeg = (id) => {
      segs.forEach((s) => s.classList.toggle('active', s.dataset.id === id));
      if (cursor) return;                     // the scrub knob sits exactly where you left it
      const s = segs.find((x) => x.dataset.id === id);
      if (s) now.style.left = `${s.offsetLeft + s.offsetWidth / 2}px`;
      now.style.opacity = s ? 1 : 0;
    };
    store.on('selected', (id) => { markSeg(id); if (!cursor || !store.get('playing')) setLabel(db.legById.get(id)); });

    // ---------- scrubbing: drag along the timeline to move through the journey
    // cursor = { k: leg index, f: 0..1 along that leg } - where the replay is / was left
    let cursor = null;
    const track = bar.querySelector('.tl-track');
    const segsEl = bar.querySelector('.tl-segs');
    const tip = bar.querySelector('.tl-tip');
    const dateTime = (iso) => `${day(iso)} · ${time(iso)}`;
    const at = (l, f) => new Date(new Date(l.start).getTime() + f * (new Date(l.end).getTime() - new Date(l.start).getTime())).toISOString();
    // pointer x -> { k, f, x } on the segment under it (or the nearest one)
    const posAt = (clientX) => {
      const tr = segsEl.getBoundingClientRect();
      const x = Math.max(tr.left, Math.min(tr.right, clientX));
      let best = null;
      for (let k = 0; k < segs.length; k++) {
        const r = segs[k].getBoundingClientRect();
        if (x >= r.left && x <= r.right) { best = { k, f: (x - r.left) / Math.max(1, r.width) }; break; }
        const d = x < r.left ? r.left - x : x - r.right;
        if (!best || d < best.d) best = { k, f: x < r.left ? 0 : 1, d };
      }
      return best ? { k: best.k, f: Math.max(0, Math.min(1, best.f)), x: x - tr.left + segsEl.offsetLeft } : null;
    };
    const prefix = [];        // trail features for every leg before k (built once per k)
    let prefixK = -1;
    const trailTo = (k) => {
      if (prefixK !== k) {
        prefix.length = 0;
        for (let i = 0; i < k; i++) if (legs[i].coords?.length > 1) prefix.push(feature(legs[i], legs[i].coords));
        prefixK = k;
      }
      return prefix;
    };
    let showRaf = 0;
    function showAt(k, f, x, { camera = true } = {}) {
      const l = legs[k];
      if (!l || !l.coords?.length) return;
      cursor = { k, f };
      cancelAnimationFrame(showRaf);
      showRaf = requestAnimationFrame(() => {
        const { point, bearing, index } = along(l.coords, f, l.acc);
        map.dimRoutes(true);
        map.setPlane(point, bearing, l);
        map.setTrail([...trailTo(k), feature(l, [...l.coords.slice(0, index), point])]);
        if (camera) {
          if (store.get('follow')) map.map.jumpTo({ center: point });
          else {
            const p = map.map.project(point), c = map.map.getContainer(), pad = 140;
            if (p.x < pad || p.y < pad || p.x > c.clientWidth - pad || p.y > c.clientHeight - pad) map.map.easeTo({ center: point, duration: 500 });
          }
        }
      });
      segs.forEach((s, i) => s.classList.toggle('active', i === k));
      now.style.left = `${x}px`;
      now.style.opacity = 1;
      document.body.classList.add('scrubbed');
      render(label, html`${l.from} → ${l.to}<small>${dateTime(at(l, f))}</small>`);
    }
    function clearCursor() {
      if (!cursor) return;
      cursor = null;
      document.body.classList.remove('scrubbed');
      if (!store.get('playing')) { map.hidePlane(); map.setTrail([]); map.dimRoutes(false); }
      markSeg(store.get('selected'));
      setLabel(db.legById.get(store.get('selected')));
    }
    let drag = null;
    track.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      const p = posAt(e.clientX);
      if (!p) return;
      drag = { id: e.pointerId, x0: e.clientX, moved: false, wasPlaying: store.get('playing'), p };
      track.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    track.addEventListener('pointermove', (e) => {
      const p = posAt(e.clientX);
      if (!p) return;
      if (!drag) {                                   // hover preview
        const l = legs[p.k];
        render(tip, html`<b>${l.from} → ${l.to}</b><small>${dateTime(at(l, p.f))}</small>`);
        tip.style.left = `${p.x}px`;
        tip.hidden = false;
        return;
      }
      if (!drag.moved && Math.abs(e.clientX - drag.x0) < 4) return;
      if (!drag.moved) {
        drag.moved = true;
        if (drag.wasPlaying) pause();
        store.set('scrubbing', true);
        document.body.classList.add('scrubbing');
      }
      tip.hidden = true;
      showAt(p.k, p.f, p.x);
    });
    const endDrag = (e) => {
      if (!drag || (e && e.pointerId !== drag.id)) return;
      const d = drag;
      drag = null;
      try { track.releasePointerCapture(d.id); } catch {}
      if (!d.moved) {                                  // a plain click: open that leg, as before
        const l = legs[d.p.k];
        if (store.get('playing')) stop();
        clearCursor();
        store.set('selected', l.id);
        return;
      }
      document.body.classList.remove('scrubbing');
      const k = cursor?.k;
      if (k != null && legs[k].id !== store.get('selected')) store.set('selected', legs[k].id);
      store.set('scrubbing', false);
      if (d.wasPlaying) play();                         // carry on from where you let go
    };
    track.addEventListener('pointerup', endDrag);
    track.addEventListener('pointercancel', endDrag);
    track.addEventListener('lostpointercapture', endDrag);
    track.addEventListener('pointerleave', () => { if (!drag) tip.hidden = true; });
    window.addEventListener('blur', () => endDrag());
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && cursor && !store.get('playing') && !document.querySelector('.sheet, .tagcard')) clearCursor();
    });
    ui.scrubTo = (k, f = 0) => {                       // for other features (e.g. a future live view)
      const s = segs[k];
      if (!s) return;
      if (store.get('playing')) pause();
      showAt(k, f, s.offsetLeft + f * s.offsetWidth);
      store.set('selected', legs[k].id);
    };
    ui.clearScrub = clearCursor;
    ui.scrubbedLeg = () => (cursor ? legs[cursor.k]?.id : null);
    store.on('selected', (id) => { if (!store.get('playing') && cursor && legs[cursor.k]?.id !== id) clearCursor(); });
    ui.timelineSegs = () => segsEl;

    // ---------- replay options: speed (slow-motion to fast) + where the local news appears
    const speeds = [0.25, 0.5, 1, 2, 4, 8];
    if (!speeds.includes(store.get('speed'))) store.set('speed', 1);
    const menu = document.createElement('div');
    menu.id = 'replaymenu';
    menu.className = 'popover glass';
    menu.hidden = true;
    document.body.append(menu);
    const drawMenu = () => render(menu, html`
      <h5>Replay speed</h5>
      <div class="segmented speeds">${speeds.map((s) => html`<button data-speed="${s}" class="${store.get('speed') === s ? 'on' : ''}">${speedLabel(s)}</button>`)}</div>
      <p class="pm-note">${store.get('speed') < 1 ? 'Slow motion - time to take in every landing.' : store.get('speed') > 1 ? 'Fast forward.' : 'Normal pace.'} Use − and + on the keyboard any time.</p>
      <h5>Local news while replaying</h5>
      <div class="segmented">${[['map', 'On the map'], ['side', 'At the side'], ['both', 'Both'], ['off', 'Off']].map(([v, l]) =>
        html`<button data-news="${v}" class="${store.get('newsMode') === v ? 'on' : ''}">${l}</button>`)}</div>`);
    const placeMenu = () => {
      const r = speedBtn.getBoundingClientRect();
      menu.style.left = `${Math.max(12, r.left + r.width / 2 - 190)}px`;
      menu.style.bottom = `${innerHeight - r.top + 12}px`;
    };
    speedBtn.addEventListener('click', () => {
      if (!menu.hidden) { menu.hidden = true; speedBtn.classList.remove('on'); return; }
      drawMenu(); placeMenu(); menu.hidden = false; speedBtn.classList.add('on');
    });
    menu.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.speed) store.set('speed', +b.dataset.speed);
      if (b.dataset.news) store.set('newsMode', b.dataset.news);
      drawMenu();
    });
    document.addEventListener('pointerdown', (e) => {
      if (!menu.hidden && !menu.contains(e.target) && e.target !== speedBtn && !speedBtn.contains(e.target)) { menu.hidden = true; speedBtn.classList.remove('on'); }
    });
    store.on('speed', (s) => { speedBtn.textContent = speedLabel(s); if (!menu.hidden) drawMenu(); });
    document.addEventListener('keydown', (e) => {
      if (e.target.matches('input, textarea')) return;
      const i = speeds.indexOf(store.get('speed'));
      if (e.key === '-' || e.key === '_') store.set('speed', speeds[Math.max(0, i - 1)]);
      if (e.key === '=' || e.key === '+') store.set('speed', speeds[Math.min(speeds.length - 1, i + 1)]);
    });

    let raf = 0, token = 0;
    const trail = [];
    // how long a leg takes at 1x; the current speed is applied every frame, so changing it mid-flight works
    const legMs = (l) => Math.min(7000, Math.max(1600, 900 + Math.sqrt(l.acc[l.acc.length - 1] || 1) * 70));
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    const feature = (l, coords) => ({ type: 'Feature', properties: { color: ui.routeColor?.(l) || l.color },
      geometry: { type: 'LineString', coordinates: coords } });

    async function play() {
      const my = ++token;
      store.set('playing', true);
      playBtn.innerHTML = icon('pause').s;
      document.body.classList.add('playing');
      const cur = db.legById.get(store.get('selected'));
      // resume from the scrub position if there is one, else from the selected leg
      const from = cursor && cursor.f < 0.999 ? { ...cursor } : cursor ? { k: Math.min(legs.length - 1, cursor.k + 1), f: 0 } : null;
      const startAt = from ? from.k : cur && cur.index < legs.length - 1 ? cur.index : 0;
      cursor = null;
      document.body.classList.remove('scrubbed');
      prefixK = -1;
      trail.length = 0;
      for (const l of legs.slice(0, startAt)) trail.push(feature(l, l.coords));
      map.setTrail(trail);
      map.dimRoutes(true);
      for (let k = startAt; k < legs.length; k++) {
        if (my !== token) return;
        const l = legs[k];
        if (l.aircraft && store.get('hiddenAircraft').has(l.aircraft)) continue;
        store.set('selected', l.id);
        const f0 = from && k === from.k ? from.f : 0;
        if (f0 > 0) {                                   // resuming mid-leg: no fly-in, just carry on
          await fly(l, my, f0);
          if (my !== token) return;
          if (l.kind === 'flight') ui.popNews?.(l);
          trail.push(feature(l, l.coords));
          map.setTrail(trail);
          continue;
        }
        if (store.get('follow')) {
          const km = l.acc[l.acc.length - 1] || 10;
          const zoom = Math.max(3.6, Math.min(10.5, 10.6 - Math.log2(km / 12)));
          map.map.flyTo({ center: l.coords[0], zoom, pitch: 58, bearing: l.coords.length > 1 ? bearingOf(l) : 0, duration: 1100 / store.get('speed'), essential: true });
        } else map.fitLegs([l], { duration: 900 / store.get('speed'), maxZoom: l.kind === 'ground' ? 7 : 7.5 });
        await wait(1150 / store.get('speed'));
        if (my !== token) return;
        await fly(l, my);
        if (my !== token) return;
        if (l.kind === 'flight') ui.popNews?.(l);      // what was in the local news the day you landed
        trail.push(feature(l, l.coords));
        map.setTrail(trail);
        await wait(250 / store.get('speed'));
      }
      if (my === token) { stop(); map.fitAll(); }
    }

    // eased progress e for linear time f, and back (so a resume lands exactly where you scrubbed to)
    const easeOf = (f) => (f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2);
    const timeOf = (e) => (e < 0.5 ? Math.sqrt(e / 2) : 1 - Math.sqrt(2 * (1 - e)) / 2);
    function fly(l, my, startE = 0) {
      return new Promise((resolve) => {
        const ms = legMs(l);
        let f = startE > 0 ? timeOf(Math.min(1, startE)) : 0, last = performance.now();
        const pending = l.photos.map((id) => db.photos[id]).filter((p) => p.fraction != null && p.fraction > startE).sort((a, b) => a.fraction - b.fraction);
        const tick = (t) => {
          if (my !== token) return resolve();
          f = Math.min(1, f + (t - last) * store.get('speed') / ms);
          last = t;
          const e = easeOf(f);
          const { point, bearing, index } = along(l.coords, e, l.acc);
          map.setPlane(point, bearing, l);
          const s = segs[l.index];
          if (s) { now.style.left = `${s.offsetLeft + e * s.offsetWidth}px`; now.style.opacity = 1; }
          if (l.end && l.start) render(label, html`${l.from} → ${l.to}<small>${dateTime(at(l, e))}</small>`);
          lastPos = { k: l.index, f: e };
          map.setTrail([...trail, feature(l, [...l.coords.slice(0, index), point])]);
          if (store.get('follow')) {
            // ease the camera's heading toward the aircraft's so turns feel smooth
            const cur = map.map.getBearing(), d = ((bearing - cur + 540) % 360) - 180;
            map.map.jumpTo({ center: point, bearing: cur + d * 0.08 });
          }
          while (pending.length && pending[0].fraction <= e) ui.flashPhoto(pending.shift());
          if (f < 1) raf = requestAnimationFrame(tick); else resolve();
        };
        raf = requestAnimationFrame(tick);
      });
    }

    // pause: freeze the replay where it is (the plane and trail stay; Play carries on from here)
    let lastPos = null;
    function pause() {
      if (!lastPos) { stop(); return; }             // nothing on screen yet: a plain stop
      token++;
      cancelAnimationFrame(raf);
      store.set('playing', false);
      playBtn.innerHTML = icon('play').s;
      document.body.classList.remove('playing');
      if (lastPos) {
        const s = segs[lastPos.k];
        showAt(lastPos.k, lastPos.f, s ? s.offsetLeft + lastPos.f * s.offsetWidth : 0, { camera: false });
      }
    }
    function stop() {
      token++;
      lastPos = null;
      cursor = null;
      document.body.classList.remove('scrubbed');
      cancelAnimationFrame(raf);
      store.set('playing', false);
      playBtn.innerHTML = icon('play').s;
      document.body.classList.remove('playing');
      map.hidePlane();
      map.setTrail([]);
      map.dimRoutes(false);
      map.clearDrops();
      ui.endNewsRail?.();
      if (map.map.getPitch() > 1) map.map.easeTo({ pitch: 0, bearing: 0, duration: 900 });
    }
    const bearingOf = (l) => along(l.coords, 0.02, l.acc).bearing ?? 0;

    // Play / Pause: pausing keeps your place, so you can scrub around and carry on
    playBtn.addEventListener('click', () => (store.get('playing') ? pause() : play()));
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !e.target.matches('input, button') && !document.body.classList.contains('lightbox-open')) {
        e.preventDefault();
        store.get('playing') ? pause() : play();
      }
    });
    ui.stopPlayback = stop;
  },
};
