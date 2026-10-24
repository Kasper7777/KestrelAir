# Baron RotAIR / PulsAIR setup

Status: initial discovery notes retained below. Completed variants and current usage instructions are in README.md. The selected GNS 530 + TDS GTNxi 650 variant remains; the 12 other generated variants were backed up and removed. RANGE was restored, and GTN knob controls moved to the ADF encoder. See README.md.

- Source: C:\Users\Aero\Documents\SPAD.neXt\profiles\Baron.xml
- Working copy: Baron - RotAIR PulsAIR.xml (new unique ProfileID; existing device mappings preserved).
- Backups: backups\SPAD.neXt-20261024-170138\profiles and conf.
- Verified original Baron backup SHA-256 matches the source; copied device mappings match the source.

Device identities found in local SPAD.neXt configuration/logs:

| Device | VID | PID |
| --- | --- | --- |
| RotAIR Type-1 ANA | 16D0 | 1290 |
| RotAIR Type-2 ANA | 16D0 | 13E4 |
| PulsAIR Type-1 | 16D0 | 14CA |
| PulsAIR Type-2 | 16D0 | 14CB |

Older GC device identities also appear in PanelNames.xml (Type-1 PID 128F, Type-2 PID 13E3). Mode changes alter device identity, so mappings must match the selected mode.

Manufacturer references:
- https://simflightservices.com/docs/manuals/rotair_manual.pdf
- https://simflightservices.com/docs/manuals/pulsair_manual.pdf
- https://simflightservices.com/shop/air-modules/rotair/ (SPAD.neXt XML download)

RotAIR provides four dual encoders per module, with push, hold and press/rotate functions. For custom SPAD.neXt use the manufacturer recommends Type-1 GC and Type-2 GC (AM); ANA is also supported by their downloadable XML. Existing local logs show ANA devices.

PulsAIR physical keys run 1-6 down the left column and 7-12 down the right. Firmware emits separate long-press button numbers, so do not assume each visible key corresponds to only one HID button. Type-1 is the autopilot panel; Type-2 is the display/navigation panel with selectable avionics modes.

Subsequent discovery: saved aircraft assignments identify MSFS 2024 and Black Square Baron Professional alongside the default Baron G58. The user requested separate Garmin variants and a GNS530 + GTN650 combination; see README.md for the resulting profiles and assumptions.

