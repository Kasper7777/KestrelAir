// On-map layer switches: a glass strip on the right edge of the map that turns
// each thing on the map on or off (same settings as View > Show).
import { store } from '../core/store.js';
import { html, render } from '../core/format.js';
import { icon } from '../core/icons.js';

const ITEMS = [
  ['countries', 'flag', 'Country flags'],
  ['routes', 'plane', 'Flights'],
  ['transfers', 'reposition', 'Transfers'],
  ['airports', 'pin', 'Airports'],
  ['labels', 'tag', 'Airport codes'],
  ['photos', 'photo', 'Photo pins'],
];

export default {
  id: 'layers',
  init() {
    const el = document.getElementById('layerdock');
    const draw = () => {
      const L = store.get('layers');
      render(el, html`${ITEMS.map(([k, ic, label]) => html`<button class="ld-btn ${L[k] ? 'on' : ''}" data-k="${k}" aria-pressed="${L[k] ? 'true' : 'false'}">
        ${icon(ic)}<span class="ld-tip">${label}<em>${L[k] ? 'On' : 'Off'}</em></span></button>`)}`);
    };
    el.addEventListener('click', (e) => {
      const b = e.target.closest('[data-k]');
      if (!b) return;
      store.set('layers', { ...store.get('layers'), [b.dataset.k]: !store.get('layers')[b.dataset.k] });
    });
    store.on('layers', draw);
    draw();
  },
};
