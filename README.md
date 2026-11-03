ï»¿# Baron - GNS 530 + TDS GTNxi 650

This profile is installed in `C:\Users\Aero\Documents\SPAD.neXt\profiles`. The Baron variant and matching Black Square Bonanza A36, A36TC and B36TP profiles are installed alongside the original profiles. Camera routing and portable installation are documented in thumbstick-keys.md and portable-setup/README.md. Earlier versions are backed up under `backups/`.

## PFD/MFD now switches controls together

Press the PulsAIR display module's **PFD** button to select the **GNS 530**, or **MFD** to select the **TDS GTN 650 unit 2**. The profile starts in PFD focus. A profile variable `PROFILE:KA_AVIONICS_FOCUS` stores the shared selection (0=PFD/GNS; 1=MFD/TDS).

| Control | PFD selection | MFD selection |
| --- | --- | --- |
| RANGE inner/outer clockwise / anticlockwise | GNS range increase / decrease | TDS inner knob decrease / increase (map zoom out / in, same direction as GNS) |
| RANGE push | GNS flight plan | No action (keeps current page/mode) |
| FMS inner | GNS small knob | TDS inner knob |
| FMS outer | GNS large knob | TDS outer knob |
| FMS push | GNS cursor | TDS knob push |
| Direct-To key | GNS Direct-To | TDS Direct-To |
| MENU key | GNS menu | TDS Home |
| CLR key | GNS clear | TDS knob push |
| FPL / PROC / ENT keys | GNS flight plan / procedures / enter | Touchscreen required |
| CDI / OBS / VNAV / MSG keys | GNS corresponding action | No GNS action is sent; use GTN screen |

The same selection applies to every firmware button bank, both GC FMS banks, and ANA mode. Buttons no longer select only one set of navigation keys while leaving the rotaries fixed on the GNS. Supported long-press shortcuts also follow focus. Changing selection resets held TDS keys; their release events run regardless of the current focus.

**TDS map zoom:** RANGE now uses the GTN inner-knob commands, as specified in Garmin's GTN Xi guide (190-02327-03 Rev. G, page 1-14). Display the Map page with the knob in page-navigation mode, rather than standby radio tuning or data entry. The former outer-knob assignment selected pages instead of zooming.

## Other controls

NAV/COM tuning, swaps, heading, selected altitude, course, baro, transponder and autopilot remain aircraft controls. The ADF encoder is also a dedicated TDS inner/outer knob and cursor control, available in either focus; its inner ring is reversed so clockwise zooms out, matching RANGE. In MFD focus, hold the display CDI key to reduce GTN volume or hold VNAV to increase it; course hold pushes its volume knob. ADF hold activates GTN Direct-To; RANGE hold activates GTN Home. Heading push syncs the bug to magnetic heading.

**Transponder (top RotAIR):** ALT knob push selects ALT (altitude reporting, the normal in-flight mode); ALT knob hold selects STBY; heading knob hold sends IDENT. Push-and-turn sets the squawk code one digit per knob: NAV = thousands, heading = hundreds, ADF/GTN = tens, ALT = ones. The RANGE knob's push-and-turn on the bottom RotAIR also adjusts the ones digit.

**VIRPIL CP3 E1 (squawk knob):** turn to change the selected squawk digit; push (button 37) to move to the next digit, thousands â†’ hundreds â†’ tens â†’ ones â†’ thousands. The profile starts on thousands; the cockpit display does not show which digit is selected. Remove any MSFS control binding on CP3 buttons 37â€“39 (E1 previously changed heading through MSFS), or both will act.

AP VNV opens the GNS VNAV page; it does not arm autopilot VNAV. AP nose-up/down changes the VS reference, rather than switching automatically between VS, pitch and FLC airspeed functions. Only modes supported by the aircraft's autopilot will operate. AP-module long presses remain unused G1000 softkeys.

## Reload and check

1. Fully exit SPAD.neXt **without saving its cached generated profile**, reopen it, and select **Baron - GNS 530 + TDS GTNxi 650** after the aircraft loads. Existing automatic assignments still select original Baron.xml.
2. Press **PFD** once. Check RANGE and FMS operate the GNS, and Direct-To/Menu operate its pages.
3. Press **MFD** once. Check FMS and Direct-To/Home operate the TDS 650 and RANGE no longer changes the GNS scale.
4. Press **PFD** again and verify control returns to the GNS.

Both RotAIR GC and ANA identities are mapped. Your confirmed FMS inputs are 15/16 inner, 23/24 outer and 4 push; GC's alternate bank 34-38 is also covered. Confirm the aircraft has the TDS 650 loaded as unit 2 and its LVAR bridge is working. Disable overlapping SFSmonitor/simulator assignments for these controls to avoid double commands.

`focus-validation.txt` records 151 static routing assertions, including absence of GNS commands in MFD display focus. `validation.txt` records device and original-profile integrity checks. `all-SFS-bindings.csv` includes each action's focus condition. Static checks cannot prove live SPAD or Garmin behavior; the checks above remain necessary.

Build: `build-profiles.ps1`. Checks: `validate-profiles.ps1`, `validate-focus.ps1`, `audit-mappings.ps1`. Manufacturer input references are retained under `references/`. TDS commands were checked against the installed unit-2 behavior XML; SPAD profile-variable scope and condition fields were checked against the installed SPAD assemblies.


RANGE update: both rings and pressed-turn inputs now use the same selected-device zoom route. Volume is removed from RANGE. MFD RANGE push no longer opens Home; use MENU for Home. TDS still uses a contextual inner-knob command: map zoom requires the Map page and page-navigation knob focus, as described in the [Garmin guide](https://static.garmin.com/pumac/190-02327-03_g.pdf), pages 1-14 and 1-16. A dedicated context-independent TDS zoom event has not been established.


GNS ENT correction: inputs 9/18/24 and long-press input 34 use MSFS:AS530_ENT_Push. Only those GNS commands were changed; existing focus conditions, TDS behavior and working rotaries were retained. Live GNS response still requires a test after reloading the profile.


Native ENT update: GNS inputs 9/18/24 and long input 34 now set the aircraft-advertised B:AS530_ENT input to 1 on press and 0 on release. This supersedes the MSFS alias described above. Live validation is still required; working knob and focus bindings were not changed.


CP3 red button 6: PRESS sends `H:bksq_JpiButton_1_L_Short`, the EDM-760 STEP button. Installed and workspace profiles were patched independently, preserving their other mappings. Backups: `backups/cp3-step-20261030-233515/`. Reload the generated Baron profile without saving the old cached copy, then check the engine monitor advances one item per press. Live cockpit response remains unverified. Event reference: Black Square Baron Professional User Guide (2025), EDM 760 hardware inputs, https://msfs.dev-pset.com/assets/docs/BKSQ_BaronProfessionalManual.pdf (PDF page 153).

CP3 STEP repair (2026-10-31): SPAD's cached profile had overwritten the installed binding. Stopped SPAD, restored only CP3 button 6, verified all other installed XML was unchanged, and restarted SPAD. The patch script now refuses to run while SPAD is open and accepts an already-correct binding. Backup: backups/cp3-step-20261031-002207. Physical button response still requires a live press.

2026-11-02 update: right-stick range removed; RotAir ANA ADF/heading roles restored; CP3 B1/B2 battery (red), B3/B4 avionics (white), CP2 B1/B2 cowl toggles (purple/green). View bindings preserved. See [current power and color setup](ana-power-and-colours.md). This supersedes the earlier top-module GTN/ADF shortcuts and transponder push mapping described above.

Latest cabin, light and heat layout: [cabin-and-heat-controls.md](cabin-and-heat-controls.md). CP2 B3/B4 now pressure/door seal with amber/cyan state feedback; CP2 T1/T3 swapped; CP3 T2/T3 pitot heat and T8 propeller heat.

Latest correction: [rotary-and-throttle-lighting.md](rotary-and-throttle-lighting.md). Heading/course use verified one-degree commands; throttle T5 flood unchanged, T6 panel lighting, T7 unassigned. Cabin pressure/door seal are on CP2 B5/B6 with amber/cyan feedback; B3/B4 are unassigned blue.

Latest toggle/trim repair: [single-press-and-cp2-trim.md](single-press-and-cp2-trim.md). Cowl/battery/avionics use actual-state toggles; CP2 E1 elevator, E2 rudder, E3 aileron trim. Cabin B5/B6 logical IDs corrected to 37/38.

Throttle T7 now controls prop sync: logical 52 ON, 53 OFF, PRESS only, via the aircraft-advertised LVAR:var_PropSyncSwitch. Backups: backups/throttle-prop-sync-* .

CP2 B7/B8 (beneath B5/B6) now provide hold-to-test cabin pressure and hold-to-inflate standby door seal, with dim/bright red feedback. Both main and held-button flags are explicitly cleared on release. See cabin-and-heat-controls.md. Backups: backups/cabin-test-standby-* .

Thumbstick crash fix (2026-11-03): the SPAD on-foot MiniStick SimConnect events crashed MSFS 2024 and are removed. The MiniSticks now hold MSFS keyboard keys from SPAD (right stick = arrow keys: look around in cockpit, outside and on foot; left stick = W/A/S/D: walk on foot), released at centre. Run `bind-thumbstick-keys.ps1` with SPAD closed. See [thumbstick-keys.md](thumbstick-keys.md).
