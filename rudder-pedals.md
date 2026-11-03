# Saitek rudder pedals in SPAD

Since 2026-11-03 the Saitek Pro Flight Rudder Pedals (USB 06A3:0763) are driven by SPAD in every profile, not by MSFS.

| Pedal input | HID axis | Raw range (measured live) | SPAD action |
|---|---|---|---|
| Rudder | Rz | 5 (left pedal forward) to 501, centre 253 | `LEVER_RUDDER`, centre 253, **inverted** |
| Left toe brake | X | 0 released, 125 full | `LEVER_BRAKELEFT` |
| Right toe brake | Y | 0 released, 125 full (127 max) | `LEVER_BRAKERIGHT` |

The rudder is inverted because SPAD's rudder lever treats low raw values as right rudder. The first install was reversed in the sim, and you confirmed it was correct after the flip. The SimConnect check, `verify-rudder-pedals.py`, logs the rudder and both brakes; the before and after runs are `rudder-pedals-sim-20261103-before-invert.txt` and `rudder-pedals-sim-20261103.txt`. The raw pedal bytes from the axis test are in `rudder-pedal-raw.txt`. Each report holds 3 bytes: 7 bits X, 7 bits Y, 9 bits Rz, little-endian.

## MSFS side

There was no custom MSFS preset for the pedals; MSFS was using its built-in default. A built-in preset can't be deleted, so `portable-setup/KestrelAir-RudderPedals-SPAD.xml` is an empty Airplanes preset named "KestrelAir Pedals via SPAD". You imported it on 2026-11-03 under Controls > Saitek Pro Flight Rudder Pedals > Airplanes and selected it, so only SPAD moves the rudder and brakes. If the rudder ever feels doubled or jittery, check that this preset is still the one selected.

## Files and backup

- `bind-sticks-and-pedals.py` writes the pedal axes, together with the stick buttons, into any SPAD profile. The pedal HID path in it is this PC's (`9&2a71f0e4`). On another PC, update the `PEDALS` path from Device Manager or SPAD's device list first.
- Backup of all eight SPAD profiles before this change: `backups/all-profiles-sticks-pedals-20261103-211953/`.
