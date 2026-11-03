# Throttle B4 drone camera — 3 November 2026

Throttle B4 (logical input 45 in the current unshifted firmware) sends Shift+X once on press. The installed MSFS keyboard profile `inputprofile_2012295680` binds this shortcut to `TOGGLE_CAMERA_DRONE`. Release does not toggle it again. Apply with `bind-throttle-drone.ps1 -Apply` while SPAD is closed; both profile copies are backed up and unrelated XML is checked for equality.

The existing FSUIPC LED helper now opens the throttle (PID 0194). B4 uses physical LED address 3, report slot 4: cyan (`BC`) when CAMERA STATE is 4, dim purple (`91`) otherwise. All other throttle LED slots stay at zero, leaving them under firmware control. State feedback follows changes from the keyboard or simulator UI as well as B4. The installed FSUIPC7 Offsets Status PDF documents byte offset 026D as CAMERA STATE; [Microsoft's camera variable reference](https://docs.flightsimulator.com/html/Programming_Tools/SimVars/Camera_Variables.htm) identifies state 4 as Drone. The throttle definition extracted from the installed Configurator is retained in `references/virpil-throttle-primary.json`.

The corrected thumbstick mappings were also reapplied after SPAD had overwritten them with its older cached profile. Zone-change conditions prevent axis jitter from repeatedly queuing keyboard actions.

Live verification: `verify-drone-camera.py` read cockpit state 2, temporarily set drone state 4, then restored state 2. FSUIPC's `ipcInit.log` recorded throttle slot 4 changing `91 -> BC -> 91`, with no feature-report errors. SPAD's startup log confirmed the repaired 20 ms keyboard actions and `KA_STICK` zone variables are in use. Physical B4 operation and on-foot right-thumbstick response still need a user check in the simulator.
