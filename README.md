# Baron - GNS 530 + TDS GTNxi 650

This profile is installed in `C:\Users\Aero\Documents\SPAD.neXt\profiles`. Only this generated variant remains alongside your original Aerostar, Baron and Piper profiles, which are untouched. Earlier versions are backed up under `backups/`.

## PFD/MFD now switches controls together

Press the PulsAIR display module's **PFD** button to select the **GNS 530**, or **MFD** to select the **TDS GTN 650 unit 2**. The profile starts in PFD focus. A profile variable `PROFILE:KA_AVIONICS_FOCUS` stores the shared selection (0=PFD/GNS; 1=MFD/TDS).

| Control | PFD selection | MFD selection |
| --- | --- | --- |
| RANGE inner clockwise / anticlockwise | GNS range increase / decrease | TDS outer knob increase / decrease |
| RANGE push | GNS flight plan | TDS Home |
| FMS inner | GNS small knob | TDS inner knob |
| FMS outer | GNS large knob | TDS outer knob |
| FMS push | GNS cursor | TDS knob push |
| Direct-To key | GNS Direct-To | TDS Direct-To |
| MENU key | GNS menu | TDS Home |
| CLR key | GNS clear | TDS knob push |
| FPL / PROC / ENT keys | GNS flight plan / procedures / enter | Touchscreen required |
| CDI / OBS / VNAV / MSG keys | GNS corresponding action | No GNS action is sent; use GTN screen |

The same selection applies to every firmware button bank, both GC FMS banks, and ANA mode. Buttons no longer select only one set of navigation keys while leaving the rotaries fixed on the GNS. Supported long-press shortcuts also follow focus. Changing selection resets held TDS keys; their release events run regardless of the current focus.

**TDS RANGE limitation:** the exposed TDS interface provides outer-knob commands, rather than a dedicated map-zoom command. In MFD focus RANGE controls that GTN knob. Its native behavior depends on the GTN page and outer-knob configuration; a map-zoom response is not guaranteed. It must not change GNS range in MFD focus.

## Other controls

NAV/COM tuning, swaps, heading, selected altitude, course, baro, transponder and autopilot remain aircraft controls. The ADF encoder is also a dedicated TDS inner/outer knob and cursor control, available in either focus. RANGE outer turns adjust GTN volume; course hold pushes its volume knob. ADF hold activates GTN Direct-To; RANGE hold activates GTN Home. Heading push syncs the bug to magnetic heading.

AP VNV opens the GNS VNAV page; it does not arm autopilot VNAV. AP nose-up/down changes the VS reference, rather than switching automatically between VS, pitch and FLC airspeed functions. Only modes supported by the aircraft's autopilot will operate. AP-module long presses remain unused G1000 softkeys.

## Reload and check

1. Fully exit SPAD.neXt **without saving its cached generated profile**, reopen it, and select **Baron - GNS 530 + TDS GTNxi 650** after the aircraft loads. Existing automatic assignments still select original Baron.xml.
2. Press **PFD** once. Check RANGE and FMS operate the GNS, and Direct-To/Menu operate its pages.
3. Press **MFD** once. Check FMS and Direct-To/Home operate the TDS 650 and RANGE no longer changes the GNS scale.
4. Press **PFD** again and verify control returns to the GNS.

Both RotAIR GC and ANA identities are mapped. Your confirmed FMS inputs are 15/16 inner, 23/24 outer and 4 push; GC's alternate bank 34-38 is also covered. Confirm the aircraft has the TDS 650 loaded as unit 2 and its LVAR bridge is working. Disable overlapping SFSmonitor/simulator assignments for these controls to avoid double commands.

`focus-validation.txt` records 123 static routing assertions, including absence of GNS commands in MFD display focus. `validation.txt` records device and original-profile integrity checks. `all-SFS-bindings.csv` includes each action's focus condition. Static checks cannot prove live SPAD or Garmin behavior; the checks above remain necessary.

Build: `build-profiles.ps1`. Checks: `validate-profiles.ps1`, `validate-focus.ps1`, `audit-mappings.ps1`. Manufacturer input references are retained under `references/`. TDS commands were checked against the installed unit-2 behavior XML; SPAD profile-variable scope and condition fields were checked against the installed SPAD assemblies.
