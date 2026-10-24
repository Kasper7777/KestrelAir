# Baron - GNS 530 + TDS GTNxi 650

The corrected profile is in `profiles/Baron - GNS 530 + TDS GTNxi 650.xml` and installed in `C:\Users\Aero\Documents\SPAD.neXt\profiles`.

Only this generated variant remains installed. Your three original profiles — Aerostar.xml, Baron.xml and Piper PA-24-250.xml — were preserved and their hashes checked after cleanup. The other 12 generated variants were backed up before removal. See `cleanup-state.json` for the backup folder.

## Load the corrected profile

1. Fully exit SPAD.neXt and reopen it so it reloads the changed file and profile list. Avoid saving an old cached copy of the generated profile over the corrected file.
2. Select **Baron - GNS 530 + TDS GTNxi 650** after the aircraft loads. Existing automatic aircraft assignments still select your original Baron.xml.
3. Keep both RotAIR modules in **ANA** mode. Use the aircraft configuration with GNS 530 and TDS GTNxi 650 unit 2. The TDS LVAR bridge must be available.

## Corrected knob layout

Number knobs top to bottom on each module.

| Control | Function |
| --- | --- |
| RotAIR Type-2 RANGE (knob 3), inner clockwise | GNS 530 range increase / zoom out |
| RotAIR Type-2 RANGE (knob 3), inner anticlockwise | GNS 530 range decrease / zoom in |
| RotAIR Type-2 RANGE push | GNS 530 flight plan |
| RotAIR Type-2 FMS (bottom knob 4) | GNS 530 inner/outer knobs; push cursor |
| RotAIR Type-1 ADF (knob 3) | TDS GTN 650 inner/outer knobs; push cursor |

The range failure came from assigning the RANGE encoder to the secondary GPS. RANGE now sends `B:AS530_RANGE_ZOOM_Inc` / `B:AS530_RANGE_ZOOM_Dec`, matching the primary GNS range controls used in your original Baron profile. The GTN encoder controls moved to the ADF knob instead. Its former ADF tuning and transponder-ALT push assignments are replaced in this generated profile only. Other original hardware sections remain intact.

PulsAIR display **PFD** selects GNS 530 navigation keys; **MFD** selects TDS GTN 650 keys. This does not switch the rotary assignments. Avoid combined PFD+MFD firmware mode, which targets the primary GNS bank.

| Printed display key | GNS 530 bank | TDS GTN 650 bank |
| --- | --- | --- |
| Direct-To | Direct-To | Direct-To |
| FPL | Flight plan | Unassigned |
| CLR | Clear | Knob push |
| MENU | Menu | Home |
| PROC | Procedures | Unassigned |
| ENT | Enter | Unassigned |

TDS touchscreen FPL/PROC/ENT actions still require the screen or mouse. Lower CDI/OBS/VNAV/MSG display keys target the GNS. The AP module uses standard AP, HDG, NAV, APR, VS, FLC, FD, ALT and BC controls where supported by the installed autopilot. Its VNV key is unassigned; nose-up/down adjusts the VS reference only.

## Verify

With the aircraft parked and avionics powered, display the GNS 530 map and turn RANGE one detent each way. Check the displayed scale changes. Then check the FMS knob operates the GNS and the ADF knob operates only the TDS 650, including cursor release.

Structural checks pass, including explicit range targets, GTN knob inputs, key releases, and preservation of original hardware/options. Live simulator/hardware behavior has not been tested. `all-SFS-bindings.csv` lists the complete SFS assignments; `validation.txt` records the checks. `build-profiles.ps1` now generates only this combination.

References: [RotAIR official mappings](https://simflightservices.com/shop/air-modules/rotair/), [PulsAIR manual](https://simflightservices.com/docs/manuals/pulsair_manual.pdf). TDS variables were checked against the locally installed TDS unit-2 behavior XML.
