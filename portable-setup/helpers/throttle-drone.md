# Throttle B4 drone toggle and colours

Throttle B4 is SPAD BUTTON_45 in the current unshifted firmware. It sends Shift+X once on press. The MSFS keyboard General Controls profile binds Shift+X to Toggle Drone Camera. Release does not toggle it again. Another PC needs the same keyboard binding.

The FSUIPC KestrelAirLEDs.lua helper reads actual CAMERA STATE from byte offset 026D. B4 uses physical LED address 3, report slot 4: hot pink (A3) while state is 4 / Drone, neon green (8C) otherwise. Other throttle LEDs remain under firmware control.

The live ipcInit.log recorded state 4 / colour A3 followed by state 2 / colour 8C during the user's B4 test. This follows camera changes from the simulator or keyboard as well as the throttle button.

The four SPAD profiles preserve the same B4 action. See portable-setup/README.md and bonanza-profiles.md for installation and aircraft details.
