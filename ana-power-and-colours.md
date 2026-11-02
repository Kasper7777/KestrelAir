Updated 2 November 2026 in the installed and workspace **Baron - GNS 530 + TDS GTNxi 650** profile.

| Physical control | Function | Off / up | On / down |
|---|---|---|---|
| CP3 B1 | Battery master 1 | Dim red | Bright red |
| CP3 B2 | Battery master 2, where supported by aircraft | Dim red | Bright red |
| CP3 B3 | Avionics master 1 | Dim white | Bright white |
| CP3 B4 | Avionics master 2, where supported by aircraft | Dim white | Bright white |
| CP2 B1 | Toggle left cowl flap | Purple, closed/up | Green, open/down |
| CP2 B2 | Toggle right cowl flap | Purple, closed/up | Green, open/down |

CP3 B8–B13 view actions are identical to the installed profile backed up before this task. B13 retains its previous Back-key external-view shortcut. Original B8–B11 colors were restored from the Configurator export taken before the color edits. CP2 B5–B10 were not reassigned.

**CP3 LED hardware addresses are not Configurator swatch positions.** The installed VIRPIL device definition gives B1=7, B2=8, B3=6, B4=9 (zero-based). B8–B13 use addresses 0,1,2,3,5,4. Lua's one-based report slots are therefore B1=8, B2=9, B3=7, B4=10. All six view LEDs are restored to their original cyan (0/255/255), confirmed in the pre-edit export. The manufacturer's relevant definitions are saved in `references/virpil-panel-led-physical-addresses.json`. Final Configurator exports: `cp3-final-verified-map.device.vpcprofile` and `cp2-cowls-corrected.device.vpcprofile`. No firmware profile was edited by hand.

SPAD sends the controls through the Baron's advertised native battery, avionics and cowl inputs. Testing showed that the generic BATTERY1_SET event was accepted but did not move the aircraft state; the native input did. Existing FSUIPC7 supplies read-only simulator state through `myOffsets.txt`; `ipcInit.lua` starts `KestrelAirLEDs.lua` automatically on simulator connection, without waiting for Ready To Fly or the WASM bridge. The helper writes only the six requested LEDs and returns other LEDs to firmware control. White and red have dim/bright states; cowl LEDs use purple/green. The Baron advertises one battery and one avionics master, so the second numbered controls only operate when the aircraft supports them.

Removed both right-stick wheel range events (right WarBRD-D, BUTTON_21/22). Top RotAir roles follow the retained SimFlight Services ANA reference: NAV, heading bug / gyro adjustment, ADF, selected altitude; pressed rotation retains squawk digits. Restored real ADF tuning instead of the former GTN shortcuts, and restored ADF push / ALT push transponder modes. Heading increments use the running Baron's advertised `B:INSTRUMENT_HEADING_BUG` with wraparound. The second heading ring remains gyro adjustment, not OBS; the Baron's compass slaving governs whether manual gyro changes remain visible. Existing lower-module avionics focus, range, FMS and PulsAIR mappings were preserved.

References: manufacturer XML under `references/rotAIR_SpadNext/` and ANA input reference files under `references/rotAIR-Xplane/`; [Baron manual](https://msfs.dev-pset.com/assets/docs/BKSQ_BaronProfessionalManual.pdf), remote compass and hardware interfaces; [VIRPIL feature-report protocol example](https://github.com/mixMugz/vpc_virpil_fsuipc_led). Installed FSUIPC documentation supplied the read-only offset and Lua startup interfaces.

Backups are under `backups/ana-power-*`. The patch checks all XML outside its explicit edits for equality. SPAD logs confirm the generated profile loaded and all toggle expressions compiled; FSUIPC logs confirm both panels opened and state feedback started automatically. Live native-input tests changed battery 1 and avionics 1 off/on, and both cowl flaps closed/open, then restored every original state. The LED log recorded the corresponding red, white and purple/green transitions on the corrected slots. This validates the simulator-to-LED path; it does not simulate a physical hardware press.

Correction: earlier attempts confused Configurator swatch indices with wire addresses. Those incorrect mappings were replaced using the embedded `PrimaryTypeParams.json` definitions and `ATmegaHandler.CombineLEDs` address conversion in the installed VIRPIL Configurator. Original pink/red belonged to the four power-button positions; the six view buttons were cyan throughout the pre-edit backup. Live feedback now holds all six view addresses at cyan (0xBC) and applies red/white only to the four documented power addresses. View actions remain unchanged.

Later update: CP2 B3/B4 cowl-open duplicate bindings (logical 6/7) removed; both are now unassigned with blue lights (physical LED addresses 3/2). T3/T4 changes await identification of CP2 versus CP3; their existing bindings remain intact.

Confirmed follow-up: T3/T4 are on the Mongoos throttle. T3 logical 38/39 master-power bindings removed. T4 logical 40/41 avionics bindings replaced with B:LANDING_GEAR_PARKINGBRAKE: away/pushed-in = 0 (released), toward pilot = 1 (applied). PRESS only, no release cancellation. CP2 and CP3 switches preserved; CP2 B3/B4 remain unbound and blue. Backup: backups/spares-parking-* .
