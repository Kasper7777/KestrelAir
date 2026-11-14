// Liquid glass tabs: a drop of glass sits under the selected tab and flows to the
// next one when you switch - stretching as it travels, settling with a little wobble.
//   liquidTabs(container)  - any row of buttons where the chosen one has class "on"
export function liquidTabs(container, sel = 'button') {
  container.classList.add('liquid');
  let puck = container.querySelector(':scope > .puck');
  if (!puck) {
    puck = document.createElement('span');
    puck.className = 'puck';
    container.prepend(puck);
  }
  let last = null;
  const move = (animate = true) => {
    const on = container.querySelector(`${sel}.on`);
    if (!on || !on.offsetWidth) { puck.style.opacity = 0; return; }
    const x = on.offsetLeft, y = on.offsetTop, w = on.offsetWidth, h = on.offsetHeight;
    puck.style.opacity = 1;
    puck.style.width = `${w}px`;
    puck.style.height = `${h}px`;
    puck.style.transform = `translate(${x}px, ${y}px)`;
    if (animate && last && (last.x !== x || last.y !== y) && puck.animate) {
      const d = Math.abs(x - last.x);
      const midW = Math.max(w, last.w) + d * 0.35;
      const midX = Math.min(x, last.x) + (Math.abs(x - last.x) + Math.max(w, last.w) - midW) / 2 + (x > last.x ? d * 0.12 : -d * 0.12);
      puck.animate([
        { transform: `translate(${last.x}px, ${last.y}px)`, width: `${last.w}px`, height: `${last.h}px` },
        { offset: 0.42, transform: `translate(${midX}px, ${(y + last.y) / 2 + h * 0.06}px)`, width: `${midW}px`, height: `${h * 0.88}px` },
        { offset: 0.78, transform: `translate(${x}px, ${y}px)`, width: `${w * 1.04}px`, height: `${h}px` },
        { transform: `translate(${x}px, ${y}px)`, width: `${w}px`, height: `${h}px` },
      ], { duration: 560, easing: 'cubic-bezier(.22, 1, .36, 1)' });
    }
    last = { x, y, w, h };
  };
  new MutationObserver(() => move(true)).observe(container, { subtree: true, attributes: true, attributeFilter: ['class'], childList: true });
  if (window.ResizeObserver) new ResizeObserver(() => move(false)).observe(container);
  requestAnimationFrame(() => move(false));
  return { move };
}
