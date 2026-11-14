// Full-screen photo viewer. ui.openPhotos(ids, startIndex, title?)
import { html, render, day, time } from '../core/format.js';
import { store } from '../core/store.js';

export default {
  id: 'lightbox',
  init({ db, ui }) {
    const box = document.getElementById('lightbox');
    let ids = [], i = 0, title = '';

    const caption = (p) => {
      const l = p.leg && db.legById.get(p.leg);
      const s = p.stop && db.stopById.get(p.stop);
      if (l && l.kind === 'flight') return html`${l.from} → ${l.to} · ${db.aircraft[l.aircraft]?.name || ''}`;
      if (l) return html`${l.icon} ${l.from} → ${l.to} transfer`;
      if (s) return html`On the ground at ${s.airport} · ${db.airports[s.airport]?.name || ''}`;
      return html`${title || p.source}`;
    };

    const draw = () => {
      const p = db.photos[ids[i]];
      render(box, html`
        <div class="lb-stage"><img src="${p.src}" alt=""></div>
        <div class="lb-bar">
          <div><b>${caption(p)}</b><small>${day(p.takenAt)} · ${time(p.takenAt)} · ${p.source}</small></div>
          <div class="lb-actions">
            ${p.leg ? html`<button data-act="leg">Show on map</button>` : ''}
            <span>${i + 1} / ${ids.length}</span>
          </div>
        </div>
        <button class="lb-nav prev" data-d="-1" ${ids.length > 1 ? '' : 'hidden'}>‹</button>
        <button class="lb-nav next" data-d="1" ${ids.length > 1 ? '' : 'hidden'}>›</button>
        <button class="lb-close" data-act="close">✕</button>
        <div class="lb-strip">${ids.map((id, k) => html`<img src="${db.photos[id].thumb}" data-k="${k}" class="${k === i ? 'on' : ''}" loading="lazy" alt="">`)}</div>`);
      box.querySelector('.lb-strip .on')?.scrollIntoView({ inline: 'center', block: 'nearest' });
    };
    const close = () => { box.hidden = true; document.body.classList.remove('lightbox-open'); };
    const step = (d) => { i = (i + d + ids.length) % ids.length; draw(); };

    ui.openPhotos = (list, start = 0, t = '') => {
      ids = list.filter((id) => db.photos[id]);
      if (!ids.length) return;
      i = Math.max(0, Math.min(ids.length - 1, start));
      title = t;
      box.hidden = false;
      document.body.classList.add('lightbox-open');
      draw();
    };

    box.addEventListener('click', (e) => {
      const t = e.target;
      if (t.dataset.d) step(+t.dataset.d);
      else if (t.dataset.k) { i = +t.dataset.k; draw(); }
      else if (t.dataset.act === 'close' || t.classList.contains('lb-stage')) close();
      else if (t.dataset.act === 'leg') { const p = db.photos[ids[i]]; close(); store.set('selected', p.leg); }
    });
    document.addEventListener('keydown', (e) => {
      if (box.hidden) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowRight') step(1);
      if (e.key === 'ArrowLeft') step(-1);
    });
  },
};
