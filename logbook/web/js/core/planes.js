// Top-down aircraft silhouettes (nose up, 64x64) and logbook type designators,
// picked from the NeoFly/MSFS aircraft name.

const SHAPES = {
  // high-wing single: Cessna 152 / 172 / 182 / 208
  highwing: `<path d="M30.3 5.5c.6-1.6 2.8-1.6 3.4 0l.9 3.2.3 11.3H58a1.6 1.6 0 0 1 1.6 1.6v4.3a1.6 1.6 0 0 1-1.6 1.6H35l-.5 18.6 7.6 1.1a1.3 1.3 0 0 1 1.1 1.3v2.9a1.3 1.3 0 0 1-1.3 1.3H33.6l-.6 3.8h-2l-.6-3.8h-8.3a1.3 1.3 0 0 1-1.3-1.3v-2.9a1.3 1.3 0 0 1 1.1-1.3l7.6-1.1-.5-18.6H6a1.6 1.6 0 0 1-1.6-1.6v-4.3A1.6 1.6 0 0 1 6 20h23.1l.3-11.3z"/><rect x="26" y="3.2" width="12" height="1.6" rx=".8" opacity=".7"/>`,
  // low-wing single: Piper Comanche / Bonanza / TBM
  lowwing: `<path d="M30.4 5c.5-1.5 2.7-1.5 3.2 0l1 3.8.4 13.6 21.6 2.4a2 2 0 0 1 1.8 2v2.8a1.6 1.6 0 0 1-1.8 1.6l-21.6-1.4-.6 18 7.4 1.5a1.3 1.3 0 0 1 1 1.3v2.6a1.2 1.2 0 0 1-1.4 1.2l-7.8-.6-.6 3.4h-2l-.6-3.4-7.8.6a1.2 1.2 0 0 1-1.4-1.2v-2.6a1.3 1.3 0 0 1 1-1.3l7.4-1.5-.6-18-21.6 1.4a1.6 1.6 0 0 1-1.8-1.6v-2.8a2 2 0 0 1 1.8-2l21.6-2.4.4-13.6z"/><rect x="26" y="2.6" width="12" height="1.6" rx=".8" opacity=".7"/>`,
  // twin piston: Baron / Aerostar / Seneca
  twin: `<path d="M30.4 4.6c.5-1.6 2.7-1.6 3.2 0l1 4 .4 14.4 22.2 2a2 2 0 0 1 1.8 2v2.6a1.6 1.6 0 0 1-1.8 1.6l-22.2-1-.6 17.4 7.6 1.5a1.3 1.3 0 0 1 1 1.3v2.6a1.2 1.2 0 0 1-1.4 1.2l-8-.6-.6 3.4h-2l-.6-3.4-8 .6a1.2 1.2 0 0 1-1.4-1.2v-2.6a1.3 1.3 0 0 1 1-1.3l7.6-1.5-.6-17.4-22.2 1a1.6 1.6 0 0 1-1.8-1.6V27a2 2 0 0 1 1.8-2l22.2-2 .4-14.4z"/><path d="M15.6 14.5c.4-1.4 2.4-1.4 2.8 0l.9 3.5v16.2a2.3 2.3 0 0 1-4.6 0V18zM45.6 14.5c.4-1.4 2.4-1.4 2.8 0l.9 3.5v16.2a2.3 2.3 0 0 1-4.6 0V18z"/><rect x="11" y="12.4" width="12" height="1.4" rx=".7" opacity=".7"/><rect x="41" y="12.4" width="12" height="1.4" rx=".7" opacity=".7"/>`,
  // business jet: Citation X / Longitude / CJ
  jet: `<path d="M30.2 3.6c.6-2 3-2 3.6 0l1.2 5.4.3 13.5 22 13.2a1.8 1.8 0 0 1 .9 1.5v2.4a1.1 1.1 0 0 1-1.5 1l-21.4-7.4-.4 9.6 2.6 2.4 5.6-1a1.3 1.3 0 0 1 1.4.8l.4 1a1.2 1.2 0 0 1-.5 1.4l-8.8 5.5-.8 3.2h-1.6l-.8-3.2-8.8-5.5a1.2 1.2 0 0 1-.5-1.4l.4-1a1.3 1.3 0 0 1 1.4-.8l5.6 1 2.6-2.4-.4-9.6-21.4 7.4a1.1 1.1 0 0 1-1.5-1v-2.4a1.8 1.8 0 0 1 .9-1.5l22-13.2.3-13.5z"/><rect x="24.4" y="38" width="4" height="10" rx="2"/><rect x="35.6" y="38" width="4" height="10" rx="2"/>`,
  // airliner
  airliner: `<path d="M30.2 3c.6-2 3-2 3.6 0l1 5 .4 15 23 12a1.6 1.6 0 0 1 .8 1.4v2.8l-23.8-7.4-.6 15 6 4.4a1 1 0 0 1 .4.8V54l-7.6-2.4-.8 3.8h-1.2l-.8-3.8L22.4 54v-1.8a1 1 0 0 1 .4-.8l6-4.4-.6-15-23.8 7.4v-2.8a1.6 1.6 0 0 1 .8-1.4l23-12 .4-15z"/><rect x="15" y="30" width="4" height="8" rx="2"/><rect x="45" y="30" width="4" height="8" rx="2"/>`,
  // helicopter
  heli: `<ellipse cx="32" cy="26" rx="6" ry="9"/><rect x="31" y="33" width="2" height="22" rx="1"/><rect x="26" y="52" width="12" height="2" rx="1"/><path d="M8 24.5 56 27.5M33.5 2 30.5 50" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".55"/>`,
};

const RULES = [
  [/citation|c750|longitude|cj[1-4]|learjet|phenom|hondajet|vision jet|sf50/i, 'jet', null],
  [/a3[1-9]0|a32|b7[0-9]7|737|747|777|787|crj|e1[79]0|atr/i, 'airliner', null],
  [/h1[23]5|ec1[23]5|bell|robinson|r44|r22|cabri|helicopter/i, 'heli', null],
  [/baron|aerostar|seneca|da62|da42|twin|kingair|king air|p2006|be58/i, 'twin', null],
  [/comanche|bonanza|tbm|pa-?28|cherokee|archer|cirrus|sr22|mooney|da40|pc-?12/i, 'lowwing', null],
  [/c1[5-9]\d|cessna 1|c208|caravan|cub|kodiak|savage|husky/i, 'highwing', null],
];
const TYPES = [
  [/citation\s*x|c750/i, 'C750'], [/c152|cessna 152/i, 'C152'], [/c172|cessna 172/i, 'C172'], [/black square.*baron|b58p|58p/i, 'BE58'],
  [/baron/i, 'BE58'], [/comanche|pa-?24/i, 'PA24'], [/aerostar/i, 'AEST'], [/a320/i, 'A20N'], [/h135/i, 'EC35'], [/longitude/i, 'C700'],
];

export function shapeFor(ac) {
  const s = `${ac?.name || ''} ${ac?.livery || ''}`;
  for (const [rx, shape] of RULES) if (rx.test(s)) return shape;
  return (ac?.engines || 1) > 1 ? 'twin' : 'lowwing';
}
export function planeSvg(ac, cls = '') {
  return `<svg class="${cls}" viewBox="0 0 64 64" fill="currentColor">${SHAPES[shapeFor(ac)]}</svg>`;
}
export function typeCode(ac) {
  const s = `${ac?.name || ''} ${ac?.livery || ''}`;
  for (const [rx, t] of TYPES) if (rx.test(s)) return t;
  return (ac?.name || '').split(' ').slice(-1)[0].toUpperCase().slice(0, 4);
}
// registration from the livery name (N513LW, G-ABCD, NI22PC); else none
export function registration(ac) {
  const m = (ac?.tail || '') || `${ac?.livery || ''}`.match(/\b([A-Z]{1,2}-[A-Z0-9]{3,5}|N[0-9][0-9A-Z]{1,4}|N[A-Z][0-9A-Z]{2,4})\b/)?.[1];
  return m || '';
}
