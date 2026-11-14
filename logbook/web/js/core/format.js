// Display helpers. Logbook times are local PC time without an offset, so
// new Date('2026-08-12T20:59:29') is read as local time - which is what we want.

export const toDate = (s) => (s ? new Date(s) : null);

const dfDay = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
const dfShort = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const dfMonth = new Intl.DateTimeFormat('en-GB', { month: 'short', year: '2-digit' });
const tf = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' });

export const day = (s) => (s ? dfDay.format(toDate(s)) : '—');
export const shortDay = (s) => (s ? dfShort.format(toDate(s)) : '—');
export const month = (s) => (s ? dfMonth.format(toDate(s)) : '');
export const time = (s) => (s ? tf.format(toDate(s)) : '—');
export const dayKey = (s) => (s ? s.slice(0, 10) : 'unknown');

export function duration(mins) {
  if (mins == null || isNaN(mins)) return '—';
  const m = Math.round(mins);
  if (m < 60) return `${m}m`;
  if (m < 60 * 48) return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
  const d = Math.floor(m / 1440), h = Math.round((m % 1440) / 60);
  return `${d}d ${h}h`;
}

export const num = (n, dp = 0) => (n == null ? '—' : Number(n).toLocaleString('en-GB', { maximumFractionDigits: dp, minimumFractionDigits: dp }));
export const money = (n) => (n == null ? '—' : '$' + Math.round(n).toLocaleString('en-GB'));
export function compact(n) {
  if (n == null) return '—';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M';
  if (Math.abs(n) >= 1e4) return Math.round(n / 1e3) + 'k';
  return num(n);
}

export function landing(fpm, crash) {
  if (crash) return { label: 'Crash', tone: 'bad', pct: 1 };
  if (fpm == null) return null;
  const v = Math.abs(fpm);
  const pct = Math.min(1, v / 800);
  if (v <= 100) return { label: 'Butter', tone: 'great', pct };
  if (v <= 200) return { label: 'Smooth', tone: 'good', pct };
  if (v <= 350) return { label: 'Firm', tone: 'ok', pct };
  if (v <= 600) return { label: 'Hard', tone: 'warn', pct };
  return { label: 'Very hard', tone: 'bad', pct };
}

export const flagUrl = (iso) => (iso ? `https://flagcdn.com/w40/${iso.toLowerCase()}.png` : null);

export function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// html`...` tagged template: escapes interpolations unless wrapped in raw()
const RAW = Symbol('raw');
export const raw = (s) => ({ [RAW]: true, s: String(s) });
export function html(strings, ...vals) {
  let out = '';
  strings.forEach((str, i) => {
    out += str;
    if (i < vals.length) {
      const v = vals[i];
      if (Array.isArray(v)) out += v.map((x) => (x && x[RAW] ? x.s : esc(x))).join('');
      else out += v && v[RAW] ? v.s : v == null || v === false ? '' : esc(v);
    }
  });
  return raw(out);
}
export const render = (el, tpl) => { el.innerHTML = tpl.s; return el; };
