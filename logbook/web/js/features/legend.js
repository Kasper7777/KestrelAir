// Route legend: which colour is which aircraft (shown while routes are coloured by aircraft).
// Hover a plane to light up every route it flew; click to hide / show its routes
// (the same as the eye on the Fleet tab). In "Age" mode it shows the newest -> oldest scale instead.
import { html, render } from '../core/format.js';
import { store } from '../core/store.js';

const short = (n) => String(n || '').replace(/^(Asobo|A2A|Black Square|FlightFX|Carenado|Just Flight|PMDG|Milviz|Got Friends)\s+/i, '');

export default {
  id: 'legend',
  init({ db, map, ui }) {
    const el = document.createElement('div');
    el.id = 'legend';
    el.className = 'route-legend';
    document.body.append(el);
    const planes = Object.values(db.aircraft).filter((a) => a.legs).sort((a, b) => b.legs - a.legs);
    const legsOf = new Map(planes.map((a) => [a.id, db.legs.filter((l) => l.aircraft === a.id && l.kind === 'flight')]));

    const draw = () => {
      const mode = store.get('colorBy');
      const hidden = store.get('hiddenAircraft');
      el.hidden = !store.get('layers').routes || mode === 'month';
      if (mode === 'age') {
        render(el, html`<div class="lg-head">Route age</div><div class="lg-scale"><i></i></div><div class="lg-ends"><span>Newest</span><span>Oldest</span></div>`);
        return;
      }
      render(el, html`<div class="lg-head">Aircraft</div>${planes.map((a) => html`
        <button class="lg-item ${hidden.has(a.id) ? 'off' : ''}" data-ac="${a.id}" title="${a.name} · ${a.legs} flights - click to hide or show">
          <i style="--c:${a.color}"></i><span>${short(a.name)}</span><em>${a.legs}</em></button>`)}`);
    };
    draw();
    store.on('colorBy', draw);
    store.on('hiddenAircraft', draw);
    store.on('layers', draw);

    let lit = [];
    const light = (id) => {
      const M = map.map;
      for (const l of lit) M.setFeatureState({ source: 'legs', id: l.index }, { hover: false });
      lit = id ? legsOf.get(id) || [] : [];
      for (const l of lit) M.setFeatureState({ source: 'legs', id: l.index }, { hover: true });
    };
    el.addEventListener('pointerover', (e) => { const b = e.target.closest('[data-ac]'); if (b) light(b.dataset.ac); });
    el.addEventListener('pointerleave', () => light(null));
    el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-ac]');
      if (!b) return;
      const h = new Set(store.get('hiddenAircraft'));
      h.has(b.dataset.ac) ? h.delete(b.dataset.ac) : h.add(b.dataset.ac);
      store.set('hiddenAircraft', h);
    });
  },
};
