#!/usr/bin/env node
// Generates true-scale laser-cut overlay drawings for VIRPIL Control Panels from measured data.
//   node make-overlays.js [panels.json] [outDir]
// Output per panel: <name>.dxf (import this into Fusion, units = mm), <name>.svg, <name>.pdf (print at 100%).
// Coordinates are millimetres, origin = bottom-left corner of the plate, X right, Y up.
'use strict';
const fs = require('fs');
const path = require('path');

const main = require.main === module;
const src = (main && process.argv[2]) || path.join(__dirname, 'panels.json');
const outDir = (main && process.argv[3]) || path.join(__dirname, 'out');
const cfg = JSON.parse(fs.readFileSync(src, 'utf8'));
const defaultClearance = Number(cfg.hole_clearance_mm || 0);
if (main) fs.mkdirSync(outDir, { recursive: true });

// ---------- geometry ----------
// Primitives: {t:'line',a:[x1,y1,x2,y2]} {t:'arc',a:[cx,cy,r,deg0,deg1]} (CCW) {t:'circle',a:[cx,cy,r]} {t:'text',a:[x,y,h,str]}
function roundedRect(cx, cy, w, h, r, layer) {
  r = Math.max(0, Math.min(r || 0, w / 2, h / 2));
  const x0 = cx - w / 2, x1 = cx + w / 2, y0 = cy - h / 2, y1 = cy + h / 2, p = [];
  const L = (a, b, c, d) => { if (Math.hypot(c - a, d - b) > 1e-9) p.push({ t: 'line', layer, a: [a, b, c, d] }); };
  L(x0 + r, y0, x1 - r, y0); L(x1, y0 + r, x1, y1 - r); L(x1 - r, y1, x0 + r, y1); L(x0, y1 - r, x0, y0 + r);
  if (r > 0) {
    p.push({ t: 'arc', layer, a: [x1 - r, y0 + r, r, 270, 360] }, { t: 'arc', layer, a: [x1 - r, y1 - r, r, 0, 90] },
           { t: 'arc', layer, a: [x0 + r, y1 - r, r, 90, 180] }, { t: 'arc', layer, a: [x0 + r, y0 + r, r, 180, 270] });
  }
  return p;
}
function filletPoly(pts, rDefault, layer) {
  // Closed polygon with corners rounded (like a FreeCAD Draft wire with FilletRadius). A point's optional 3rd value overrides the radius.
  const n = pts.length, p = [], ends = [];
  for (let i = 0; i < n; i++) {
    const P = pts[i], A = pts[(i + n - 1) % n], B = pts[(i + 1) % n], r = P[2] ?? rDefault;
    const la = Math.hypot(A[0] - P[0], A[1] - P[1]), lb = Math.hypot(B[0] - P[0], B[1] - P[1]);
    const u1 = [(A[0] - P[0]) / la, (A[1] - P[1]) / la], u2 = [(B[0] - P[0]) / lb, (B[1] - P[1]) / lb];
    const th = Math.acos(Math.max(-1, Math.min(1, u1[0] * u2[0] + u1[1] * u2[1])));
    if (!(r > 0) || th > Math.PI - 1e-6) { ends.push([P, P]); continue; }
    const t = Math.min(r / Math.tan(th / 2), la / 2, lb / 2), rr = t * Math.tan(th / 2);
    const T1 = [P[0] + u1[0] * t, P[1] + u1[1] * t], T2 = [P[0] + u2[0] * t, P[1] + u2[1] * t];
    const bi = [u1[0] + u2[0], u1[1] + u2[1]], bl = Math.hypot(...bi), dc = rr / Math.sin(th / 2);
    const C = [P[0] + bi[0] / bl * dc, P[1] + bi[1] / bl * dc];
    const a1 = Math.atan2(T1[1] - C[1], T1[0] - C[0]) * 180 / Math.PI, a2 = Math.atan2(T2[1] - C[1], T2[0] - C[0]) * 180 / Math.PI;
    const sw = ((a2 - a1) % 360 + 360) % 360;
    p.push(sw <= 180 ? { t: 'arc', layer, a: [C[0], C[1], rr, a1, a1 + sw] } : { t: 'arc', layer, a: [C[0], C[1], rr, a2, a2 + 360 - sw] });
    ends.push([T1, T2]);
  }
  for (let i = 0; i < n; i++) { const a = ends[i][1], b = ends[(i + 1) % n][0]; if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 1e-9) p.push({ t: 'line', layer, a: [a[0], a[1], b[0], b[1]] }); }
  return p;
}
function rotate(prims, cx, cy, deg) {
  if (!deg) return prims;
  const c = Math.cos(deg * Math.PI / 180), s = Math.sin(deg * Math.PI / 180);
  const R = (x, y) => [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
  return prims.map(p => {
    if (p.t === 'line') return { ...p, a: [...R(p.a[0], p.a[1]), ...R(p.a[2], p.a[3])] };
    if (p.t === 'arc') return { ...p, a: [...R(p.a[0], p.a[1]), p.a[2], p.a[3] + deg, p.a[4] + deg] };
    return { ...p, a: [...R(p.a[0], p.a[1]), ...p.a.slice(2)] };
  });
}

// ---------- clean contours: overlapping cut shapes merged into single closed outlines, true lines/arcs kept ----------
const TAU = 2 * Math.PI, rad = d => d * Math.PI / 180;
const arcSpan = p => p.t === 'circle' ? [0, 360] : [p.a[3], ((p.a[4] - p.a[3]) % 360 + 360) % 360 || 360];
function primPoint(p, u) { // u in [0,1] along the primitive
  if (p.t === 'line') return [p.a[0] + (p.a[2] - p.a[0]) * u, p.a[1] + (p.a[3] - p.a[1]) * u];
  const [a0, sw] = arcSpan(p), t = rad(a0 + sw * u); return [p.a[0] + p.a[2] * Math.cos(t), p.a[1] + p.a[2] * Math.sin(t)];
}
function tess(p, sag = 1e-4) {
  if (p.t === 'line') return [[p.a[0], p.a[1]], [p.a[2], p.a[3]]];
  const sw = arcSpan(p)[1], n = Math.max(2, Math.ceil(rad(sw) / (2 * Math.acos(1 - Math.min(sag / p.a[2], 1)))));
  return Array.from({ length: n + 1 }, (_, i) => primPoint(p, i / n));
}
function shapeOf(prims) { // segment soup for inside / distance tests
  const segs = []; let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of prims) { const q = tess(p); for (let i = 1; i < q.length; i++) { segs.push([...q[i - 1], ...q[i]]); for (const v of [q[i - 1], q[i]]) { x0 = Math.min(x0, v[0]); x1 = Math.max(x1, v[0]); y0 = Math.min(y0, v[1]); y1 = Math.max(y1, v[1]); } } }
  return { segs, box: [x0, y0, x1, y1] };
}
function inside(sh, x, y) {
  const [x0, y0, x1, y1] = sh.box; if (x < x0 || x > x1 || y < y0 || y > y1) return false;
  let c = false; for (const s of sh.segs) if ((s[1] > y) !== (s[3] > y) && x < (s[2] - s[0]) * (y - s[1]) / (s[3] - s[1]) + s[0]) c = !c; return c;
}
function nearest(sh, x, y) {
  let best = Infinity, q = null;
  for (const s of sh.segs) { const dx = s[2] - s[0], dy = s[3] - s[1], t = Math.max(0, Math.min(1, ((x - s[0]) * dx + (y - s[1]) * dy) / (dx * dx + dy * dy || 1)));
    const px = s[0] + t * dx, py = s[1] + t * dy, d = Math.hypot(x - px, y - py); if (d < best) { best = d; q = [px, py]; } }
  return { d: best, q };
}
function params(p, X, Y) { // parameter u in [0,1] of point (X,Y) on p, or null if off its span
  if (p.t === 'line') { const dx = p.a[2] - p.a[0], dy = p.a[3] - p.a[1], u = ((X - p.a[0]) * dx + (Y - p.a[1]) * dy) / (dx * dx + dy * dy); return u > -1e-9 && u < 1 + 1e-9 ? Math.min(1, Math.max(0, u)) : null; }
  const [a0, sw] = arcSpan(p), ang = ((Math.atan2(Y - p.a[1], X - p.a[0]) * 180 / Math.PI - a0) % 360 + 360) % 360;
  if (sw === 360) return ang / 360; return ang <= sw + 1e-7 ? Math.min(1, ang / sw) : (ang > 360 - 1e-7 ? 0 : null);
}
function intersect(p, q) { // points where primitives p and q cross
  const pts = [], L = r => r.t === 'line', C = r => [r.a[0], r.a[1], r.a[2]];
  const lineCircle = (l, c) => { const [x1, y1, x2, y2] = l.a, [cx, cy, r] = C(c), dx = x2 - x1, dy = y2 - y1, A = dx * dx + dy * dy, B = 2 * (dx * (x1 - cx) + dy * (y1 - cy)), D = B * B - 4 * A * ((x1 - cx) ** 2 + (y1 - cy) ** 2 - r * r);
    if (D < -1e-12) return []; const s = Math.sqrt(Math.max(D, 0)); return [(-B - s) / (2 * A), (-B + s) / (2 * A)].map(t => [x1 + t * dx, y1 + t * dy]); };
  let cand;
  if (L(p) && L(q)) { const [x1, y1, x2, y2] = p.a, [x3, y3, x4, y4] = q.a, d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3);
    if (Math.abs(d) < 1e-12) return []; const t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d; cand = [[x1 + t * (x2 - x1), y1 + t * (y2 - y1)]]; }
  else if (L(p)) cand = lineCircle(p, q); else if (L(q)) cand = lineCircle(q, p);
  else { const [x1, y1, r1] = C(p), [x2, y2, r2] = C(q), d = Math.hypot(x2 - x1, y2 - y1);
    if (d < 1e-12 || d > r1 + r2 + 1e-9 || d < Math.abs(r1 - r2) - 1e-9) return [];
    const a = (r1 * r1 - r2 * r2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, r1 * r1 - a * a)), mx = x1 + a * (x2 - x1) / d, my = y1 + a * (y2 - y1) / d;
    cand = [[mx + h * (y2 - y1) / d, my - h * (x2 - x1) / d], [mx - h * (y2 - y1) / d, my + h * (x2 - x1) / d]]; }
  for (const c of cand) if (params(p, ...c) !== null && params(q, ...c) !== null) pts.push(c);
  return pts;
}
// groups: [{id, outline:bool, prims}] -> boundary pieces of (outline minus all holes)
function mergeContours(groups) {
  const shapes = groups.map(g => shapeOf(g.prims)), out = [], warnings = [], seen = new Set();
  const material = (x, y) => inside(shapes[0], x, y) && !shapes.some((sh, i) => i > 0 && inside(sh, x, y));
  groups.forEach((g, gi) => g.prims.forEach(p => {
    let us = [0, 1];
    groups.forEach((h, hi) => { if (hi !== gi) for (const q of h.prims) for (const c of intersect(p, q)) us.push(params(p, ...c)); });
    const len = p.t === 'line' ? Math.hypot(p.a[2] - p.a[0], p.a[3] - p.a[1]) : rad(arcSpan(p)[1]) * p.a[2];
    us.sort((a, b) => a - b); const uu = [];
    for (const u of us) if (!uu.length || (u - uu[uu.length - 1]) * len > 1e-5) uu.push(u); else if (u === 1) uu[uu.length - 1] = 1;
    if (uu[uu.length - 1] !== 1) uu.push(1);
    const full = p.t === 'circle', pieces = [];
    for (let i = 0; i + 1 < uu.length; i++) pieces.push([uu[i], uu[i + 1]]);
    for (const [u0, u1] of pieces) {
      // keep a piece only where there is material on exactly one side of it (robust for shared / coincident edges)
      // test at the point of the piece furthest from every other contour (near-tangent pieces can be ~0.001 mm from one)
      let um = (u0 + u1) / 2, clear = -1;
      for (const f of [0.5, 0.3, 0.7, 0.15, 0.85, 0.05, 0.95]) {
        const u = u0 + (u1 - u0) * f, q = primPoint(p, u);
        let c = Infinity; groups.forEach((h, hi) => { if (hi === gi) return; const b = shapes[hi].box; if (q[0] < b[0] - 1 || q[0] > b[2] + 1 || q[1] < b[1] - 1 || q[1] > b[3] + 1) return; c = Math.min(c, nearest(shapes[hi], ...q).d); });
        if (c > clear) { clear = c; um = u; }
        if (clear > 0.01) break;
      }
      const m = primPoint(p, um), m2 = primPoint(p, um + 1e-6 * (um < 1 ? 1 : -1));
      let nx = -(m2[1] - m[1]), ny = m2[0] - m[0]; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
      const e = clear > 1e-6 ? Math.min(2e-3, clear / 2) : 2e-3, A = material(m[0] + nx * e, m[1] + ny * e), B = material(m[0] - nx * e, m[1] - ny * e);
      if (A === B) continue;
      const key = [primPoint(p, u0), m, primPoint(p, u1)].map(v => v.map(c => c.toFixed(4)).join(',')), k1 = key.join('|'), k2 = [...key].reverse().join('|');
      if (seen.has(k1) || seen.has(k2)) continue; seen.add(k1);
      if (full && pieces.length === 1) { out.push(p); continue; }
      if (p.t === 'line') out.push({ ...p, a: [...primPoint(p, u0), ...primPoint(p, u1)] });
      else { const [a0, sw] = arcSpan(p); out.push({ t: 'arc', layer: p.layer, a: [p.a[0], p.a[1], p.a[2], a0 + sw * u0, a0 + sw * u1] }); }
    }
  }));
  // Islands: material completely cut free (it would drop out of the sheet) is removed together with its boundary.
  const ends = out.map(p => p.t === 'circle' ? null : [primPoint(p, 0), primPoint(p, 1)]), used = new Set(), loops = [];
  out.forEach((p, i) => {
    if (used.has(i)) return; used.add(i);
    const loop = [i];
    if (p.t !== 'circle') {
      let [start, end] = ends[i];
      for (let guard = 0; guard < out.length && Math.hypot(end[0] - start[0], end[1] - start[1]) > 2e-3; guard++) {
        const j = out.findIndex((q, k) => !used.has(k) && ends[k] && (Math.hypot(ends[k][0][0] - end[0], ends[k][0][1] - end[1]) < 2e-3 || Math.hypot(ends[k][1][0] - end[0], ends[k][1][1] - end[1]) < 2e-3));
        if (j < 0) break;
        used.add(j); loop.push(j);
        end = Math.hypot(ends[j][0][0] - end[0], ends[j][0][1] - end[1]) < 2e-3 ? ends[j][1] : ends[j][0];
      }
    }
    loops.push(loop);
  });
  const ring = loop => { const pts = []; for (const i of loop) { const q = tess(out[i], 1e-3); const last = pts[pts.length - 1];
    if (last && Math.hypot(q[0][0] - last[0], q[0][1] - last[1]) > 2e-3) q.reverse(); pts.push(...(pts.length ? q.slice(1) : q)); } return pts; };
  const info = loops.map(loop => {
    const r = ring(loop), A = r.reduce((t, p, k) => { const q = r[(k + 1) % r.length]; return t + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;
    // a point just inside the loop (left of travel for CCW): is it material?
    const k = Math.floor(r.length / 2), a = r[k], b = r[k + 1] || r[0], dl = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, sg = A > 0 ? 1 : -1;
    const mx = (a[0] + b[0]) / 2 - sg * (b[1] - a[1]) / dl * 1e-3, my = (a[1] + b[1]) / 2 + sg * (b[0] - a[0]) / dl * 1e-3;
    return { loop, r, area: Math.abs(A), outer: material(mx, my), sh: { segs: r.map((p, k2) => [...p, ...r[(k2 + 1) % r.length]]), box: [Math.min(...r.map(p => p[0])), Math.min(...r.map(p => p[1])), Math.max(...r.map(p => p[0])), Math.max(...r.map(p => p[1]))] } };
  });
  const outers = info.filter(l => l.outer).sort((x, y) => y.area - x.area), drop = new Set(), islands = [];
  for (const isl of outers.slice(1)) {
    islands.push({ area: isl.area, sh: isl.sh });
    for (const l of info) if (l === isl || (!l.outer && inside(isl.sh, ...l.r[0]))) for (const i of l.loop) drop.add(i);
  }
  return { prims: out.filter((p, i) => !drop.has(i)), warnings: [...new Set(warnings)], islands };
}

function featurePrims(f, c, layer) {
  if (f.type === 'circle') return [{ t: 'circle', layer, a: [f.x, f.y, (f.d + c) / 2] }];
  if (f.type === 'rect' || f.type === 'slot') {
    const w = f.w + c, h = f.h + c, r = f.type === 'slot' ? Math.min(w, h) / 2 : (f.r || 0) + (f.r ? c / 2 : 0);
    return rotate(roundedRect(f.x, f.y, w, h, r, layer), f.x, f.y, f.angle || 0);
  }
  if (f.type === 'poly') return filletPoly(f.points.map(([px, py]) => [f.x + px, f.y + py]), f.fillet || 0, layer);
  return [];
}

function buildPanel(name, panel) {
  const o = panel.outline, prims = [], problems = [], notes = [], cutGroups = [];
  const clearance = Number(panel.hole_clearance_mm ?? defaultClearance);
  // outline: rounded rectangle, or a polygon of [x, y, cornerRadius] points (e.g. the L-shaped CM3 throttle plate)
  cutGroups.push({ id: 'plate edge', outline: true, prims: o.points ? filletPoly(o.points, 0, 'CUT') : roundedRect(o.w / 2, o.h / 2, o.w, o.h, o.corner_r, 'CUT') });
  // screw_holes: "through" = cut every screw position right through (laser), true = keep the original layers (POCKET recesses), false = leave them out
  const screwMode = panel.screw_holes ?? cfg.screw_holes ?? true, screwHoles = screwMode !== false;
  for (const f of panel.features || []) {
    if (f.screw && !screwHoles) continue;
    const id = f.id || '?', c = f.no_clearance ? 0 : clearance;
    const layer = f.screw && screwMode === 'through' ? 'CUT' : f.layer || (f.type === 'text' ? 'ENGRAVE' : 'CUT');
    if (![f.x, f.y].every(Number.isFinite)) { problems.push(`${id}: missing x/y`); continue; }
    if (f.type === 'circle' && !(f.d > 0)) { problems.push(`${id}: missing d`); continue; }
    if ((f.type === 'rect' || f.type === 'slot') && !(f.w > 0 && f.h > 0)) { problems.push(`${id}: missing w/h`); continue; }
    if (f.type === 'poly' && (!Array.isArray(f.points) || f.points.length < 3)) { problems.push(`${id}: poly needs 3+ points`); continue; }
    if (f.type === 'circle' || f.type === 'rect' || f.type === 'slot' || f.type === 'poly') {
      const fp = featurePrims(f, c, layer);
      if (layer === 'CUT') cutGroups.push({ id, screw: !!f.screw, f, prims: fp }); else prims.push(...fp);
    } else if (f.type === 'text') {
      prims.push({ t: 'text', layer, a: [f.x, f.y, f.h || 3, String(f.text || '')], align: f.align || 'center' });
    } else problems.push(`${id}: unknown type ${f.type}`);
    if (cfg.id_labels !== false && f.type !== 'text' && f.id && !f.no_id) prims.push({ t: 'text', layer: 'IDS', a: [f.x + (f.id_dx || 0), f.y + (f.id_dy || 0) - 1, 2, f.id], align: 'center' });
    if (!f.edge && (f.type === 'circle' || f.type === 'rect' || f.type === 'slot')) {
      let ex, ey;
      if (f.type === 'circle') ex = ey = (f.d + c) / 2;
      else {
        const t = (f.angle || 0) * Math.PI / 180, w = (f.w + c) / 2, h = (f.h + c) / 2;
        ex = Math.abs(w * Math.cos(t)) + Math.abs(h * Math.sin(t)); ey = Math.abs(w * Math.sin(t)) + Math.abs(h * Math.cos(t));
      }
      if (f.x - ex < 0 || f.y - ey < 0 || f.x + ex > o.w || f.y + ey > o.h) problems.push(`${id}: extends past plate edge (check coordinates)`);
    }
  }
  // Laser-cut screw holes. In the 3D-printed original these were 2 mm-deep recesses on the back; cut right through, a
  // hole that ends up closer than min_web_mm to something else would leave a sliver that snaps or burns away.
  // One fixed rule set, applied identically everywhere, so every joint on a panel looks the same:
  //   screw diagonally off a control opening's corner -> full-width bridge aimed straight at that corner
  //   screw overlapping an opening's edge (CP3 style)  -> left as a round "ear"; a hairline neck to the corner is filled
  //   screw at the plate edge                         -> straight full-width notch out through the edge
  //   edge screw + screw + opening in a row            -> one straight channel of constant width (no zig-zag)
  //   two screws too close otherwise                   -> one slot with straight tangent sides
  const minWeb = Number(panel.min_web_mm ?? cfg.min_web_mm ?? 1.0), bridges = [];
  if (screwMode === 'through') {
    const shapes = new Map(cutGroups.map(g => [g, shapeOf(g.prims)]));
    const plate = cutGroups[0], screws = cutGroups.filter(g => g.screw), openings = cutGroups.filter(g => !g.screw && !g.outline);
    const circ = g => g.prims[0].a;
    const addJoin = (id, s, to, web, prims, f) => { const b = { id, bridge: true, f, prims }; bridges.push({ screw: s.id, to, web }); cutGroups.push(b); shapes.set(b, shapeOf(prims)); };
    const corners = g => {
      const f = g.f;
      if (f.type === 'rect') { const t = rad(f.angle || 0), c = Math.cos(t), sn = Math.sin(t); return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([i, j]) => { const dx = i * f.w / 2, dy = j * f.h / 2; return [f.x + dx * c - dy * sn, f.y + dx * sn + dy * c]; }); }
      if (f.type === 'poly') return f.points.map(([px, py]) => [f.x + px, f.y + py]);
      return [];
    };
    // straight bridge of half-width hw from the screw centre along u, long enough that its far end sits >= 0.5 mm
    // inside the target opening (or outside the plate)
    const bridge = (s, g, u, hw) => {
      const [cx, cy] = circ(s), sh = shapes.get(g), nv = [-u[1], u[0]];
      const ok = (x, y) => (g.outline ? !inside(sh, x, y) : inside(sh, x, y)) && nearest(sh, x, y).d >= 0.5;
      for (let l = 0.5; l <= 4 * hw + 12; l += 0.05) {
        const F = [cx + u[0] * l, cy + u[1] * l];
        if (ok(F[0] + nv[0] * hw, F[1] + nv[1] * hw) && ok(F[0] - nv[0] * hw, F[1] - nv[1] * hw) && ok(...F)) {
          const ang = Math.atan2(u[1], u[0]) * 180 / Math.PI, bx = cx + u[0] * l / 2, by = cy + u[1] * l / 2;
          return { f: { type: 'rect', x: bx, y: by, w: l, h: 2 * hw, angle: ang }, prims: rotate(roundedRect(bx, by, l, 2 * hw, 0, 'CUT'), bx, by, ang) };
        }
      }
      return null;
    };
    const unit = (a, b) => { const d = Math.hypot(b[0] - a[0], b[1] - a[1]); return [(b[0] - a[0]) / d, (b[1] - a[1]) / d]; };

    // what each screw needs
    const need = new Map(screws.map(s => [s, { edge: null, open: [] }]));
    for (const s of screws) {
      const [cx, cy, r] = circ(s), n = need.get(s);
      const e = nearest(shapes.get(plate), cx, cy); if (e.d - r < minWeb) n.edge = { web: e.d - r, u: unit([cx, cy], e.q) };
      for (const g of openings) {
        const sh = shapes.get(g); if (inside(sh, cx, cy)) continue;
        const { d, q } = nearest(sh, cx, cy); if (d - r >= minWeb) continue;
        const cs = corners(g).map(P => [P, Math.hypot(P[0] - cx, P[1] - cy)]).sort((m, k) => m[1] - k[1]);
        n.open.push({ g, web: d - r, P: cs.length && cs[0][1] - d < r ? cs[0][0] : q, q });
      }
    }
    const pairs = [];
    screws.forEach((a, i) => screws.slice(i + 1).forEach(b => { const [x1, y1, r1] = circ(a), [x2, y2, r2] = circ(b), d = Math.hypot(x2 - x1, y2 - y1); if (d - r1 - r2 < minWeb && d > Math.abs(r1 - r2)) pairs.push([a, b, d - r1 - r2]); }));

    // edge screw + neighbour screw + opening in a row: one straight channel of the larger screw's width
    const done = new Set();
    for (const [a, b, web] of pairs) {
      const e = need.get(a).edge ? a : need.get(b).edge ? b : null, o = e === a ? b : a;
      const oo = e && (need.get(o).open[0] || need.get(e).open[0]);
      if (!e || !oo) continue;
      const hw = Math.max(circ(a)[2], circ(b)[2]), A = circ(e), u = unit(A, oo.P);
      const off = (s) => { const c = circ(s); return Math.abs((c[0] - A[0]) * u[1] - (c[1] - A[1]) * u[0]) + c[2]; };
      if (off(o) > hw + 1e-6) continue; // not in a row: fall back to separate joints
      const inner = bridge(e, oo.g, u, hw), outer = bridge(e, plate, [-u[0], -u[1]], hw);
      if (!inner || !outer) continue;
      addJoin(`${e.id}~${oo.g.id}`, e, `${o.id} + ${oo.g.id} (one straight channel)`, web, inner.prims, inner.f);
      addJoin(`${e.id}~edge`, e, 'plate edge (same channel)', need.get(e).edge.web, outer.prims, outer.f);
      done.add(a); done.add(b);
    }
    // screw <-> screw: tangent slot
    for (const [a, b, web] of pairs) {
      if (done.has(a) && done.has(b)) continue;
      const [x1, y1, r1] = circ(a), [x2, y2, r2] = circ(b), d = Math.hypot(x2 - x1, y2 - y1);
      const th = Math.atan2(y2 - y1, x2 - x1), ph = Math.acos((r1 - r2) / d), P = (x, y, r, t) => [x + r * Math.cos(t), y + r * Math.sin(t)];
      const q = [P(x1, y1, r1, th + ph), P(x2, y2, r2, th + ph), P(x2, y2, r2, th - ph), P(x1, y1, r1, th - ph)];
      addJoin(`${a.id}+${b.id}`, a, b.id, web, q.map((p, k) => ({ t: 'line', layer: 'CUT', a: [...p, ...q[(k + 1) % 4]] })), { type: 'poly', x: 0, y: 0, points: q });
    }
    for (const s of screws) {
      if (done.has(s)) continue;
      const [cx, cy, r] = circ(s), n = need.get(s);
      // screw <-> control opening
      for (const { g, web, P, q } of n.open) {
        const b = bridge(s, g, unit([cx, cy], P), r) || bridge(s, g, unit([cx, cy], q), r);
        if (b) { addJoin(`${s.id}>${g.id}`, s, g.id, web, b.prims, b.f); continue; }
        if (web >= 0) { problems.push(`${s.id}: ${web.toFixed(2)} mm from ${g.id} and no clean bridge fits; check it`); continue; }
        // overlapping the opening's edge: keep the round ear; fill a hairline neck to a nearby corner with tangent lines
        for (const V of corners(g)) {
          const D = Math.hypot(V[0] - cx, V[1] - cy), gap = D - r;
          if (!(gap > 0 && gap < minWeb)) continue;
          const phi = Math.atan2(V[1] - cy, V[0] - cx), beta = Math.acos(r / D), T = sgn => [cx + r * Math.cos(phi + sgn * beta), cy + r * Math.sin(phi + sgn * beta)];
          const t1 = T(1), t2 = T(-1);
          addJoin(`${s.id}>${g.id} corner`, s, `${g.id} (ear, corner neck filled)`, gap, [{ t: 'line', layer: 'CUT', a: [...V, ...t1] }, { t: 'line', layer: 'CUT', a: [...t1, ...t2] }, { t: 'line', layer: 'CUT', a: [...t2, ...V] }], { type: 'poly', x: 0, y: 0, points: [V, t1, t2] });
        }
        notes.push(`${s.id} overlaps the edge of ${g.id}: kept as a round ear`);
      }
      // screw <-> plate edge
      if (n.edge) {
        const b = bridge(s, plate, n.edge.u, r);
        if (b) addJoin(`${s.id}>edge`, s, 'plate edge', n.edge.web, b.prims, b.f);
        else problems.push(`${s.id}: ${n.edge.web.toFixed(2)} mm from the plate edge and no clean notch fits; check it`);
      }
    }
  }
  const merged = mergeContours(cutGroups);
  prims.unshift(...merged.prims);
  for (const w of merged.warnings) problems.push(`coincident edge: ${w}`);
  for (const { area: a } of merged.islands) notes.push(`a ${a.toFixed(0)} mm² strip was cut completely free by the through screw holes and is left out (it would drop out of the sheet)`);
  // Scale check, kept outside the plate on its own layer: a 50 mm bar and a 20 mm square.
  const sy = -12;
  prims.push({ t: 'line', layer: 'CHECK', a: [0, sy, 50, sy] }, { t: 'line', layer: 'CHECK', a: [0, sy - 2, 0, sy + 2] },
             { t: 'line', layer: 'CHECK', a: [50, sy - 2, 50, sy + 2] },
             ...roundedRect(70, sy, 20, 20, 0, 'CHECK'),
             { t: 'text', layer: 'CHECK', a: [0, sy - 18, 3, `${name}  |  bar = 50.00 mm, square = 20.00 mm  |  extra hole clearance +${clearance} mm  |  ${screwMode === "through" ? "screw holes" : screwHoles ? "screw recesses" : "no screw holes"}`], align: 'left' });
  return { prims, problems, notes, bridges, cutGroups, islands: merged.islands };
}

function bounds(prims) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
  for (const p of prims) {
    if (p.t === 'line') { add(p.a[0], p.a[1]); add(p.a[2], p.a[3]); }
    else if (p.t === 'circle' || p.t === 'arc') { add(p.a[0] - p.a[2], p.a[1] - p.a[2]); add(p.a[0] + p.a[2], p.a[1] + p.a[2]); }
    else if (p.t === 'text') { const w = p.a[2] * 0.6 * p.a[3].length; add(p.a[0] - (p.align === 'left' ? 0 : w / 2), p.a[1]); add(p.a[0] + (p.align === 'left' ? w : w / 2), p.a[1] + p.a[2]); }
  }
  return { x0, y0, x1, y1 };
}
const n = v => (Math.abs(v) < 1e-9 ? 0 : +v.toFixed(4));

// ---------- DXF (R12 ASCII, mm) ----------
function toDXF(prims) {
  const out = ['0', 'SECTION', '2', 'HEADER', '9', '$ACADVER', '1', 'AC1009', '9', '$INSUNITS', '70', '4', '9', '$MEASUREMENT', '70', '1', '0', 'ENDSEC',
    '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER', '70', '5'];
  for (const [l, col] of [['CUT', 1], ['POCKET', 6], ['ENGRAVE', 5], ['IDS', 8], ['CHECK', 3]]) out.push('0', 'LAYER', '2', l, '70', '0', '62', String(col), '6', 'CONTINUOUS');
  out.push('0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES');
  for (const p of prims) {
    const a = p.a;
    if (p.t === 'line') out.push('0', 'LINE', '8', p.layer, '10', n(a[0]), '20', n(a[1]), '30', 0, '11', n(a[2]), '21', n(a[3]), '31', 0);
    else if (p.t === 'circle') out.push('0', 'CIRCLE', '8', p.layer, '10', n(a[0]), '20', n(a[1]), '30', 0, '40', n(a[2]));
    else if (p.t === 'arc') out.push('0', 'ARC', '8', p.layer, '10', n(a[0]), '20', n(a[1]), '30', 0, '40', n(a[2]), '50', n(((a[3] % 360) + 360) % 360), '51', n(((a[4] % 360) + 360) % 360));
    else if (p.t === 'text') {
      out.push('0', 'TEXT', '8', p.layer, '10', n(a[0]), '20', n(a[1]), '30', 0, '40', n(a[2]), '1', a[3].replace(/[\r\n]/g, ' '));
      if (p.align !== 'left') out.push('72', '1', '11', n(a[0]), '21', n(a[1]), '31', 0);
    }
  }
  out.push('0', 'ENDSEC', '0', 'EOF');
  return out.join('\r\n') + '\r\n';
}

// ---------- SVG (mm units, Y flipped) ----------
function toSVG(prims, b, m) {
  const W = b.x1 - b.x0 + 2 * m, H = b.y1 - b.y0 + 2 * m, X = x => n(x - b.x0 + m), Y = y => n(b.y1 + m - y);
  const col = { CUT: '#ff0000', POCKET: '#d000d0', ENGRAVE: '#0000ff', IDS: '#888888', CHECK: '#00a000' }, s = [];
  s.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${n(W)}mm" height="${n(H)}mm" viewBox="0 0 ${n(W)} ${n(H)}">`);
  for (const p of prims) {
    const a = p.a, st = `fill="none" stroke="${col[p.layer] || '#000'}" stroke-width="0.1"`;
    if (p.t === 'line') s.push(`<line x1="${X(a[0])}" y1="${Y(a[1])}" x2="${X(a[2])}" y2="${Y(a[3])}" ${st}/>`);
    else if (p.t === 'circle') s.push(`<circle cx="${X(a[0])}" cy="${Y(a[1])}" r="${n(a[2])}" ${st}/>`);
    else if (p.t === 'arc') {
      const r0 = a[3] * Math.PI / 180, r1 = a[4] * Math.PI / 180, sweep = ((a[4] - a[3]) % 360 + 360) % 360;
      s.push(`<path d="M ${X(a[0] + a[2] * Math.cos(r0))} ${Y(a[1] + a[2] * Math.sin(r0))} A ${n(a[2])} ${n(a[2])} 0 ${sweep > 180 ? 1 : 0} 0 ${X(a[0] + a[2] * Math.cos(r1))} ${Y(a[1] + a[2] * Math.sin(r1))}" ${st}/>`);
    } else if (p.t === 'text') {
      const esc = a[3].replace(/&/g, '&amp;').replace(/</g, '&lt;');
      s.push(`<text x="${X(a[0])}" y="${Y(a[1])}" font-family="Arial, Helvetica, sans-serif" font-size="${n(a[2] * 1.4)}" text-anchor="${p.align === 'left' ? 'start' : 'middle'}" fill="${col[p.layer] || '#000'}">${esc}</text>`);
    }
  }
  s.push('</svg>');
  return s.join('\n') + '\n';
}

// ---------- PDF (1:1, page sized to drawing) ----------
function toPDF(prims, b, m) {
  // Real paper size (A4, else A3, portrait), drawing centred, so "Actual size" printing is unambiguous.
  const k = 72 / 25.4, dw = b.x1 - b.x0 + 2 * m, dh = b.y1 - b.y0 + 2 * m;
  const [pw, ph] = [[210, 297], [297, 420]].find(([w, h]) => dw <= w - 10 && dh <= h - 20) || [dw, dh + 14];
  const W = pw * k, H = ph * k, offX = (pw - dw) / 2 * k, offY = (ph - dh) / 2 * k;
  const P = (x, y) => `${(offX + (x - b.x0 + m) * k).toFixed(3)} ${(offY + (y - b.y0 + m) * k).toFixed(3)}`;
  const rgb = { CUT: '1 0 0', POCKET: '0.8 0 0.8', ENGRAVE: '0 0 1', IDS: '0.55 0.55 0.55', CHECK: '0 0.6 0' }, ops = ['0.283 w'];
  const arcOps = (cx, cy, r, d0, d1, move) => {
    let sweep = d1 - d0; while (sweep <= 0) sweep += 360;
    const segs = Math.ceil(sweep / 90 - 1e-9), step = sweep / segs * Math.PI / 180, out = [];
    let t = d0 * Math.PI / 180;
    if (move) out.push(`${P(cx + r * Math.cos(t), cy + r * Math.sin(t))} m`);
    for (let i = 0; i < segs; i++) {
      const t2 = t + step, q = 4 / 3 * Math.tan(step / 4);
      const p1 = [cx + r * (Math.cos(t) - q * Math.sin(t)), cy + r * (Math.sin(t) + q * Math.cos(t))];
      const p2 = [cx + r * (Math.cos(t2) + q * Math.sin(t2)), cy + r * (Math.sin(t2) - q * Math.cos(t2))];
      out.push(`${P(...p1)} ${P(...p2)} ${P(cx + r * Math.cos(t2), cy + r * Math.sin(t2))} c`); t = t2;
    }
    return out.join(' ');
  };
  for (const p of prims) {
    const a = p.a, c = rgb[p.layer] || '0 0 0';
    if (p.t === 'line') ops.push(`${c} RG ${P(a[0], a[1])} m ${P(a[2], a[3])} l S`);
    else if (p.t === 'circle') ops.push(`${c} RG ${arcOps(a[0], a[1], a[2], 0, 360, true)} h S`);
    else if (p.t === 'arc') ops.push(`${c} RG ${arcOps(a[0], a[1], a[2], a[3], a[4], true)} S`);
    else if (p.t === 'text') {
      const sz = a[2] * k * 1.4, str = a[3].replace(/[\\()]/g, ch => '\\' + ch).replace(/[^\x20-\x7e]/g, '?');
      const dx = p.align === 'left' ? 0 : -a[3].length * sz * 0.5 / 2 / k;
      ops.push(`${c} rg BT /F1 ${sz.toFixed(2)} Tf ${P(a[0] + dx, a[1])} Td (${str}) Tj ET`);
    }
  }
  ops.push(`0 0 0 rg BT /F1 8 Tf ${(10 * k).toFixed(2)} ${(H - 10 * k).toFixed(2)} Td (${pw === 210 ? 'A4' : pw === 297 ? 'A3' : 'Custom'} page. Print at 100% / Actual size - NOT fit-to-page. Check: green bar = 50 mm, square = 20 x 20 mm.) Tj ET`);
  const stream = ops.join('\n');
  const objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${W.toFixed(3)} ${H.toFixed(3)}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>`,
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`, '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'];
  let pdf = '%PDF-1.4\n'; const offs = [];
  objs.forEach((o, i) => { offs.push(Buffer.byteLength(pdf)); pdf += `${i + 1} 0 obj\n${o}\nendobj\n`; });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + offs.map(o => String(o).padStart(10, '0') + ' 00000 n \n').join('');
  pdf += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return pdf;
}

// ---------- run ----------
module.exports = { buildPanel, cfg, shapeOf, inside, nearest, tess };
if (require.main === module) {
let made = 0;
for (const [name, panel] of Object.entries(cfg.panels || {})) {
  const o = panel.outline;
  if (!o || !((o.w > 0 && o.h > 0) || o.points)) { console.log(`${name}: skipped (outline not measured yet)`); continue; }
  const { prims, problems, notes, bridges } = buildPanel(name, panel);
  const b = bounds(prims), m = 10, file = name.replace(/[^\w.-]+/g, '_');
  fs.writeFileSync(path.join(outDir, file + '.dxf'), toDXF(prims));
  fs.writeFileSync(path.join(outDir, file + '.svg'), toSVG(prims, b, m));
  fs.writeFileSync(path.join(outDir, file + '.pdf'), toPDF(prims, b, m), 'latin1');
  made++;
  console.log(`${name}: ${o.w} x ${o.h} mm, ${(panel.features || []).filter(f => !(f.screw && (panel.screw_holes ?? cfg.screw_holes ?? true) === false)).length} openings -> ${file}.dxf/.svg/.pdf${panel.verified ? '' : '  [NOT VERIFIED against the real panel]'}`);
  for (const b of bridges) console.log(`  join    ${b.screw} -> ${b.to} (${b.web < 0 ? 'overlapping' : b.web.toFixed(2) + ' mm apart'})`);
  for (const nt of notes) console.log(`  note    ${nt}`);
  for (const pr of problems) console.log(`  ! ${pr}`);
}
console.log(`${made} panel(s) written to ${outDir}`);
}
