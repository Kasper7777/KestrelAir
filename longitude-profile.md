# Citation Longitude — Asobo / Working Title G5000

Profile: **Citation Longitude - Asobo G5000.xml** for MSFS 2024. Built by `build-longitude-profile.py`; `--install` requires SPAD closed, backs up the installed profile and aircraft assignments, and assigns the installed flyable Longitude entries. The existing Citation X profile remains separate.

The two WarBRD sticks, pedals, ATC/window controls, Tobii, drone controls and cabin-camera mode are retained. Either flip lever up disables the main sticks and paints both grips bright pink; both down restores flight controls. Left MiniStick moves the cabin camera and right MiniStick looks around. Keep SFS Monitor closed to use the RotAIR/PulsAIR panels through SPAD.

## Throttle

| Control | Longitude function |
|---|---|
| Left/right thrust levers | Separate engines; existing idle detent retained. Below detent stays idle. Fuel shutoff is on the engine selector, not the rear throttle stop. |
| Grip three-way switches | Per-engine reverse while held: medium/full/low; release restores forward lever position. Inhibited with that engine not burning fuel. Reverse strength needs an engine-running check. |
| Flap lever | Native full flap-handle travel; measured indices 0–3. Forward = up. |
| Nose up/down wheel | Pitch reference in pitch mode; selected vertical speed in VS; selected IAS or Mach in FLC. |
| T4 | Parking brake: toward you = set, away = release. Uses the Longitude's own handle command; generic PARKING_BRAKE_SET was ignored by this aircraft. Both positions verified live. |
| T5 | Cockpit flood 70% / off. |
| T6 | Panel lighting 70% / minimum 5% (measured input clamps its minimum). |
| Engine selector | Left engine: OFF = fuel STOP; other positions = RUN; START also operates starter. |
| T7 / E1 | Unassigned: the Citation X fan-sync and pressure-rate bindings were removed. |

## CP3

| Control | Longitude function |
|---|---|
| B1/B2 | Left/right battery toggle. |
| B3/B4 | Left/right electrical/avionics bus toggle. |
| T1 / ARM | Left/right boost pump. Centre off, either outer position on. |
| T2 | Pitot heat. |
| T3 | Right engine anti-ice. |
| T4 | Both engines anti-ice. |
| T5 / T6 | Wing / stabilizer anti-ice. |
| T7 | Unassigned; no verified separate windshield-heat event. |
| T8 | Seat-belt sign. |
| B6 | Autothrottle button. |
| Rotary selector | Right engine: OFF = STOP; other positions = RUN; START also operates starter. |
| L/R switch | Left/right engine starter. |
| Left inner lever | Speedbrake; forward stowed, back extended. Other CP3 axes unassigned. |
| View buttons, squawk encoder | Existing shortcuts retained; exact instrument-view angles depend on the Longitude. |

## CP2

| Control | Longitude function |
|---|---|
| Gear lever / trim encoders | Unchanged. |
| T1/T2/T3/T4 | Strobes / beacon / nav / taxi lights. |
| T5/T6 | Left/right landing lights. |
| T7/T8 | Left/right generators. |
| T9/T10 | Recognition / logo lights. |
| B1/B2 | APU off / start. B1 is shutdown, rather than the Citation X master switch. |
| B3/B4 | APU generator toggle / APU bleed toggle. |
| B5 | Standby power on; use cockpit switch to turn off. |
| B6 | Emergency lights on; use cockpit switch to turn off. |
| B7/B8 | Left/right engine bleed toggle. |

## RotAIR and PulsAIR

Heading, altitude (both steps), COM/NAV tuning and swaps, course, baro/STD, transponder and speed bug retain the established layout. PulsAIR AP/HDG/NAV/APR/VS/FLC/FD/ALT/VNAV/YD are mapped; nose up/down follows the current vertical mode as above.

PulsAIR **PFD** selects pilot PFD map range; **MFD** selects the pilot MFD GTC map-range control, which is the default. Either ring of the bottom RotAIR RANGE knob changes range. The FMS inner/outer rings operate the pilot MFD GTC right inner/outer knobs; FMS push presses that knob. MENU operates the GTC middle-knob push. PulsAIR ENT presses the GTC right knob; CLR is its long push. These are context-dependent GTC hardware controls, not touchscreen page shortcuts.

FPL, PROC, DIR and other Citation X FMC page shortcuts are unassigned here: the G5000 uses different touchscreen pages. Enter/select those pages on screen. The GTC physical-knob and PFD range event names were checked against [Microsoft's G3000/G5000 source](https://github.com/microsoft/msfs-avionics-mirror/tree/main/src/workingtitle-instruments-g3000).

## Validation and limits

`verify-longitude-profile.py` checks both repository and portable profiles for unique bindings, valid B-event base names from the live Longitude catalog, absence of Citation X commands, a distinct profile ID, and preservation of the complete stick/cabin-camera and pedal device blocks. Results: `verify-longitude-results.txt`.

Heading, altitude and baro actions from the generated XML passed live checks with their original settings restored. With the aircraft parked and engines off, live measurements confirmed forward throttle Set 0/0.5/1 produces input display 20/60/100; speedbrake accepts 0–1; the flap axis reaches native handle indices 0–3; battery/bus/pump/light and selected standby/bleed switch inputs respond. Tested positions were restored, with flaps up and both throttles at idle. The panel-light input enforces a 5% floor. APU generator toggle requires parameter/index 1.

The engines were not started. Starter commands, run/stop during engine operation, reverse levels, autothrottle, exact view angles and visible G5000 range/knob behavior still require physical checks in this aircraft. No claim is made that these have been flight tested.
