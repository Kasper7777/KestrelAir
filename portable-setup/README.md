# KestrelAir SPAD camera and Bonanza setup

The Baron and separate Black Square Bonanza A36, A36TC and B36TP profiles are installed. All 23 installed Bonanza and Baron 58P liveries have matching SPAD assignments. The Bonanza conversions follow the manufacturer's manual; physical operation in each aircraft remains unverified.

Camera routes are installed in all four SPAD profiles. The failed CUSTOM expression mapping was removed. The final routes use SPAD's built-in RESPONSECURVE axis mapping, checked on unused virtual axes before activation. SPAD's bundled vJoy 2.1.8 library also did not match the installed 2.2.2 driver. The matching 2.2.2 library was installed with a backup. The API confirms the DLL and driver now match.

MSFS confirmed successful import of KestrelAir-vJoy-GeneralControls.xml as "KestrelAir SPAD Cameras v2" on vJoy Device. This native General Controls preset has ten camera bindings and a 6% centre dead zone. The right grip's crossed horizontal/vertical channels were swapped after the live test. Final direction and centre-stop confirmation remains pending. A five-second read-only check confirmed all six virtual camera axes at centre and zero camera pitch/yaw drift. Final physical movement testing is still required.

| vJoy axis | MSFS assignment | Thumbstick |
|---|---|---|
| X | Drone X translation | Right horizontal |
| Y | Drone Z translation | Right vertical |
| Z | Drone Y rotation / yaw | Left horizontal |
| Rx | Drone Y translation / height | Left vertical |
| Ry | Cockpit, external and on-foot horizontal look | Right horizontal |
| Rz | Cockpit, external and on-foot vertical look | Right vertical |

MSFS camera contexts activate the appropriate assignments. Existing left-stick walking keys are excluded from drone mode. B4 retains Shift+X. The LED helper reads actual camera state: hot pink (0xA3) in drone mode and neon green (0x8C) otherwise.

## Move to another PC

1. Install SPAD, FSUIPC and the included signed vJoy 2.2.2 package; reboot if requested.
2. Keep this folder in its permanent location. Close MSFS and SPAD, then run Install-KestrelAir.ps1 from an administrator PowerShell window. It backs up profiles and the library, copies profiles, fixes right-click helper paths, and installs the LED Lua helper when FSUIPC is found. Supply -SpadDirectory or -FsuipcDirectory for other locations.
3. In MSFS Controls select vJoy Device, scroll below the device list to General controls, then gear > Import and choose KestrelAir-vJoy-GeneralControls.xml. Select the imported preset and choose Apply to all aircraft. General Controls is required for all camera contexts.
4. In the MSFS keyboard General Controls preset assign Shift+X to Toggle Drone Camera. This is B4's SPAD output.
5. On a new FSUIPC installation merge helpers/KestrelAir-myOffsets.txt into its myOffsets.txt without replacing other custom offsets.
6. Assign each SPAD profile to its matching aircraft; aircraft-assignments.csv records this PC's installed liveries. SPAD may ask which identical WarBRD grip is right after moving PCs. On this PC it is VPC WarBRD-D Base_1, SPAD DeviceIndex 0.

Before flight check every direction, simultaneous axes, no movement at centre, B4 toggle/colours, and engine controls. The B36TP condition lever selects fuel cutoff below 10% and high idle above it. Select GNS 530 / TDS GTNxi 650 in the aircraft tablet.

Use profiles/ for installation. camera-profiles-pending/ contains diagnostic generated copies. vjoy-camera-empty.xml is the original empty export template, not the finished camera preset.

The final horizontal correction is in SPAD: right grip, Ry Axis, profile-specific response curve with endpoints (0,1) and (1,0). Its centre stays at 0.5; the vertical Rx Axis is unchanged. The portable MSFS preset uses normal horizontal direction so this inversion is applied once.
