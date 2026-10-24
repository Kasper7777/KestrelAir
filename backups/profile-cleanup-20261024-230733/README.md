# Baron Garmin profiles

13 separate SPAD.neXt profiles are in **profiles/** and have also been copied into your SPAD.neXt profiles folder. They extend your original Baron profile, retaining its existing hardware mappings and options. Your original live Baron profile and aircraft assignments were not edited. These are prepared configurations: static checks pass, but SPAD.neXt loading and simulator operation still need testing.

Your saved aircraft assignments identify MSFS 2024, the default Baron G58, and Black Square Baron Professional variants. G1000 profiles are for a G1000-equipped aircraft; choosing one does not install a G1000 into the Black Square Baron. Choose the actual avionics in the aircraft's tablet first.

| Profile | Primary | Secondary |
| --- | --- | --- |
| Baron - GNS 530 | GNS 530 | — |
| Baron - GNS 430 | GNS 430 | — |
| Baron - GNS 530 + GNS 430 | GNS 530 | GNS 430 |
| Baron - G1000 PFD | G1000 PFD rotary controls | MFD navigation buttons |
| Baron - G1000 MFD | G1000 MFD rotary controls | MFD navigation buttons |
| Baron - PMS50 GTN 750 | PMS50 GTN 750 | — |
| Baron - PMS50 GTN 650 | PMS50 GTN 650 | — |
| Baron - PMS50 GTN 750 + 650 | PMS50 GTN 750 | PMS50 GTN 650 on COM2/NAV2 |
| Baron - GNS 530 + PMS50 GTN 650 | GNS 530 | PMS50 GTN 650 on COM2/NAV2 |
| Baron - TDS GTNxi 750 | TDS GTNxi 750 unit 1 | — |
| Baron - TDS GTNxi 650 | TDS GTNxi 650 unit 1 | — |
| Baron - TDS GTNxi 750 + 650 | TDS GTNxi 750 unit 1 | TDS GTNxi 650 unit 2 |
| Baron - GNS 530 + TDS GTNxi 650 | GNS 530 | TDS GTNxi 650 unit 2 |

“530” and “GNS 530” mean the same unit here. GNS 530 + GTN 650 is provided for both GTN providers. Single GTN650 profiles target unit 1; combinations target unit 2. If your aircraft loads the 650 as unit 1 even in a combination, change `GTN650_2` to `GTN650` (PMS50), or `TDSGTNXI650U2` to `TDSGTNXI650U1` (TDS), in a copy of that combination profile. Confirm the aircraft's actual unit assignment in SPAD.neXt's event/data monitor.

## Load a profile

1. Keep both RotAIR modules in **ANA** mode, matching the devices found in your latest log. These profiles use VID 16D0, PIDs 1290 / 13E4. GC mode changes the device identity and input behavior.
2. The generated variants are already copied into `C:\Users\Aero\Documents\SPAD.neXt\profiles`. Restart SPAD.neXt if needed to refresh its profile list. For future reinstalls, close SPAD.neXt and copy the desired XML files from **profiles/**. The earlier root-level `Baron - RotAIR PulsAIR.xml` is only a baseline copy.
3. Start SPAD.neXt, select the desired variant under Profiles, and activate it manually. Existing automatic assignments still point to `Baron.xml`, so select the variant after the aircraft loads. Assign it to the aircraft later if desired.
4. Use SPAD.neXt as the input handler for these modules. Disable overlapping simulator bindings and SFSmonitor handling for them to prevent double actions.
5. For TDS, ensure the TDS avionics and SPAD.neXt LVAR bridge are running. For PMS50, these files target the cockpit instrument, not the toolbar panel.

## RotAIR layout

Each module has four dual encoders, numbered top to bottom. Turn clockwise to increase, counterclockwise to decrease. The manufacturer's ANA assignments supply radio 1/2 tuning, heading, ADF, selected altitude, baro, course and transponder controls. Press/rotate radio functions select the alternate radios through firmware-generated inputs.

| Module / knob | Function |
| --- | --- |
| Type-1 / 1 | NAV radio tuning; hold swaps NAV1, alternate inputs tune NAV2 |
| Type-1 / 2 | Heading; hold/rotate changes transponder hundreds |
| Type-1 / 3 | ADF; hold/rotate changes transponder tens |
| Type-1 / 4 | Selected altitude: inner 100 ft, outer 1,000 ft |
| Type-2 / 1 | COM radio tuning; hold swaps COM1, alternate inputs tune COM2 |
| Type-2 / 2 | Course and baro |
| Type-2 / 3, single GNS/G1000 | Map range; push flight plan (GNS) / map joystick (G1000) |
| Type-2 / 3, single PMS50 GTN | Inner map zoom, outer volume, push Home |
| Type-2 / 3, single TDS GTN | Volume; push Home |
| Type-2 / 3, combination | **Secondary GPS** inner/outer knob and cursor push |
| Type-2 / 4 | **Primary GPS** inner/outer knob and cursor push |

In combinations, knob 3 is repurposed from map range to the second GPS. Knob focus is fixed: the PulsAIR display selection does not move the RotAIR knob assignments. The heading push from the old manufacturer template was omitted because it sent a heading-set command with no value. It is unassigned rather than a heading-sync function.

## PulsAIR layout

Physical keys 1–6 run down the left column; 7–12 run down the right. Firmware supplies different HID button numbers for display modes and long presses; these are handled as separate inputs, without adding another software long-press timer.

| Left key | Function | Right key | Function |
| --- | --- | --- | --- |
| 1 | AP master | 7 | Flight director |
| 2 | Heading mode | 8 | Altitude hold |
| 3 | NAV mode | 9 | VNV: unassigned |
| 4 | Approach mode | 10 | Backcourse |
| 5 | Vertical speed mode | 11 | VS reference increase |
| 6 | Flight level change | 12 | VS reference decrease |

Modes work only when supported by the aircraft's installed autopilot. Nose up/down keys adjust the VS reference; they do not dynamically change FLC airspeed or pitch references. There is no universal SimConnect VNAV toggle, so VNV is left unassigned.

On the display module, **PFD selects primary** and **MFD selects secondary** for the six upper navigation keys. In single-unit profiles both banks control the same GPS. G1000 profiles retain MFD buttons in the MFD bank. Avoid the firmware's combined PFD+MFD mode in dual-GPS profiles: that third bank targets the primary unit.

| Printed key | GNS | G1000 | PMS50 GTN | TDS GTNxi |
| --- | --- | --- | --- | --- |
| Direct-To | Direct-To | Direct-To | Direct-To | Direct-To |
| FPL | Flight plan | Flight plan | Flight plan page | Unassigned |
| CLR | Clear | Clear | Contextual Back | Knob push |
| MENU | Menu | Menu | Contextual Menu | Home |
| PROC | Procedures | Procedures | Procedures page | Unassigned |
| ENT | Enter | Enter | Contextual Enter | Unassigned |

TDS exposes bezel controls, so touchscreen flight-plan/procedure/enter actions still require the screen or mouse. PMS50 page shortcuts require Premium; contextual actions work only when the relevant on-screen control is available. Lower CDI/OBS/MSG keys target the primary GNS or PMS50 unit. In G1000 profiles, long presses on the AP module access PFD softkeys and long presses on the display module access MFD softkeys. Other long-press inputs are unassigned.

## Check on the ground

Confirm each radio's fine/coarse tuning and swaps, both directions of the GPS knobs, cursor push, Direct-To and Menu/Home. In a combination, verify that knob 3 and MFD-bank buttons affect only the secondary GPS, and knob 4 and PFD-bank buttons affect only the primary. Check a TDS key releases rather than remaining held. Verify one encoder detent produces one expected change. Then check each supported AP mode while parked. No simulator or hardware operation was exercised during generation.

**all-SFS-bindings.csv** lists every SFS input/action in every variant. **added-bindings.csv** gives labels for the newly authored assignments. **validation.txt** records structural checks and original-profile integrity. **build-profiles.ps1** regenerates the files; **validate-profiles.ps1** checks them.

Backups of all original profiles and the device configuration are in **backups/SPAD.neXt-20261024-170138/**. Restore by closing SPAD.neXt and copying the required original file back. No existing live files were replaced by this task.

References: [RotAIR manual and official SPAD.neXt profile](https://simflightservices.com/shop/air-modules/rotair/), [PulsAIR manual](https://simflightservices.com/docs/manuals/pulsair_manual.pdf), [PMS50 event reference](https://pms50.com/fs2020/gtn750/events.pdf), [Microsoft autopilot events](https://docs.flightsimulator.com/html/Programming_Tools/Event_IDs/Aircraft_Autopilot_Flight_Assist_Events.htm). TDS unit names and press/release behavior were checked against your installed TDS gauge JavaScript and 650 unit-2 behavior XML.
