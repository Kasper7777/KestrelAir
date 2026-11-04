# Throttle mini-stick as a mouse (2026-11-04)

`.tools/ka-mouse/ka-mouse.exe` runs hidden in the background, reads the MongoosT-50CM3 throttle directly, and drives the Windows mouse:

| Throttle input (recorded live, `watch-cm3-all.ps1`) | Mouse |
|---|---|
| Right-grip mini-stick (HID Rx/Ry, centre 30000) | Moves the pointer; MSFS shows its cursor. Speed rises with deflection |
| Button 11 (press) | Left button, held while pressed |
| Button 8 / 13 (push down) | Left button |
| Button 9 (pull up) | Right button |

None of these inputs are bound in MSFS. SPAD can't move the pointer smoothly (it would launch a program per axis change), so this is a background helper. SPAD starts it: the four mouse buttons (8, 9, 11, 13) run ka-mouse.exe on press, so the first press after a reboot wakes it (that press doesn't click); later launches exit at once because it is single-instance. No Windows Startup entry. Tuning without rebuilding: `ka-mouse.ini` beside the exe with `Speed=1400`, `Deadzone=2500`, `InvertX=1`, `InvertY=1`. Log: `%TEMP%\ka-mouse.log`. Build: `csc -target:winexe -out:ka-mouse.exe ka-mouse.cs`.
