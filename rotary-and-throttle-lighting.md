RotAir and throttle lighting correction — 2 November 2026.

The heading turn actions previously read `B:INSTRUMENT_HEADING_BUG` and reused its readback as a degree setpoint. Live SPAD telemetry showed repeated setpoints collapsing from 359 to 99 to 26, causing the reported jumping. Both GC and ANA top-module identities now use one PRESS action per direction: `HEADING_BUG_INC` or `HEADING_BUG_DEC`, with no readback/set loop. Lower-module course inputs use explicit `VOR1_OBI_INC/DEC` commands. Heading sync, ANA gyro-ring roles, and the other rotary functions remain unchanged.

Live verification with `KARotaryProbe.lua` reads the simulator's heading and course, checks forward/backward one-degree commands and a burst of ten increments/decrements, and restores the initial values. Commands follow the [Microsoft heading event reference](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Autopilot_Flight_Assist_Events.htm) and [radio navigation event reference](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Radio_Navigation_Events.htm).

Recorded results: heading +0.99976° / −0.99976° per command, ten rapid increments +9.99756° (16-bit readout quantization); course +1° / −1° and +10° for ten rapid increments. Initial heading 6.35010° and course 0° were restored. SPAD loaded the updated profile. Verification logs are saved with `backups/rotary-lighting-cabin-20261102-204515/`.

| Mongoos throttle switch | Assignment |
|---|---|
| T5 (48/49) | Floodlights, unchanged |
| T6 (50/51) | Panel lighting, `LVAR:bksq_MasterPanelLights` 1/0 |
| T7 (52/53) | Unassigned; duplicate pitot controls removed |

Pitot heat remains on CP3 T2/T3. Cabin pressure and door seal are now on CP2 B5/B6, with amber/cyan feedback at hardware LED addresses 16/13. CP2 B3/B4 are unassigned and blue. View lights/actions, CP3 battery/avionics controls, light-switch ordering, throttle parking brake, and other profile content are preserved by whole-profile comparison outside the explicit edits.
