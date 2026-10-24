# Mapping audit

Every documented manufacturer input is mapped or has an explicit exception below. All exposed installed TDS bezel commands are assigned. This is static coverage, not proof of simulator operation.

| Device PID | Mapped | Firmware selectors | Touchscreen required | Not applicable | Undocumented inputs |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0x1290 | 37 | 0 | 0 | 0 | 3 |
| 0x13E4 | 37 | 0 | 0 | 0 | 3 |
| 0x14CA | 12 | 0 | 0 | 12 | 0 |
| 0x14CB | 32 | 2 | 3 | 0 | 0 |
| 0x128F | 37 | 0 | 0 | 0 | 3 |
| 0x13E3 | 37 | 0 | 0 | 0 | 3 |

Touchscreen exceptions: PulsAIR Type-2 MFD-bank FPL (B2), PROC (B8), and ENT (B9). TDS Home, Direct-To, both knobs, volume and both knob pushes are mapped. Its touchscreen page actions still require the screen or mouse.

AP-module long presses B13â€“B24 are factory G1000 PFD softkeys and have no equivalent in this selected avionics configuration. They remain unassigned. PFD/MFD selectors are internal device functions.

See mapping-audit.csv for every exposed button slot, including dormant/undocumented slots, and all-SFS-bindings.csv for action values and triggers. Your three original profiles are not edited.

Live verification still required: NAV/COM tuning and swaps, heading sync, selected altitude, course/baro, transponder digits/state, GNS RANGE/FMS/buttons, GTN Home/Direct-To/knobs/volume and key release, supported AP modes, and display long presses.
