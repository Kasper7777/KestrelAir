#!/usr/bin/env node
// Independent checks of out/*.{dxf,pdf} against the original sources in source/.
//   node verify-overlays.js
'use strict';
const fs = require('fs'), path = require('path'), zlib = require('zlib');
const D = __dirname, OUT = path.join(D, 'out'), SRC = path.join(D, 'source');
const cfg = JSON.parse(fs.readFileSync(path.join(D, 'panels.json'), 'utf8'));
let failures = 0;
const check = (ok, msg) => { console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${msg}`); if (!ok) failures++; };

// ---------- DXF reader -> sample points along CUT geometry ----------
function readDXF(file) {
  const L = fs.readFileSync(file, 'utf8').split(/\r?\n/), ents = [];
  let i = L.findIndex(l => l.trim() === 'ENTITIES') + 1;
  let cur = null;
  for (; i < L.length - 1; i += 2) {
    const code = L[i].trim(), val = L[i + 1].trim();
    if (code === '0') { if (cur) ents.push(cur); cur = { type: val }; if (val === 'EOF') break; continue; }
    if (cur) cur[code] = isNaN(+val) ? val : +val;
  }
  return ents.filter(e => ['LINE', 'ARC', 'CIRCLE', 'TEXT'].includes(e.type));
}
function samples(ents, layer, step = 0.1) {
  const pts = [];
  for (const e of ents) {
    if (e['8'] !== layer) continue;
    if (e.type === 'LINE') {
      const n = Math.max(1, Math.ceil(Math.hypot(e['11'] - e['10'], e['21'] - e['20']) / step));
      for (let j = 0; j <= n; j++) pts.push([e['10'] + (e['11'] - e['10']) * j / n, e['20'] + (e['21'] - e['20']) * j / n]);
    } else if (e.type === 'CIRCLE' || e.type === 'ARC') {
      const a0 = e.type === 'ARC' ? e['50'] : 0; let a1 = e.type === 'ARC' ? e['51'] : 360; if (a1 <= a0) a1 += 360;
      const n = Math.max(4, Math.ceil((a1 - a0) * Math.PI / 180 * e['40'] / step));
      for (let j = 0; j <= n; j++) { const t = (a0 + (a1 - a0) * j / n) * Math.PI / 180; pts.push([e['10'] + e['40'] * Math.cos(t), e['20'] + e['40'] * Math.sin(t)]); }
    }
  }
  return pts;
}

// ---------- zip / 3MF ----------
function unzipEntry(file, wanted) {
  const b = fs.readFileSync(file); let e = b.length - 22; while (b.readUInt32LE(e) !== 0x06054b50) e--;
  let p = b.readUInt32LE(e + 16); const n = b.readUInt16LE(e + 10);
  for (let k = 0; k < n; k++) {
    const method = b.readUInt16LE(p + 10), csize = b.readUInt32LE(p + 20), nl = b.readUInt16LE(p + 28), xl = b.readUInt16LE(p + 30), cl = b.readUInt16LE(p + 32), off = b.readUInt32LE(p + 42);
    const name = b.toString('utf8', p + 46, p + 46 + nl);
    if (name === wanted) { const ds = off + 30 + b.readUInt16LE(off + 26) + b.readUInt16LE(off + 28), d = b.subarray(ds, ds + csize); return method === 8 ? zlib.inflateRawSync(d) : d; }
    p += 46 + nl + xl + cl;
  }
  throw Error(`${wanted} not in ${file}`);
}
// Boundary edges of the top face (z = max) of a 3MF plate mesh = every through-cut edge as seen from above.
function meshTopEdges(file) {
  const x = unzipEntry(file, '3D/3dmodel.model').toString('utf8');
  const V = [...x.matchAll(/<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/g)].map(m => [+m[1], +m[2], +m[3]]);
  const T = [...x.matchAll(/<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"/g)].map(m => [+m[1], +m[2], +m[3]]);
  const zt = Math.max(...V.map(v => v[2])), cnt = new Map();
  for (const t of T) {
    if (!t.every(i => Math.abs(V[i][2] - zt) < 1e-4)) continue;
    for (let j = 0; j < 3; j++) { const a = t[j], c = t[(j + 1) % 3], key = a < c ? a + ',' + c : c + ',' + a; cnt.set(key, (cnt.get(key) || 0) + 1); }
  }
  const segs = [];
  for (const [key, c] of cnt) if (c === 1) { const [a, d] = key.split(',').map(Number); segs.push([V[a][0], V[a][1], V[d][0], V[d][1]]); }
  return { segs, thickness: zt };
}
// nearest distance from point to set of segments / points, via grid hashing
function segIndex(segs, cell = 2) {
  const g = new Map();
  segs.forEach((s, i) => {
    const x0 = Math.floor(Math.min(s[0], s[2]) / cell), x1 = Math.floor(Math.max(s[0], s[2]) / cell), y0 = Math.floor(Math.min(s[1], s[3]) / cell), y1 = Math.floor(Math.max(s[1], s[3]) / cell);
    for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) { const k = x + ',' + y; if (!g.has(k)) g.set(k, []); g.get(k).push(i); }
  });
  return (px, py) => {
    let best = Infinity; const cx = Math.floor(px / cell), cy = Math.floor(py / cell);
    for (let r = 0; r <= 3 && best > (r - 1) * cell; r++)
      for (let x = cx - r; x <= cx + r; x++) for (let y = cy - r; y <= cy + r; y++) {
        if (Math.max(Math.abs(x - cx), Math.abs(y - cy)) !== r) continue;
        for (const i of g.get(x + ',' + y) || []) {
          const [ax, ay, bx, by] = segs[i], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
          const t = l2 ? Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2)) : 0;
          best = Math.min(best, Math.hypot(px - ax - t * dx, py - ay - t * dy));
        }
      }
    return best;
  };
}

// ---------- PDF: measure what will actually print ----------
function checkPDF(name) {
  const b = fs.readFileSync(path.join(OUT, name + '.pdf'), 'latin1'), k = 72 / 25.4;
  const mb = b.match(/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]/), pw = mb[1] / k, ph = mb[2] / k;
  check(Math.abs(pw - 210) < 0.01 && Math.abs(ph - 297) < 0.01, `PDF page is A4 portrait (${pw.toFixed(2)} x ${ph.toFixed(2)} mm)`);
  const sx = b.indexOf('startxref\n'), xo = +b.slice(sx + 10).split('\n')[0];
  check(b.slice(xo, xo + 4) === 'xref', 'PDF cross-reference table valid');
  const stream = b.slice(b.indexOf('stream\n') + 7, b.indexOf('\nendstream'));
  const green = [], red = [];
  for (const line of stream.split('\n')) {
    const m = line.match(/^([\d.]+) ([\d.]+) ([\d.]+) RG (.*) S$/); if (!m) continue;
    const nums = m[4].replace(/[mlch]/g, ' ').trim().split(/\s+/).map(Number), pts = [];
    for (let j = 0; j + 1 < nums.length; j += 2) pts.push([nums[j] / k, nums[j + 1] / k]);
    if (m[1] === '0' && m[3] === '0' && m[2] === '0.6') green.push(pts);
    if (m[1] === '1' && m[2] === '0' && m[3] === '0') red.push(pts);
  }
  const bar = green.find(p => p.length === 2 && Math.abs(p[0][1] - p[1][1]) < 1e-6);
  const barLen = Math.abs(bar[1][0] - bar[0][0]);
  check(Math.abs(barLen - 50) < 0.01, `printed scale bar = ${barLen.toFixed(3)} mm (should be 50.000)`);
  // plate outline = the 4 straight edges, which are the longest red lines
  const lines = red.filter(p => p.length === 2), xs = [], ys = [];
  for (const p of lines) { if (Math.abs(p[0][0] - p[1][0]) < 1e-6 && Math.abs(p[0][1] - p[1][1]) > 150) xs.push(p[0][0]); if (Math.abs(p[0][1] - p[1][1]) < 1e-6 && Math.abs(p[0][0] - p[1][0]) > 120) ys.push(p[0][1]); }
  const all0 = red.flat();
  const w = xs.length > 1 ? Math.max(...xs) - Math.min(...xs) : Math.max(...all0.map(p => p[0])) - Math.min(...all0.map(p => p[0]));
  const h = ys.length > 1 ? Math.max(...ys) - Math.min(...ys) : Math.max(...all0.map(p => p[1])) - Math.min(...all0.map(p => p[1]));
  check(Math.abs(w - 170) < 0.01 && Math.abs(h - 200) < 0.01, `printed plate = ${w.toFixed(3)} x ${h.toFixed(3)} mm (should be 170 x 200)`);
  const all = red.flat(), minX = Math.min(...all.map(p => p[0])), maxX = Math.max(...all.map(p => p[0])), minY = Math.min(...all.map(p => p[1])), maxY = Math.max(...all.map(p => p[1]));
  check(minX > 5 && maxX < pw - 5 && minY > 5 && maxY < ph - 15, `cut lines sit inside the page with >= 5 mm margin (x ${minX.toFixed(1)}-${maxX.toFixed(1)}, y ${minY.toFixed(1)}-${maxY.toFixed(1)} mm)`);
}

// ---------- template raster comparison (signed distance) ----------
function sdShape(f, x, y) {
  const c = 0;
  if (f.type === 'circle') return Math.hypot(x - f.x, y - f.y) - (f.d + c) / 2;
  let dx = x - f.x, dy = y - f.y;
  if (f.angle) { const t = -f.angle * Math.PI / 180; [dx, dy] = [dx * Math.cos(t) - dy * Math.sin(t), dx * Math.sin(t) + dy * Math.cos(t)]; }
  const w = f.w / 2, h = f.h / 2, r = f.type === 'slot' ? Math.min(w, h) : (f.r || 0);
  const qx = Math.abs(dx) - w + r, qy = Math.abs(dy) - h + r;
  return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
}
function templateCompare(name, png) {
  const { W, H, px } = readPNG(png), panel = cfg.panels[name], o = panel.outline;
  const plate = i => { const r = px[i * 4], b = px[i * 4 + 2], a = px[i * 4 + 3]; return a > 128 && r > 110 && r < 205 && r - b >= 10; };
  let x0 = W, x1 = 0, y0 = H, y1 = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (plate(y * W + x)) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const kx = (x1 - x0 + 1) / o.w, ky = (y1 - y0 + 1) / o.h;
  const holes = panel.features.filter(f => (f.layer || 'CUT') === 'CUT' && f.type !== 'text' && f.type !== 'poly');
  const plateSD = (x, y) => sdShape({ type: 'rect', x: o.w / 2, y: o.h / 2, w: o.w, h: o.h, r: o.corner_r }, x, y);
  const errs = [];
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const mx = (x + 0.5 - x0) / kx, my = o.h - (y + 0.5 - y0) / ky;
    const holeSD = Math.min(...holes.map(f => sdShape(f, mx, my)));
    const sd = Math.max(plateSD(mx, my), -holeSD); // <0 = material in our drawing
    if ((sd < 0) !== plate(y * W + x)) errs.push(Math.abs(sd));
  }
  errs.sort((a, b) => a - b);
  const px1 = 1 / ((kx + ky) / 2), p99 = errs.length ? errs[Math.floor(errs.length * 0.99)] : 0, max = errs.length ? errs[errs.length - 1] : 0;
  return { scale: [kx, ky], px1, n: errs.length, p99, max };
}
function readPNG(file) {
  const b = fs.readFileSync(file); let p = 8, W, H, ct, idat = [];
  while (p < b.length) { const len = b.readUInt32BE(p), t = b.toString('ascii', p + 4, p + 8), d = b.subarray(p + 8, p + 8 + len); if (t === 'IHDR') { W = d.readUInt32BE(0); H = d.readUInt32BE(4); ct = d[9]; } if (t === 'IDAT') idat.push(d); p += 12 + len; }
  const ch = { 6: 4, 2: 3 }[ct], raw = zlib.inflateSync(Buffer.concat(idat)), st = W * ch, out = Buffer.alloc(W * H * 4); let prev = Buffer.alloc(st);
  for (let y = 0; y < H; y++) {
    const f = raw[y * (st + 1)], row = raw.subarray(y * (st + 1) + 1, (y + 1) * (st + 1)), cur = Buffer.alloc(st);
    for (let i = 0; i < st; i++) { const a = i >= ch ? cur[i - ch] : 0, u = prev[i], c = i >= ch ? prev[i - ch] : 0; let v = row[i];
      if (f === 1) v += a; else if (f === 2) v += u; else if (f === 3) v += (a + u) >> 1; else if (f === 4) { const q = a + u - c, pa = Math.abs(q - a), pb = Math.abs(q - u), pc = Math.abs(q - c); v += (pa <= pb && pa <= pc) ? a : (pb <= pc ? u : c); }
      cur[i] = v & 255; }
    for (let x = 0; x < W; x++) { const o = (y * W + x) * 4; out[o] = cur[x * ch]; out[o + 1] = cur[x * ch + 1]; out[o + 2] = cur[x * ch + 2]; out[o + 3] = ch === 4 ? cur[x * ch + 3] : 255; }
    prev = cur;
  }
  return { W, H, px: out };
}

// Second designer's template: where does each of our control openings land on their plate?
function centreCompare(name, png) {
  const { W, H, px } = readPNG(png), o = cfg.panels[name].outline;
  const plate = i => { const r = px[i * 4], b = px[i * 4 + 2], a = px[i * 4 + 3]; return a > 128 && r > 110 && r < 205 && r - b >= 10; };
  let x0 = W, x1 = 0, y0 = H, y1 = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) if (plate(y * W + x)) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  const kx = (x1 - x0 + 1) / o.w, ky = (y1 - y0 + 1) / o.h;
  const toPx = (x, y) => [Math.round(x0 - 0.5 + x * kx), Math.round(y0 - 0.5 + (o.h - y) * ky)];
  const feats = cfg.panels[name].features.filter(f => (f.layer || 'CUT') === 'CUT' && !/guard/.test(f.id));
  const rows = [];
  for (const f of feats) {
    // the template opening under our centre: measure its extent along the row and column through our centre
    let [cx, cy] = toPx(f.x, f.y + (f.type === 'poly' ? -19 : 0));
    if (plate(cy * W + cx)) { rows.push([f.id, null]); continue; }
    let l = cx, r = cx, u = cy, d = cy;
    while (l > 0 && !plate(cy * W + l - 1)) l--; while (r < W - 1 && !plate(cy * W + r + 1)) r++;
    while (u > 0 && !plate((u - 1) * W + cx)) u--; while (d < H - 1 && !plate((d + 1) * W + cx)) d++;
    const tx = ((l + r + 1) / 2 - x0) / kx, ty = o.h - ((u + d + 1) / 2 - y0) / ky;
    rows.push([f.id, f.type === 'poly' ? null : Math.hypot(tx - f.x, ty - f.y)]);
  }
  const missing = rows.filter(r => r[1] === null && !/Gear Indicator/.test(r[0])).map(r => r[0]);
  const off = rows.filter(r => r[1] !== null).map(r => r[1]).sort((a, b) => a - b);
  check(missing.length === 0, `every control opening also exists on DeathDonky's independent ${name} template${missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''}`);
  console.log(`  INFO  centre agreement with that independent template: median ${off[Math.floor(off.length / 2)].toFixed(2)} mm, worst ${off[off.length - 1].toFixed(2)} mm (${rows.find(r => r[1] === off[off.length - 1])[0]})`);
}

// ---------- run ----------
for (const name of ['CP1', 'CP2', 'CP3', 'CM3']) {
  console.log(`\n${name}`);
  const ents = readDXF(path.join(OUT, name + '.dxf'));
  const cut = samples(ents, 'CUT'), pocket = samples(ents, 'POCKET');
  check(cut.length > 0, `DXF parses: ${ents.length} entities, ${ents.filter(e => e['8'] === 'CUT').length} on CUT`);
  checkPDF(name);
  const mesh = path.join(SRC, 'printables', name === 'CM3' ? 'virpil-throttle-plate.3mf' : `virpil-control-panel-${name.slice(2)}-plate.3mf`);
  if (fs.existsSync(mesh)) {
    const { segs, thickness } = meshTopEdges(mesh), near = segIndex(segs);
    const d1 = cut.map(([x, y]) => near(x, y)), max1 = d1.length ? Math.max(...d1) : Infinity;
    const cutSegs = []; for (let j = 1; j < cut.length; j++) if (Math.hypot(cut[j][0] - cut[j - 1][0], cut[j][1] - cut[j - 1][1]) < 0.2) cutSegs.push([...cut[j - 1], ...cut[j]]);
    const near2 = segIndex(cutSegs), d2 = segs.map(s => near2(s[0], s[1])), max2 = Math.max(...d2);
    check(max1 < 0.06, `every DXF cut line lies on the original 3D model's edge (worst ${max1.toFixed(3)} mm; ${cut.length} points)`);
    check(max2 < 0.06, `every edge of the original 3D model is in the DXF (worst ${max2.toFixed(3)} mm; ${segs.length} mesh edges)`);
    console.log(`        original plate thickness ${thickness} mm; ${pocket.length ? 'POCKET layer = 2 mm back recesses' : ''}`);
  }
  const tpl = path.join(SRC, 'deathdonky', name === 'CP3' ? 'SharKA-50-Template.png' : name === 'CM3' ? 'Throttle-Template-Image.png' : `${name}-Template-Image.png`);
  if (fs.existsSync(tpl)) {
    const r = templateCompare(name, tpl);
    const msg = `${path.basename(tpl)}: scale ${r.scale[0].toFixed(3)}/${r.scale[1].toFixed(3)} px/mm (1 px = ${r.px1.toFixed(2)} mm); 99% of differing pixels within ${r.p99.toFixed(2)} mm of our edges, worst ${r.max.toFixed(2)} mm`;
    if (name === 'CP3') check(r.p99 < 0.5, `matches its source template, ${msg}`);
    else centreCompare(name, tpl);
  }
}
console.log(failures ? `\n${failures} check(s) FAILED` : '\nAll checks passed.');
process.exit(failures ? 1 : 0);
