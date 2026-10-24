# Baron - GNS 530 + TDS GTNxi 650

The corrected profile is in `profiles/Baron - GNS 530 + TDS GTNxi 650.xml` and installed in `C:\Users\Aero\Documents\SPAD.neXt\profiles`.

Only this generated variant remains installed. Your three original profiles — Aerostar.xml, Baron.xml and Piper PA-24-250.xml — were preserved and their hashes checked after cleanup. The other 12 generated variants were backed up before removal. See `cleanup-state.json` for the backup folder.

## Load the corrected profile

1. Fully exit SPAD.neXt and reopen it so it reloads the changed file and profile list. Avoid saving an old cached copy of the generated profile over the corrected file.
2. Select **Baron - GNS 530 + TDS GTNxi 650** after the aircraft loads. Existing automatic aircraft assignments still select your original Baron.xml.
3. Both RotAIR **GC and ANA modes** are now mapped; your latest session connects in GC mode. Use the aircraft configuration with GNS 530 and TDS GTNxi 650 unit 2. The TDS LVAR bridge must be available.

## Corrected knob layout

Number knobs top to bottom on each module.

| Control | Function |
| --- | --- |
| RotAIR Type-2 RANGE (knob 3), inner clockwise | GNS 530 range increase / zoom out |
| RotAIR Type-2 RANGE (knob 3), inner anticlockwise | GNS 530 range decrease / zoom in |
| RotAIR Type-2 RANGE push | GNS 530 flight plan |
| RotAIR Type-2 FMS (bottom knob 4) | GNS 530 inner/outer knobs; push cursor |
| RotAIR Type-1 ADF (knob 3) | TDS GTN 650 inner/outer knobs; push cursor |

The first range failure came from assigning RANGE to the secondary GPS. A further log check found the connected modules were in GC mode (PIDs 128F / 13E3), while the earlier correction only mapped ANA (1290 / 13E4). The profile now covers both device identities, with RANGE buttons 13/14 mapped in each. RANGE now sends `B:AS530_RANGE_ZOOM_Inc` / `B:AS530_RANGE_ZOOM_Dec`, matching the primary GNS range controls used in your original Baron profile. The GTN encoder controls moved to the ADF knob instead. Its former ADF tuning and transponder-ALT push assignments are replaced in this generated profile only. Heading push now syncs the bug to magnetic heading; NAV push toggles NAV1 audio ident. Other original hardware sections remain intact.

PulsAIR display **PFD** selects GNS 530 navigation keys; **MFD** selects TDS GTN 650 keys. This does not switch the rotary assignments. Avoid combined PFD+MFD firmware mode, which targets the primary GNS bank.

| Printed display key | GNS 530 bank | TDS GTN 650 bank |
| --- | --- | --- |
| Direct-To | Direct-To | Direct-To |
| FPL | Flight plan | Unassigned |
| CLR | Clear | Knob push |
| MENU | Menu | Home |
| PROC | Procedures | Unassigned |
| ENT | Enter | Unassigned |

TDS touchscreen FPL/PROC/ENT actions still require the screen or mouse. Lower CDI/OBS/VNAV/MSG display keys target the GNS. The AP module uses standard AP, HDG, NAV, APR, VS, FLC, FD, ALT and BC controls where supported by the installed autopilot. Its VNV key now opens the GNS VNAV page (it does not arm AP VNAV); nose-up/down adjusts the VS reference only.

## Verify

With the aircraft parked and avionics powered, display the GNS 530 map and turn RANGE one detent each way. Check the displayed scale changes. Then check the FMS knob operates the GNS and the ADF knob operates only the TDS 650, including cursor release.

Structural checks pass, including explicit range targets, GTN knob inputs, key releases, and preservation of original hardware/options. Live simulator/hardware behavior has not been tested. `all-SFS-bindings.csv` lists the complete SFS assignments; `validation.txt` records the checks. `build-profiles.ps1` now generates only this combination.

References: [RotAIR official mappings](https://simflightservices.com/shop/air-modules/rotair/), [PulsAIR manual](https://simflightservices.com/docs/manuals/pulsair_manual.pdf). TDS variables were checked against the locally installed TDS unit-2 behavior XML.


## FMS update

GNS 530 FMS now uses the exact SPAD control names from the manufacturer's supplied XML: `MSFS:AS530_RightSmallKnob_Right/Left`, `MSFS:AS530_RightLargeKnob_Right/Left`, and `MSFS:AS530_RightSmallKnob_Push`. GC mode covers inner 15/16, outer 23/24, push 4, and alternate inner 34/35, outer 36/37, push 38. Static validation checks these assignments against the expected manufacturer definitions. Actual response still requires a live test after fully exiting SPAD.neXt without saving its old cached generated profile, then reopening and selecting the combo. The existing running session cannot be assumed to use an XML file updated on disk.

## Complete input audit

See **mapping-audit.md** and **mapping-audit.csv** for coverage of every input slot in GC/ANA mode and both PulsAIR modules. The audit checks all manufacturer reference assignments and all ten exposed installed TDS bezel commands. Unexplained missing documented inputs fail the audit.

Additional controls:

| Control | Assignment |
| --- | --- |
| Type-1 NAV push | NAV1 audio ident toggle |
| Type-1 heading push | Sync heading bug to current magnetic heading |
| Type-1 ADF hold | GTN 650 Direct-To |
| Type-2 COM push | COM1 receiver toggle |
| Type-2 course push | GNS OBS toggle |
| Type-2 course hold | GTN volume knob push |
| Type-2 RANGE outer clockwise/anticlockwise | GTN volume increase/decrease |
| Type-2 RANGE hold | GTN Home |
| Type-2 pressed RANGE rotation | GNS range increase/decrease |
| PulsAIR AP VNV | Open GNS VNAV page; not AP VNAV arming |

Display-module long presses always use these shortcuts, regardless of its selected bank: Direct-To = GNS Direct-To, FPL = GNS flight plan, CLR = GNS long clear, PFD = GNS cursor, CDI = GNS CDI, OBS = GNS OBS, MENU = GNS menu, PROC = GNS procedures, ENT = GNS enter, MFD = GTN Home, VNAV = GNS VNAV, MSG = GNS messages. Firmware already emits separate long-press inputs; there is no extra software timer.

Exceptions remain deliberate: the TDS-bank short FPL/PROC/ENT keys require touchscreen actions, PFD/MFD selectors are firmware functions, and AP-module long presses are G1000 softkeys without an equivalent here. Dormant/undocumented HID slots are listed rather than assigned arbitrary actions. Configuration coverage is verified; actual avionics operation still requires the ground checks above.

