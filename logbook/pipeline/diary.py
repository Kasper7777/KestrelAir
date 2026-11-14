"""Layover diary: for every stop of 8 hours or more, an imagined day-by-day
Instagram-style account of Casper on the ground - meals at real restaurants
near the airport, local dishes, and real sights within reach.

The places come from places.py (OpenStreetMap + Wikipedia); the days themselves
are made up, deterministically (same stop -> same diary on every build).
"""
import hashlib
import os
import random
import shutil
from datetime import datetime, timedelta

MIN_HOURS = 8
MAX_DAYS = 7
SLOTS = [(8, 30, 'breakfast'), (11, 15, 'sight'), (13, 0, 'lunch'), (15, 45, 'sight'), (19, 30, 'dinner')]

MEAL_LINES = {
    'breakfast': ["Coffee and {dish} at {place} before checking the weather.", "Slow start: {dish} at {place}. METARs can wait.",
                  "{dish} at {place}, {km} km from the field. Good fuel for a pilot."],
    'lunch': ["Lunch stop: {dish} at {place}.", "{place} for lunch - the {dish} was the right call.",
              "Grabbed {dish} at {place}, a short hop from {icao}."],
    'dinner': ["Dinner at {place}: {dish}. Long day, worth it.", "Ended the day with {dish} at {place}. Tomorrow: wheels up.",
               "{dish} at {place}. Locals swear by it - so do I now.", "Crew dinner for one at {place}. {dish}, no regrets."],
}
SIGHT_LINES = ["Afternoon off, so I went to see {title}.", "Couldn't leave without visiting {title}.",
               "Stretched the legs: {title}, {desc}.", "Found {title} a short ride from the airport."]
NO_PLACE = {'breakfast': 'the airfield café', 'lunch': 'the crew room', 'dinner': 'the only place still open near {icao}'}


def _rng(key):
    return random.Random(int(hashlib.sha1(key.encode()).hexdigest()[:12], 16))


def build(stops, legs, airports, places, web_media, places_img):
    os.makedirs(web_media, exist_ok=True)
    by_id = {l['id']: l for l in legs}

    def publish(f):
        if not f:
            return None
        src, dst = os.path.join(places_img, f), os.path.join(web_media, f)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
        return f'media/places/{f}' if os.path.exists(dst) else None

    count = 0
    for s in stops:
        if not s.get('arrive'):
            continue
        arrive = datetime.fromisoformat(s['arrive'])
        depart = datetime.fromisoformat(s['depart']) if s.get('depart') else datetime.now()
        hours = (depart - arrive).total_seconds() / 3600
        nxt = by_id.get(s.get('before'))
        if hours < MIN_HOURS or (nxt and nxt['kind'] == 'ground') or s['airport'] not in places:
            continue
        a, p = airports[s['airport']], places[s['airport']]
        rng = _rng(s['id'])
        rests = list(p.get('restaurants') or [])
        rng.shuffle(rests)
        sights = list(p.get('sights') or [])
        rng.shuffle(sights)
        dishes = list(p.get('dishes') or [])
        city = a.get('city') or a['name']
        tags = ['#' + ''.join(w.capitalize() for w in city.split() if w.isalpha())[:24], '#layover', '#pilotlife']
        if (a.get('country') or {}).get('name'):
            tags.insert(1, '#' + ''.join(w.capitalize() for w in a['country']['name'].split() if w.isalpha()))

        days, d = [], arrive.date()
        while d <= depart.date():
            lo = arrive + timedelta(hours=1) if d == arrive.date() else datetime.combine(d, datetime.min.time())
            hi = depart - timedelta(hours=1, minutes=30) if d == depart.date() else datetime.combine(d, datetime.max.time())
            posts, used_sight = [], False
            for h, m, kind in SLOTS:
                t = datetime.combine(d, datetime.min.time()) + timedelta(hours=h, minutes=m)
                if not (lo <= t <= hi):
                    continue
                if kind == 'sight':
                    if used_sight or not sights or rng.random() < 0.25:
                        continue
                    sg = sights.pop(0)
                    used_sight = True
                    posts.append({'kind': 'sight', 'time': t.strftime('%Y-%m-%dT%H:%M'), 'place': sg['title'],
                                  'where': sg.get('description') or f'near {s["airport"]}', 'image': publish(sg['image']),
                                  'caption': rng.choice(SIGHT_LINES).format(title=sg['title'], desc=(sg.get('description') or 'a local landmark').lower()),
                                  'extract': sg.get('extract'), 'url': sg.get('url'), 'likes': rng.randint(40, 420)})
                    continue
                if kind == 'lunch' and any(x['kind'] in ('breakfast', 'lunch') for x in posts) and rng.random() < 0.6:
                    continue
                dish = rng.choice(dishes) if dishes else None
                place = rests.pop(0) if rests else None
                pname = place['name'] if place else NO_PLACE[kind].format(icao=s['airport'])
                posts.append({'kind': kind, 'time': t.strftime('%Y-%m-%dT%H:%M'), 'place': pname,
                              'where': f'{place["km"]} km from {s["airport"]}' + (f' · {place["cuisine"]}' if place and place.get('cuisine') else '') if place else s['airport'],
                              'dish': dish['title'] if dish else None, 'image': publish(dish['image']) if dish else None,
                              'caption': rng.choice(MEAL_LINES[kind]).format(dish=(dish['title'] if dish else 'something local').lower() if dish and dish['title'][0].islower() else (dish['title'] if dish else 'something local'),
                                                                             place=pname, km=place['km'] if place else 1, icao=s['airport']),
                              'likes': rng.randint(18, 260)})
            if posts:
                days.append({'date': d.isoformat(), 'posts': posts})
            d += timedelta(days=1)
        if not days:
            continue
        extra = max(0, len(days) - MAX_DAYS)
        if extra:
            days = days[:MAX_DAYS - 1] + [days[-1]]
        s['diary'] = {'hours': round(hours, 1), 'nights': max(0, (depart.date() - arrive.date()).days), 'city': city,
                      'tags': tags, 'days': days, 'skippedDays': extra, 'ongoing': not s.get('depart')}
        count += 1
    return count
