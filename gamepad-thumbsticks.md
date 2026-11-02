# WarBRD thumbsticks as PlayStation sticks

**Crash cause:** `bind-onfoot-thumbsticks.ps1` (2026-11-02 23:03) made SPAD send the on-foot SimConnect events `AXIS_PC_MOVE_X/Z` and `AXIS_PC_FPV_ROTATION_X/Y` for every MiniStick movement, including while seated in the aircraft. Clicking a MiniStick moves it slightly. MSFS 2024 then crashed with an access violation (0xc0000005, `FlightSimulator2024.exe` +0x12eb9b1/+0x12eb9fd) at 23:15 and 23:38. No MSFS crash was logged in the previous 30 days. That script and `probe-onfoot-events.ps1` have been removed.

**Fix:** `bind-gamepad-thumbsticks.ps1` removes those four SPAD axis events and binds the MiniSticks natively in MSFS instead. The MSFS bindings are context actions, so each one acts only in its own mode (cockpit, external camera, on foot or drone), exactly as on a gamepad. Actions, directions and flags are copied from Asobo's `Dualsense_2024_Transversal.xml`.

| | Left MiniStick (PS left stick) | Right MiniStick (PS right stick) |
| --- | --- | --- |
| Cockpit | Head slide, when MSFS camera-translate mode is active | Look around (`KEY_COCKPIT_LOOK_*`) |
| External camera | — | Orbit the aircraft (`KEY_CHASE_LOOK_*`) |
| On foot | Walk (`KEY_PC_MOVE_*`) | Look (`KEY_AXIS_PC_FPV_ROTATION_X/Y`) |
| Drone | Move | Rotate |
| Click | Unassigned (DualSense L3 only toggles the assistance overlay) | Reset view: cockpit, chase, on-foot look, drone horizon |

The bindings use Joystick R-Axis X/Y (the MiniStick's RX/RY) on the **Right/Left VPC WarBRD-D Base** general profiles. Every such profile is updated (right: 1753164800; left: 0981998016 and 1270879104), because the active one cannot be read from `profile_00`. Flight axes stay in SPAD.

## Apply

1. Exit MSFS and SPAD. SPAD runs elevated and cannot be stopped from a normal shell.
2. Run `.\bind-gamepad-thumbsticks.ps1 -DetectClicks`. Click the right MiniStick, then the left one, when prompted; the script reads the button numbers from raw HID. If you already know the buttons, use `-RightClickButton N` instead.
3. Start SPAD and load the Baron profile, then start MSFS. If Steam reports a cloud conflict, keep the **local** files.

Backups go to `backups/gamepad-thumbsticks-*`. The script verifies that no other SPAD event or MSFS action changed. Re-running it is safe.

Untested live: direction follows the DualSense convention (stick up = lower Y value), which the VPC configurator's MiniStick calibration should provide. If up and down are reversed, invert the MiniStick vertical axis in the VPC configurator.
