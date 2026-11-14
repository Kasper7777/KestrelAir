// Light that follows the pointer: buttons and cards get a soft highlight under the
// cursor, and glass panels catch a gentle glare where the pointer is - like light
// moving across real glass. Pure presentation; one rAF-throttled listener.
const INTERACTIVE = '.tb-btn, .icon-btn, .ld-btn, .segmented button, .pager button, .link-btn, .speed, .follow, .play, ' +
  '.toast-actions button, .lb-tabs button, .leg, .fleet-card, .record, .country, .tile, .pilot-btn, .tag-btn, .eye, ' +
  '.card.clickable, .top-ap, .ds-book, .lb-nav, .lb-close, .hero .close, .ig-nav';

export default {
  id: 'glassfx',
  init() {
    if (matchMedia('(pointer: coarse)').matches) return;   // touch screens: no hover light
    let raf = 0, ev = null, lastEl = null, lastPanel = null;
    const frame = () => {
      raf = 0;
      const e = ev;
      const el = e.target.closest?.(INTERACTIVE);
      if (lastEl && lastEl !== el) lastEl.classList.remove('lit');
      if (el) {
        const r = el.getBoundingClientRect();
        el.style.setProperty('--mx', `${e.clientX - r.left}px`);
        el.style.setProperty('--my', `${e.clientY - r.top}px`);
        el.classList.add('lit');
      }
      lastEl = el;
      const panel = e.target.closest?.('.glass');
      if (lastPanel && lastPanel !== panel) lastPanel.style.removeProperty('--gx');
      if (panel) {
        const r = panel.getBoundingClientRect();
        panel.style.setProperty('--gx', `${e.clientX - r.left}px`);
        panel.style.setProperty('--gy', `${e.clientY - r.top}px`);
      }
      lastPanel = panel;
    };
    document.addEventListener('pointermove', (e) => { ev = e; if (!raf) raf = requestAnimationFrame(frame); }, { passive: true });
    document.addEventListener('pointerleave', () => { lastEl?.classList.remove('lit'); lastPanel?.style.removeProperty('--gx'); });
  },
};
