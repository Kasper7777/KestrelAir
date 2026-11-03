# WarBRD stick buttons: vPilot and BeyondATC

Both WarBRD-D sticks (Constellation ALPHA Prime grips) are set up the same way in all four SPAD profiles (Baron, Bonanza A36, A36TC, B36TP).

| Grip control | HID button | SPAD sends | App action |
|---|---|---|---|
| Top push button | 7 | vJoy 1 button 1 (held while pressed) | vPilot push-to-talk (VATSIM) |
| Bottom push button | 18 | vJoy 1 button 2 (held while pressed) | BeyondATC push-to-talk (PushToTalk1) |
| Main trigger (first stage) | 4 | vJoy 1 button 3 | BeyondATC auto respond (DoAction1) |
| Flip trigger (folded down and squeezed) | 3 | vJoy 1 button 3 | BeyondATC auto respond (DoAction1) |
| vPilot window button | 8 | runs `ka-front-vpilot.exe` | Brings vPilot to the front; press again to return to MSFS |
| BeyondATC window button | 13 | runs `ka-front-beyondatc.exe` | Brings BeyondATC to the front; press again to return to MSFS |
| Wheel up / down | 22 / 21 | runs `ka-menu-prev.exe` / `ka-menu-next.exe` | Moves the mouse pointer up/down one reply in BeyondATC's reply list (bottom left); scrolls the list at its ends |
| Wheel press | 19 | runs `ka-menu-select.exe` | Clicks the reply under the pointer, then puts the pointer and focus back on MSFS |

The button numbers were read live from both grips on 2026-11-03 with `watch-warbrd-buttons.ps1` (logs: `warbrd-button-map-20261103*.txt`; SPAD-to-vJoy proof: `stick-ptt-verify-20261103.txt`).

## Window and reply-list helpers

vPilot has no "bring to front" command, and BeyondATC's reply list responds only to the mouse. Its Tab and Enter hotkeys, the arrow keys and vJoy didn't move it in testing. So two small helpers in `.tools/ka-front/` do this work. Their source is next to them, and they build with the .NET Framework `csc.exe`, like ka-click. Each copy of the exe reads its job from its own file name.

- `ka-front`: if the target app is already in front, it switches back to MSFS instead. If the app isn't running, it does nothing.
- `ka-menu`: the first wheel click places the pointer on the top visible reply and remembers where the pointer was. Pressing the wheel when the pointer isn't on the list does nothing. Row positions were measured on a 719×649 BeyondATC window and scale with its height. If the window is resized and the pointer lands between rows, put `ka-menu.ini` next to the exe with `RowPitch=18.6`, `FirstRowFromBottom=101`, `Rows=4`, `X=120` (client pixels) adjusted, or `Scale=` to fix the scale. The trigger's second stage (HID 5) is left unbound so a full pull doesn't fire twice. The flip trigger reports HID 1 when stowed and 2 when folded down; only the squeeze (3) is used here.

## Why vJoy

Since the 2026-10-31 firmware repair, both grips report the same USB name ("VPC WarBRD-D Base"). Because of that, vPilot (which supports one PTT device) and BeyondATC could no longer tell the sticks apart, and their old bindings pointed at device names that no longer exist. SPAD can still tell them apart by HID path, so SPAD presses a button on the vJoy virtual stick, and each app listens to vJoy only. This keeps all hardware routing in SPAD.

vJoy device 1 has 8 buttons. Buttons 1-3 are used here and 4-8 are free. The MSFS camera preset uses vJoy axes only, never buttons.

## Files

- `bind-stick-ptt.py <profile.xml>...` adds the SPAD events to both grips. It's idempotent, and it replaced the old right-grip BUTTON_7 action (a stray CJ4 flood-light toggle).
- `configure-atc-apps.py` points vPilot PTT at vJoy button 1 and BeyondATC PushToTalk1/DoAction1 at vJoy buttons 2/3. Close vPilot and BeyondATC before running it, because both save their settings on exit.
- `watch-warbrd-buttons.ps1` is a read-only live button logger for both grips.
- Backups made before each change: `backups/stick-ptt-20261103-203221/` (SPAD profiles from all four locations, `vPilotConfig.xml`, the BeyondATC `config.json` and registry, the old portable zip) and `backups/stick-wheel-window-20261103-205204/` (profiles and BeyondATC registry before the window and wheel buttons).
- The portable installer rewrites the ka-front and ka-menu paths to `helpers/ka-front/` on another PC, the same way it does for ka-click.

## If an app doesn't respond

Open the app's PTT or hotkey setting, click to bind, and press the grip button. With SPAD running, the app will see the vJoy button, so the binding comes out the same as the script's.

- vPilot: Settings, then Push-to-Talk.
- BeyondATC: Settings, then Controls. Don't bind the grips directly. Because they share one name, a direct binding can't tell left from right.

The BeyondATC bindings for ToggleBringToFront (left button 8, now handled by ka-front instead), ToggleTaxiArrows (left button 7) and PushToTalk2 (right button 7) still name the old CONF_A01 devices, so they're inactive. They were left as they were.
