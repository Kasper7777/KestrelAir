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
import threading
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
QUERY_VERSION = 2      # 2 = town + region/country (so "Mount Pleasant" means the Falklands one)


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
    _gdelt_off[0] = time.time() + 120   # still throttled: give GDELT two minutes, the app will try again
    return []


_LOCK = threading.RLock()       # the picture finder and the build can both write the archive


def _write(path, cache):
    with _LOCK:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=0)
        os.replace(tmp, path)


def pending_arrivals(cache_dir):
    """Arrivals whose stories all came via Google News and GDELT hasn't been asked about yet."""
    path = os.path.join(cache_dir, 'news.json')
    try:
        cache = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    tried = set(cache.get('_gdeltTried', []))
    return sum(1 for k, v in cache.items() if not k.startswith('_') and k not in tried and isinstance(v, list)
               and not any(s.get('image') and 'news.google.' not in (s.get('url') or '') for s in v))


def pending(cache_dir):
    """How many arrivals still only have Google-News stories (no picture/summary of their own)."""
    path = os.path.join(cache_dir, 'news.json')
    try:
        cache = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    # stories still waiting for their own picture (each is looked up at most MAX_TRIES times)
    return sum(1 for k, v in cache.items() if not k.startswith('_') and isinstance(v, list)
               for s in v if not s.get('image') and s.get('tries', 0) < MAX_TRIES)


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
                    'source': src.text if src is not None else '', 'site': src.get('url') if src is not None else '',
                    'date': it.findtext('pubDate'), 'lang': hl.split('-')[0]})
    return out


def _meta(url, text=None, final=None):
    """The story's own headline, summary and picture from its page (og: tags, then
    structured data, then the first big picture in the article)."""
    if text is None:
        try:
            raw, final, ctype = _get(url, timeout=12, limit=2_000_000)
        except Exception:
            return {}
        if 'html' not in ctype:
            return {'url': final}
        text = raw.decode('utf-8', 'replace')
    final = final or url
    def tag(*names):
        for n in names:
            m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(n) + r'["\'][^>]*content=["\']([^"\']+)', text, re.I) or \
                re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']' + re.escape(n) + r'["\']', text, re.I)
            if m:
                return htmlmod.unescape(m.group(1)).strip()
        return None
    t = tag('og:title', 'twitter:title')
    if not t:
        m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.I | re.S) or re.search(r'<title[^>]*>([^<]+)</title>', text, re.I)
        t = htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None
    img = tag('og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image', 'twitter:image:src')
    if not img:
        m = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]*href=["\']([^"\']+)', text, re.I) or \
            re.search(r'"image"\s*:\s*(?:\[\s*)?(?:\{[^{}]*?"url"\s*:\s*)?"(https?:[^"]+?\.(?:jpe?g|png|webp)[^"]*)"', text, re.I)
        if not m:
            art = re.search(r'<article.*?</article>', text, re.I | re.S)
            m = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)', art.group(0) if art else '', re.I)
        img = htmlmod.unescape(m.group(1)).replace('\\/', '/') if m else None
    return {'url': final, 'summary': tag('og:description', 'description', 'twitter:description'), 'image': img, 'title': t}


# ---------- finding each story's real article (and its own picture)
# Google News only gives a scrambled link, so the story's page can't be read from it.
# Three ways to find the real article, each checked the same way - a page only counts
# when its own headline matches the story's:
#   1. the paper's own pages that the Internet Archive saw that week (works best for
#      local papers; one listing per paper per week, shared by all its stories)
#   2. a web search for the headline (DuckDuckGo, unhurried; backs off when it says no)
# A story is only counted as "tried" when a route actually ran - a search engine
# saying "slow down" doesn't use up a try.
_last_search = [0.0]
_search_off = [0.0]
_archive_off = [0.0]
_last_archive = [0.0]
_last_google = [0.0]
_ARCHIVE_LISTS = {}
_ARCHIVE_SLOW = {}
_PACE = {}


def _pace(last, gap):
    """Space requests to one service `gap` seconds apart, across all finder threads."""
    with _PACE.setdefault(id(last), threading.Lock()):
        wait = gap - (time.time() - last[0])
        if wait > 0:
            time.sleep(wait)
        last[0] = time.time()
RETRY_AFTER = 900          # a story that wasn't found is tried again 15 min later
MAX_TRIES = 4
NOT_A_PHOTO = re.compile(r'logo|placeholder|/default|fallback|blank\.|sprite|favicon|brand[-_]?(?:mark|image)|avatar|og[-_]default', re.I)
SOCIAL = re.compile(r'(^|\.)(facebook|instagram|twitter|x|linkedin|youtube|tiktok|reddit|pinterest|threads)\.(com|net)$', re.I)
SEARCH_GAP = 9             # seconds between searches
LANG_EDITION = {'en': [('en-GB', 'GB'), ('en-US', 'US')], 'fr': [('fr', 'FR')], 'es': [('es', 'ES'), ('es-419', 'MX')], 'de': [('de', 'DE')],
                'tr': [('tr', 'TR')], 'hr': [('hr', 'HR')], 'no': [('no', 'NO')], 'fi': [('fi', 'FI')], 'ru': [('ru', 'RU')], 'ja': [('ja', 'JP')],
                'ko': [('ko', 'KR')], 'th': [('th', 'TH')], 'zh': [('zh-CN', 'CN')], 'it': [('it', 'IT')]}


def _fold(t):
    import unicodedata
    t = (t or '').replace('’', "'").replace('‘', "'")
    return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()


def _words(t):
    return {w for w in re.findall(r"[a-z0-9]{3,}", _fold(t))} or {w for w in re.findall(r"[^\W_]{2,}", (t or '').lower())}


def _same_story(a, b):
    """True when two headlines are the same story (outlets add their name, trim words...)."""
    A, B = _words(a), _words(b)
    if len(A) < 3 or len(B) < 2:
        return False
    return len(A & B) / min(len(A), len(B)) >= 0.7


def _squash(s):
    return re.sub(r'[^a-z0-9]', '', _fold(s))


def _search(q):
    """Result links for a web search, or None when the search engine is resting."""
    if _search_off[0] > time.time():
        return None
    for ep in ('https://html.duckduckgo.com/html/?', 'https://lite.duckduckgo.com/lite/?'):
        _pace(_last_search, SEARCH_GAP)

        try:
            raw, _, _ = _get(ep + urllib.parse.urlencode({'q': q}), timeout=15, limit=800_000)
        except Exception:
            continue
        text = raw.decode('utf-8', 'replace')
        if re.search(r'anomaly|captcha|unusual traffic', text, re.I) and 'uddg=' not in text:
            break                                   # it wants us to slow down
        links = [urllib.parse.unquote(x) for x in re.findall(r'uddg=([^&"\']+)', text)]
        links += re.findall(r'class=["\']result-link["\'][^>]*href=["\'](https?://[^"\']+)', text)
        return [u for u in dict.fromkeys(links) if u.startswith('http') and not re.search(r'duckduckgo\.com|bing\.com|google\.', u)
                and not SOCIAL.search(urllib.parse.urlparse(u).netloc)]
    _search_off[0] = time.time() + 900              # rest a quarter of an hour; the archive route carries on
    return None


def _site_for(s):
    """The paper's own website for a Google News story (Google's feed names it)."""
    for hl, gl in LANG_EDITION.get(s.get('lang') or 'en', [('en-GB', 'GB')]):
        _pace(_last_google, 1.5)

        q = ' '.join(re.findall(r'[^\W_]+', s['title'])[:14])
        try:
            raw, _, _ = _get('https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q, 'hl': hl, 'gl': gl, 'ceid': f'{gl}:{hl[:2]}'}), timeout=15)
            items = list(ElementTree.fromstring(raw).iter('item'))
        except Exception:
            return None
        for it in items[:10]:
            src = it.find('source')
            if src is None or not src.get('url'):
                continue
            same_paper = _squash(src.text) == _squash(s.get('source'))
            if same_paper and _same_story(s['title'], re.sub(r'\s+-\s+[^-]+$', '', it.findtext('title') or '')):
                return src.get('url')
    return ''


def _archive_query(host, d, keyword=None, timeout=60):
    params = [('url', re.sub(r'^www\.', '', host) + '/*'), ('from', f'{d - timedelta(days=3):%Y%m%d}'), ('to', f'{d + timedelta(days=5):%Y%m%d}'),
              ('output', 'json'), ('fl', 'original'), ('collapse', 'urlkey'), ('limit', '25000'), ('filter', 'mimetype:text/html')]
    if keyword:
        params.append(('filter', f'original:.*{keyword}.*'))
    raw, _, _ = _get('https://web.archive.org/cdx/search/cdx?' + urllib.parse.urlencode(params), timeout=timeout, limit=40_000_000)
    return [r[0] for r in json.loads(raw or b'[]')[1:]]


def _archive_list(site, date, title=''):
    """Pages of a paper the Internet Archive saw in the week around a date: the whole
    week's list (cached, shared by that paper's stories), or - when that's too big or
    slow - just the pages whose address contains the headline's most telling word."""
    host = urllib.parse.urlparse(site).netloc or site
    try:
        d = datetime.strptime(date, '%Y-%m-%d')
    except (TypeError, ValueError):
        return None
    k = (host, f'{d:%Y%m%d}')
    if k in _ARCHIVE_LISTS:
        return _ARCHIVE_LISTS[k]
    if _archive_off[0] > time.time():
        return None
    def pace():
        _pace(_last_archive, 6)
    if _ARCHIVE_SLOW.get(host, 0) < 2:
        pace()
        try:
            rows = _archive_query(host, d, timeout=45)
            _ARCHIVE_LISTS[k] = rows
            return rows
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                _archive_off[0] = time.time() + 300
                return None
        except Exception:
            _ARCHIVE_SLOW[host] = _ARCHIVE_SLOW.get(host, 0) + 1     # big site or a slow moment
    words = sorted({w for w in re.findall(r'[a-z0-9]{5,}', _fold(title))}, key=len, reverse=True)
    if not words:
        return []
    pace()
    try:
        return _archive_query(host, d, keyword=words[0], timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (429, 503):
            _archive_off[0] = time.time() + 300
        return None
    except Exception:
        _archive_off[0] = time.time() + 120
        return None

def _from_archive_list(s, rows):
    W = _words(s['title'])
    def score(u):
        path = urllib.parse.unquote(urllib.parse.urlparse(u).path)
        return len(W & _words(re.sub(r'[-_/.+]', ' ', path)))
    best = sorted(rows, key=score, reverse=True)[:3]
    return [u for u in best if score(u) >= max(3, 0.55 * len(W))]


def _page(u, date):
    """Read a candidate page from the paper's own site (if a site turns us away, we leave it be)."""
    return _meta(u)


def _image_hashes(cache):
    return cache.setdefault('_imgHash', {})


def _keep_image(cache, story_id, img_url, page_url, dest, archive_stamp=None):
    """Download the article's own picture; refuse logos and pictures another story already uses."""
    if not img_url or NOT_A_PHOTO.search(img_url.split('?')[0]):
        return False
    if not _save_img(urllib.parse.urljoin(page_url or '', img_url), dest):
        return False
    h = hashlib.sha1(open(dest, 'rb').read()).hexdigest()
    owners = _image_hashes(cache)
    if owners.get(h, story_id) != story_id:      # the outlet's stock picture, not this story's
        os.remove(dest)
        return False
    owners[h] = story_id
    return True


def resolve(cache_dir, budget_s=150, log=print):
    """Find the real article (and its own picture + summary) for stories that only came
    via Google News. Works through the archive a little at a time; returns how many were found."""
    path = os.path.join(cache_dir, 'news.json')
    if not os.path.exists(path):
        return 0
    cache = _CACHE.setdefault(path, json.load(open(path, encoding='utf-8')))
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    now, t0, found, checked = time.time(), time.time(), 0, 0
    with _LOCK:
        if cache.get('_finder', 0) < 3:             # tries "used up" while the search engine was refusing: give them back
            for k, v in list(cache.items()):
                if not k.startswith('_') and isinstance(v, list):
                    for s in v:
                        if not s.get('image') and not s.get('resolved'):
                            s.pop('tries', None)
                            s.pop('triedAt', None)
            cache['_finder'] = 3
        todo = [s for k, v in list(cache.items()) if not k.startswith('_') and isinstance(v, list) for s in v
                if not s.get('image') and s.get('tries', 0) < MAX_TRIES and now - s.get('triedAt', 0) > RETRY_AFTER]
    todo.sort(key=lambda s: s.get('tries', 0))       # fresh stories first

    def one(s):
        """Look one story up. Returns 'found', 'checked', 'skip' or 'resting'."""
        if time.time() - t0 > budget_s:
            return 'skip'
        if 'site' not in s and 'news.google.' in (s.get('url') or ''):
            site = _site_for(s)
            if site is None:
                return 'skip'
            s['site'] = site
        ran, cands = False, []
        if s.get('site'):
            rows = _archive_list(s['site'], s.get('date'), s['title'])
            if rows is not None:
                ran = True
                cands += _from_archive_list(s, rows)
        hit = None
        for u in cands:
            m = _page(u, s.get('date'))
            if _same_story(s['title'], m.get('title')):
                hit = m
                break
        if not hit:
            links = _search(f'{s["title"]} {s.get("source") or ""}'.strip())
            if links is not None:
                ran = True
                src = _squash(s.get('source'))
                site_host = _squash(urllib.parse.urlparse(s.get('site') or '').netloc)
                links.sort(key=lambda u: 0 if (site_host and site_host in _squash(urllib.parse.urlparse(u).netloc))
                           or (src and src[:10] in _squash(urllib.parse.urlparse(u).netloc)) else 1)
                for u in links[:4]:
                    m = _page(u, s.get('date'))
                    if _same_story(s['title'], m.get('title')):
                        hit = m
                        break
        if not ran:
            return 'resting' if (_search_off[0] > time.time() and _archive_off[0] > time.time()) else 'skip'
        result = 'checked'
        with _LOCK:
            s['tries'] = s.get('tries', 0) + 1
            s['triedAt'] = int(time.time())
        if hit:
            url = hit.get('url') or s['url']
            f = f'news-{s["id"]}.jpg'
            with _LOCK:
                got = _keep_image(cache, s['id'], hit.get('image'), url, os.path.join(img_dir, f))
                s['url'] = url
                summ = hit.get('summary') or ''
                if summ and not _same_story(s['title'], summ):
                    s['summary'] = summ[:400]
                if got:
                    s['image'] = f
                    result = 'found'
                else:
                    s['tries'] = MAX_TRIES          # the article has no usable picture: a cutting it is
                s['resolved'] = True
        _write(path, cache)
        return result

    # four stories at a time: one slow archive answer doesn't hold up the rest
    # (each service still gets its requests one at a time, politely spaced)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(one, todo[:60]))
    found = results.count('found')
    checked = found + results.count('checked')
    if checked:
        log(f'News: found the real article picture for {found} of {checked} stories checked this round')
    return found

# ---------- keeping it local
# "Jersey" also matches New Jersey (and ice-hockey shirts); US league sites aren't local news elsewhere
FAR_AWAY = re.compile(r'\b(nhl|nba|nfl|mlb|mls|espn|yahoo sports|cbs sports|fox sports|bleacher report)\b', re.I)


def _misplaced(s, iso):
    town = s.get('place') or ''
    if town and not town.lower().startswith('new ') and re.search(r'\bnew\s+' + re.escape(town) + r'\b', s.get('title') or '', re.I):
        return True
    return iso not in ('US', 'CA') and bool(FAR_AWAY.search(f'{s.get("source") or ""} {s.get("url") or ""}'))


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
    versions = cache.setdefault('_qv', {})
    iso0 = (airport.get('country') or {}).get('iso') or ''
    needs_region = bool(airport.get('state')) or iso0 not in ('GB', 'JE', 'GG', '')
    if key in cache and fetch and needs_region and versions.get(key, 1) < QUERY_VERSION:
        del cache[key]                      # archived under the old, ambiguous search: look it up again
        if key in tried:
            tried.remove(key)
    upgrade = False
    if key in cache:
        entry = cache[key]
        direct = any(s.get('image') and 'news.google.' not in (s.get('url') or '') for s in entry)
        # stories that only came via Google News (no picture/summary of their own): try GDELT again, patiently
        if not fetch or direct or key in tried or _gdelt_off[0] > time.time():
            return [s for s in entry if not _misplaced(s, iso0)]
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
    # pin the place down: plenty of towns share a name (Mount Pleasant: Falklands, Michigan, Texas...)
    region = airport.get('state') or ('' if iso in ('GB', 'JE', 'GG') else (airport.get('country') or {}).get('name') or '')
    region = re.sub(r'\s*\(.*\)', '', region)
    for town in towns[:2]:
        q = f'"{town}"' + (f' "{region}"' if region and region.lower() not in town.lower() else '')
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
            _write(path, cache)
            return [s for s in cache[key] if not _misplaced(s, iso0)]
    elif len(found) < 3:
        for town in towns[:2]:
            for a in _google(f'"{town}"' + (f' "{region}"' if region and region.lower() not in town.lower() else ''), iso, start, end):
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
                    'lang': s.get('lang') or '', 'tone': 'sad' if SAD.search(title) else 'neutral',
                    **({'site': s['site']} if s.get('site') else {})})
        if len(out) >= limit:
            break
    # a mix: lead with the brighter stories, keep the serious ones too
    out.sort(key=lambda x: (x['tone'] == 'sad', not x['image']))
    with _LOCK:
        cache[key] = out
        versions[key] = QUERY_VERSION
    _write(path, cache)
    return [s for s in out if not _misplaced(s, iso0)]


_CACHE = {}