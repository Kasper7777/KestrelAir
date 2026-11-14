// Pilot settings (click the pilot in the title bar): which NeoFly pilot this logbook
// follows, the name shown, and the pilot's photo. Saved to config.json by the
// local server, which rebuilds; then the page reloads. Lets anyone use the logbook
// with their own NeoFly character.
import { html, render, esc } from '../core/format.js';
import { icon } from '../core/icons.js';
import { openSheet } from '../core/sheet.js';

export default {
  id: 'settings',
  init({ db, ui }) {
    const pilots = db.meta.pilots || [db.pilot.name];
    ui.openSettings = () => {
      const { el, body } = openSheet({ id: 'settings', title: 'Pilot', cls: 'settings-sheet',
        sub: 'Choose the NeoFly pilot this logbook follows, and how they appear' });
      let photo = null;
      render(body, html`<form class="settings">
        <label class="field"><span>NeoFly pilot</span>
          <select name="pilot">
            <option value="">Whoever is logged in to NeoFly</option>
            ${pilots.map((n) => html`<option value="${n}">${n}</option>`)}
          </select>
          <small>${pilots.length} pilot${pilots.length === 1 ? '' : 's'} in this NeoFly save. Showing <b>${db.pilot.name}</b>.</small></label>
        <label class="field"><span>Name shown in the logbook and diary</span>
          <input name="displayName" value="${db.pilot.character || db.pilot.name}" maxlength="40" autocomplete="off"></label>
        <label class="field"><span>SimBrief username or Pilot ID</span>
          <input name="simbrief" value="${db.pilot.simbrief || ''}" placeholder="e.g. kazber or 123456" autocomplete="off">
          <small>Each time the logbook runs it saves your latest SimBrief plan (briefing, PDF, route map) and attaches it to that flight.</small></label>
        <div class="field"><span>Photo</span>
          <div class="photo-row"><img class="avatar big" src="${db.pilot.photo || 'icon.png'}" alt="">
            <label class="link-btn">${icon('photo')}Choose a photo<input type="file" name="photo" accept="image/*" hidden></label></div></div>
        <div class="toast-actions"><button type="button" data-close>Cancel</button><button type="submit" class="primary">Save</button></div>
        <p class="note settings-msg"></p>
      </form>`);
      const form = body.querySelector('form');
      const chosen = (db.meta.pilotChosen || '');
      form.pilot.value = pilots.includes(chosen) ? chosen : '';
      form.photo.addEventListener('change', () => {
        const f = form.photo.files[0];
        if (!f) return;
        const r = new FileReader();
        r.onload = () => { photo = r.result; form.querySelector('.avatar').src = photo; };
        r.readAsDataURL(f);
      });
      form.pilot.addEventListener('change', () => {
        // switching pilot: their own name applies unless you type another
        const n = form.pilot.value || db.pilot.name;
        form.displayName.value = n === db.pilot.name ? (db.pilot.character || n) : n;
      });
      form.querySelector('[data-close]').addEventListener('click', () => el.querySelector('[data-close]').click());
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = form.querySelector('.settings-msg');
        msg.textContent = 'Saving and rebuilding…';
        form.querySelector('[type=submit]').disabled = true;
        const target = form.pilot.value || db.pilot.name;
        try {
          const r = await fetch('/__settings', { method: 'POST', headers: { 'X-Logbook': '1', 'Content-Type': 'application/json' },
            body: JSON.stringify({ pilot: form.pilot.value, for: target, displayName: form.displayName.value, simbrief: form.simbrief.value, photo }) }).then((x) => x.json());
          if (!r.ok) throw new Error(r.error || 'Could not save');
          msg.textContent = 'Saved. Reloading…';
          location.reload();
        } catch (err) {
          msg.innerHTML = `Couldn't save: ${esc(err.message)}`;
          form.querySelector('[type=submit]').disabled = false;
        }
      });
    };

    // "new details found" notice while the background fetch runs
    const pill = document.getElementById('fetchpill');
    const loaded = db.meta.builtAt;
    const check = async () => {
      try {
        const s = await fetch('/__status').then((r) => r.json());
        if (s.builtAt && s.builtAt !== loaded && !s.fetching) {
          render(pill, html`${icon('check')}New places and photos found <button>Refresh</button>`);
          pill.hidden = false;
          pill.querySelector('button').onclick = () => location.reload();
          return;
        }
        if (s.fetching) { render(pill, html`<span class="spinner"></span>Looking up places and photos…`); pill.hidden = false; }
        else pill.hidden = true;
      } catch { /* server gone */ }
      setTimeout(check, 8000);
    };
    setTimeout(check, 2500);
  },
};
