// Layover diary: an Instagram-style feed of the pilot's time on the ground wherever
// he stayed 8 hours or more. The restaurants and sights are real and near the
// airport (OpenStreetMap + Wikipedia); the day out is imagined - and labelled so.
import { html, render, flagUrl, num } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';
import { store } from '../core/store.js';

const dayFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
const shortFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

export default {
  id: 'diary',
  init({ db, ui }) {
    const who = db.pilot.character || db.pilot.name;
    const handle = `${who.toLowerCase().replace(/\W+/g, '')}.flies`;
    const avatar = db.pilot.photo;
    const stays = db.stops.filter((s) => s.diary);

    // Instagram-style carousel: dish, the real place, its menu
    const slideLabel = { dish: 'Ordered', place: '', menu: 'Menu' };
    const carousel = (p) => {
      const slides = p.slides || [];
      if (!slides.length) return html`<div class="ig-photo"><div class="ig-blank">${icon(p.kind === 'hotel' ? 'pin' : 'fork')}<span>${p.place}</span></div></div>`;
      return html`<div class="ig-photo ig-carousel" data-i="0">
        <div class="ig-track">${slides.map((sl) => sl.kind === 'menutext'
          ? html`<div class="ig-slide ig-papermenu"><div class="pm-inner">
              <h5>${sl.label}</h5><p class="pm-sub">Menu</p>
              <ul>${sl.items.map((it) => html`<li class="${it.name === sl.ordered ? 'ordered' : ''}"><span>${it.name}</span><i></i><b>${it.price}</b></li>`)}</ul>
              <a href="${sl.url}" target="_blank" rel="noopener">Full menu on their website ↗</a></div></div>`
          : sl.kind === 'menulink'
          ? html`<a class="ig-slide ig-menucard" href="${sl.url}" target="_blank" rel="noopener">${icon('fork')}<b>${sl.isMenu ? 'See the menu' : 'Visit their website'}</b><span>${sl.label}</span><small>${new URL(sl.url, location.href).hostname.replace(/^www\./, '')}</small></a>`
          : html`<figure class="ig-slide"><img src="${sl.src}" alt="" loading="lazy">
              <figcaption>${slideLabel[sl.kind] ? html`<b>${slideLabel[sl.kind]}</b> ` : ''}${sl.label}</figcaption>
              ${sl.credit ? html`<a class="ig-credit" href="${sl.credit}" target="_blank" rel="noopener" title="${sl.from ? `Photo from ${sl.from}` : 'Photo source'}">©</a>` : ''}</figure>`)}</div>
        ${slides.length > 1 ? html`<button class="ig-nav prev" data-d="-1" aria-label="Previous">${icon('back')}</button>
          <button class="ig-nav next" data-d="1" aria-label="Next">${icon('forward')}</button>
          <div class="ig-dots">${slides.map((_, i) => html`<i class="${i ? '' : 'on'}"></i>`)}</div>` : ''}</div>`;
    };
    const slide = (car, d) => {
      const track = car.querySelector('.ig-track'), n = track.children.length;
      const i = Math.max(0, Math.min(n - 1, +car.dataset.i + d));
      car.dataset.i = i;
      track.style.transform = `translateX(-${i * 100}%)`;
      car.querySelectorAll('.ig-dots i').forEach((dot, k) => dot.classList.toggle('on', k === i));
    };

    // ---------- hashtags: every tag opens a card with real information
    const posts = new Map();
    const keyOf = (s, p) => { const k = `${s.id}|${p.time}|${p.place}`; posts.set(k, { s, p }); return k; };
    const wiki = new Map();
    const summary = async (titles) => {
      for (const t of titles.filter(Boolean)) {
        if (!wiki.has(t)) {
          wiki.set(t, fetch('https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(t.replace(/ /g, '_')))
            .then((r) => (r.ok ? r.json() : null)).catch(() => null));
        }
        const s = await wiki.get(t);
        if (s && s.type !== 'disambiguation' && s.extract) return s;
      }
      return null;
    };
    let card = null;
    const closeCard = () => { card?.remove(); card = null; };
    const place = (el, x, y) => {
      const w = 340, h = el.offsetHeight;
      el.style.left = `${Math.max(12, Math.min(innerWidth - w - 12, x - w / 2))}px`;
      el.style.top = `${Math.max(12, Math.min(innerHeight - h - 12, y + 14))}px`;
    };
    const facts = (rows) => rows.filter((r) => r && r[1]).length
      ? html`<div class="facts">${rows.filter((r) => r && r[1]).map(([k, v]) => html`<div class="fact"><span>${k}</span><b>${v}</b></div>`)}</div>` : '';
    const wikiBlock = (s) => s ? html`${s.extract ? html`<p>${s.extract}</p>` : ''}` : html`<p class="note">No Wikipedia article found.</p>`;

    async function openTag(key, i, x, y) {
      const { s, p } = posts.get(key) || {};
      const t = p?.tags?.[i];
      if (!t) return;
      closeCard();
      card = document.createElement('div');
      card.className = 'glass tagcard';
      document.body.append(card);
      const a = db.airports[s.airport];
      const show = (tpl) => { if (!card) return; render(card, html`<button class="tc-close" aria-label="Close">${icon('close')}</button>${tpl}`); place(card, x, y); };
      const loading = html`<div class="tc-body"><div class="tc-kind">${t.k}</div><h3>${t.t}</h3><div class="loading"><span class="spinner"></span>Looking it up…</div></div>`;
      if (t.k === 'country') {
        show(loading);
        const w = await summary([t.name]);
        const here = Object.values(db.airports).filter((x) => x.country?.iso === t.iso);
        show(html`${w?.thumbnail ? html`<img class="tc-img" src="${w.originalimage?.source || w.thumbnail.source}" alt="">` : ''}
          <div class="tc-body"><div class="tc-kind">Country</div><h3>${t.iso ? html`<img src="${flagUrl(t.iso)}" alt="">` : ''}${t.name}</h3>
          <div class="tc-sub">${w?.description || ''}</div>${wikiBlock(w)}
          ${facts([['Your airports here', here.map((x) => x.ident).join(', ')], ['Landings here', here.reduce((n, x) => n + x.visits, 0)]])}
          <div class="links">${w?.content_urls ? html`<a class="link-btn" href="${w.content_urls.desktop.page}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div></div>`);
      } else if (t.k === 'town') {
        show(loading);
        const w = await summary([`${t.name}, ${t.country}`, t.name]);
        show(html`${w?.thumbnail ? html`<img class="tc-img" src="${w.originalimage?.source || w.thumbnail.source}" alt="">` : ''}
          <div class="tc-body"><div class="tc-kind">Town</div><h3>${t.name}</h3><div class="tc-sub">${w?.description || t.country || ''}</div>${wikiBlock(w)}
          ${facts([['Country', t.country], ['Airport', `${a.ident} · ${a.name}`], ['Stay', s.diary.nights ? `${s.diary.nights} night${s.diary.nights === 1 ? '' : 's'}` : `${Math.round(s.diary.hours)} hours`]])}
          <div class="links">${w?.content_urls ? html`<a class="link-btn" href="${w.content_urls.desktop.page}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div></div>`);
      } else if (t.k === 'airport') {
        show(html`${a.wiki?.image ? html`<img class="tc-img" src="${a.wiki.image}" alt="">` : ''}
          <div class="tc-body"><div class="tc-kind">Airport</div><h3>${a.ident}</h3><div class="tc-sub">${a.name}${a.city ? ` · ${a.city}` : ''}</div>
          ${a.wiki?.extract ? html`<p>${a.wiki.extract}</p>` : ''}
          ${facts([['Elevation', a.elevationFt != null ? `${num(a.elevationFt)} ft` : null], ['Longest runway', a.longestRunwayFt ? `${num(a.longestRunwayFt)} ft` : null],
                   ['Your visits', a.visits], ['Opened', a.wiki?.opened]])}
          <div class="links"><button class="link-btn" data-goleg="${s.after}">${icon('plane')}Your flight in</button>
            ${a.wiki?.url ? html`<a class="link-btn" href="${a.wiki.url}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div></div>`);
      } else if (t.k === 'venue') {
        const v = p.venue;
        const pic = (p.slides || []).find((x) => x.kind === 'place')?.src;
        const osm = v.lat != null ? `https://www.openstreetmap.org/?mlat=${v.lat}&mlon=${v.lon}#map=18/${v.lat}/${v.lon}` : null;
        show(html`${pic ? html`<img class="tc-img" src="${pic}" alt="">` : ''}
          <div class="tc-body"><div class="tc-kind">${p.kind === 'hotel' ? 'Hotel' : 'Restaurant'}</div><h3>${v.name}</h3>
          <div class="tc-sub">${[v.cuisine, v.kind && v.kind !== 'restaurant' ? v.kind : null, v.stars ? `${v.stars}★` : null].filter(Boolean).join(' · ')}</div>
          ${facts([['Address', [v.street, v.town].filter(Boolean).join(', ')], ['From the airport', v.km != null ? `${v.km} km from ${s.airport}` : null],
                   ['Opening hours', v.hours], p.price ? ['Kazber had', `${p.dish} · ${p.price}`] : p.dish ? ['Kazber had', p.dish] : null])}
          <div class="links">${v.menu ? html`<a class="link-btn" href="${v.menu}" target="_blank" rel="noopener">${icon('fork')}Menu</a>` : ''}
            ${v.website ? html`<a class="link-btn" href="${v.website}" target="_blank" rel="noopener">Website ${icon('external')}</a>` : ''}
            ${osm ? html`<a class="link-btn" href="${osm}" target="_blank" rel="noopener">${icon('pin')}Map</a>` : ''}</div>
          <p class="note" style="margin-top:10px">Details from OpenStreetMap${pic ? ' · photo from the venue' : ''}.</p></div>`);
      } else if (t.k === 'menu') {
        const m = (p.slides || []).find((x) => ['menu', 'menutext', 'menulink'].includes(x.kind));
        show(html`<div class="tc-body"><div class="tc-kind">Menu</div><h3>${p.venue?.name || p.place}</h3>
          ${m.kind === 'menu' ? html`<div class="tc-menu"><a href="${m.credit || m.src}" target="_blank" rel="noopener"><img src="${m.src}" alt=""></a></div>` : ''}
          ${m.kind === 'menutext' ? html`<div class="tc-menu"><div class="ig-papermenu"><div class="pm-inner"><ul>${m.items.map((it) =>
              html`<li class="${it.name === m.ordered ? 'ordered' : ''}"><span>${it.name}</span><i></i><b>${it.price}</b></li>`)}</ul></div></div></div>` : ''}
          <div class="links"><a class="link-btn" href="${m.url || m.credit}" target="_blank" rel="noopener">${icon('fork')}${m.kind === 'menulink' ? 'Open their menu' : 'Full menu'} ${icon('external')}</a></div></div>`);
      } else if (t.k === 'sight') {
        const sg = p.sight;
        show(html`${sg.src ? html`<img class="tc-img" src="${sg.src}" alt="">` : ''}
          <div class="tc-body"><div class="tc-kind">Place to see</div><h3>${sg.title}</h3><div class="tc-sub">${sg.description || ''}</div>
          ${sg.extract ? html`<p>${sg.extract}</p>` : ''}
          <div class="links">${sg.url ? html`<a class="link-btn" href="${sg.url}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div></div>`);
      }
    }
    document.addEventListener('click', (e) => {
      const tb = e.target.closest('.tag-btn');
      if (tb) { e.stopPropagation(); openTag(tb.dataset.post, +tb.dataset.tag, e.clientX, e.clientY); return; }
      if (card && e.target.closest('.tc-close')) { closeCard(); return; }
      const go = e.target.closest('[data-goleg]');
      if (go && card?.contains(go)) { closeCard(); closeSheet(); store.set('selected', go.dataset.goleg); return; }
      if (card && !card.contains(e.target)) closeCard();
    }, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && card) { e.stopImmediatePropagation(); closeCard(); } }, true);

    const post = (s, p, dayNo) => html`<article class="ig">
      <header><span class="ig-av">${avatar ? html`<img src="${avatar}" alt="">` : ''}</span>
        <div><b>${handle}</b><small>${p.place}</small></div><span class="ig-kind">${p.kind === 'sight' ? icon('pin') : icon('fork')}</span></header>
      ${carousel(p)}
      <div class="ig-actions">${icon('heart')}<span>${p.likes.toLocaleString('en-GB')} likes</span><time>Day ${dayNo} · ${p.time.slice(11, 16)}</time></div>
      <p class="ig-cap"><b>${handle}</b> ${p.caption} <span class="ig-tags">${(p.tags || []).map((t, i) =>
        html`<button class="tag-btn ${t.k === 'menu' ? 'menu' : ''}" data-post="${keyOf(s, p)}" data-tag="${i}" title="About ${t.t.slice(1)}">${t.t}</button>`)}</span></p>
      <p class="ig-where">${p.where}${p.hours ? html`<br>Open ${p.hours}` : ''}</p>
      ${p.menu || p.website || p.url ? html`<div class="ig-links">
        ${p.menu ? html`<a class="link-btn" href="${p.menu}" target="_blank" rel="noopener">${icon('fork')}Menu</a>` : ''}
        ${p.website ? html`<a class="link-btn" href="${p.website}" target="_blank" rel="noopener">Website ${icon('external')}</a>` : ''}
        ${p.url ? html`<a class="link-btn" href="${p.url}" target="_blank" rel="noopener">Wikipedia ${icon('external')}</a>` : ''}</div>` : ''}
    </article>`;

    const stayBlock = (s) => {
      const a = db.airports[s.airport], d = s.diary;
      const arrive = new Date(s.arrive), leave = s.depart ? new Date(s.depart) : null;
      const length = d.nights ? `${d.nights} night${d.nights === 1 ? '' : 's'}` : `${Math.round(d.hours)} hours`;
      let n = 0;
      return html`<section class="stay" id="stay-${s.id}">
        <div class="stay-head" style="${a.wiki?.image ? `--bg:url('${a.wiki.image}')` : ''}">
          <div><span class="stay-code">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}${s.airport}</span>
            <h3>${d.city}</h3><small>${a.name} · ${shortFmt.format(arrive)}${leave ? ` – ${shortFmt.format(leave)}` : ' – now'} · ${length}${d.ongoing ? ' · still here' : ''}</small></div>
          <button class="link-btn" data-leg="${s.after}">${icon('plane')}See the flight in</button>
        </div>
        ${d.days.map((day, i) => {
          const dayNo = i === d.days.length - 1 && d.skippedDays ? i + 1 + d.skippedDays : i + 1;
          return html`${i === d.days.length - 1 && d.skippedDays ? html`<p class="stay-skip">… ${d.skippedDays} more days in ${d.city} …</p>` : ''}
            <h4 class="stay-day">${dayFmt.format(new Date(day.date))}<small>Day ${dayNo}</small></h4>
            <div class="ig-row">${day.posts.map((p) => post(s, p, dayNo))}</div>`;
        })}
      </section>`;
    };

    ui.openDiary = (stopId) => {
      const { body } = openSheet({ id: 'diary', title: `${who}'s layover diary`,
        sub: `${stays.length} long stops · the restaurants and sights are real and near each airport; what ${who} got up to is imagined` });
      render(body, html`${stays.length ? stays.map(stayBlock) : html`<p class="note">No stops of 8 hours or more yet.</p>`}`);
      body.addEventListener('click', (e) => {
        const nav = e.target.closest('.ig-nav');
        if (nav) { slide(nav.closest('.ig-carousel'), +nav.dataset.d); return; }
        const b = e.target.closest('[data-leg]');
        if (b) { closeSheet(); store.set('selected', b.dataset.leg); }
      });
      // swipe on touch screens / trackpads
      let sx = null;
      body.addEventListener('pointerdown', (e) => { if (e.target.closest('.ig-carousel')) sx = e.clientX; });
      body.addEventListener('pointerup', (e) => {
        const car = e.target.closest('.ig-carousel');
        if (car && sx != null && Math.abs(e.clientX - sx) > 40) slide(car, e.clientX < sx ? 1 : -1);
        sx = null;
      });
      if (stopId) body.querySelector(`#stay-${CSS.escape(stopId)}`)?.scrollIntoView({ block: 'start' });
    };

    // a preview in the leg card when the next stop was a long one
    ui.diaryPreview = (s) => {
      if (!s?.diary) return '';
      const posts = s.diary.days.flatMap((d) => d.posts).slice(0, 3);
      const d = s.diary;
      return html`<div class="card diary-card"><h4>Layover in ${d.city}<small>${d.nights ? `${d.nights} night${d.nights === 1 ? '' : 's'}` : `${Math.round(d.hours)} h`}</small></h4>
        <div class="dp-row">${posts.map((p) => { const src = (p.slides || []).find((x) => x.src)?.src; return html`<figure>${src ? html`<img src="${src}" alt="" loading="lazy">` : html`<div class="ig-blank">${icon('fork')}</div>`}
          <figcaption>${p.dish || p.place}</figcaption></figure>`; })}</div>
        <button class="link-btn" data-diary="${s.id}">${icon('diary')}Open ${who}'s diary</button></div>`;
    };
  },
};
