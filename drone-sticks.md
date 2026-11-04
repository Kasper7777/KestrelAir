# Drone mode on the main sticks (2026-11-04)

Throttle B4 toggles the MSFS drone camera (Shift+X). While the drone camera is on (CAMERA STATE 4):

- The main sticks fly the drone like the Star Citizen twin-stick layout, and stop moving the plane's ailerons/elevator.
  - **Left stick:** left/right = slide sideways, forward/back = fly forward/back, twist = up/down.
  - **Right stick:** forward/back = pitch, left/right = yaw (turn), twist = roll.
- **Stick wheel (either stick): up = drone faster, down = slower** (MSFS drone speed steps, via vJoy buttons 4/5). Outside drone mode the wheel works the ATC menus as before.
- Both sticks glow **sky blue**. Out of drone mode they return to their own firmware colours.

Press B4 again: plane mode, normal flight controls, normal colours. The plane's controls stay where they were when you entered drone mode and follow the stick again from its next movement.

How it's built:
- `drone-sticks.py` (SPAD, all 8 profiles): each grip's X, Y and twist (Rz) get a drone definition, `SIMCONNECT:CAMERA STATE Equals 4` → vJoy axis; the existing flight-control definitions gain `Unequal 4`. Routing table in the script.
- `build-vjoy-onfoot-preset.py --live`: MSFS "Look" vJoy preset gets drone pitch (vJoy Rz) and roll (vJoy Dial = MSFS "Slider Y"). Read at MSFS start.
- `.tools/ka-drone-leds/ka-drone-leds.exe`: background helper; reads CAMERA STATE through SimConnect. The ring colour set on the Configurator's "WarBRD-D Base" page is really the ALPHA Prime grip's 9 LEDs on shift-register chain 1: VIRPIL feature report 2, command 103, one byte per LED = 0x40 | BBGGRR (sky blue 0x78); command 100 hands back to the stored colours. Command 102 with 0x80 bytes (what the panels and throttle use) does nothing on the sticks. User confirmed blue on both sticks, 2026-11-04. SPAD starts it: B4 (drone toggle) also runs ka-drone-leds.exe in every profile; it is single-instance, so later presses just exit. No Windows Startup entry. `--test` = 15 s of blue. Log `%TEMP%\ka-drone-leds.log`.

If a direction is backwards, flip that drone action's Flag (4 = normal, 132 = inverted) via `build-vjoy-onfoot-preset.py` rather than in SPAD. The mini-sticks still work in drone mode too.
