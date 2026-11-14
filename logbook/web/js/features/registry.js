// Feature registry - the extension point for later stages (scrapbook, journal,
// other sims...). A feature is a plain object:
//
//   {
//     id: 'scrapbook',
//     init(ctx) {},                       // once, after data + map are ready
//     legSections(leg, ctx) -> [{title, el}]   // optional: extra blocks in the leg card
//     stopSections(stop, ctx) -> [{title, el}] // optional: extra blocks in airport popups
//   }
//
// ctx = { db, store, map, ui } where ui holds shared helpers (openPhotos, select...).
const features = [];

export function register(feature) {
  features.push(feature);
  return feature;
}

export const all = () => features.slice();

export function sectionsFor(kind, item, ctx) {
  const out = [];
  for (const f of features) {
    const fn = f[kind];
    if (typeof fn !== 'function') continue;
    try { out.push(...(fn.call(f, item, ctx) || [])); } catch (e) { console.error(`[${f.id}.${kind}]`, e); }
  }
  return out;
}
