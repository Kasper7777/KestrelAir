// Layover diary: an Instagram-style feed of Casper's time on the ground wherever
// he stayed 8 hours or more. The restaurants and sights are real and near the
// airport (OpenStreetMap + Wikipedia); the day out is imagined - and labelled so.
import { html, render, flagUrl } from '../core/format.js';
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

    const post = (s, p, dayNo) => html`<article class="ig">
      <header><span class="ig-av">${avatar ? html`<img src="${avatar}" alt="">` : ''}</span>
        <div><b>${handle}</b><small>${p.place}</small></div><span class="ig-kind">${p.kind === 'sight' ? icon('pin') : icon('fork')}</span></header>
      <div class="ig-photo">${p.image ? html`<img src="${p.image}" alt="" loading="lazy">` : html`<div class="ig-blank">${icon('fork')}</div>`}
        ${p.dish ? html`<span class="ig-tag">${p.dish}</span>` : ''}</div>
      <div class="ig-actions">${icon('heart')}<span>${p.likes.toLocaleString('en-GB')} likes</span><time>Day ${dayNo} · ${p.time.slice(11, 16)}</time></div>
      <p class="ig-cap"><b>${handle}</b> ${p.caption} <span class="ig-tags">${s.diary.tags.join(' ')}</span></p>
      <p class="ig-where">${p.where}${p.url ? html` · <a href="${p.url}" target="_blank" rel="noopener">Wikipedia</a>` : ''}</p>
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
        const b = e.target.closest('[data-leg]');
        if (b) { closeSheet(); store.set('selected', b.dataset.leg); }
      });
      if (stopId) body.querySelector(`#stay-${CSS.escape(stopId)}`)?.scrollIntoView({ block: 'start' });
    };

    // a preview in the leg card when the next stop was a long one
    ui.diaryPreview = (s) => {
      if (!s?.diary) return '';
      const posts = s.diary.days.flatMap((d) => d.posts).slice(0, 3);
      const d = s.diary;
      return html`<div class="card diary-card"><h4>Layover in ${d.city}<small>${d.nights ? `${d.nights} night${d.nights === 1 ? '' : 's'}` : `${Math.round(d.hours)} h`}</small></h4>
        <div class="dp-row">${posts.map((p) => html`<figure>${p.image ? html`<img src="${p.image}" alt="" loading="lazy">` : html`<div class="ig-blank">${icon('fork')}</div>`}
          <figcaption>${p.dish || p.place}</figcaption></figure>`)}</div>
        <button class="link-btn" data-diary="${s.id}">${icon('diary')}Open ${who}'s diary</button></div>`;
    };
  },
};
