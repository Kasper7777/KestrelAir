# Portable SPAD setup — activation pending

vJoy 2.2.2.0 from BrunnerInnovation is installed. Its signed installer reports that Windows needs a reboot. A direct API check can already acquire device 1, but a clean reboot and in-simulator verification are still required. No automatic Windows reboot was issued.

The active Baron profile has not been replaced with untested vJoy routes. `camera-profiles-pending/` contains staged camera versions of the Baron and all three Bonanza profiles. They use SPAD's installed `EventActionVirtualJoyStick` action and one vJoy device. These routes have not yet been accepted by SPAD's running loader or tested with physical input. Do not treat the camera as repaired yet.

After reboot, verify vJoy device 1 in SPAD, install/test the staged routes, and bind this virtual controller in MSFS General Controls:

| vJoy axis | MSFS assignment | Thumbstick |
|---|---|---|
| X | Drone X translation | Right horizontal |
| Y | Drone Z translation | Right vertical |
| Z | Drone yaw / Y rotation | Left horizontal |
| Rx | Drone Y translation | Left vertical |
| Ry | Cockpit, external and on-foot horizontal look axes | Right horizontal |
| Rz | Cockpit, external and on-foot vertical look axes | Right vertical |

Check each direction, centre stops, and simultaneous movement before using the profiles. The simulator's camera contexts select the appropriate assignments. Export the working vJoy General Controls profile from MSFS after testing; an MSFS export is not yet included. The prior physical-stick bindings in old saved profiles did not reach the simulator's live controller configuration.

For another PC, install SPAD, vJoy and FSUIPC, then copy the validated SPAD profiles, import the eventual MSFS vJoy profile, and install the included LED/helper files. The existing right-stick click actions reference `.tools/ka-click` by absolute path and must be updated if the repository moves. The setup is not yet a one-click installer.

B4 retains hot pink for drone active and neon green otherwise. The LED helper uses actual camera state, rather than remembering button presses. The physical right stick has been identified as **VPC WarBRD-D Base_1** on this PC; SPAD's corresponding device index is 0.
