# Cabin camera mode

Installed across the nine SPAD profiles on 2026-11-07. This moves the cockpit viewpoint inside the cabin during flight; it does not enter the separate MSFS on-foot mode.

- Either grip's flip lever folded DOWN (HID button 2; up = button 1): both main sticks' X/Y/twist flight and drone actions are blocked, and both grips glow hot pink. (Swapped 2026-11-08 at the user's request; it used to be lever up.)
- Both levers up: normal flight inputs and firmware colours return. Existing drone-camera mode still uses sky blue when the levers are up.
- In pink mode with the cockpit camera active (CAMERA STATE 2), the wheel on either grip changes the viewpoint height. Wheel up (HID 22) stands up with Shift+E (`KEY_COCKPIT_CAMERA_HEIGHT_INC`); wheel down (HID 21) crouches with Shift+Q (`_DEC`). These are the sim defaults in `Keyboard_2024_Transversal.xml`. Each click holds the key for 150 ms (`WHEEL_HOLD_MS`). In pink mode in any other view, the wheel does nothing. Outside pink mode it still drives the ATC reply menus, and in drone camera it still sets drone speed. Shift+R/F were tried first and were wrong: Shift+F is cockpit quick view 4 (looks left).
- In the cockpit, the left MiniStick moves the viewpoint forward/back and left/right using Shift+W/S/A/D. These are the bindings in both the sim's default 2024 keyboard profile and the user's custom keyboard profile.
- The right MiniStick retains its established vJoy look routing. On-foot and drone MiniStick mappings remain intact.

`cabin-camera-mode.py` patches only the relevant events. With SPAD closed, `--installed` backs up and patches its installed profiles. `build-citation-x-profile.py` reapplies this patch when rebuilding the Citation.

SPAD handles the input routing, flight-axis gates and keyboard actions. `.tools/ka-drone-leds/ka-walk-leds.exe` reads the real flip-lever HID states and publishes `L:KA_WALK_MODE`, avoiding saved toggle flags. The same helper paints both grips bright pink (0x77) or restores their normal/drone colours. It starts on either flip-lever edge or throttle B4; it was started explicitly during installation. It shares a single instance, reconnects to MSFS and treats missing/unreported grip input as disabled flight sticks. No Windows Startup entry is added. The older ka-drone-leds process was stopped to prevent competing LED writes.

Lever edges release W/A/S/D and Shift and clear the cabin movement state. Centring the MiniStick releases the direction keys; Shift is released once both movement axes are centred. Leaving cockpit or cabin mode releases held movement keys on the next axis update. Neither the helper nor the SPAD patch uses the on-foot SimConnect axis events previously associated with simulator crashes.

Validation: all 18 repository/portable profiles passed flight-axis gating, unique lever binding and repeated-patch checks. A read-only HID probe found both grips; the running helper reports successful hot-pink writes to both. SPAD's live log shows cabin movement keys and their releases. Physical movement, direction and lever/colour transitions require user confirmation. Aircraft camera boundaries can limit cabin travel.

Lever direction corrected from a user-confirmed both-UP HID capture: both grips report button 1. The earlier button-2 interpretation was reversed. Between switch contacts the helper retains the last known position, avoiding momentary changes while the lever moves. Pink now uses full red/blue plus a small green component (0x77), increased from red plus medium blue (0x63). The live helper was rebuilt and restarted without restarting SPAD or MSFS.


2026-11-08: lever direction swapped (pink = folded down) in `ka-drone-leds.cs`; rebuilt `ka-walk-leds.exe` and restarted it. Grip wheels added for camera up/down in pink mode. Repository, portable and installed profiles were patched, and SPAD was restarted. Wheel keys corrected the same day to Shift+E/Shift+Q (camera height) and limited to the cockpit camera.
