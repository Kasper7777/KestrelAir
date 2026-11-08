#!/usr/bin/env node
// Generates true-scale laser-cut overlay drawings for VIRPIL Control Panels from measured data.
//   node make-overlays.js [panels.json] [outDir]
// Output per panel: <name>.dxf (import this into Fusion, units = mm), <name>.svg, <name>.pdf (print at 100%).
// Coordinates are millimetres, origin = bottom-left corner of the plate, X right, Y up.
'use strict';
const fs = require('fs');
const path = require('path');

const src = process.argv[2] || path.join(__dirname, 'panels.json');
const outDir = process.argv[3] || path.join(__dirname, 'out');
const cfg = JSON.parse(fs.readFileSync(src, 'utf8'));
const defaultClearance = Number(cfg.hole_clearance_mm || 0);
fs.mkdirSync(outDir, { recursive: true });

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

function buildPanel(name, panel) {
  const o = panel.outline, prims = [], problems = [];
  const clearance = Number(panel.hole_clearance_mm ?? defaultClearance);
  // outline: rounded rectangle, or a polygon of [x, y, cornerRadius] points (e.g. the L-shaped CM3 throttle plate)
  prims.push(...(o.points ? filletPoly(o.points, 0, 'CUT') : roundedRect(o.w / 2, o.h / 2, o.w, o.h, o.corner_r, 'CUT')));
  for (const f of panel.features || []) {
    const id = f.id || '?', c = f.no_clearance ? 0 : clearance, layer = f.layer || (f.type === 'text' ? 'ENGRAVE' : 'CUT');
    if (![f.x, f.y].every(Number.isFinite)) { problems.push(`${id}: missing x/y`); continue; }
    if (f.type === 'circle') {
      if (!(f.d > 0)) { problems.push(`${id}: missing d`); continue; }
      prims.push({ t: 'circle', layer, a: [f.x, f.y, (f.d + c) / 2] });
    } else if (f.type === 'rect' || f.type === 'slot') {
      if (!(f.w > 0 && f.h > 0)) { problems.push(`${id}: missing w/h`); continue; }
      const w = f.w + c, h = f.h + c, r = f.type === 'slot' ? Math.min(w, h) / 2 : (f.r || 0) + (f.r ? c / 2 : 0);
      prims.push(...rotate(roundedRect(f.x, f.y, w, h, r, layer), f.x, f.y, f.angle || 0));
    } else if (f.type === 'poly') {
      if (!Array.isArray(f.points) || f.points.length < 3) { problems.push(`${id}: poly needs 3+ points`); continue; }
      prims.push(...filletPoly(f.points.map(([px, py]) => [f.x + px, f.y + py]), f.fillet || 0, layer));
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
  // Scale check, kept outside the plate on its own layer: a 50 mm bar and a 20 mm square.
  const sy = -12;
  prims.push({ t: 'line', layer: 'CHECK', a: [0, sy, 50, sy] }, { t: 'line', layer: 'CHECK', a: [0, sy - 2, 0, sy + 2] },
             { t: 'line', layer: 'CHECK', a: [50, sy - 2, 50, sy + 2] },
             ...roundedRect(70, sy, 20, 20, 0, 'CHECK'),
             { t: 'text', layer: 'CHECK', a: [0, sy - 18, 3, `${name}  |  bar = 50.00 mm, square = 20.00 mm  |  extra hole clearance +${clearance} mm`], align: 'left' });
  return { prims, problems };
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
let made = 0;
for (const [name, panel] of Object.entries(cfg.panels || {})) {
  const o = panel.outline;
  if (!o || !((o.w > 0 && o.h > 0) || o.points)) { console.log(`${name}: skipped (outline not measured yet)`); continue; }
  const { prims, problems } = buildPanel(name, panel);
  const b = bounds(prims), m = 10, file = name.replace(/[^\w.-]+/g, '_');
  fs.writeFileSync(path.join(outDir, file + '.dxf'), toDXF(prims));
  fs.writeFileSync(path.join(outDir, file + '.svg'), toSVG(prims, b, m));
  fs.writeFileSync(path.join(outDir, file + '.pdf'), toPDF(prims, b, m), 'latin1');
  made++;
  console.log(`${name}: ${o.w} x ${o.h} mm, ${(panel.features || []).length} features -> ${file}.dxf/.svg/.pdf${panel.verified ? '' : '  [NOT VERIFIED against the real panel]'}`);
  for (const pr of problems) console.log(`  ! ${pr}`);
}
console.log(`${made} panel(s) written to ${outDir}`);
