# Cabin camera mode

Installed across the nine SPAD profiles on 2026-11-07. This moves the cockpit viewpoint inside the cabin during flight; it does not enter the separate MSFS on-foot mode.

- Either grip's flip lever raised (HID button 1 held; lowered = button 2): both main sticks' X/Y/twist flight and drone actions are blocked, and both grips glow hot pink.
- Both levers lowered: normal flight inputs and firmware colours return. Existing drone-camera mode still uses sky blue when the levers are lowered.
- In the cockpit, the left MiniStick moves the viewpoint forward/back and left/right using Shift+W/S/A/D. These are the bindings in both the sim's default 2024 keyboard profile and the user's custom keyboard profile.
- The right MiniStick retains its established vJoy look routing. On-foot and drone MiniStick mappings remain intact.

`cabin-camera-mode.py` patches only the relevant events. With SPAD closed, `--installed` backs up and patches its installed profiles. `build-citation-x-profile.py` reapplies this patch when rebuilding the Citation.

SPAD handles the input routing, flight-axis gates and keyboard actions. `.tools/ka-drone-leds/ka-walk-leds.exe` reads the real flip-lever HID states and publishes `L:KA_WALK_MODE`, avoiding saved toggle flags. The same helper paints both grips bright pink (0x77) or restores their normal/drone colours. It starts on either flip-lever edge or throttle B4; it was started explicitly during installation. It shares a single instance, reconnects to MSFS and treats missing/unreported grip input as disabled flight sticks. No Windows Startup entry is added. The older ka-drone-leds process was stopped to prevent competing LED writes.

Lever edges release W/A/S/D and Shift and clear the cabin movement state. Centring the MiniStick releases the direction keys; Shift is released once both movement axes are centred. Leaving cockpit or cabin mode releases held movement keys on the next axis update. Neither the helper nor the SPAD patch uses the on-foot SimConnect axis events previously associated with simulator crashes.

Validation: all 18 repository/portable profiles passed flight-axis gating, unique lever binding and repeated-patch checks. A read-only HID probe found both grips; the running helper reports successful hot-pink writes to both. SPAD's live log shows cabin movement keys and their releases. Physical movement, direction and lever/colour transitions require user confirmation. Aircraft camera boundaries can limit cabin travel.

Lever direction corrected from a user-confirmed both-UP HID capture: both grips report button 1. The earlier button-2 interpretation was reversed. Between switch contacts the helper retains the last known position, avoiding momentary changes while the lever moves. Pink now uses full red/blue plus a small green component (0x77), increased from red plus medium blue (0x63). The live helper was rebuilt and restarted without restarting SPAD or MSFS.
