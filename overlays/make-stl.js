#!/usr/bin/env node
// Writes a 3D-printable STL for every panel into out/, then checks each one.
//   node make-stl.js
// Every plate is the CUT layer of out/<name>.dxf extruded to 3 mm, so a print is exactly the same part as the laser cut.
// (The designer's original 3D-print versions of CP1 / CP2 / CM3, with blind screw recesses, are the 3MFs in source/printables/.)
// Needs polygon-clipping + earcut from ../.tools/stl-deps (npm install there if missing).
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const DEPS = path.join(__dirname, '..', '.tools', 'stl-deps', 'node_modules');
const pc = require(path.join(DEPS, 'polygon-clipping'));
const earcut = require(path.join(DEPS, 'earcut'));

const OUT = path.join(__dirname, 'out'), SRC = path.join(__dirname, 'source', 'printables');
const THICK = 3; // mm, same as the Printables plates
const ORIGINAL = {}; // name -> source 3MF to convert instead of extruding (none: all plates follow the laser DXF)
let failures = 0;
const check = (ok, msg) => { console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${msg}`); if (!ok) failures++; };

// ---------- 3MF -> triangles ----------
function unzipEntry(file, want) {
  const b = fs.readFileSync(file); let e = b.length - 22;
  while (b.readUInt32LE(e) !== 0x06054b50) e--;
  let p = b.readUInt32LE(e + 16);
  for (let i = 0, n = b.readUInt16LE(e + 10); i < n; i++) {
    const nl = b.readUInt16LE(p + 28), xl = b.readUInt16LE(p + 30), cl = b.readUInt16LE(p + 32), name = b.toString('utf8', p + 46, p + 46 + nl);
    if (name === want) {
      const lo = b.readUInt32LE(p + 42), m = b.readUInt16LE(p + 10), cs = b.readUInt32LE(p + 20);
      const d = b.subarray(lo + 30 + b.readUInt16LE(lo + 26) + b.readUInt16LE(lo + 28)); const raw = d.subarray(0, cs);
      return m === 8 ? zlib.inflateRawSync(raw) : raw;
    }
    p += 46 + nl + xl + cl;
  }
  throw new Error(`${want} not in ${file}`);
}
function trisFrom3MF(file) {
  const x = unzipEntry(file, '3D/3dmodel.model').toString('utf8');
  if (!/unit="millimeter"/.test(x)) throw new Error(`${file}: not in millimetres`);
  const V = [...x.matchAll(/<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/g)].map(m => [+m[1], +m[2], +m[3]]);
  return [...x.matchAll(/<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"/g)].map(m => [V[+m[1]], V[+m[2]], V[+m[3]]]);
}

// ---------- DXF CUT layer -> closed loops -> plate polygon ----------
function readDXF(file) {
  const L = fs.readFileSync(file, 'utf8').split(/\r?\n/), ents = []; let cur = null;
  for (let i = L.findIndex(l => l.trim() === 'ENTITIES') + 1; i < L.length - 1; i += 2) {
    const code = L[i].trim(), val = L[i + 1].trim();
    if (code === '0') { if (cur) ents.push(cur); cur = { type: val }; if (val === 'EOF') break; continue; }
    if (cur) cur[code] = isNaN(+val) ? val : +val;
  }
  return ents;
}
const SAG = 0.002; // max chord deviation from a true arc, mm
const arcPts = (cx, cy, r, a0, a1) => {
  const sweep = ((a1 - a0) % 360 + 360) % 360 || 360, step = 2 * Math.acos(1 - SAG / r) * 180 / Math.PI, n = Math.max(2, Math.ceil(sweep / step));
  return Array.from({ length: n + 1 }, (_, i) => { const t = (a0 + sweep * i / n) * Math.PI / 180; return [cx + r * Math.cos(t), cy + r * Math.sin(t)]; });
};
function plateFromDXF(file) {
  const ents = readDXF(file).filter(e => e['8'] === 'CUT'), loops = [], open = [];
  for (const e of ents) {
    if (e.type === 'CIRCLE') loops.push(arcPts(e['10'], e['20'], e['40'], 0, 360).slice(0, -1));
    else if (e.type === 'ARC') open.push(arcPts(e['10'], e['20'], e['40'], e['50'], e['51']));
    else if (e.type === 'LINE') open.push([[e['10'], e['20']], [e['11'], e['21']]]);
  }
  // chain lines/arcs end-to-end into closed loops
  const eq = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-3;
  while (open.length) {
    let chain = open.pop();
    for (let grown = true; grown && !eq(chain[0], chain[chain.length - 1]);) {
      grown = false;
      for (let i = 0; i < open.length; i++) {
        const s = open[i], end = chain[chain.length - 1];
        if (eq(s[0], end)) chain = chain.concat(s.slice(1));
        else if (eq(s[s.length - 1], end)) chain = chain.concat(s.slice(0, -1).reverse());
        else continue;
        open.splice(i, 1); grown = true; break;
      }
    }
    if (!eq(chain[0], chain[chain.length - 1])) throw new Error(`${file}: CUT contour does not close near ${chain[0].map(v => v.toFixed(2))}`);
    loops.push(chain.slice(0, -1));
  }
  const area = r => r.reduce((s, p, i) => { const q = r[(i + 1) % r.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;
  loops.sort((a, b) => Math.abs(area(b)) - Math.abs(area(a)));
  const close = r => [...r, r[0]];
  // biggest loop = plate edge; every other loop is removed (overlapping openings merge, openings over the edge become notches)
  const mp = pc.difference([close(loops[0])], ...loops.slice(1).map(r => [close(r)]));
  return { mp, loops, ringArea: area };
}
function extrude(mp, h) {
  const tris = [];
  for (const poly of mp) {
    // drop exactly collinear points first: earcut removes them internally, which would leave T-junctions against the walls
    const rings = poly.map(r => { let p = r.slice(0, -1);
      for (let changed = true; changed && p.length > 3;) { changed = false;
        p = p.filter((q, i) => { const a = p[(i + p.length - 1) % p.length], b = p[(i + 1) % p.length]; const keep = (q[1] - a[1]) * (b[0] - q[0]) - (q[0] - a[0]) * (b[1] - q[1]) !== 0; if (!keep) changed = true; return keep; }); }
      return p; }), flat = [], holes = [];
    for (const r of rings) { if (flat.length) holes.push(flat.length / 2); for (const p of r) flat.push(p[0], p[1]); }
    // triangulate a slightly rotated copy: openings whose edges line up exactly (e.g. a row of squares) otherwise make earcut drop
    // zero-area triangles and leave hairline gaps. Only the vertex order comes from the rotated copy; coordinates stay exact.
    const c = Math.cos(0.0123), sn = Math.sin(0.0123), rot = flat.map((v, i) => i % 2 ? flat[i - 1] * sn + v * c : v * c - flat[i + 1] * sn);
    const idx = earcut(rot, holes), P = i => [flat[2 * i], flat[2 * i + 1]];
    for (let i = 0; i < idx.length; i += 3) {
      let [a, b, c] = [P(idx[i]), P(idx[i + 1]), P(idx[i + 2])];
      if ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]) < 0) [b, c] = [c, b]; // make CCW
      tris.push([[...a, h], [...b, h], [...c, h]], [[...a, 0], [...c, 0], [...b, 0]]); // top faces up, bottom faces down
    }
    // walls: polygon-clipping gives outer rings CCW and holes CW, so the same winding faces outward for both
    for (const r of rings) for (let i = 0; i < r.length; i++) {
      const a = r[i], b = r[(i + 1) % r.length];
      tris.push([[...a, 0], [...b, 0], [...b, h]], [[...a, 0], [...b, h], [...a, h]]);
    }
  }
  return tris;
}

// ---------- STL write + checks ----------
function writeSTL(file, tris, name) {
  const b = Buffer.alloc(84 + 50 * tris.length);
  b.write(`VIRPIL ${name} overlay plate, mm`.padEnd(80, ' '), 0, 'ascii'); b.writeUInt32LE(tris.length, 80);
  tris.forEach((t, i) => {
    const o = 84 + 50 * i, u = t[1].map((v, k) => v - t[0][k]), w = t[2].map((v, k) => v - t[0][k]);
    const n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]], l = Math.hypot(...n) || 1;
    n.forEach((v, k) => b.writeFloatLE(v / l, o + 4 * k));
    t.forEach((p, j) => p.forEach((v, k) => b.writeFloatLE(v, o + 12 + 12 * j + 4 * k)));
  });
  fs.writeFileSync(file, b);
}
function readSTL(file) {
  const b = fs.readFileSync(file), n = b.readUInt32LE(80), tris = [];
  for (let i = 0; i < n; i++) { const o = 84 + 50 * i + 12; tris.push([0, 1, 2].map(j => [0, 1, 2].map(k => b.readFloatLE(o + 12 * j + 4 * k)))); }
  return tris;
}
function meshStats(tris) {
  // weld by float position, then every directed edge must be matched by exactly one reverse edge (closed, consistently oriented)
  const id = new Map(), key = p => p.map(v => v.toFixed(4)).join(','), vid = p => { const k = key(p); if (!id.has(k)) id.set(k, id.size); return id.get(k); };
  const dir = new Map(); let vol = 0, x0 = Infinity, y0 = Infinity, z0 = Infinity, x1 = -Infinity, y1 = -Infinity, z1 = -Infinity;
  for (const t of tris) {
    const v = t.map(vid);
    for (let j = 0; j < 3; j++) { const k = v[j] + '>' + v[(j + 1) % 3]; dir.set(k, (dir.get(k) || 0) + 1); }
    const [a, b, c] = t; vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
    for (const p of t) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); z0 = Math.min(z0, p[2]); z1 = Math.max(z1, p[2]); }
  }
  let bad = 0, nonManifold = 0;
  for (const [k, c] of dir) { const [a, b] = k.split('>'), r = dir.get(b + '>' + a) || 0; if (c !== r) bad++; else if (c > 1) nonManifold++; }
  return { bad, nonManifold, vol, size: [x1 - x0, y1 - y0, z1 - z0], min: [x0, y0, z0] };
}

const panels = JSON.parse(fs.readFileSync(path.join(__dirname, 'panels.json'), 'utf8')).panels;
for (const name of Object.keys(panels)) {
  console.log(`\n${name}`);
  const file = path.join(OUT, name + '.stl'), o = panels[name].outline;
  let tris, expectVol = null, dxfLoops = null;
  if (ORIGINAL[name]) {
    tris = trisFrom3MF(path.join(SRC, ORIGINAL[name]));
    console.log(`        source: original Printables model ${ORIGINAL[name]} (back-side screw-head recesses kept)`);
  } else {
    const { mp, loops, ringArea } = plateFromDXF(path.join(OUT, name + '.dxf'));
    tris = extrude(mp, THICK); dxfLoops = loops;
    expectVol = THICK * mp.reduce((s, poly) => s + poly.reduce((t, r, i) => t + (i ? -1 : 1) * Math.abs(ringArea(r.slice(0, -1))), 0), 0);
    console.log(`        source: out/${name}.dxf CUT layer extruded ${THICK} mm (${loops.length} contours -> ${mp.length} solid piece${mp.length > 1 ? 's' : ''})`);
    check(mp.length === 1, `plate is one piece (no loose islands)`);
  }
  writeSTL(file, tris, name);
  const back = readSTL(file), s = meshStats(back);
  check(back.length === tris.length, `${path.basename(file)} written and re-read: ${back.length} triangles, ${(fs.statSync(file).size / 1024).toFixed(0)} KB`);
  check(s.bad === 0 && (s.nonManifold === 0 || ORIGINAL[name]), `watertight, consistently oriented mesh (${s.bad} open edges)`);
  if (s.nonManifold) console.log(`  INFO  ${s.nonManifold / 2} shared seam edge(s) where the designer's half-circle edge recesses meet the plate side; slicers handle this, the mesh is still closed`);
  check(Math.abs(s.size[0] - o.w) < 0.01 && Math.abs(s.size[1] - o.h) < 0.01 && Math.abs(s.size[2] - THICK) < 0.01 && s.min.every(v => Math.abs(v) < 0.01),
    `size ${s.size.map(v => v.toFixed(3)).join(' x ')} mm at origin (should be ${o.w} x ${o.h} x ${THICK})`);
  check(s.vol > 0, `outward-facing normals (volume ${(s.vol / 1000).toFixed(2)} cm3)`);
  if (expectVol !== null) check(Math.abs(s.vol - expectVol) / expectVol < 1e-4, `volume = plate area x ${THICK} mm (${(expectVol / 1000).toFixed(2)} cm3)`);
  if (dxfLoops) {
    // every vertex on the top face boundary must lie on a DXF cut contour
    const segs = dxfLoops.flatMap(r => r.map((p, i) => [...p, ...r[(i + 1) % r.length]]));
    const dseg = (x, y, q) => { const dx = q[2] - q[0], dy = q[3] - q[1], t = Math.max(0, Math.min(1, ((x - q[0]) * dx + (y - q[1]) * dy) / (dx * dx + dy * dy || 1))); return Math.hypot(x - q[0] - t * dx, y - q[1] - t * dy); };
    const top = back.filter(t => t.every(p => Math.abs(p[2] - THICK) < 1e-4)).flat();
    let worst = 0; for (const p of top) worst = Math.max(worst, Math.min(...segs.map(q => dseg(p[0], p[1], q))));
    check(worst < 0.01, `every top-face vertex lies on the DXF cut lines (worst ${worst.toFixed(4)} mm)`);
  }
}
console.log(failures ? `\n${failures} check(s) FAILED` : '\nAll STL checks passed.');
process.exit(failures ? 1 : 0);
