# Throttle mini-stick as a mouse (2026-11-04)

`.tools/ka-mouse/ka-mouse.exe` runs hidden in the background, reads the MongoosT-50CM3 throttle directly, and drives the Windows mouse:

| Throttle input (recorded live, `watch-cm3-all.ps1`) | Mouse |
|---|---|
| Right-grip mini-stick (HID Rx/Ry, centre 30000) | Moves the pointer; MSFS shows its cursor. Speed rises with deflection |
| Button 11 (press) | Left button, held while pressed |
| Button 8 / 13 (push down) | Left button |
| Button 9 (pull up) | Right button |

None of these inputs are bound in SPAD or in the MSFS throttle presets. SPAD can't move the pointer smoothly (it would launch a program per axis change), so this is a helper like `ka-sfs-watch`. It must be running: start it by hand, or add a shortcut to it in `shell:startup`. Tuning without rebuilding: `ka-mouse.ini` beside the exe with `Speed=1400`, `Deadzone=2500`, `InvertX=1`, `InvertY=1`. Log: `%TEMP%\ka-mouse.log`. Build: `csc -target:winexe -out:ka-mouse.exe ka-mouse.cs`.
