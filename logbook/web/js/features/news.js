// Local news: real stories from where you landed, from around the day you landed.
// - News feed (toolbar): every arrival's stories, newest trip first, with liquid
//   glass tabs (All / Good news / Serious) and a country strip to jump around
// - Story card: ui.openStory(id, x?, y?) - picture, headline, summary, outlet, date, link
// - Leg card section: "Local news" on each flight (via the registry)
// - Replay: ui.popNews(leg) - on the map, in a column at the side, both, or off
//   (Replay options on the dock); ui.endNewsRail() clears the column
// Stories whose own picture hasn't been found yet show as a newspaper cutting -
// never a stand-in photo.
import { html, render, day, flagUrl, duration, num } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';
import { store } from '../core/store.js';
import { liquidTabs } from '../core/liquid.js';
import { register } from './registry.js';

const dateFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
const shortFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };

export default {
  id: 'news',
  init({ db, ui, map }) {
    const news = db.news || {};
    const legsWithNews = db.flights.filter((l) => (l.news || []).some((id) => news[id]));
    const place = (s) => s.place || db.airports[s.airport]?.city || s.airport;
    const outlet = (s) => s.source || host(s.url);

    // a story with no picture of its own: a cutting from that day's paper
    const cutting = (s) => html`<div class="cutting"><span class="ct-mast">${outlet(s)}</span><span class="ct-date">${s.date ? dateFmt.format(new Date(s.date)) : ''}</span>
      <span class="ct-rule"></span><span class="ct-head">${place(s)}</span><span class="ct-cols"><i></i><i></i><i></i></span></div>`;

    const storyCard = (s, compact = false) => html`<article class="story ${compact ? 'compact' : ''} ${s.tone === 'sad' ? 'sad' : ''}" data-story="${s.id}">
      <div class="st-img">${s.image ? html`<img src="${s.image}" alt="" loading="lazy">` : cutting(s)}</div>
      <div class="st-body">
        <div class="st-meta"><b>${outlet(s)}</b><span>${s.date ? dateFmt.format(new Date(s.date)) : ''}</span></div>
        <h4>${s.title}</h4>
        ${!compact && s.summary ? html`<p>${s.summary}</p>` : ''}
        <div class="st-foot"><span>${icon('pin')}${place(s)}</span>
          ${s.url ? html`<a class="link-btn" href="${s.url}" target="_blank" rel="noopener">Read ${icon('external')}</a>` : ''}</div>
      </div></article>`;

    // the flight that brought you there, as a little boarding-pass button
    const flightPass = (l) => {
      const ac = db.aircraft[l.aircraft];
      return html`<button class="flight-pass" data-leg="${l.id}" title="Show this flight on the map">
        <span class="fp-ico">${icon('plane')}</span>
        <span class="fp-main"><b>${l.from}<em>→</em>${l.to}</b>
          <small>${[ac?.name, l.minutes ? duration(l.minutes) : '', l.distanceNm ? `${num(l.distanceNm)} nm` : ''].filter(Boolean).join(' · ')}</small></span>
        <span class="fp-go">${icon('forward')}</span></button>`;
    };

    // ---------- the feed
    ui.openNews = () => {
      const groups = [...legsWithNews].reverse();
      const total = Object.keys(news).length;
      const withPics = Object.values(news).filter((s) => s.image).length;
      const tones = html`<div class="segmented news-tabs" role="tablist">
        <button data-tone="all" class="on">${icon('news')}All</button><button data-tone="good">${icon('heart')}Good news</button><button data-tone="sad">${icon('flag')}Serious</button></div>`;
      const { body } = openSheet({ id: 'news', title: 'Local news', cls: 'news-sheet', head: tones,
        sub: total ? `${total} stories from where you landed, from around the day you landed · ${withPics} with their own photo so far` : 'Looking up local news for your arrivals…' });
      const countries = [];
      for (const l of groups) {
        const c = db.airports[l.to].country;
        if (c?.iso && !countries.some((x) => x.iso === c.iso)) countries.push({ ...c, n: 0 });
        const x = countries.find((k) => k.iso === c?.iso);
        if (x) x.n += l.news.filter((id) => news[id]).length;
      }
      render(body, html`${groups.length ? html`
        <nav class="nf-strip"><div class="nf-places">
          <button data-iso="" class="on">${icon('globe')}Everywhere</button>
          ${countries.map((c) => html`<button data-iso="${c.iso}"><img src="${flagUrl(c.iso)}" alt="" onerror="this.remove()">${c.name}<em>${c.n}</em></button>`)}</div></nav>
        ${groups.map((l) => {
          const a = db.airports[l.to];
          return html`<section class="nf-group" data-iso="${a.country?.iso || ''}">
            <header class="nf-head">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}
              <div><b>${a.city || a.name}</b><small>Landed ${day(l.end)} at ${a.name}</small></div>
              ${flightPass(l)}</header>
            <div class="nf-row">${l.news.filter((id) => news[id]).map((id) => storyCard(news[id]))}</div></section>`;
        })}` : html`<p class="note">No stories yet - they're fetched in the background and appear here as they arrive.</p>`}`);
      const sheet = body.closest('.sheet');
      const tabs = sheet.querySelector('.news-tabs');
      const strip = body.querySelector('.nf-places');
      liquidTabs(tabs);
      if (strip) liquidTabs(strip);
      const filter = () => {
        const tone = tabs.querySelector('.on')?.dataset.tone || 'all';
        const iso = strip?.querySelector('.on')?.dataset.iso || '';
        body.querySelectorAll('.nf-group').forEach((g) => {
          let shown = 0;
          g.querySelectorAll('.story').forEach((st) => {
            const sad = st.classList.contains('sad');
            const ok = tone === 'all' || (tone === 'sad' ? sad : !sad);
            st.hidden = !ok;
            shown += ok;
          });
          g.hidden = !shown || (iso && g.dataset.iso !== iso);
        });
      };
      tabs.addEventListener('click', (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        tabs.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
        filter();
      });
      body.addEventListener('click', (e) => {
        const p = e.target.closest('.nf-places button');
        if (p) {
          strip.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === p));
          p.scrollIntoView({ inline: 'nearest', block: 'nearest', behavior: 'smooth' });
          filter();
          body.scrollTo({ top: 0, behavior: 'smooth' });
          return;
        }
        const b = e.target.closest('[data-leg]');
        if (b) { closeSheet(); store.set('selected', b.dataset.leg); }
      });
    };

    // ---------- a single story, as a glass card (used by diary hashtags + the map)
    let card = null;
    const close = () => { card?.remove(); card = null; };
    ui.openStory = (id, x = innerWidth / 2, y = innerHeight / 3) => {
      const s = news[id];
      if (!s) return;
      close();
      card = document.createElement('div');
      card.className = 'glass tagcard storycard';
      render(card, html`<button class="tc-close" aria-label="Close">${icon('close')}</button>
        ${s.image ? html`<img class="tc-img" src="${s.image}" alt="">` : html`<div class="tc-cutting">${cutting(s)}</div>`}
        <div class="tc-body"><div class="tc-kind">Local news · ${place(s)}</div>
          <h3>${s.title}</h3><div class="tc-sub">${outlet(s)} · ${s.date ? dateFmt.format(new Date(s.date)) : ''}</div>
          ${s.summary ? html`<p>${s.summary}</p>` : ''}
          <div class="links">${s.url ? html`<a class="link-btn" href="${s.url}" target="_blank" rel="noopener">Read the article ${icon('external')}</a>` : ''}</div></div>`);
      document.body.append(card);
      const w = 340;
      card.style.left = `${Math.max(12, Math.min(innerWidth - w - 12, x - w / 2))}px`;
      card.style.top = `${Math.max(12, Math.min(innerHeight - card.offsetHeight - 12, y + 14))}px`;
    };
    document.addEventListener('click', (e) => {
      const st = e.target.closest('[data-story]');
      if (st && !e.target.closest('a')) { e.stopPropagation(); ui.openStory(st.dataset.story, e.clientX, e.clientY); return; }
      if (card && (e.target.closest('.tc-close') || !card.contains(e.target))) close();
    }, true);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && card) { e.stopImmediatePropagation(); close(); } }, true);

    // ---------- leg card section
    register({
      id: 'news-section',
      legSections(l) {
        const ids = (l.news || []).filter((id) => news[id]).slice(0, 3);
        if (!ids.length) return [];
        const el = document.createElement('div');
        el.className = 'leg-news';
        render(el, html`${ids.map((id) => storyCard(news[id], true))}`);
        return [{ title: `Local news · ${db.airports[l.to]?.city || l.to}`, el }];
      },
    });

    // ---------- replay: news on the map, in a column at the side, or both
    let rail = null;
    const railEl = () => {
      if (rail) return rail;
      rail = document.createElement('aside');
      rail.id = 'newsrail';
      rail.className = 'glass';
      render(rail, html`<header class="nr-head">${icon('news')}<b>Local news</b><small>as you land</small></header><div class="nr-list"></div>`);
      document.body.append(rail);
      return rail;
    };
    const addToRail = (l, ids) => {
      const r = railEl();
      const a = db.airports[l.to];
      const entry = document.createElement('section');
      entry.className = 'nr-entry';
      render(entry, html`<div class="nr-place">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}
          <div><b>${a.city || a.name}</b><small>Landed ${shortFmt.format(new Date(l.end))} · ${l.from} → ${l.to}</small></div></div>
        ${ids.slice(0, 3).map((id) => storyCard(news[id], true))}`);
      const list = r.querySelector('.nr-list');
      list.prepend(entry);
      while (list.children.length > 6) list.lastElementChild.remove();
      list.scrollTo({ top: 0, behavior: 'smooth' });
      document.body.classList.add('news-rail');
    };
    ui.endNewsRail = () => {
      document.body.classList.remove('news-rail');
      if (rail) setTimeout(() => { if (!document.body.classList.contains('news-rail') && rail) rail.querySelector('.nr-list').innerHTML = ''; }, 600);
    };
    store.on('newsMode', (m) => { if (m === 'map' || m === 'off') ui.endNewsRail(); });

    ui.popNews = (l) => {
      const mode = store.get('newsMode') || 'both';
      const ids = (l.news || []).filter((x) => news[x]);
      if (!ids.length || mode === 'off') return;
      if ((mode === 'map' || mode === 'both') && map.dropNews) {
        map.dropNews(news[ids[0]], [l.arr.lon, l.arr.lat], () => { ui.stopPlayback?.(); ui.openStory(ids[0]); });
      }
      if (mode === 'side' || mode === 'both') addToRail(l, ids);
    };
  },
};
