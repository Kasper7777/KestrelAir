# WarBRD thumbsticks as PlayStation sticks (SPAD only)

**3 November update:** Drone mode now uses native proportional axes with DJI Mode 2 layout: left MiniStick up/down = climb/descent, left/right = yaw; right MiniStick up/down = forward/back, left/right = strafe. `bind-dji-thumbsticks.ps1` installs these in the current left/right MSFS general profiles and suppresses SPAD's keyboard axes whenever `SIMCONNECT:CAMERA STATE` is 4. A drone-only branch releases both keys and resets each remembered zone. The LED runtime also releases held walking/look keys on transitions into/out of drone mode. On-foot and cockpit mappings below remain in use outside drone mode. Run the DJI patch after the base keyboard-binding script if rebuilding profiles. B4 is hot pink while drone is active and neon green otherwise. Native stick directions and feel still require a live physical check after restarting MSFS.

**Crash cause:** `bind-onfoot-thumbsticks.ps1` (2026-11-02 23:03) made SPAD transmit the on-foot SimConnect events `AXIS_PC_MOVE_X/Z` and `AXIS_PC_FPV_ROTATION_X/Y` on every MiniStick movement. MSFS 2024 crashed with an access violation each time a stick was touched (23:15, 23:38, 00:03; `FlightSimulator2024.exe` +0x12eb9b1/9fd). `spad.log` shows those events being transmitted seconds before each crash. MSFS 2024 also ignores the ordinary camera events (`PAN_*`, `ZOOM_*`) when they arrive through SimConnect, so no SimConnect route can drive the camera from SPAD.

**Fix (`bind-thumbstick-keys.ps1`):** the four SimConnect axis events are removed. Each MiniStick axis gets a SPAD "Axis value changed" event with three conditional definitions on `EVENT:VALUE`. For these axes that is the raw device value (0–60000, rest 30000, measured over HID; the first attempt used 0–100 thresholds and `spad.log` showed only the "greater" branch firing): below 12000 hold one key, above 48000 hold the other, in between release both. A profile variable per axis (`PROFILE:KA_STICK<index>_<RX|RY>`, -1/0/1) remembers the current zone and each definition also requires a zone change, because the MiniStick jitters at rest on every HID report: without that gate SPAD sent 3,422 keyboard macros in one minute (spad.log 2026-11-03 00:54), each holding a worker for 80 ms, which lagged every other control, including the RotAIR/PulsAIR encoders. Keyboard macro duration for the stick keys is 20 ms. Keys are sent with SPAD's keyboard action (`PRESS` / `RELEASE`) to the active window, like the existing CP3 view shortcuts. MSFS's own keyboard map is context-aware, so one key does the right thing everywhere:

| | Left MiniStick (PS left stick): W / A / S / D | Right MiniStick (PS right stick): arrow keys |
| --- | --- | --- |
| Cockpit | — (bare W/A/S/D are unbound in the aircraft contexts) | Look around |
| External camera | — | Orbit the aircraft |
| On foot | Walk | Look |
| Drone | Move | Rotate |
| Menus / EFB | Navigate | Navigate / scroll |

**Stick clicks** (HID button 1 on each grip, read over raw HID): the right click holds the **left mouse button at the centre of the sim window** for as long as the stick is pressed, using SPAD's "Run external program" action (`EventActionCommand CommandName="SPAD_neXt.RunProgram"`) to launch `.tools\ka-click\ka-click-down.exe` on PRESS and `ka-click-up.exe` on RELEASE. That is the PlayStation Cross role: look at a switch with the right stick, press in to operate it (hold and move for knobs). The helper is `ka-click.cs`, compiled with the .NET Framework `csc.exe`; it reads its mode from its own file name so no argument field is needed. The left click sends Shift+Space, MSFS's view reset in every camera context. `-ClickButton 0` skips both. `-InvertVertical` swaps up/down on both sticks (the default already matches these grips, where pushing up raises the raw value). `-Deflect 30` (default) sets the hold threshold at 20 % / 80 %; lower it for a shorter throw.

No MSFS controller profile is touched. The script refuses to run while SPAD is open, backs up both profile copies to `backups/thumbstick-keys-*`, and checks that every other XML node is unchanged.

## Apply and test

1. Exit SPAD.neXt (and MSFS). Run `.\bind-thumbstick-keys.ps1`.
2. Start SPAD and load the Baron profile. Without MSFS, run `keylog-window.ps1` from the scratch folder (or any text editor) and move the sticks: the right stick should hold arrow keys, the left W/A/S/D, each released at centre. If up/down are reversed, re-run with `-InvertVertical`.
3. Start MSFS. Touching or clicking the sticks sends no SimConnect events any more.

Live MSFS behaviour is not yet verified at the time of writing.
