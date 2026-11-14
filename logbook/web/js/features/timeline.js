// Bottom bar: every leg as a segment in order (click to jump), plus the replay
// player that flies a little plane along the whole journey, drawing the trail
// behind it and popping up photos at the spot they were taken.
import { store } from '../core/store.js';
import { html, render, shortDay, month, day } from '../core/format.js';
import { along } from '../core/geo.js';

export default {
  id: 'timeline',
  init({ db, map, ui }) {
    const bar = document.getElementById('timeline');
    const legs = db.legs;
    let lastMonth = '';
    render(bar, html`
      <div class="tl-controls">
        <button id="play" class="play" title="Replay the journey (Space)">▶</button>
        <button id="speed" class="speed" title="Replay speed">1×</button>
      </div>
      <div class="tl-track">
        <div class="tl-segs">${legs.map((l) => {
          const m = month(l.start), label = m !== lastMonth ? m : '';
          lastMonth = m;
          return html`<button class="seg ${l.kind}" data-id="${l.id}" style="--c:${l.color}" title="${l.from} → ${l.to} · ${shortDay(l.start)}">
            ${label ? html`<span class="tl-month">${label}</span>` : ''}${l.photos.length ? html`<em></em>` : ''}</button>`;
        })}</div>
        <div class="tl-now"></div>
      </div>
      <div class="tl-label" id="tl-label">${day(legs[0]?.start)} → ${day(legs[legs.length - 1]?.end)}</div>`);

    const segs = [...bar.querySelectorAll('.seg')];
    const now = bar.querySelector('.tl-now');
    const label = bar.querySelector('#tl-label');
    const playBtn = bar.querySelector('#play');
    const speedBtn = bar.querySelector('#speed');

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
    store.on('selected', (id) => { markSeg(id); const l = db.legById.get(id); label.textContent = l ? `${day(l.start)} · ${l.from} → ${l.to}` : `${day(legs[0]?.start)} → ${day(legs[legs.length - 1]?.end)}`; });

    // ---------- player
    const speeds = [1, 2, 4, 8];
    speedBtn.addEventListener('click', () => {
      const s = speeds[(speeds.indexOf(store.get('speed')) + 1) % speeds.length];
      store.set('speed', s);
      speedBtn.textContent = `${s}×`;
    });

    let raf = 0, token = 0;
    const trail = [];
    const legMs = (l) => Math.min(7000, Math.max(1600, 900 + Math.sqrt(l.acc[l.acc.length - 1] || 1) * 70)) / store.get('speed');
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));

    async function play() {
      const my = ++token;
      store.set('playing', true);
      playBtn.textContent = '❚❚';
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
        map.fitLegs([l], { duration: 900 / store.get('speed'), maxZoom: l.kind === 'ground' ? 7 : 7.5 });
        await wait(950 / store.get('speed'));
        if (my !== token) return;
        await fly(l, my);
        if (my !== token) return;
        trail.push(feature(l, l.coords));
        map.setTrail(trail);
        await wait(250 / store.get('speed'));
      }
      if (my === token) { stop(); map.fitAll(); }
    }

    function fly(l, my) {
      return new Promise((resolve) => {
        const ms = legMs(l), t0 = performance.now();
        const pending = l.photos.map((id) => db.photos[id]).filter((p) => p.fraction != null).sort((a, b) => a.fraction - b.fraction);
        const tick = (t) => {
          if (my !== token) return resolve();
          const f = Math.min(1, (t - t0) / ms);
          const e = f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2; // ease in-out
          const { point, bearing, index } = along(l.coords, e, l.acc);
          map.setPlane(point, bearing);
          map.setTrail([...trail, feature(l, [...l.coords.slice(0, index), point])]);
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
      playBtn.textContent = '▶';
      document.body.classList.remove('playing');
      map.hidePlane();
      map.setTrail([]);
      map.dimRoutes(false);
    }

    const feature = (l, coords) => ({ type: 'Feature', properties: { color: l.color }, geometry: { type: 'LineString', coordinates: coords } });
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
