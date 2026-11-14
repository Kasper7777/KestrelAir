// Photo wall: every screenshot as a print, month by month, in the order taken.
// Click a print to open it full screen; "Show on map" from there jumps to the leg.
import { html, render, time } from '../core/format.js';
import { openSheet, closeSheet } from '../core/sheet.js';

const monthFmt = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric' });
const dayFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

export default {
  id: 'gallery',
  init({ db, ui }) {
    ui.openGallery = () => {
      const placed = db.photoList.filter((p) => p.leg || p.stop);
      const loose = db.unplacedPhotos.map((id) => db.photos[id]).filter(Boolean);
      const places = new Set(placed.map((p) => {
        const l = db.legById.get(p.leg);
        return l ? l.to : db.stopById.get(p.stop)?.airport;
      }));
      const { body } = openSheet({ id: 'photos', title: 'Photo wall',
        sub: `${placed.length} shots across ${places.size} places${loose.length ? ` · ${loose.length} from before the logbook` : ''}` });

      const groups = [];
      for (const p of placed) {
        const k = p.takenAt.slice(0, 7);
        if (!groups.length || groups.at(-1).key !== k) groups.push({ key: k, photos: [] });
        groups.at(-1).photos.push(p);
      }
      const all = [...placed.map((p) => p.id), ...loose.map((p) => p.id)];
      const caption = (p) => {
        const l = db.legById.get(p.leg);
        const where = l ? (l.kind === 'flight' ? `${l.from} → ${l.to}` : `${l.modeLabel}`) : db.stopById.get(p.stop)?.airport || '';
        return html`${where}<small>${dayFmt.format(new Date(p.takenAt))} · ${time(p.takenAt)}</small>`;
      };
      const print = (p) => {
        const l = db.legById.get(p.leg);
        const ac = l && db.aircraft[l.aircraft];
        return html`<figure class="print" data-id="${p.id}">
          <img src="${p.thumb}" alt="" loading="lazy">${ac ? html`<span class="route-tag">${ac.name.replace(/^(Asobo|A2A|FlightFX|Black Square)\s+/i, '')}</span>` : ''}
          <figcaption>${caption(p)}</figcaption></figure>`;
      };
      render(body, html`
        ${groups.map((g) => html`<div class="wall-month"><h3>${monthFmt.format(new Date(g.key + '-01'))}</h3><small>${g.photos.length} photos</small></div>
          <div class="wall">${g.photos.map(print)}</div>`)}
        ${loose.length ? html`<div class="wall-month"><h3>Before the logbook</h3><small>${loose.length} earlier MSFS shots</small></div>
          <div class="wall">${loose.map((p) => html`<figure class="print" data-id="${p.id}"><img src="${p.thumb}" alt="" loading="lazy">
            <figcaption>${dayFmt.format(new Date(p.takenAt))} ${p.takenAt.slice(0, 4)}<small>${time(p.takenAt)}</small></figcaption></figure>`)}</div>` : ''}`);
      body.addEventListener('click', (e) => {
        const f = e.target.closest('.print');
        if (f) ui.openPhotos(all, all.indexOf(f.dataset.id));
      });
    };
    // "Show on map" in the lightbox should also close the wall
    ui.onShowOnMap = () => closeSheet();
  },
};
