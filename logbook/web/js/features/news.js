// Local news: real stories from where you landed, from around the day you landed.
// - News feed (toolbar): every arrival's stories, newest trip first
// - Story card: ui.openStory(id, x?, y?) - picture, headline, summary, outlet, date, link
// - Leg card section: "Local news" on each flight (via the registry)
// - Replay: ui.popNews(leg) drops the top story onto the map as the plane lands
import { html, render, day, flagUrl } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet, closeSheet } from '../core/sheet.js';
import { store } from '../core/store.js';
import { register } from './registry.js';

const dateFmt = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return ''; } };

export default {
  id: 'news',
  init({ db, ui, map }) {
    const news = db.news || {};
    const legsWithNews = db.flights.filter((l) => (l.news || []).some((id) => news[id]));

    const storyCard = (s, compact = false) => html`<article class="story ${compact ? 'compact' : ''} ${s.tone === 'sad' ? 'sad' : ''}" data-story="${s.id}">
      <div class="st-img">${s.image ? html`<img src="${s.image}" alt="" loading="lazy">` : html`<div class="st-blank">${icon('book')}</div>`}
        ${s.placeImage ? html`<span class="st-note">Photo of ${db.airports[s.airport]?.city || s.airport}</span>` : ''}</div>
      <div class="st-body">
        <div class="st-meta"><b>${s.source || host(s.url)}</b><span>${s.date ? dateFmt.format(new Date(s.date)) : ''}</span></div>
        <h4>${s.title}</h4>
        ${!compact && s.summary ? html`<p>${s.summary}</p>` : ''}
        <div class="st-foot"><span>${icon('pin')}${s.place || db.airports[s.airport]?.city || s.airport}</span>
          ${s.url ? html`<a class="link-btn" href="${s.url}" target="_blank" rel="noopener">Read ${icon('external')}</a>` : ''}</div>
      </div></article>`;

    // ---------- the feed
    ui.openNews = () => {
      const groups = [...legsWithNews].reverse();
      const total = Object.keys(news).length;
      const { body } = openSheet({ id: 'news', title: 'Local news', cls: 'news-sheet',
        sub: total ? `${total} stories from the places you landed, from around the day you landed - from local outlets` : 'Looking up local news for your arrivals…' });
      render(body, html`${groups.length ? groups.map((l) => {
        const a = db.airports[l.to];
        return html`<section class="nf-group">
          <header class="nf-head">${a.country?.iso ? html`<img src="${flagUrl(a.country.iso)}" alt="" onerror="this.remove()">` : ''}
            <div><b>${a.city || a.name}</b><small>Landed ${day(l.end)} · ${l.from} → ${l.to}</small></div>
            <button class="link-btn" data-leg="${l.id}">${icon('plane')}The flight</button></header>
          <div class="nf-row">${l.news.filter((id) => news[id]).map((id) => storyCard(news[id]))}</div></section>`;
      }) : html`<p class="note">No stories yet - they're fetched in the background and appear here as they arrive.</p>`}`);
      body.addEventListener('click', (e) => {
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
        ${s.image ? html`<img class="tc-img" src="${s.image}" alt="">` : ''}
        <div class="tc-body"><div class="tc-kind">Local news · ${s.place || db.airports[s.airport]?.city || ''}</div>
          <h3>${s.title}</h3><div class="tc-sub">${s.source || host(s.url)} · ${s.date ? dateFmt.format(new Date(s.date)) : ''}</div>
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

    // ---------- replay: the top story drops onto the map as the plane lands
    ui.popNews = (l) => {
      const id = (l.news || []).find((x) => news[x]);
      if (!id || !map.dropNews) return;
      map.dropNews(news[id], [l.arr.lon, l.arr.lat], () => { ui.stopPlayback?.(); ui.openStory(id); });
    };
  },
};
