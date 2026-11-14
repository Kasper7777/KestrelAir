// Line icons (24px grid, 1.7 stroke) in the spirit of SF Symbols. icon('globe')
import { raw } from './format.js';

const P = {
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
  map: '<path d="M9 4 3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5L9 4z"/><path d="M9 4v13.5M15 6.5V20"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/>',
  photo: '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10" r="1.6"/><path d="m21 16-5-5-8 8"/>',
  play: '<path d="M8 5.5v13a.6.6 0 0 0 .9.5l10.2-6.5a.6.6 0 0 0 0-1L8.9 5a.6.6 0 0 0-.9.5z" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6.5" y="5" width="3.6" height="14" rx="1" fill="currentColor" stroke="none"/><rect x="13.9" y="5" width="3.6" height="14" rx="1" fill="currentColor" stroke="none"/>',
  back: '<path d="m15 5-7 7 7 7"/>',
  forward: '<path d="m9 5 7 7-7 7"/>',
  close: '<path d="M6 6l12 12M18 6 6 18"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  expand: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
  save: '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5"/><path d="M4 16v2.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V16"/>',
  folder: '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6H9l2 2h8.5A1.5 1.5 0 0 1 21 9.5v8a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>',
  plane: '<path d="M21 15.5v-1.8l-7.5-4.8V4.2a1.5 1.5 0 0 0-3 0v4.7L3 13.7v1.8l7.5-2.3v4.6l-2 1.4V21l3.5-1 3.5 1v-1.8l-2-1.4v-4.6z" fill="currentColor" stroke="none"/>',
  taxi: '<path d="M5 16V12l1.6-4.2A1.5 1.5 0 0 1 8 7h8a1.5 1.5 0 0 1 1.4.8L19 12v4"/><rect x="4" y="12" width="16" height="5" rx="1.5"/><path d="M7 17v2M17 17v2M10 4.5h4"/>',
  train: '<rect x="6" y="3.5" width="12" height="13" rx="3"/><path d="M6 10.5h12M9 20l1.5-3.5M15 20l-1.5-3.5"/><circle cx="9.5" cy="13.5" r=".8"/><circle cx="14.5" cy="13.5" r=".8"/>',
  ferry: '<path d="M3 18c1.5 1 3 1 4.5 0s3-1 4.5 0 3 1 4.5 0 3-1 4.5 0"/><path d="m4.5 15-1-4h17l-1 4M7 11V7h10v4M12 4v3"/>',
  ticket: '<path d="M4 7.5A1.5 1.5 0 0 1 5.5 6h13A1.5 1.5 0 0 1 20 7.5V10a2 2 0 0 0 0 4v2.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 16.5V14a2 2 0 0 0 0-4z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
  reposition: '<path d="M4 7h11l-3-3M20 17H9l3 3"/>',
  walk: '<circle cx="13" cy="4.5" r="1.6"/><path d="m10 21 2-6 3 3v3M9.5 10.5 12 8l3 3 2.5 1M12 8l-1 5"/>',
  external: '<path d="M14 4h6v6M20 4l-9 9M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
  pin: '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
  sidebar: '<rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="M9 4.5v15"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  speed: '<path d="M4 17a8 8 0 1 1 16 0"/><path d="m12 17 4-5"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  tag: '<path d="M4 6.5A2.5 2.5 0 0 1 6.5 4h5.2a2 2 0 0 1 1.4.6l6.8 6.8a2 2 0 0 1 0 2.8l-5.4 5.4a2 2 0 0 1-2.8 0L4.6 12.8a2 2 0 0 1-.6-1.4z"/><circle cx="8.5" cy="8.5" r="1.4"/>',
  book: '<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v15H6.5A1.5 1.5 0 0 0 5 19.5z"/><path d="M5 19.5A1.5 1.5 0 0 0 6.5 21H19v-3M9 7h6"/>',
  diary: '<rect x="4" y="4" width="16" height="16" rx="4.5"/><circle cx="12" cy="12" r="3.6"/><circle cx="16.6" cy="7.4" r=".9" fill="currentColor"/>',
  heart: '<path d="M12 20s-7.5-4.6-7.5-10A4.4 4.4 0 0 1 12 7.2 4.4 4.4 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z"/>',
  fork: '<path d="M7 3v7a2 2 0 0 0 4 0V3M9 10v11M17 21V3c-2 1.5-3 4-3 7s1 4 3 4"/>',
  chart:'<path d="M4 20h16"/><rect x="6" y="11" width="3" height="7" rx="1"/><rect x="11" y="6" width="3" height="12" rx="1"/><rect x="16" y="13" width="3" height="5" rx="1"/>',
  camera: '<path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2.2l1.5-2h5.6l1.5 2h2.2A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5z"/><circle cx="12" cy="13" r="3.4"/>',
  trophy: '<path d="M8 4h8v5a4 4 0 0 1-8 0zM8 6H5a3 3 0 0 0 3 4M16 6h3a3 3 0 0 1-3 4M12 13v4M9 20h6M10 17h4"/>',
  feather: '<path d="M19 5c-6 0-11 5-11 11v3h3c6 0 11-5 11-11V5z"/><path d="M5 19 15 9"/>',
  moneybag: '<path d="M9 4h6l-1.5 3h-3zM10.5 7C6 9 4.5 13 5 16.5 5.4 19 7.5 20 12 20s6.6-1 7-3.5C19.5 13 18 9 13.5 7"/><path d="M12 10.5v6M14 11.8c-.5-.6-1.2-.8-2-.8-1.1 0-2 .6-2 1.5s.9 1.3 2 1.5 2 .6 2 1.5-.9 1.5-2 1.5c-.9 0-1.6-.3-2-.9"/>',
  calendar: '<rect x="4" y="5.5" width="16" height="14.5" rx="2.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
  follow: '<path d="M3 12a9 9 0 0 1 9-9M21 12a9 9 0 0 1-9 9"/><circle cx="12" cy="12" r="3.2"/>',
};

export function icon(name, cls = '') {
  return raw(`<svg class="i ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || ''}</svg>`);
}
export const MODE_ICON = { walk: 'walk', taxi: 'taxi', train: 'train', ferry: 'ferry', airline: 'ticket', reposition: 'reposition' };
