# VIRPIL MiniStick camera controls

Updated 2026-11-03 (evening). Earlier versions of this file had the wrong axis table; this one is checked against live recordings and the preset MSFS actually holds.

## Current behaviour

| Input | On foot | Cockpit / external | Drone (current, "Mode 2") |
|---|---|---|---|
| Left MiniStick up/down | W/S walking keys | – | Climb / descend |
| Left MiniStick left/right | A/D walking keys | – | Turn (yaw) |
| Right MiniStick up/down | Look up/down | Look up/down | Fly forward / back |
| Right MiniStick left/right | Look left/right | Look left/right | Slide sideways |

You confirmed look and walking work the right way. The drone has no camera tilt in this layout, which is what the FPV preset below adds.

## How it's wired

Measured live on both grips: the MiniStick's HID **Rx is horizontal** (right = high) and **Ry is vertical** (up = high). The recordings are `right-thumbstick-watch-20261103-before.txt` and `-after.txt`.

SPAD (`route-thumbsticks.py`, all four GTN profiles; response-curve mode, no inversion in SPAD):

| Grip | Axis | vJoy axes |
|---|---|---|
| Right | Rx (horizontal) | Ry + X |
| Right | Ry (vertical) | Rz + Y |
| Left | Rx (horizontal) | Z (plus A/D keys, except in drone mode) |
| Left | Ry (vertical) | Rx (plus W/S keys, except in drone mode) |

MSFS preset "KestrelAir SPAD Cameras v2" on vJoy Device, as it stands in the live file:

| vJoy axis | Action |
|---|---|
| Ry | Look left/right (cockpit, external, on foot), inverted flag |
| Rz | Look up/down, inverted flag |
| X | Drone sideways |
| Y | Drone forward/back |
| Z | Drone yaw |
| Rx | Drone height |

**What went wrong before.** The right stick's two channels were crossed in SPAD, so up/down looked left/right. On top of that, the SPAD calibration curve that used to invert the right stick's Ry was lost from the profiles sometime between 18:37 and 19:57 on 2026-11-03, before the button work started. Look directions are now right without it, because the live MSFS preset carries the inversion flags, so don't add the curve back.

## FPV drone preset (built, not yet imported)

`portable-setup/KestrelAir-vJoy-GeneralControls-v3-FPV.xml` comes from `build-vjoy-fpv-preset.py`, which builds it from the live v2 preset. Only the drone bindings change:

| Stick | Direction | FPV drone action |
|---|---|---|
| Left | Up/down | Throttle (fly along where the camera points) |
| Left | Left/right | Yaw |
| Right | Up/down | Pitch (camera tilt) |
| Right | Left/right | Roll |

SPAD needs no change for it. To use it: MSFS Controls > vJoy Device > General controls > gear > Import, then select "KestrelAir SPAD Cameras v3 FPV". If pitch or roll tests backwards, add that action to `INVERT` in the builder, rebuild, and re-import. To go back, select "KestrelAir SPAD Cameras v2" again.

## Notes

- SPAD's bundled vJoy library was replaced with the one matching the installed 2.2.2 driver; the old DLL is backed up, and the portable installer repeats the repair.
- Direct SimConnect on-foot axis events crashed MSFS and remain removed. Don't reapply `bind-thumbstick-keys.ps1` or `bind-dji-thumbsticks.ps1`; they describe older approaches.
- `watch-right-thumbstick.ps1` logs the right grip next to the vJoy axes for future checks.
- Backup before this fix: `backups/thumbstick-mode2-20261103-221914/`.
