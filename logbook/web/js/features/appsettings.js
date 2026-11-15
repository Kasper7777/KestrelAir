// The glass cogwheel: app settings.
// - Background updates: what's being fetched, when it next checks (every 2 min
//   while anything is still missing), and "Check now"
// - Archives: everything downloaded is kept and only ever added to; each archive
//   shows its size and can be wiped (it refills from the internet next time)
// - Pilot: opens Pilot settings (NeoFly pilot, name, photo, SimBrief)
// - Self-check: the results of the last build's consistency checks
import { html, render } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet } from '../core/sheet.js';

export default {
  id: 'appsettings',
  init({ db, ui }) {
    const post = (url, body) => fetch(url, { method: 'POST', headers: { 'X-Logbook': '1', 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}) }).then((r) => r.json());

    ui.openAppSettings = () => {
      const { el, body } = openSheet({ id: 'appsettings', title: 'Settings', cls: 'app-settings',
        sub: 'Features, background updates, your archives, and how the logbook checks itself' });
      let timer = null, busy = false, testMsg = '';
      const feats = { finances: false, neoflyWrite: false, ...(db.meta.features || {}) };
      const draw = async () => {
        if (!document.body.contains(body)) { clearInterval(timer); return; }
        if (busy) return;
        let info, nw = {};
        try { info = await fetch('/__datainfo').then((r) => r.json()); } catch { return; }
        try { nw = await post('/__neofly-write'); } catch { /* older server */ }
        const swRow = (key, ic, title, text, extra = '') => html`<div class="set-row feature"><div>
            <b>${icon(ic)}${title}${key === 'neoflyWrite' ? html` <span class="exp">Experimental</span>` : ''}</b><small>${text}</small>${extra}</div>
          <div class="actions">${key === 'neoflyWrite' && feats.neoflyWrite ? html`<button class="link-btn" data-act="nwtest">${icon('check')}Test</button>` : ''}
            <button class="switch ${feats[key] ? 'on' : ''}" data-feature="${key}" role="switch" aria-checked="${feats[key] ? 'true' : 'false'}" aria-label="${title}"></button></div></div>`;
        const nwStatus = html`<div class="status">
          ${nw.save ? html`<span class="ok">${icon('check')}NeoFly save found</span>` : html`<span class="no">No NeoFly save on this PC</span>`}
          ${nw.neoflyRunning ? html`<span class="no">${icon('clock')}NeoFly is open - changes wait until it's closed</span>` : html`<span class="ok">${icon('check')}NeoFly closed</span>`}
          ${nw.lastBackup ? html`<span>${icon('save')}Last copy before a change: ${nw.lastBackup.replace(/^pre-write-(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d).*$/, '$3/$2/$1 $4:$5')}</span>` : ''}
          ${testMsg ? html`<span class="${testMsg === 'ok' ? 'ok' : 'no'}">${testMsg === 'ok' ? html`${icon('check')}Test passed: the save can be written, nothing was changed` : testMsg}</span>` : ''}</div>`;
        const bg = info.background || {};
        const status = bg.running ? html`<span class="spinner"></span>Fetching new details now…`
          : bg.nextCheckIn != null ? html`${icon('clock')}Next check in ${Math.ceil(bg.nextCheckIn / 60) > 1 ? `${Math.ceil(bg.nextCheckIn / 60)} min` : `${bg.nextCheckIn}s`}`
          : html`${icon('check')}Up to date`;
        render(body, html`
          <section class="set-sec">
            <h4>${icon('layers')}Features <small>from NeoFly, more to come</small></h4>
            ${swRow('finances', 'moneybag', 'Finances', 'Cash, income and costs by kind, fuel spend, each aircraft\'s fuel and condition, loans and the full ledger. Adds a Finances button to the toolbar.')}
            ${swRow('neoflyWrite', 'save', 'Write to NeoFly', 'Lets the logbook make changes to your NeoFly save - the first step towards running your company from here instead of NeoFly. Off by default. Before every change a full copy of the save is kept, it only writes while NeoFly is closed, and the save is checked afterwards (the copy goes back if anything is wrong).',
              feats.neoflyWrite ? nwStatus : '')}
          </section>
          <section class="set-sec">
            <h4>${icon('refresh')}Background updates</h4>
            <div class="set-row"><div><b>${status}</b>
              <small>Looks up anything new as you fly - news, places, menus, photos, Wikipedia - and adds it to the archive.
                While something is still missing it tries again every ${Math.round((bg.retrySeconds || 120) / 60)} minutes.</small>
              <small>${bg.pending ? `${bg.pending} news stor${bg.pending === 1 ? 'y' : 'ies'} still waiting for their own picture - each one's real article is looked up politely, a batch every couple of minutes.` : 'Nothing waiting.'}
                ${bg.lastRun ? ` Last run ${bg.lastRun.replace('T', ' ').slice(0, 16)}.` : ''}</small></div>
              <button class="link-btn" data-act="refresh">${icon('refresh')}Check now</button></div>
          </section>
          <section class="set-sec">
            <h4>${icon('folder')}Archives <small>kept and added to - never re-downloaded</small></h4>
            ${info.archives.map((a) => html`<div class="set-row">
              <div><b>${a.label}</b><small>${a.mb} MB · ${a.files.toLocaleString('en-GB')} files${a.key === 'news' ? ` · ${info.newsStories} stories` : ''}</small></div>
              <button class="link-btn danger" data-wipe="${a.key}">${icon('trash')}Wipe</button></div>`)}
            <div class="set-row pilot-row">
              <div><b>${db.pilot.character || db.pilot.name}'s backups</b><small>NeoFly save copies, original screenshots, flight list, SimBrief plans · ${info.pilot.mb} MB.
                These can't be fetched again - wiping them is permanent.</small></div>
              <button class="link-btn danger" data-wipe="pilot">${icon('trash')}Wipe…</button></div>
            <p class="note set-msg"></p>
          </section>
          <section class="set-sec">
            <h4>${icon('feather')}Pilot</h4>
            <div class="set-row"><div><b>${db.pilot.character || db.pilot.name}</b><small>NeoFly pilot, name shown, photo and SimBrief username</small></div>
              <button class="link-btn" data-act="pilot">Pilot settings ${icon('forward')}</button></div>
          </section>
          <section class="set-sec">
            <h4>${icon('check')}Self-check</h4>
            ${info.checks?.length ? html`<ul class="set-checks">${info.checks.map((c) => html`<li>${c}</li>`)}</ul>`
              : html`<p class="note">All good: every airport sits in its country, every flag fill is valid, every file the page uses exists.</p>`}
          </section>`);
      };
      draw();
      timer = setInterval(draw, 5000);
      body.addEventListener('click', async (e) => {
        const b = e.target.closest('button');
        if (!b) return;
        const msg = body.querySelector('.set-msg');
        if (b.dataset.act === 'refresh') { await post('/__refresh'); setTimeout(draw, 800); return; }
        if (b.dataset.feature) {
          const key = b.dataset.feature, on = !feats[key];
          if (key === 'neoflyWrite' && on && !confirm('Let the logbook write to your NeoFly save?\n\nNothing is changed by switching this on. When a feature does change something, a full copy of the save is kept first, it only writes while NeoFly is closed, and the save is checked afterwards.')) return;
          busy = true;
          b.classList.toggle('on', on);
          b.setAttribute('aria-checked', on ? 'true' : 'false');
          b.disabled = true;
          try {
            const r = await post('/__features', { key, on });
            if (!r.ok) throw new Error(r.error || 'not saved');
            Object.assign(feats, r.features);
            if (key === 'finances') await ui.reloadFinances?.();
            testMsg = '';
          } catch (err) {
            b.classList.toggle('on', !on);
            alert(`Couldn't change that setting: ${err.message}`);
          } finally { busy = false; b.disabled = false; }
          draw();
          return;
        }
        if (b.dataset.act === 'nwtest') {
          b.disabled = true;
          const r = await post('/__neofly-write', { test: true }).catch((err) => ({ test: err.message }));
          testMsg = r.test || 'No answer';
          b.disabled = false;
          draw();
          return;
        }
        if (b.dataset.act === 'pilot') { ui.openSettings?.(); return; }
        if (b.dataset.wipe) {
          const what = b.dataset.wipe;
          let confirmText = '';
          if (what === 'pilot') {
            confirmText = prompt(`This permanently deletes ${db.pilot.character || db.pilot.name}'s backups (NeoFly save copies, original screenshots, plans).\nType the pilot name to confirm:`) || '';
            if (!confirmText) return;
          } else if (!confirm('Wipe this archive? It will be downloaded again in the background as needed.')) return;
          b.disabled = true;
          if (msg) msg.textContent = 'Wiping…';
          const r = await post('/__wipe', { what, confirm: confirmText });
          if (msg) msg.textContent = r.ok ? 'Done. The logbook has been rebuilt - refresh to see the change.' : `Couldn't wipe: ${r.error}`;
          b.disabled = false;
          draw();
        }
      });
    };
  },
};
