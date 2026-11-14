"""Real photos and real menus for a restaurant or hotel, from the venue's own website.

For a venue with a website (from OpenStreetMap):
  - photos: the site's share image and its large pictures (food, dining room,
    hotel rooms...), skipping logos, icons and badges
  - menu: the site's menu link (or OSM's menu URL); a PDF menu is rendered to an
    image (needs pypdfium2), an image menu is saved, and an HTML menu page is read
    for dish names and prices so the diary can order a real dish at its real price
  - hotels: also looks at a "rooms" page for room photos

Everything is cached in backup/places/venues.json + backup/places/img/, fetched
once per venue, in the background.
"""
import hashlib
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 KestrelAirLogbook',
      'Accept-Language': 'en-GB,en;q=0.9'}
SKIP_IMG = re.compile(r'logo|icon|sprite|favicon|badge|award|tripadvisor|trustpilot|booking|payment|visa|mastercard|'
                      r'flag|arrow|button|banner-ad|placeholder|loader|spinner|avatar|social|facebook|instagram|twitter|map', re.I)
NOT_MENU = re.compile(r'nutrition|allergen|calorie|spreadsheet|ingredient|careers|jobs|privacy|terms', re.I)
MENU_LINK = re.compile(r'\bmenu|menus|carte|speisekarte|our[- ]?food|food[- ]?(and|&)[- ]?drink|eat\b|dining|メニュー|菜单|메뉴', re.I)
ROOM_LINK = re.compile(r'\broom|suite|accommodation|stay|chambre|zimmer', re.I)
PRICE = re.compile(r'([£$€¥₩₺₽]\s?\d{1,4}(?:[.,]\d{1,2})?|\d{1,4}[.,]\d{2}\s?(?:€|£|₺|₽|zł|kr|TL)?)')


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs, self.links, self.meta, self.text = [], [], {}, []
        self._skip, self._a = 0, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg'):
            self._skip += 1
        if tag == 'meta' and (a.get('property') or a.get('name') or '').lower() in ('og:image', 'twitter:image', 'og:image:url'):
            self.meta.setdefault('image', a.get('content'))
        if tag == 'img':
            src = a.get('data-src') or a.get('data-lazy-src') or a.get('src')
            srcset = a.get('srcset') or a.get('data-srcset')
            if srcset:  # take the widest candidate
                parts = [p.strip().split(' ') for p in srcset.split(',') if p.strip()]
                best = max(parts, key=lambda p: int(re.sub(r'\D', '', p[1]) or 0) if len(p) > 1 else 0)
                src = best[0] or src
            if src:
                self.imgs.append((src, (a.get('alt') or '') + ' ' + (a.get('class') or '')))
        if tag == 'source' and (a.get('srcset') or a.get('data-srcset')):
            first = (a.get('srcset') or a.get('data-srcset')).split(',')[-1].strip().split(' ')[0]
            self.imgs.append((first, ''))
        style = a.get('style') or ''
        for u in re.findall(r'url\((["\']?)([^)"\']+)\1\)', style):     # background-image galleries
            self.imgs.append((u[1], 'bg'))
        if tag == 'a' and a.get('href'):
            self._a = [a['href'], '']
            if re.search(r'\.(jpe?g|png|webp)(\?|$)', a['href'], re.I):  # lightbox links to full-size photos
                self.imgs.append((a['href'], a.get('title') or ''))
        if tag in ('br', 'p', 'li', 'div', 'tr', 'h1', 'h2', 'h3', 'h4', 'td', 'span'):
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg') and self._skip:
            self._skip -= 1
        if tag == 'a' and self._a:
            self.links.append(tuple(self._a))
            self._a = None

    def handle_data(self, data):
        if self._skip:
            return
        self.text.append(data)
        if self._a is not None:
            self._a[1] += data


def _fetch(url, limit=6_000_000, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get('Content-Type', '')
        return r.read(limit), ctype, r.geturl()


def _page(url):
    raw, ctype, final = _fetch(url)
    if 'html' not in ctype:
        return None, final, raw, ctype
    p = _Page()
    try:
        p.feed(raw.decode('utf-8', 'replace'))
    except Exception:
        pass
    return p, final, raw, ctype


def _save_image(data, dest, min_w=420, min_h=280):
    from PIL import Image, ImageOps
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    except Exception:
        return False
    w, h = im.size
    if w < min_w or h < min_h or w / h > 3.2 or h / w > 3.2:
        return False
    im.thumbnail((1000, 1000))
    im.save(dest, 'JPEG', quality=84, optimize=True)
    return True


def _menu_items(text):
    """Dish name + price pairs from a menu page's text."""
    items, seen = [], set()
    lines = [re.sub(r'\s+', ' ', l).strip() for l in ''.join(text).split('\n')]
    for i, line in enumerate(lines):
        m = PRICE.search(line)
        if not m:
            continue
        name = line[:m.start()].strip(' .-–…:|')
        if len(name) < 3 and i > 0:          # price on its own line: name is the line above
            name = lines[i - 1].strip(' .-–…:|')
        if not (3 <= len(name) <= 60) or not re.search(r'[^\W\d_]{3}', name) or PRICE.search(name):
            continue
        if re.search(r'cookie|privacy|delivery|voucher|gift|vat|service charge|book|reserv|opening|copyright', name, re.I):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({'name': name[:60], 'price': m.group(1).replace(' ', '')})
        if len(items) >= 18:
            break
    return items


def _pdf_first_page(data, dest):
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return False
    try:
        pdf = pdfium.PdfDocument(data)
        page = pdf[0]
        img = page.render(scale=1.6).to_pil().convert('RGB')
        img.thumbnail((1100, 1500))
        img.save(dest, 'JPEG', quality=85)
        return True
    except Exception:
        return False


def venue_media(place, cache_dir, fetch=True, hotel=False):
    """{'photos': [file], 'menu': {kind: image|text, file?, items?, url}, 'site': url} or None."""
    url = (place or {}).get('website') or None
    menu_url = (place or {}).get('menu')
    if not url and not menu_url:
        return None
    path = os.path.join(cache_dir, 'venues.json')
    cache = _CACHE.setdefault(path, json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {})
    key = (url or menu_url).strip()
    if key in cache:
        return cache[key]
    if not fetch:
        return None
    img_dir = os.path.join(cache_dir, 'img')
    os.makedirs(img_dir, exist_ok=True)
    tag = hashlib.sha1(key.encode()).hexdigest()[:10]
    out = {'photos': [], 'menu': None, 'site': url, 'fetched': time.strftime('%Y-%m-%d')}
    try:
        if url and not url.startswith('http'):
            url = 'https://' + url
        pages = []
        if url:
            p, final, _, _ = _page(url)
            if p:
                pages.append((p, final))
                if not menu_url:
                    menu_url = next((urllib.parse.urljoin(final, h) for h, t in p.links
                                     if MENU_LINK.search(h.rsplit('/', 1)[-1] + ' ' + t) and not NOT_MENU.search(h + ' ' + t)
                                     and not h.startswith(('mailto:', 'tel:', '#'))), None)
                if hotel:
                    room = next((urllib.parse.urljoin(final, h) for h, t in p.links if ROOM_LINK.search(h + ' ' + t)
                                 and urllib.parse.urlparse(urllib.parse.urljoin(final, h)).netloc == urllib.parse.urlparse(final).netloc), None)
                    if room:
                        try:
                            rp, rfinal, _, _ = _page(room)
                            if rp:
                                pages.insert(0, (rp, rfinal))   # room photos first
                        except Exception:
                            pass
        # menu
        if menu_url:
            try:
                mp, mfinal, raw, ctype = _page(menu_url)
                if mp is None and ('pdf' in ctype or mfinal.lower().endswith('.pdf')):
                    f = f'venue-{tag}-menu.jpg'
                    if _pdf_first_page(raw, os.path.join(img_dir, f)):
                        out['menu'] = {'kind': 'image', 'file': f, 'url': mfinal}
                elif mp is None and ctype.startswith('image/'):
                    f = f'venue-{tag}-menu.jpg'
                    if _save_image(raw, os.path.join(img_dir, f), 300, 300):
                        out['menu'] = {'kind': 'image', 'file': f, 'url': mfinal}
                elif mp is not None:
                    items = _menu_items(mp.text)
                    if len(items) >= 4:
                        out['menu'] = {'kind': 'text', 'items': items, 'url': mfinal}
                    else:   # a page linking a PDF menu
                        pdf = next((urllib.parse.urljoin(mfinal, h) for h, t in mp.links
                                    if h.lower().split('?')[0].endswith('.pdf') and not NOT_MENU.search(h + ' ' + t)), None)
                        if pdf:
                            raw2, ct2, f2 = _fetch(pdf)
                            f = f'venue-{tag}-menu.jpg'
                            if _pdf_first_page(raw2, os.path.join(img_dir, f)):
                                out['menu'] = {'kind': 'image', 'file': f, 'url': f2}
                        if not out['menu']:
                            out['menu'] = {'kind': 'link', 'url': mfinal}
                    pages.append((mp, mfinal))
            except Exception:
                out['menu'] = {'kind': 'link', 'url': menu_url}
        # photos: share image first, then large pictures from the pages
        cands = []
        for p, base in pages:
            if p.meta.get('image'):
                cands.append(urllib.parse.urljoin(base, p.meta['image']))
            for src, alt in p.imgs:
                full = urllib.parse.urljoin(base, src.strip())
                if full.startswith('http') and not SKIP_IMG.search(full + ' ' + alt) and not full.lower().split('?')[0].endswith(('.svg', '.gif')):
                    cands.append(full)
        seen = set()
        for c in cands:
            if c in seen or len(out['photos']) >= 4:
                continue
            seen.add(c)
            try:
                data, ctype, _ = _fetch(c, limit=8_000_000, timeout=12)
            except Exception:
                continue
            f = f'venue-{tag}-{len(out["photos"])}.jpg'
            if _save_image(data, os.path.join(img_dir, f)):
                out['photos'].append(f)
            if len(seen) > 14:
                break
    except Exception as e:
        out['error'] = str(e)[:120]
    cache[key] = out
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0)
    return out


_CACHE = {}
