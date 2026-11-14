#!/usr/bin/env node
// Lays all four overlay plates (CP1, CP2, CP3, CM3) out on one 600 x 400 mm acrylic sheet for the laser cutter.
//   node make-sheet.js [outDir]
// Output: out/sheet-600x400.svg / .dxf / .pdf, all at true scale (mm), CUT layer only.
// Panels are only rotated 90 deg and moved. The geometry comes straight from make-overlays.js and is never scaled.
'use strict';
const fs = require('fs');
const path = require('path');
const m = require('./make-overlays.js');

const outDir = process.argv[2] || path.join(__dirname, 'out');
const SHEET = { w: 600, h: 400 };
const MARGIN = 10, GAP = 10;     // edge margin and the gap between plates, mm
// Each 170 x 200 plate is turned 90 deg CCW (200 wide x 170 tall) so a 2 x 2 grid fits the sheet.
// Unrotated, two rows would need 2 x 200 = 400 mm with no margin at all.
// The plates sit in the bottom-left corner, which leaves the right-hand strip of the sheet as one usable offcut.
const LAYOUT = [
  { name: 'CP1', col: 0, row: 1 }, { name: 'CP2', col: 1, row: 1 },
  { name: 'CP3', col: 0, row: 0 }, { name: 'CM3', col: 1, row: 0 },
];
const ROT = 90;

function exactBounds(prims) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of prims) for (const [x, y] of m.tess(p)) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return { x0, y0, x1, y1, w: x1 - x0, h: y1 - y0 };
}
const length = prims => prims.reduce((s, p) => { const t = m.tess(p); for (let i = 1; i < t.length; i++) s += Math.hypot(t[i][0] - t[i - 1][0], t[i][1] - t[i - 1][1]); return s; }, 0);
const move = (prims, dx, dy) => prims.map(p => ({ ...p, a: [p.a[0] + dx, p.a[1] + dy, ...(p.t === 'line' ? [p.a[2] + dx, p.a[3] + dy] : p.a.slice(2))] }));

const sheet = [], placed = [], fails = [];
for (const L of LAYOUT) {
  const panel = m.cfg.panels[L.name];
  if (!panel) { fails.push(`${L.name} missing from panels.json`); continue; }
  const cut = m.buildPanel(L.name, panel).prims.filter(p => p.layer === 'CUT');
  const before = exactBounds(cut);
  const rot = m.rotate(cut, 0, 0, ROT), rb = exactBounds(rot);
  const cellW = before.h, cellH = before.w;   // rotated footprint
  const tx = MARGIN + L.col * (cellW + GAP), ty = MARGIN + L.row * (cellH + GAP);
  const fin = move(rot, tx - rb.x0, ty - rb.y0), fb = exactBounds(fin);
  sheet.push(...fin);
  placed.push({ name: L.name, b: fb });
  // Checks: same size (swapped by the rotation), same total cut length, same number of entities.
  if (Math.abs(fb.w - before.h) > 1e-6 || Math.abs(fb.h - before.w) > 1e-6) fails.push(`${L.name} size changed`);
  if (Math.abs(length(fin) - length(cut)) > 1e-6) fails.push(`${L.name} cut length changed`);
  if (fin.length !== cut.length) fails.push(`${L.name} entity count changed`);
  if (fb.x0 < -1e-9 || fb.y0 < -1e-9 || fb.x1 > SHEET.w + 1e-9 || fb.y1 > SHEET.h + 1e-9) fails.push(`${L.name} is off the sheet`);
  console.log(`${L.name}: ${before.w.toFixed(3)} x ${before.h.toFixed(3)} mm plate, rotated ${ROT} deg -> x ${fb.x0.toFixed(1)}..${fb.x1.toFixed(1)}, y ${fb.y0.toFixed(1)}..${fb.y1.toFixed(1)} mm, ${fin.length} cut entities, ${length(fin).toFixed(1)} mm of cut`);
}
for (let i = 0; i < placed.length; i++) for (let j = i + 1; j < placed.length; j++) {
  const a = placed[i].b, b = placed[j].b;
  const gap = Math.max(b.x0 - a.x1, a.x0 - b.x1, b.y0 - a.y1, a.y0 - b.y1);
  if (gap < GAP - 1e-6) fails.push(`${placed[i].name} and ${placed[j].name} are only ${gap.toFixed(2)} mm apart`);
}

const all = exactBounds(sheet);
const page = { x0: 0, y0: 0, x1: SHEET.w, y1: SHEET.h };
fs.mkdirSync(outDir, { recursive: true });
const base = path.join(outDir, `sheet-${SHEET.w}x${SHEET.h}`);
fs.writeFileSync(base + '.svg', m.toSVG(sheet, page, 0));
fs.writeFileSync(base + '.dxf', m.toDXF(sheet));
fs.writeFileSync(base + '.pdf', m.toPDF(sheet, page, 0, [SHEET.w, SHEET.h]), 'latin1');
console.log(`Sheet ${SHEET.w} x ${SHEET.h} mm: plates use x ${all.x0.toFixed(1)}..${all.x1.toFixed(1)}, y ${all.y0.toFixed(1)}..${all.y1.toFixed(1)} mm; free strip on the right ${(SHEET.w - all.x1).toFixed(1)} mm wide`);
console.log(fails.length ? 'FAIL\n  ' + fails.join('\n  ') : `PASS -> ${base}.svg/.dxf/.pdf`);
process.exitCode = fails.length ? 1 : 0;
