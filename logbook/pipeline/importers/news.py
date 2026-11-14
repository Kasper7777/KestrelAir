"""Local news from the day you arrived somewhere.

For each arrival (airport + date) finds real stories from that local area around
that date, then normalises every story to the same shape so the app can show
them all the same way:

    {id, title, summary, image, source, url, date, place, lang, tone}

Sources (no keys needed):
  1. GDELT DOC 2.0 - a global archive of news coverage, searchable by words and
     date range, with direct article links and share images. Queried with the
     town's name, limited to outlets in that country, so it stays local.
  2. Google News search (RSS) with after:/before: dates, in that country's
     edition - used when GDELT has nothing.
Each story's own page is then read once for its real summary and picture
(og:description / og:image). Missing pictures fall back to the place's photo.

Cached per (airport, date) in backup/news/news.json + backup/news/img/, fetched
politely in the background (GDELT allows about one request every 5 seconds).
"""
import hashlib
import html as htmlmod
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from xml.etree import ElementTree

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 KestrelAirLogbook',
      'Accept-Language': 'en-GB,en;q=0.8'}
GDELT_COUNTRY = {'GB': 'UK', 'JE': 'UK', 'GG': 'UK', 'FK': 'UK', 'US': 'US', 'FR': 'FR', 'ES': 'SP', 'DE': 'GM', 'HR': 'HR', 'TR': 'TU',
                 'CY': 'CY', 'BA': 'BK', 'NO': 'NO', 'FI': 'FI', 'RU': 'RS', 'KZ': 'KZ', 'CN': 'CH', 'IN': 'IN', 'TH': 'TH', 'KR': 'KS',
                 'JP': 'JA', 'CA': 'CA', 'MX': 'MX', 'JM': 'JM', 'CO': 'CO', 'CL': 'CI', 'MR': 'MR', 'DZ': 'AG', 'IE': 'EI', 'IT': 'IT'}
GNEWS = {'GB': ('en-GB', 'GB'), 'JE': ('en-GB', 'GB'), 'GG': ('en-GB', 'GB'), 'FK': ('en-GB', 'GB'), 'US': ('en-US', 'US'), 'CA': ('en-CA', 'CA'),
         'IN': ('en-IN', 'IN'), 'JM': ('en-US', 'US'), 'FR': ('fr', 'FR'), 'ES': ('es', 'ES'), 'DE': ('de', 'DE'), 'HR': ('hr', 'HR'),
         'TR': ('tr', 'TR'), 'NO': ('no', 'NO'), 'FI': ('fi', 'FI'), 'RU': ('ru', 'RU'), 'JP': ('ja', 'JP'), 'KR': ('ko', 'KR'),
         'MX': ('es-419', 'MX'), 'CO': ('es-419', 'CO'), 'CL': ('es-419', 'CL'), 'TH': ('th', 'TH'), 'CN': ('zh-CN', 'CN')}
SAD = re.compile(r'\b(die[sd]?|death|dead|killed|kill|murder|fatal|crash|collision|stabb|shoot|shot|fire|blaze|flood|missing|'
                 r'tribute|funeral|injur|assault|arrest|jailed|court|charged|attack|tragedy|disaster|victim)', re.I)
_last_gdelt = [0.0]


def _get(url, timeout=25, limit=4_000_000):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read(limit), r.geturl(), r.headers.get('Content-Type', '')


def _gdelt(query, start, end, n=25):
    url = 'https://api.gdeltproject.org/api/v2/doc/doc?' + urllib.parse.urlencode({
        'query': query, 'mode': 'artlist', 'format': 'json', 'maxrecords': n, 'sort': 'hybridrel',
        'startdatetime': start.strftime('%Y%m%d%H%M%S'), 'enddatetime': end.strftime('%Y%m%d%H%M%S')})
    if _gdelt_off[0] > time.time():
        return []                       # GDELT is throttling us: use the other source for a while
    for i in range(3):
        wait = 6.5 - (time.time() - _last_gdelt[0])
        if wait > 0:
            time.sleep(wait)
        _last_gdelt[0] = time.time()
        try:
            raw, _, _ = _get(url, timeout=25)
            try:
                return json.loads(raw).get('articles', [])
            except ValueError:
                return []       # GDELT answers plain text for "no results" / bad query
        except urllib.error.HTTPError as e:
            if e.code != 429:
                return []
            time.sleep(20 * (i + 1))    # be patient: it's a free public service
        except Exception:
            return []
    _gdelt_off[0] = time.time() + 600   # still throttled: leave GDELT alone for this run
    return []


_gdelt_off = [0.0]


def _google(query, iso, start, end):
    hl, gl = GNEWS.get(iso, ('en-GB', 'GB'))
    q = f'{query} after:{start:%Y-%m-%d} before:{end:%Y-%m-%d}'
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q, 'hl': hl, 'gl': gl, 'ceid': f'{gl}:{hl.split("-")[0]}'})
    try:
        raw, _, _ = _get(url)
        root = ElementTree.fromstring(raw)
    except Exception:
        return []
    out = []
    for it in root.iter('item'):
        title = (it.findtext('title') or '').strip()
        src = it.find('source')
        out.append({'title': re.sub(r'\s+-\s+[^-]+$', '', title), 'url': it.findtext('link'),
                    'source': src.text if src is not None else '', 'date': it.findtext('pubDate'), 'lang': hl.split('-')[0]})
    return out


def _meta(url):
    """The story's own summary + picture from its page (og: tags)."""
    try:
        raw, final, ctype = _get(url, timeout=9, limit=1_500_000)
    except Exception:
        return {}
    if 'html' not in ctype:
        return {'url': final}
    text = raw.decode('utf-8', 'replace')
    def tag(*names):
        for n in names:
            m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(n) + r'["\'][^>]*content=["\']([^"\']+)', text, re.I) or \
                re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + re.escape(n) + r'["\']', text, re.I)
            if m:
                return htmlmod.unescape(m.group(1)).strip()
        return None
    return {'url': final, 'summary': tag('og:description', 'description', 'twitter:description'),
            'image': tag('og:image', 'twitter:image', 'og:image:url'), 'title': tag('og:title', 'twitter:title')}


def _save_img(url, dest):
    from PIL import Image, ImageOps
    if os.path.exists(dest):
        return True
    try:
        raw, _, _ = _get(url, timeout=15, limit=8_000_000)
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert('RGB')
        if im.width < 300 or im.height < 160:
            return False
        im.thumbnail((900, 900))
        im.save(dest, 'JPEG', quality=82, optimize=True)
        return True
    except Exception:
        return False


def _norm_date(s):
    for fmt in ('%Y%m%dT%H%M%SZ', '%a, %d %b %Y %H:%M:%S %Z', '%a, %d %b %Y %H:%M:%S GMT'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except (TypeError, ValueError):
            continue
    return None


def stories_for(airport, when, cache_dir, fetch=True, limit=6):
    """Up to `limit` local stories for an airport around a date (datetime)."""
    path = os.path.join(cache_dir, 'news.json')
    cache = _CACHE.setdefault(path, json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {})
    key = f'{airport["ident"]}|{when:%Y-%m-%d}'
    tried = cache.setdefault('_gdeltTried', [])
    upgrade = False
    if key in cache:
        entry = cache[key]
        direct = any(s.get('image') and 'news.google.' not in (s.get('url') or '') for s in entry)
        # stories that only came via Google News (no picture/summary of their own): try GDELT again, patiently
        if not fetch or direct or key in tried or _gdelt_off[0] > time.time():
            return entry
        upgrade = True
    elif not fetch:
        return []
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    iso = (airport.get('country') or {}).get('iso') or ''
    towns = [t for t in dict.fromkeys([airport.get('city'), *(((airport.get('wiki') or {}).get('cities')) or [])]) if t and not re.match(r'^Q\d+$', t)]
    found, seen = [], set()
    start, end = when - timedelta(days=2), when + timedelta(days=2)
    if upgrade:
        tried.append(key)
    for town in towns[:2]:
        q = f'"{town}"'
        if GDELT_COUNTRY.get(iso):
            q += f' sourcecountry:{GDELT_COUNTRY[iso]}'
        for a in _gdelt(q, start, end):
            t = (a.get('title') or '').strip()
            if not t or t.lower() in seen:
                continue
            seen.add(t.lower())
            found.append({'title': t, 'url': a.get('url'), 'source': a.get('domain'), 'date': _norm_date(a.get('seendate')),
                          'image': a.get('socialimage'), 'lang': (a.get('language') or '')[:2].lower(), 'town': town})
        if len(found) >= limit:
            break
    if upgrade:
        if len(found) < 2:            # GDELT had nothing better: keep what we had
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(cache, fh, ensure_ascii=False, indent=0)
            return cache[key]
    elif len(found) < 3:
        for town in towns[:2]:
            for a in _google(f'"{town}"', iso, start, end):
                if a['title'].lower() in seen or not a['url']:
                    continue
                seen.add(a['title'].lower())
                found.append({**a, 'date': _norm_date(a['date']), 'town': town})
            if len(found) >= limit:
                break
    # most local first: stories that name the town; then drop near-duplicate coverage of the same event
    def words(t):
        return {w for w in re.findall(r'[^\W\d_]{4,}', t.lower())}
    found.sort(key=lambda s: -sum(1 for t in towns if t.lower() in s['title'].lower()))
    distinct = []
    for s in found:
        w = words(s['title'])
        if any(len(w & words(d['title'])) >= max(2, 0.5 * min(len(w), len(words(d['title'])))) for d in distinct):
            continue
        distinct.append(s)
    # read each story's own page (summary + picture) several at a time
    from concurrent.futures import ThreadPoolExecutor
    picks = distinct[:limit + 2]
    with ThreadPoolExecutor(6) as pool:
        metas = list(pool.map(lambda s: _meta(s['url']) if s.get('url') and 'news.google.' not in s['url'] else {}, picks))
    out = []
    for s, m in zip(picks, metas):
        if 'news.google.' in (m.get('url') or s.get('url') or ''):
            m = {'url': m.get('url') or s.get('url')}       # Google's own page, not the story: no blurb, no logo
        title = s['title'] if len(s['title']) > 15 else (m.get('title') or s['title'])
        img = s.get('image') or m.get('image')
        sid = hashlib.sha1((s.get('url') or title).encode()).hexdigest()[:12]
        f = f'news-{sid}.jpg'
        has_img = bool(img) and _save_img(urllib.parse.urljoin(s.get('url') or '', img), os.path.join(img_dir, f))
        summary = m.get('summary') or ''
        if re.search(r'aggregated from sources all over the world|comprehensive, up-to-date news', summary, re.I):
            summary = ''
        out.append({'id': sid, 'title': title, 'summary': summary[:400], 'image': f if has_img else None,
                    'source': re.sub(r'^www\.', '', s.get('source') or urllib.parse.urlparse(m.get('url') or s.get('url') or '').netloc),
                    'url': m.get('url') or s.get('url'), 'date': s.get('date') or f'{when:%Y-%m-%d}', 'place': s.get('town'),
                    'lang': s.get('lang') or '', 'tone': 'sad' if SAD.search(title) else 'neutral'})
        if len(out) >= limit:
            break
    # a mix: lead with the brighter stories, keep the serious ones too
    out.sort(key=lambda x: (x['tone'] == 'sad', not x['image']))
    cache[key] = out
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)
    return out


_CACHE = {}
