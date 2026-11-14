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
          return html`<button class="seg ${l.kind}" data-id="${l.id}" style="--c:${l.color}" title="${l.from} → ${l.to} · ${shortDay(l.start)}">
            ${label ? html`<span class="tl-month">${label}</span>` : ''}${l.photos.length ? html`<em></em>` : ''}</button>`;
        })}</div>
        <div class="tl-now"></div>
      </div>
      <div class="tl-label" id="tl-label"></div>`);

    const segs = [...bar.querySelectorAll('.seg')];
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
      const s = segs.find((x) => x.dataset.id === id);
      if (s) now.style.left = `${s.offsetLeft + s.offsetWidth / 2}px`;
      now.style.opacity = s ? 1 : 0;
    };
    bar.querySelector('.tl-segs').addEventListener('click', (e) => {
      const s = e.target.closest('.seg');
      if (!s) return;
      if (store.get('playing')) stop();
      store.set('selected', s.dataset.id);
    });
    store.on('selected', (id) => { markSeg(id); setLabel(db.legById.get(id)); });

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
    const feature = (l, coords) => ({ type: 'Feature', properties: { color: store.get('colorBy') === 'month' ? l.monthColor : l.color },
      geometry: { type: 'LineString', coordinates: coords } });

    async function play() {
      const my = ++token;
      store.set('playing', true);
      playBtn.innerHTML = icon('pause').s;
      document.body.classList.add('playing');
      const cur = db.legById.get(store.get('selected'));
      const startAt = cur && cur.index < legs.length - 1 ? cur.index : 0;
      trail.length = 0;
      for (const l of legs.slice(0, startAt)) trail.push(feature(l, l.coords));
      map.setTrail(trail);
      map.dimRoutes(true);
      for (let k = startAt; k < legs.length; k++) {
        if (my !== token) return;
        const l = legs[k];
        if (l.aircraft && store.get('hiddenAircraft').has(l.aircraft)) continue;
        store.set('selected', l.id);
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

    function fly(l, my) {
      return new Promise((resolve) => {
        const ms = legMs(l);
        let f = 0, last = performance.now();
        const pending = l.photos.map((id) => db.photos[id]).filter((p) => p.fraction != null).sort((a, b) => a.fraction - b.fraction);
        const tick = (t) => {
          if (my !== token) return resolve();
          f = Math.min(1, f + (t - last) * store.get('speed') / ms);
          last = t;
          const e = f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2;
          const { point, bearing, index } = along(l.coords, e, l.acc);
          map.setPlane(point, bearing, l);
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

    function stop() {
      token++;
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

    playBtn.addEventListener('click', () => (store.get('playing') ? stop() : play()));
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !e.target.matches('input, button') && !document.body.classList.contains('lightbox-open')) {
        e.preventDefault();
        store.get('playing') ? stop() : play();
      }
    });
    ui.stopPlayback = stop;
  },
};
