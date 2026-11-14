"""Layover diary: for every stop of 8 hours or more, an imagined day-by-day
Instagram-style account of the pilot on the ground - checking in to a real hotel
near the airport, eating at real restaurants and cafés (ordering what that place
actually serves), and visiting real sights within reach.

Each post is a little carousel: the dish, real photos of the place itself
(Wikimedia Commons, taken right there), and the menu - a photographed menu when
one exists, or a card linking the place's own online menu.

The places come from places.py (OpenStreetMap + Wikipedia/Commons); the days
themselves are made up, deterministically (same stop -> same diary every build).
"""
import hashlib
import os
import random
import re
import shutil
import urllib.parse
from datetime import datetime, timedelta

MIN_HOURS = 8
MAX_DAYS = 7
SLOTS = [(8, 30, 'breakfast'), (11, 15, 'sight'), (13, 0, 'lunch'), (15, 45, 'sight'), (19, 30, 'dinner')]
KIND_LABEL = {'cafe': 'café', 'pub': 'pub', 'bar': 'bar', 'fast_food': 'takeaway', 'restaurant': 'restaurant'}
PREFER = {'breakfast': ('cafe', 'bakery', 'fast_food'), 'lunch': ('cafe', 'restaurant', 'fast_food', 'pub'),
          'dinner': ('restaurant', 'pub')}

MEAL_LINES = {
    'breakfast': ["Coffee and {dish} at {place} before checking the weather.", "Slow start: {dish} at {place}. METARs can wait.",
                  "{dish} at {place}, {km} km from the field. Good fuel for a pilot."],
    'lunch': ["Lunch stop: {dish} at {place}.", "{place} for lunch - the {dish} was the right call.",
              "Grabbed {dish} at {place}, a short hop from {icao}.", "Asked what's good at {place}. Answer: the {dish}."],
    'dinner': ["Dinner at {place}: {dish}. Long day, worth it.", "Ended the day with {dish} at {place}. Tomorrow: wheels up.",
               "{dish} at {place}. Locals swear by it - so do I now.", "Crew dinner for one at {place}. {dish}, no regrets."],
}
HOTEL_LINES = ["Checked in at {place}. Bags down, flight bag charging.", "Home for the night: {place}, {km} km from {icao}.",
               "{place} tonight. Quick shower, then food.", "Room key in hand at {place}. Long day in the air."]
SIGHT_LINES = ["Afternoon off, so I went to see {title}.", "Couldn't leave without visiting {title}.",
               "Stretched the legs: {title}, {desc}.", "Found {title} a short ride from the airport."]
NO_PLACE = {'breakfast': 'the airfield café', 'lunch': 'the crew room', 'dinner': 'the only place still open near {icao}'}


def _rng(key):
    return random.Random(int(hashlib.sha1(key.encode()).hexdigest()[:12], 16))


def _pick(rests, kind):
    """Next unused place that suits the meal (cafés for breakfast, restaurants and pubs for dinner)."""
    for i, r in enumerate(rests):
        c = (r.get('cuisine') or '').lower()
        if r.get('kind') in PREFER[kind] or (kind == 'breakfast' and re.search(r'coffee|breakfast|bakery|cafe', c)):
            return rests.pop(i)
    return rests.pop(0) if rests else None


def _venue(place):
    """What the app shows when you tap a venue's hashtag - all from OpenStreetMap."""
    if not place:
        return None
    keep = ('name', 'kind', 'cuisine', 'street', 'town', 'hours', 'website', 'menu', 'lat', 'lon', 'km', 'stars')
    return {k: place[k] for k in keep if place.get(k) not in (None, '')}


def _tagify(text):
    return '#' + ''.join(w[:1].upper() + w[1:] for w in re.findall(r'[^\W_]+', text or ''))[:28]


def _finish(posts_by_day, a, city, ident, used, web_root):
    """Clickable hashtags for every post (country, town, airport, the place itself,
    its menu), and no photo shown twice anywhere in the diary."""
    for day in posts_by_day:
        for p in day['posts']:
            keep = []
            for sl in p.get('slides', []):
                if sl.get('src'):
                    path = os.path.join(web_root, sl['src'])
                    try:
                        with open(path, 'rb') as fh:
                            digest = hashlib.sha1(fh.read()).hexdigest()
                    except OSError:
                        continue                      # file vanished: don't show a broken slide
                    if digest in used:
                        continue                      # already shown somewhere in the diary
                    used.add(digest)
                keep.append(sl)
            p['slides'] = keep
            country = (a.get('country') or {})
            if p.get('flight'):     # a flight post: tag where it went, not where the layover is
                f = p['flight']
                p['tags'] = [{'t': '#' + f['from'], 'k': 'airport', 'ident': f['from']}, {'t': '#' + f['to'], 'k': 'airport', 'ident': f['to']},
                             {'t': _tagify(f['aircraft']), 'k': 'aircraft'}, {'t': '#MSFS2024', 'k': 'shots'}]
                continue
            tags = [{'t': _tagify(country.get('name')), 'k': 'country', 'iso': country.get('iso'), 'name': country.get('name')},
                    {'t': _tagify(city), 'k': 'town', 'name': city, 'country': country.get('name')},
                    {'t': '#' + ident, 'k': 'airport', 'ident': ident}]
            if p.get('flight'):
                tags.append({'t': _tagify(p['flight']['aircraft']), 'k': 'aircraft'})
            if p.get('venue'):
                tags.append({'t': _tagify(p['venue']['name']), 'k': 'venue'})
            if p.get('sight'):
                tags.append({'t': _tagify(p['sight']['title']), 'k': 'sight'})
            if any(sl['kind'] in ('menu', 'menutext', 'menulink') for sl in p['slides']):
                tags.append({'t': '#Menu', 'k': 'menu'})
            if p.get('newsRef'):
                tags.append({'t': p['newsRef']['tag'], 'k': 'news', 'id': p['newsRef']['id']})
            p['tags'] = [t for t in tags if len(t['t']) > 1]


FLIGHT_LINES = ["Wheels down at {to} after {dur} from {frm}.", "{frm} to {to} in the {ac}. {dur} well spent.",
                 "Made it to {to}. {dur} in the {ac} from {frm}.", "Touchdown {to}. {dur} from {frm}, {fpm}."]


def _flight_post(leg, airports, aircraft, photos, stop_photos, rng):
    """The pilot's own MSFS screenshots from the flight in (and from the ground there) as a real post."""
    shots = [photos[i] for i in list(leg.get('photos') or []) + list(stop_photos or []) if i in photos]
    if not shots:
        return None
    dep, arr = airports[leg['from']], airports[leg['to']]
    acd = aircraft.get(leg.get('aircraft')) or {}
    # the aircraft's proper type name (e.g. "Cessna 172") rather than the add-on's long title
    ac = (acd.get('wiki') or {}).get('title') or re.sub(r'^(Asobo|A2A|FlightFX|Black Square|PMDG|Carenado)\s+', '', acd.get('name') or 'aircraft')
    mins = round(leg.get('minutes') or 0)
    dur = f'{mins // 60}h {mins % 60:02d}m' if mins >= 60 else f'{mins} min'
    fpm = f'landed at {leg["landingFpm"]} fpm' if leg.get('landingFpm') else 'smooth enough'
    return {'kind': 'flight', 'time': leg['end'][:16], 'place': f'{leg["from"]} → {leg["to"]}',
            'where': f'{dep["name"]} → {arr["name"]} · {ac}', 'own': True,
            'slides': [{'kind': 'shot', 'src': p['src'], 'pid': p['id'], 'label': f'{p["takenAt"][11:16]} · {leg["from"]} → {leg["to"]}'} for p in shots[:10]],
            'flight': {'leg': leg['id'], 'from': leg['from'], 'to': leg['to'], 'minutes': leg.get('minutes'), 'aircraft': ac,
                       'aircraftId': leg.get('aircraft'),
                       'landingFpm': leg.get('landingFpm'), 'distanceNm': leg.get('distanceNm')},
            'caption': rng.choice(FLIGHT_LINES).format(to=leg['to'], frm=leg['from'], dur=dur, ac=ac, fpm=fpm),
            'likes': rng.randint(60, 480)}


NEWS_LINES = ["Picked up the {src} with breakfast: “{h}”. Big talk round here.",
               "Everyone at the bar was on about this: “{h}”.",
               "Local paper on the table: “{h}”. Never a dull day in {town}.",
               "Overheard at the next table: “{h}”."]
NEWS_SAD = ["Sobering read in the local paper this morning: “{h}”. Thoughts with everyone affected.",
            "Quiet mood in {town} today. “{h}”."]
STOP = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'after', 'over', 'have', 'will', 'set', 'new', 'says', 'said', 'are', 'was', 'its'}


def _news_tag(title, town):
    """A hashtag for a story from its distinctive words, e.g. '#HighStreetParking'."""
    skip = STOP | {w.lower() for w in re.findall(r'[^\W\d_]+', town or '')}
    ws = [w for w in re.findall(r"[^\W\d_][\w']+", title) if w.lower() not in skip and len(w) > 2]
    caps = [w for w in ws if w[0].isupper()] or ws
    return '#' + ''.join(w[:1].upper() + w[1:] for w in caps[:3])[:30]


def build(stops, legs, airports, places, web_media, places_img, places_mod=None, fetch=False, photos=None, aircraft=None, news=None):
    os.makedirs(web_media, exist_ok=True)
    by_id = {l['id']: l for l in legs}
    photos, aircraft, news = photos or {}, aircraft or {}, news or {}
    used_photos = set()
    web_root = os.path.dirname(os.path.dirname(web_media))

    def publish(f):
        if not f:
            return None
        src, dst = os.path.join(places_img, f), os.path.join(web_media, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
        return f'media/places/{f}' if os.path.exists(dst) else None

    def about(place, credit):
        """Is this Commons photo actually of the venue? Its title must name the place
        (a photo merely taken nearby could be anything - a snow gauge, a bus stop)."""
        if not credit:
            return False
        from urllib.parse import unquote
        title = unquote(credit.rsplit('/', 1)[-1]).replace('_', ' ').lower()
        words = [w for w in re.findall(r'[^\W\d_]{4,}', place['name'].lower())
                 if w not in ('hotel', 'restaurant', 'cafe', 'café', 'house', 'the', 'and', 'bar', 'pub', 'inn')]
        return bool(words) and any(w in title for w in words)

    def venue_slides(place, hotel=False):
        """Real photos of the venue (its own website first, then Commons photos titled
        with its name) + its real menu (rendered PDF / photo / dishes and prices / link)."""
        slides = []
        site = None
        if place and (place.get('website') or place.get('menu')):
            try:
                import venues
                site = venues.venue_media(place, os.path.dirname(places_img), fetch, hotel=hotel)
            except Exception:
                site = None
        if site:
            dom = urllib.parse.urlparse(site.get('site') or '').netloc.replace('www.', '')
            for f in site['photos'][:4]:
                src = publish(f)
                if src:
                    slides.append({'kind': 'place', 'src': src, 'label': place['name'], 'credit': site.get('site'), 'from': dom})
            m = site.get('menu')
            if m and m['kind'] == 'image' and publish(m['file']):
                slides.append({'kind': 'menu', 'src': publish(m['file']), 'label': f'Menu · {place["name"]}', 'credit': m['url']})
            elif m and m['kind'] == 'text':
                slides.append({'kind': 'menutext', 'items': m['items'][:14], 'label': place['name'], 'url': m['url']})
            elif m and m['kind'] == 'link':
                slides.append({'kind': 'menulink', 'url': m['url'], 'label': place['name'], 'isMenu': True})
        if slides and any(s['kind'] == 'place' for s in slides):
            return slides
        if places_mod and place:
            pp = places_mod.place_photos(places_mod.CACHE, place, places_img, fetch)
            for ph in [ph for ph in pp['photos'] if about(place, ph['credit'])][:2]:
                src = publish(ph['file'])
                if src:
                    slides.append({'kind': 'place', 'src': src, 'label': place['name'], 'credit': ph['credit']})
            if pp.get('menu') and publish(pp['menu']['file']) and not any(s['kind'].startswith('menu') for s in slides):
                slides.append({'kind': 'menu', 'src': publish(pp['menu']['file']), 'label': f'Menu · {place["name"]}', 'credit': pp['menu']['credit']})
        if place and (place.get('menu') or place.get('website')) and not any(s['kind'].startswith('menu') for s in slides) and not hotel:
            slides.append({'kind': 'menulink', 'url': place.get('menu') or place.get('website'), 'label': place['name'],
                           'isMenu': bool(place.get('menu'))})
        return slides

    count = 0
    leg_index = {l['id']: i for i, l in enumerate(legs)}
    prev_idx = -1          # legs after the previous layover = how the pilot got to this one
    for s in stops:
        if not s.get('arrive'):
            continue
        arrive = datetime.fromisoformat(s['arrive'])
        depart = datetime.fromisoformat(s['depart']) if s.get('depart') else datetime.now()
        hours = (depart - arrive).total_seconds() / 3600
        nxt = by_id.get(s.get('before'))
        if hours < MIN_HOURS or (nxt and nxt['kind'] == 'ground') or s['airport'] not in places:
            continue
        # "Getting here": a post for every flight since the last layover with the pilot's own screenshots
        here_idx = leg_index.get(s.get('after'), prev_idx)
        stop_photo_by_leg = {st['after']: st.get('photos') for st in stops if st.get('after')}
        inbound = []
        for li in range(prev_idx + 1, here_idx + 1):
            lg = legs[li]
            if lg['kind'] != 'flight':
                continue
            fp = _flight_post(lg, airports, aircraft, photos, stop_photo_by_leg.get(lg['id']), _rng(lg['id']))
            if fp:
                inbound.append(fp)
        prev_idx = here_idx
        a, p = airports[s['airport']], places[s['airport']]
        rng = _rng(s['id'])
        # places with their own website (real photos, real menu) first, then the rest
        all_rests = list(p.get('restaurants') or [])
        web = [r for r in all_rests if r.get('website') or r.get('menu')]
        other = [r for r in all_rests if not (r.get('website') or r.get('menu'))]
        rng.shuffle(web)
        rng.shuffle(other)
        rests = web + other
        # real places worth a visit - never an accident site or disaster article
        bad = re.compile(r'crash|accident|disaster|incident|flight \d|shooting|bombing|murder|massacre|explosion|collision', re.I)
        sights = [g for g in (p.get('sights') or []) if not bad.search(f'{g["title"]} {g.get("description") or ""}')]
        rng.shuffle(sights)
        dishes = list(p.get('dishes') or [])
        hotels = list(p.get('hotels') or [])
        city = a.get('city') or a['name']
        tag = lambda text: '#' + ''.join(w.capitalize() for w in re.findall(r'[^\W\d_]+', text))[:24]
        # country first, then the town, then the airfield
        tags = [t for t in (tag((a.get('country') or {}).get('name') or ''), tag(city), '#' + s['airport'], '#layover', '#pilotlife') if len(t) > 1]
        overnight = depart.date() > arrive.date() or hours >= 12
        hotels.sort(key=lambda h: (not h.get('website'), h['km']))      # a hotel we can show, nearest first
        hotel = hotels[0] if hotels and overnight else None

        days, d = [], arrive.date()
        while d <= depart.date():
            lo = arrive + timedelta(hours=1) if d == arrive.date() else datetime.combine(d, datetime.min.time())
            hi = depart - timedelta(hours=1, minutes=30) if d == depart.date() else datetime.combine(d, datetime.max.time())
            posts, used_sight = [], False
            t = arrive + timedelta(hours=1, minutes=10)   # check-in, on whichever day that falls
            if hotel and d == t.date():
                slides = venue_slides({**hotel, 'menu': None}, hotel=True)
                posts.append({'kind': 'hotel', 'time': t.strftime('%Y-%m-%dT%H:%M'), 'place': hotel['name'],
                              'where': ' · '.join(x for x in (f'{hotel["km"]} km from {s["airport"]}', hotel['kind'],
                                                             f'{hotel["stars"]}★' if hotel.get('stars') else None, hotel.get('street')) if x),
                              'slides': [x for x in slides if x['kind'] == 'place'], 'website': hotel.get('website'),
                              'venue': _venue(hotel),
                              'caption': rng.choice(HOTEL_LINES).format(place=hotel['name'], km=hotel['km'], icao=s['airport']),
                              'likes': rng.randint(20, 180)})
            for h, m, kind in SLOTS:
                t = datetime.combine(d, datetime.min.time()) + timedelta(hours=h, minutes=m)
                if not (lo <= t <= hi):
                    continue
                if kind == 'sight':
                    if used_sight or not sights or rng.random() < 0.25:
                        continue
                    sg = sights.pop(0)
                    used_sight = True
                    src = publish(sg['image'])
                    posts.append({'kind': 'sight', 'time': t.strftime('%Y-%m-%dT%H:%M'), 'place': sg['title'],
                                  'where': sg.get('description') or f'near {s["airport"]}',
                                  'slides': [{'kind': 'place', 'src': src, 'label': sg['title'], 'credit': sg.get('url')}] if src else [],
                                  'caption': rng.choice(SIGHT_LINES).format(title=sg['title'], desc=(sg.get('description') or 'a local landmark').lower()),
                                  'extract': sg.get('extract'), 'url': sg.get('url'), 'likes': rng.randint(40, 420),
                                  'sight': {'title': sg['title'], 'description': sg.get('description'), 'extract': sg.get('extract'),
                                            'url': sg.get('url'), 'src': src}})
                    continue
                if kind == 'lunch' and any(x['kind'] in ('breakfast', 'lunch') for x in posts) and rng.random() < 0.6:
                    continue
                place = _pick(rests, kind)
                pname = place['name'] if place else NO_PLACE[kind].format(icao=s['airport'])
                venue = venue_slides(place)
                real_menu = next((x for x in venue if x['kind'] == 'menutext'), None)
                mains = [i for i in (real_menu or {}).get('items', [])
                         if not re.search(r'extra|topping|\badd\b|add-on|upgrade|supplement|sauce|\bdip\b|side of|per person|each|deposit|minimum|delivery|fee', i['name'], re.I)]
                if real_menu and mains:
                    # order an actual dish off the actual menu, at its actual price
                    item = rng.choice(mains)
                    dish_name, price = item['name'], item['price']
                    real_menu['ordered'] = item['name']
                else:
                    # otherwise something this place serves (its cuisine), else a local dish
                    menu = (place or {}).get('order') or dishes
                    pick = rng.choice(menu) if menu else None
                    dish_name, price = (pick['title'] if pick else None), None
                slides = list(venue)
                if dish_name and not real_menu and not any(x['kind'] == 'place' for x in venue):
                    # no photos of the place itself: show the dish so the post still has a picture
                    dish = next((x for x in ((place or {}).get('order') or dishes) if x['title'] == dish_name), None)
                    varied = places_mod.dish_photo(places_mod.CACHE, dish_name, rng.randint(0, 997), places_img, fetch) if places_mod else None
                    src = publish(varied) or (publish(dish.get('image')) if dish else None)
                    if src:
                        slides.insert(0, {'kind': 'dish', 'src': src, 'label': dish_name})
                bits = [f'{place["km"]} km from {s["airport"]}', place.get('cuisine') or KIND_LABEL.get(place.get('kind'), ''),
                        place.get('street')] if place else [s['airport']]
                ordered = f'{dish_name} ({price})' if price else (dish_name or 'something local')
                posts.append({'kind': kind, 'time': t.strftime('%Y-%m-%dT%H:%M'), 'place': pname,
                              'where': ' · '.join(b for b in bits if b), 'dish': dish_name, 'price': price, 'slides': slides,
                              'realMenu': bool(real_menu), 'venue': _venue(place),
                              'website': (place or {}).get('website'), 'menu': (place or {}).get('menu'), 'hours': (place or {}).get('hours'),
                              'caption': rng.choice(MEAL_LINES[kind]).format(dish=ordered, place=pname,
                                                                             km=place['km'] if place else 1, icao=s['airport']),
                              'likes': rng.randint(18, 260)})
            if posts:
                days.append({'date': d.isoformat(), 'posts': posts})
            d += timedelta(days=1)
        if not days:
            continue
        extra = max(0, len(days) - MAX_DAYS)
        if extra:
            days = days[:MAX_DAYS - 1] + [days[-1]]
        # flavour the days with real local stories from when the pilot was there (one per day, each once)
        stories = [news[i] for i in (by_id.get(s.get('after')) or {}).get('news', []) if i in news]
        for di, day in enumerate(days):
            if di >= len(stories):
                break
            target = next((p for p in day['posts'] if p['kind'] in ('breakfast', 'lunch', 'dinner', 'hotel')), None) or \
                     next((p for p in day['posts'] if p['kind'] != 'flight'), None)
            if not target:
                continue
            st = stories[di]
            headline = st['title'] if len(st['title']) <= 90 else st['title'][:87].rsplit(' ', 1)[0] + '…'
            line = rng.choice(NEWS_SAD if st.get('tone') == 'sad' else NEWS_LINES).format(
                h=headline, src=st.get('source') or 'local paper', town=city)
            target['caption'] = f'{target["caption"]} {line}'
            target['newsRef'] = {'id': st['id'], 'text': headline, 'tag': _news_tag(st['title'], city)}
        if inbound:
            days.insert(0, {'date': inbound[0]['time'][:10], 'posts': inbound, 'inbound': True})
        _finish(days, a, city, s['airport'], used_photos, web_root)
        s['diary'] = {'hours': round(hours, 1), 'nights': max(0, (depart.date() - arrive.date()).days), 'city': city,
                      'tags': tags, 'days': days, 'skippedDays': extra, 'ongoing': not s.get('depart'),
                      'hotel': hotel['name'] if hotel else None}
        count += 1
    return count
