Single-press toggle and CP2 trim correction — 2 November 2026.

Cowl, battery 1 and avionics 1 toggles now calculate the next state from the actual aircraft simulation variables, matching the state used by the lights. The previous native-input readback could disagree with the aircraft's loaded state, causing the first command to repeat an already-selected state. Native inputs still execute the changes. Each button has one PRESS action and no RELEASE action.

Live `KAToggleProbe` verification changed each cowl 0 → 100 → 0, battery 1 from 1 → 0 → 1, and avionics 1 from 1 → 0 → 1. Every individual command changed the state; all original states were restored. This tests the command/state logic rather than physically pressing the hardware. Source expressions compiled successfully in SPAD.

| CP2 encoder | Counterclockwise | Clockwise | HID inputs |
|---|---|---|---|
| E1 | Elevator trim down | Elevator trim up | 9 / 10 |
| E2 | Rudder trim left | Rudder trim right | 12 / 13 |
| E3 | Aileron trim left | Aileron trim right | 15 / 16 |

Encoder pushes remain unassigned. Current VIRPIL logical input order is gear 1–3, B1–B4 4–7, E1–E3 8–16, T1–T10 17–36, then B5–B10 37–42. Cabin pressure and door seal were corrected from the mistaken E1 IDs 8/9 to the actual B5/B6 IDs 37/38. Their amber/cyan light addresses were already correct and remain unchanged. No firmware input configuration or LED settings changed during this repair.

Script: `fix-single-press-and-cp2-trims.ps1`. Backups and verification: `backups/single-press-cp2-trim-*`. Whole-profile comparison checks all XML outside the explicit edits for equality, preserving views, other rotaries, lights, heat, axes and throttle controls.
