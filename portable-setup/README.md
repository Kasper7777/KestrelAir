# KestrelAir setup: moving to another PC

Everything is in this folder (or `KestrelAir-portable-setup.zip`). Updated 2026-11-04.

## What to do

1. Install SPAD.neXt, FSUIPC7 and MSFS. Plug in the sticks, throttle, panels and pedals.
2. Put this folder where it will stay (the SPAD profiles point at the helpers inside it).
3. **Double-click `Install-KestrelAir.cmd`.** Say yes to the administrator prompt.
4. Do the short list it prints at the end. These are the steps Windows won't let a script do: picking two presets in the MSFS Controls menu, one keyboard key, and a reboot if vJoy was just installed.

## What the installer does

- Asks before closing SPAD, MSFS, vPilot, BeyondATC and the helpers, then backs up everything it replaces to `install-backup-<date>\`.
- Installs vJoy 2.2.2 if missing, and gives SPAD the matching vJoy library.
- Copies all 9 SPAD profiles, including the Citation X (sticks, pedals, throttle, panels, MSG fix, button 31 = back to MSFS), and points their helper paths at this folder.
- Throttle mini-stick mouse (`helpers\ka-mouse`): finds the throttle on this PC. SPAD starts the helper when you press a throttle mouse button.
- SFS Monitor watcher (`helpers\ka-sfs`): adds it to Startup and starts it.
- Drone stick lights (`helpers\ka-drone-leds`): SPAD starts the helper when you press B4. Drone mode on the main sticks is already in the profiles (`helpers\drone-sticks.md`).
- Puts the MSFS vJoy look/drone preset ("KestrelAir SPAD Cameras v2.2") and the pedal preset in MSFS's controls folder (Steam version), so you only have to select them.
- Sets vPilot and BeyondATC push-to-talk to the stick buttons, if Python is installed.
- Installs the FSUIPC LED helper.

Run it again any time; it's safe to repeat.

## Details

- Stick buttons, wheel and window buttons: `helpers\stick-atc-buttons.md`
- Throttle mouse: `helpers\throttle-mouse.md`
- Look and drone axes: `helpers\thumbstick-keys.md` (the v2.2 preset also fixes on-foot look and cockpit left/right)
- Rudder pedals: `helpers\rudder-pedals.md`
- SFS Monitor handover: `helpers\sfs-monitor-handover.md`
- Throttle B4 drone toggle: `helpers\throttle-drone.md`

Both WarBRD grips report the same name. If the sticks act swapped on a new PC, SPAD has picked the grips the other way round: the right grip is SPAD DeviceIndex 0.
