Installed in **Baron - GNS 530 + TDS GTNxi 650** on 2026-10-31.

| CP2 control | Assignment |
|---|---|
| Large gear lever up / down | Gear up / down; centre unused |
| T1 | Strobes |
| T2 | Beacon |
| T3 | Navigation lights |
| T4 | Taxi lights |
| T5 | Landing lights |
| T6 | Right landing light |
| T7 | Left alternator |
| T8 | Right alternator |

Correction confirmed from live testing: CP2 toggles return to centre, so ON/OFF assignments now run only on directional PRESS events. All CP2 RELEASE-to-OFF actions were removed. T5 controls the **left landing light only**, per user request; the CP3 landing-light assignments were removed. T6 writes the documented `LVAR:bksq_MasterPanelLights` switch.

Throttle front toggles now use verified IDs T5 42/43 for flood (`LVAR:bksq_MasterGlareshieldLights`), T6 44/45 for left pitot and T7 46/47 for right pitot. Pitot actions use the manufacturer's indexed `PITOT_HEAT_TOGGLE` event with state conditions, avoiding repeated toggles and release cancellation. Encoders now set documented `LVAR:BKSQ_IgnitionPosition_1/2` using bounded 0-5 increment/decrement expressions, because standard magneto events were received by MSFS but did not move the keys. Working Tobii, gear and axes were preserved. Backup: `backups/latched-switches-20261031-192331/`.

Gear-up button 1 was verified against a live HID report with the physical lever fully up. Gear down uses button 3. T1-T8 use paired inputs 17-32; release of each ON input also sends OFF, covering switches without an emulated OFF input.

Throttle mode 1: B3 (above B6), logical button 56, sends Alt+7 to toggle Tobii tracking. B6, logical button 59, sends Alt+8 to reset Tobii tracking. These match the preserved MSFS keyboard assignments. `TargetWindow` was removed after the live log showed `Failed to switch to AceApp`; the macros now send keys to the foreground cockpit. The original direct SimConnect tracking events were rejected by SPAD as command-not-found and have been removed. Other firmware banks do not receive these tracking assignments.

Throttle encoders: verified Configurator IDs E1 CCW49/CW50 and E2 CCW52/CW53 now send `MAGNETO1_DECR/INCR` and `MAGNETO2_DECR/INCR`. Removed stale throttle alternator assignments and obsolete encoder actions on mode-bank buttons. CP2 lights use advertised `B:LIGHTING_NAV_1`, `BEACON_1`, `STROBE_1`, `TAXI_1`, and both `LANDING_1/2` inputs with explicit 0/1 writes. Alternators use advertised `B:ELECTRICAL_ALTERNATOR_1/2` with explicit 0/1 writes. T6 uses `PANEL_LIGHTS_SET` with an explicitly Static parameter. Working CP2 gear assignments were preserved. Backup: `backups/encoder-cp2-tobii-20261031-191552/`.

Both WarBRD-D sticks now have X/Y pitch-and-roll assignments: right device index 0, left device index 1. CP3 X/Y remain propellers and its outer RX/RY lever pair controls mixtures, as clarified by the user. Mixtures are axis VALUE events driving the documented Black Square variables as axis percentages, not rotary increment/decrement inputs. Latest corrective backup: `backups/tobii-mixture-correction-20261031-191040/`.

Both throttles and propeller axes now have inversion disabled. A live report with all six levers physically forward showed X/Y on the throttle and X/Y/RX/RY on the CP3 at 60000. Mixtures use `LVAR:BKSQ_MixtureLeverPosition_1/2`, `SetEventValue_AxisPercent`, replacing generic AXIS_MIXTURE actions. Black Square documents these variables at 0-100 in the [Baron Professional manual](https://msfs.dev-pset.com/assets/docs/BKSQ_BaronProfessionalManual.pdf), Primary Control Variables and mixture troubleshooting.

Throttle colours, modes 1-5: blue, green, yellow, orange, purple. All six throttle button LEDs follow the mode colour. Saved VIRPIL export was checked against each RGB value.

Project backup: `backups/cp2-setup-20261031-184722/`, including SPAD profiles/configuration, VIRPIL backups, the final SPAD profile and `final-throttle.device.vpcprofile`. SPAD was restarted and its log confirms this Baron profile and CP2 were activated, MSFS connected and the two mixture variables recognised. Physical cockpit response for every switch/button has not been verified.
