CP3 layout installed 2026-10-31. Supersedes earlier CP3 selector direction.

| Control | Baron function |
|---|---|
| T1 | Left fuel pump (unchanged) |
| T2 | Left pitot heat |
| T3 | Right pitot heat |
| T4 | Propeller heat |
| T5 | Fuel-vent heat |
| T6 | Stall-warning heat |
| T7 | Windshield heat |
| T8 | Propeller heat |
| Master ARM | Right fuel pump (unchanged) |
| Rotary selector | Right magneto; reversed to match physical OFF |

Physical OFF was verified by a live HID report as button 47. Buttons 43-47 now write ignition values 5,3,2,1,0 respectively. Positions 47 through 43 therefore run OFF through START; leaving START for BOTH stops holding the starter.

Verified switch IDs: T1=14/15/16, T2=17/18, T3=19/20, T4=21/22, T5=23/24, T6=25/26, T7=27/28, T8=29/30; L/R=31/32/33; Master ARM=34/35/36. New switches use directional PRESS on/off with no release cancellation. Removed the CP3 taxi-light duplicate. The four heat LVAR names were checked against the live Baron's advertised variables; wing lighting uses its advertised input event.

Backup: `backups/cp3-layout-20261031-194542/`. Comparison check confirmed all other devices, working fuel pumps/cowl flaps, axes and Tobii bindings unchanged. Live cockpit response for new heat functions remains to be confirmed.
