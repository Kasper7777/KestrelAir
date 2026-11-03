# VIRPIL MiniStick camera controls

The right WarBRD grip is VPC WarBRD-D Base_1 in MSFS and DeviceIndex 0 in SPAD. Its RX/RY axes feed vJoy through SPAD's built-in RESPONSECURVE action. The live test confirmed the right grip's channels were crossed; RY now supplies horizontal camera control and RX supplies vertical control. Do not restore the earlier CUSTOM expression mapping: it produced endpoint output and continuous camera movement.

The native MSFS General Controls preset is portable-setup/KestrelAir-vJoy-GeneralControls.xml, named KestrelAir SPAD Cameras v2. Import it on vJoy Device and apply it to all aircraft. It supplies the camera contexts and a 6% centre dead zone; SPAD supplies all physical-stick routing.

| Input | On foot / cockpit / external | Drone mode |
|---|---|---|
| Right MiniStick horizontal | Look horizontally | Strafe |
| Right MiniStick vertical | Look vertically | Forward/back |
| Left MiniStick horizontal | Existing A/D walking keys | Yaw |
| Left MiniStick vertical | Existing W/S walking keys | Height |

The left walking keys are excluded while CAMERA STATE is 4, and the LED Lua helper releases walking/look keyboard holds on camera-mode transitions. Right-stick look uses analogue virtual axes instead of arrow-key emulation.

SPAD's bundled vJoy library was version 2.1.8, while the installed signed vJoy driver is 2.2.2. Its matching library is now installed in SPAD; the old DLL is backed up. The portable installer repeats that compatibility repair.

Validation: mappings were first exercised on unused virtual axes; the measured returned centres were 16383, matching the virtual controller's midpoint. After activation a five-second read-only check showed all six camera axes centred and zero camera pitch/yaw drift. Final physical direction and movement checks remain pending.

The old bind-thumbstick-keys.ps1 and bind-dji-thumbsticks.ps1 scripts describe earlier approaches and should not be reapplied over the current profiles. prepare-camera-bridge.py generates the current native SPAD mapping. Direct SimConnect on-foot axis events previously caused simulator crashes and remain removed.

Existing stick-click helpers and aircraft controls are preserved. See portable-setup/README.md for another PC's installation steps.

The final horizontal correction is in SPAD: right grip, Ry Axis, profile-specific response curve with endpoints (0,1) and (1,0). Its centre stays at 0.5; the vertical Rx Axis is unchanged. The portable MSFS preset uses normal horizontal direction so this inversion is applied once.
