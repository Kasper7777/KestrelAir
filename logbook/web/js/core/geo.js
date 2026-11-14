const R = Math.PI / 180;
const EARTH_KM = 6371;

export function kmBetween(a, b) {
  const [lo1, la1, lo2, la2] = [a[0] * R, a[1] * R, b[0] * R, b[1] * R];
  const h = Math.sin((la2 - la1) / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin((lo2 - lo1) / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Great-circle arc from a to b ([lon, lat]) as a polyline. Longitudes are
// "unwrapped" so a leg across the date line stays continuous (e.g. 179 -> 181).
export function greatCircle(a, b, maxStepKm = 40) {
  const d = kmBetween(a, b) / EARTH_KM;
  if (d < 1e-6) return [a, b];
  const n = Math.max(2, Math.min(256, Math.ceil((d * EARTH_KM) / maxStepKm)));
  const [lo1, la1, lo2, la2] = [a[0] * R, a[1] * R, b[0] * R, b[1] * R];
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const f = i / n;
    const A = Math.sin((1 - f) * d) / Math.sin(d);
    const B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(la1) * Math.cos(lo1) + B * Math.cos(la2) * Math.cos(lo2);
    const y = A * Math.cos(la1) * Math.sin(lo1) + B * Math.cos(la2) * Math.sin(lo2);
    const z = A * Math.sin(la1) + B * Math.sin(la2);
    pts.push([Math.atan2(y, x) / R, Math.atan2(z, Math.sqrt(x * x + y * y)) / R]);
  }
  for (let i = 1; i < pts.length; i++) {
    while (pts[i][0] - pts[i - 1][0] > 180) pts[i][0] -= 360;
    while (pts[i][0] - pts[i - 1][0] < -180) pts[i][0] += 360;
  }
  return pts;
}

// A gentle sideways bow for ground transfers so they read differently from flights.
export function bowed(a, b, bend = 0.12, n = 48) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const f = i / n, k = Math.sin(Math.PI * f) * bend;
    pts.push([a[0] + dx * f - dy * k, a[1] + dy * f + dx * k]);
  }
  return pts;
}

export function cumulative(coords) {
  const acc = [0];
  for (let i = 1; i < coords.length; i++) acc.push(acc[i - 1] + kmBetween(coords[i - 1], coords[i]));
  return acc;
}

// Point (and heading) at fraction f (0..1) along a polyline.
export function along(coords, f, acc = cumulative(coords)) {
  const total = acc[acc.length - 1];
  if (!total) return { point: coords[0], bearing: 0, index: 0 };
  const target = Math.max(0, Math.min(1, f)) * total;
  let i = 1;
  while (i < acc.length - 1 && acc[i] < target) i++;
  const seg = acc[i] - acc[i - 1] || 1;
  const t = (target - acc[i - 1]) / seg;
  const p0 = coords[i - 1], p1 = coords[i];
  return { point: [p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t], bearing: bearing(p0, p1), index: i };
}

export function bearing(a, b) {
  const [lo1, la1, lo2, la2] = [a[0] * R, a[1] * R, b[0] * R, b[1] * R];
  const y = Math.sin(lo2 - lo1) * Math.cos(la2);
  const x = Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(lo2 - lo1);
  return (Math.atan2(y, x) / R + 360) % 360;
}

export function bounds(coordsList) {
  let w = Infinity, s = Infinity, e = -Infinity, n = -Infinity;
  for (const coords of coordsList) for (const [x, y] of coords) {
    if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y;
  }
  return [[w, s], [e, n]];
}
