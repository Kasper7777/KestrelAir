# WarBRD stick buttons: vPilot and BeyondATC

Both WarBRD-D sticks (Constellation ALPHA Prime grips) are set up the same way in all four SPAD profiles (Baron, Bonanza A36, A36TC, B36TP).

| Grip control | HID button | SPAD sends | App action |
|---|---|---|---|
| Top push button | 7 | vJoy 1 button 1 (held while pressed) | vPilot push-to-talk (VATSIM) |
| Bottom push button | 18 | vJoy 1 button 2 (held while pressed) | BeyondATC push-to-talk (PushToTalk1) |
| Main trigger (first stage) | 4 | vJoy 1 button 3 | BeyondATC auto respond (DoAction1) |
| Flip trigger (folded down and squeezed) | 3 | vJoy 1 button 3 | BeyondATC auto respond (DoAction1) |

The button numbers were read live from both grips on 2026-11-03 with `watch-warbrd-buttons.ps1`. The trigger's second stage (HID 5) is left unbound so a full pull doesn't fire twice. The flip trigger reports HID 1 when stowed and 2 when folded down; only the squeeze (3) is used here.

## Why vJoy

Since the 2026-10-31 firmware repair, both grips report the same USB name ("VPC WarBRD-D Base"). Because of that, vPilot (which supports one PTT device) and BeyondATC could no longer tell the sticks apart, and their old bindings pointed at device names that no longer exist. SPAD can still tell them apart by HID path, so SPAD presses a button on the vJoy virtual stick, and each app listens to vJoy only. This keeps all hardware routing in SPAD.

vJoy device 1 has 8 buttons. Buttons 1-3 are used here and 4-8 are free. The MSFS camera preset uses vJoy axes only, never buttons.

## Files

- `bind-stick-ptt.py <profile.xml>...` adds the SPAD events to both grips. It's idempotent, and it replaced the old right-grip BUTTON_7 action (a stray CJ4 flood-light toggle).
- `configure-atc-apps.py` points vPilot PTT at vJoy button 1 and BeyondATC PushToTalk1/DoAction1 at vJoy buttons 2/3. Close vPilot and BeyondATC before running it, because both save their settings on exit.
- `watch-warbrd-buttons.ps1` is a read-only live button logger for both grips.
- Backup made before the change: `backups/stick-ptt-20261103-203221/`. It holds the SPAD profiles (installed, repo, portable, pending), `vPilotConfig.xml`, the BeyondATC `config.json` and a registry export.

## If an app doesn't respond

Open the app's PTT or hotkey setting, click to bind, and press the grip button. With SPAD running, the app will see the vJoy button, so the binding comes out the same as the script's.

- vPilot: Settings, then Push-to-Talk.
- BeyondATC: Settings, then Controls. Don't bind the grips directly. Because they share one name, a direct binding can't tell left from right.

The BeyondATC bindings for ToggleBringToFront (left button 8), ToggleTaxiArrows (left button 7) and PushToTalk2 (right button 7) still name the old CONF_A01 devices, so they're inactive. They were left as they were.
