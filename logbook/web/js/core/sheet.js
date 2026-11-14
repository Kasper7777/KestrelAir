// Full-screen glass sheet (photo wall, insights, logbook). Only one at a time.
import { html, render } from './format.js';
import { icon } from './icons.js';

let current = null;

export function openSheet({ id, title, sub = '', head = '', cls = '' }) {
  closeSheet();
  const back = document.createElement('div');
  back.className = 'sheet-backdrop';
  const el = document.createElement('section');
  el.className = `glass sheet ${cls}`;
  el.dataset.sheet = id;
  render(el, html`<header class="sheet-head"><div><h2>${title}</h2><p>${sub}</p></div><div class="grow"></div>${head}
    <button class="icon-btn" data-close title="Close (Esc)">${icon('close')}</button></header><div class="sheet-body"></div>`);
  document.body.append(back, el);
  const close = () => closeSheet();
  back.addEventListener('click', close);
  el.querySelector('[data-close]').addEventListener('click', close);
  current = { back, el, id };
  document.body.classList.add('sheet-open');
  return { el, body: el.querySelector('.sheet-body'), close };
}

export function closeSheet() {
  if (!current) return;
  current.back.remove();
  current.el.remove();
  current = null;
  document.body.classList.remove('sheet-open');
}

export const sheetOpen = (id) => current && (!id || current.id === id);

document.addEventListener('keydown', (e) => {
  // Esc closes only the topmost layer: a hashtag card or the photo viewer first, then the sheet
  if (e.key !== 'Escape' || !current || document.body.classList.contains('lightbox-open')) return;
  const tag = document.querySelector('.tagcard');
  if (tag) { e.stopImmediatePropagation(); tag.remove(); return; }
  e.stopImmediatePropagation();
  closeSheet();
}, true);
