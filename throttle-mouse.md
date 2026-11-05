# Throttle mini-stick as a mouse (2026-11-04)

`.tools/ka-mouse/ka-mouse.exe` runs hidden in the background, reads the MongoosT-50CM3 throttle directly, and drives the Windows mouse:

| Throttle input (recorded live, `watch-cm3-all.ps1`) | Mouse |
|---|---|
| Right-grip mini-stick (HID Rx/Ry, centre 30000) | Moves the pointer; MSFS shows its cursor. Speed rises with deflection |
| Button 13 (mini-stick press) | Left button, held while pressed |

Since 2026-11-05 the mini-stick press is the only click: buttons 8 and 11 no longer click, and there is no right button (button 8 is a thrust-reverser button in the Citation X profile).

None of these inputs are bound in MSFS. SPAD can't move the pointer smoothly (it would launch a program per axis change), so this is a background helper. SPAD starts it: the four mouse buttons (8, 9, 11, 13) run ka-mouse.exe on press, so the first press after a reboot wakes it (that press doesn't click); later launches exit at once because it is single-instance. No Windows Startup entry. Tuning without rebuilding: `ka-mouse.ini` beside the exe with `Speed=1400`, `Deadzone=2500`, `InvertX=1`, `InvertY=1`. Log: `%TEMP%\ka-mouse.log`. Build: `csc -target:winexe -out:ka-mouse.exe ka-mouse.cs`.

Vertical direction (2026-11-04): pushing the stick up now moves the pointer down, at the user's request; `InvertY=1` in `ka-mouse.ini` gives the earlier direction back. A copy started by an admin-mode SPAD can't be stopped by a normal process. The new build therefore exits while such an old copy is running (running both made the pointer stutter) and takes over at the first mouse-button press after the old copy has gone, which happens at the next sign-out or restart, or when it's ended in Task Manager. (On 2026-11-04 the old copy was ended with the user's consent through a Windows elevation prompt, and the new build has run alone since.)
