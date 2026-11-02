Current cabin, lighting and heat changes — 2 November 2026.

| Control | Assignment |
|---|---|
| CP2 B3/B4 | Unassigned; blue |
| CP2 B5 | Toggle cabin pressure, `LVAR:var_pressurizationPress`; amber, dim off / bright on |
| CP2 B6 | Toggle door seal, `LVAR:var_doorSealPrimaryInflate`; cyan, dim off / bright on |
| CP2 T1 | Strobes |
| CP2 T2 | Beacon, unchanged |
| CP2 T3 | Navigation lights |
| CP2 T4 | Taxi lights, unchanged |
| CP2 T5/T6 | Existing landing-light controls, unchanged |
| CP3 T2 | Left pitot heat; replaces cabin pressure |
| CP3 T3 | Right pitot heat; replaces door seal |
| CP3 T8 | Propeller heat; replaces wing/ice inspection light |

Latest correction: cabin controls now use physical CP2 B5/B6, HID buttons 8/9 and LED addresses 16/13 (Lua report slots 17/14), per the retained VIRPIL device definitions. B3/B4 are unassigned and blue. LED feedback reads the aircraft's actual switch LVARs through FSUIPC's WASM interface. The hardware has dim default colors while the connection initializes. All directional switches use PRESS actions, without release cancellation; pitot actions retain the indexed state guards from the working throttle bindings.

`move-cabin-controls.ps1` records the initial cabin/switch changes. `fix-rotary-lighting-and-cabin-placement.ps1` applies the subsequent B5/B6 correction together with the rotary and throttle-lighting repair; every other XML node is checked for equality against the installed source. Backups: `backups/cabin-buttons-*` and `backups/rotary-lighting-cabin-*`. Latest Configurator export: `cp2-cabin-b5-b6.device.vpcprofile`.

Live verification after moving to B5/B6: `KACabinProbe` read both lower/upper-case variable names, changed each state from 1 to 0, then restored it to 1. The feedback log recorded pressure slot 17 changing 8B → 85 → 8B and seal slot 14 changing BC → 94 → BC. This verifies actual state-driven colors. The remapped hardware switches were checked structurally against the existing indexed pitot bindings. CP3 B8–B13 view bindings and cyan lights, CP3 power buttons, throttle parking brake, and all other controls were preserved.
