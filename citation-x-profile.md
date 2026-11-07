# FlightFX Cessna Citation X (C750) profile

Profile: **Citation X - FlightFX C750.xml**. SPAD selects it automatically for the `Citation X Winglets` and `Citation X` aircraft. It uses the same hardware layout as the Baron GNS 530 + TDS GTNxi 650 profile. The sticks (flight controls, vPilot/BeyondATC, window buttons, drone), rudder pedals, throttle mouse, Tobii and drone keys, CP3 view keys, squawk encoder, trims, gear and all RotAIR radio rotaries work exactly as in the Baron. Everything aircraft-specific has been redone for the Citation X.

Build: `build-citation-x-profile.py --install` (derives the profile from the installed Baron profile). Live check: `verify-citation-x.py`; latest result is in `verify-citation-x-results.txt`.

## Throttle (MongoosT-50CM3)

| Control | Citation X function |
|---|---|
| Left / right thrust lever | The main thrust handles over the levers' full travel: forward of the idle detent = idle to full thrust; from the detent back = idle; hard against the rear stop (past the finger lifts) = fuel CUTOFF, off the stop = RUN |
| Grip three-way switch, left (buttons 5 / 7 / 6) and right (8 / 11 / 9) | Thrust reverser for the left / right engine while held: press down = medium, pull back = full, push forward = low. Release stows it. Only acts with that engine running. Confirmed working by the user 2026-11-05 |
| Flap lever (Z) | Flaps: the aircraft's five flap-handle positions, lever forward = UP, snapping to the nearest |
| T1, T2 | Unassigned (T1 duplicated the parking brake, T2 the gear; the gear lever is on the CP2) |
| T4 | Parking brake (toward you = set) |
| T5 | Cockpit flood lights on / off |
| T6 | Panel lighting (L, centre, R, EL) on / off |
| T7 | Engine (fan) sync on / off |
| E1 encoder | Pressurization rate knob − / + |
| Five-position selector | **Left engine:** OFF = ignition off, R = NORM, L = ignition ON (continuous), BOTH = NORM, **START = starts engine 1** |
| B3 / B6 | Tobii head-tracking toggle (Alt+7) / tracking reset. B6 sends Alt+8 and then Shift+Space, so it works on both the custom and the sim-default keyboard profile (Citation only; the Baron and Bonanzas keep Alt+8 alone) |
| Mini-stick | Mouse pointer; pressing it in (button 13) is the left click. No right click. This is the ka-mouse helper, so it applies in every aircraft |
| Trim, rudder trim, drone, zoom | Unchanged |

## CP3

| Control | Citation X function |
|---|---|
| B1 / B2 (red) | Battery 1 / 2 (LED follows battery state) |
| B3 / B4 (white) | Avionics 1 / 2 (LED follows) |
| T1 (3-position) | Left fuel boost, same positions as the cockpit switch: up ON, centre OFF, down NORM |
| Master ARM (3-position) | Right fuel boost: same positions |
| T2 / T3 | Left / right pitot-static heat |
| T4 | Engine anti-ice, both engines |
| T5 | Wing (slat) anti-ice |
| T6 | Stabilizer anti-ice, both sides |
| T7 | Windshield heat, both sides |
| T8 | Seat belt sign |
| B6 (red, was STEP) | Autothrottle (ATS) engage/disengage button |
| Rotary selector | **Right engine**, same positions as the throttle selector; START starts engine 2 |
| L / R switch | **Engine start**: L starts the left engine, R the right (same command as the selectors' START; ignored while that engine is running) |
| Inner lever, left (was prop) | **Speedbrake**: forward stowed, pull back to extend |
| Inner lever, right (was prop) | Unassigned (reverse is on the CM3 thrust levers) |
| Outer levers (were mixtures) | Unassigned. The CP3 levers do the speedbrake only |
| B8–B12 (views) | Citation instrument views: B8 pilot PFD/instruments (Shift+8), B9 pilot lower panel (Shift+5), B10 co-pilot instruments (Shift+4), B11 FMCs/pedestal (Shift+3), B12 throttle quadrant (Shift+6). The Citation numbers its views differently from the Baron, so these were matched on screen. Press the same button again to return to the pilot view. |
| B13 | Outside view / cockpit toggle (Backspace), as in the Baron |
| E1 | Squawk digit, unchanged |

## CP2

| Control | Citation X function |
|---|---|
| Gear lever | Gear up / down |
| T1 | Strobes (beacon stays on when strobes go off) |
| T2 | Beacon (off also turns strobes off, like the real switch) |
| T3 / T4 | Navigation lights / taxi light |
| T5 / T6 | Left / right landing light |
| T7 / T8 | Left / right generator |
| T9 | Recognition lights |
| T10 | Tail logo floodlight |
| B1 | APU master on / off |
| B2 | APU START (hold briefly) |
| B3 | APU generator on / off |
| B4 | APU bleed air on / off |
| B5 | Standby power on / off |
| B6 | Emergency lights ARM / OFF |
| B7 / B8 | Left / right IRS: NAV / OFF |
| E1–E3 | Elevator, rudder and aileron trim, unchanged |

B1–B8 have no state lights in the Citation; they keep their existing colours.

## RotAIR and PulsAIR

- **Top RotAIR:** NAV radios, heading bug, ADF, altitude preselect and squawk digits as in the Baron. Heading push = heading sync. The second heading ring (was gyro drift) is now the **speed bug**: IAS, or Mach when the speed reference is in Mach. ALT push = transponder ALT, ALT hold = STBY, heading hold = IDENT.
- **Bottom RotAIR:** COM 1/2, course 1/2, baro and STD as before. RANGE (either ring) = PFD/MFD map range. FMS knob (either ring) = FMC NEXT / PREV page; FMS push = MFD ADV. CDI = FMC TUN (radio page), OBS = FMC LEGS. The two hold shortcuts that opened GTN Direct-To and GTN Home in the Baron now give MFD DATA and DSPL MENU.
- **PulsAIR display keys → FMC:** Direct-To = DIR, FPL = FPLN, PROC = DEP/ARR, MENU = IDX, ENT = **EXEC**, CLR = CLR (long press = clear all), OBS = LEGS, VNAV = PERF, MSG = MSG, CDI = TUN.
- **PFD / MFD buttons** now select the side: PFD = pilot (FMC 1, left range), MFD = copilot (FMC 2, right range). The profile starts on PFD.
- **PulsAIR AP module:** AP, HDG, NAV, APR, VS, FLC, FD, ALT and VS wheel as in the Baron. The VNAV key is the autopilot's VNAV, and **BC is now the yaw damper (YD)**, which the Citation needs after take-off far more often than back course.

The SFS Monitor handover still applies: while SFS Monitor is open, SPAD ignores the RotAIR and PulsAIR panels.

## MSFS control profiles and Tobii

MSFS 2024 remembers a control profile per device **per aircraft**, and a newly used aircraft starts on the sim defaults. Read from the sim's saved settings on 2026-11-04: the Baron uses the custom Keyboard and Tobii profiles ("My new general profile"); the Citation was on the defaults (`keyboard_2024_transversal.xml`, `tobii.xml`).

- **Tracking reset (B6):** the default keyboard profile resets tracking on Shift+Space, the custom one on Alt+8; every other key the buttons send is identical in both. In this profile B6 therefore sends both, so it works on either keyboard profile and on any computer with no sim setup. The Baron and Bonanza profiles were left on Alt+8 alone. On the default profile Shift+Space also recentres the cockpit view (MSFS binds both to that key); on the custom profile the Shift+Space half does only that.
- **Head-tracking feel** (sensitivity, forward/back movement) comes from the sim's Tobii profile, which SPAD can't set. To match the Baron: with the Citation loaded, Settings > Controls > Tobii, choose "My new general profile". The choice is stored in the sim's cloud-saved `profile_00` (binary with a checksum; don't hand-edit).

## Thrust levers and reverse (measured 2026-11-05)

- **Hardware** (recorded sweep): full forward 60,000, idle detent about 19,300 (19,274 at rest, 19,301 arriving from forward), full back past the mechanical finger lifts 0. The axis reports the whole travel, so nothing is needed in the VIRPIL software. Left and right levers read identically throughout the sweep.
- **Aircraft** (engine running, parking brake set): the Citation has its own thrust lever driven by `THROTTLE1_SET` / `THROTTLE2_SET`. 0 to 16383 is idle to full forward. Negative values are the reverse lever: nothing happens down to -163; at -164 the reverser deploys (nozzle 100 %, N1 target 77.5 %); it scales to N1 target 87 % at -328; beyond that nothing changes. No EFB setting is involved (`L:VTX_C750_REV_DETENT_ON_AXIS` stays 0).
- **Mapping in SPAD (final, 2026-11-05):** on the raw lever reading `[EVENT:VALUE]` (0-60,000): 20,040-60,000 = idle to full forward, linear; 15,000-20,040 = idle (from forward the levers stop on the detent at about 19,300; coming forward again they have been left anywhere from 16,800 to 18,600); 600-15,000 = idle with fuel RUN; 600 or less, against the rear stop = fuel CUTOFF (`L:ENG_CUTOFF_n` = 0, which moves the cockpit handle back). No throttle command is sent below 15,000, so nothing races the cutoff write.
- **Reversers on the grip switches:** each direction sends a fixed reverse command while held (-168 medium, -328 full, -8 low: reverse lever 51 % / 100 % / 2 %, N1 target about 78 % / 87 % / 68 %) and sets `PROFILE:KA_REV1` / `KA_REV2` to 1, which pauses that lever's forward-thrust command; the release sets it back to 0 and sends the forward value for the lever's position. Earlier versions put reverse behind the detent, then on one button scaled by lever travel; the user chose this three-level switch.
- **Engine-off behaviour handled in the profile:** the reverser buttons only act while that engine is running (`GENERAL ENG COMBUSTION:n` = 1), because with it off the aircraft answers any reverse command by throwing the main handle backwards. At the forward stop SPAD also sets the aircraft's own handle, `B:ENGINE_THROTTLE_n` = 1 (the control the mouse drags), because with the engines off the K event only takes the handle to 0.95.
- **What can't be changed:** the aircraft draws its thrust handle in whole 1 % steps (`L:XMLVAR_ThrottlePosition_n` is rounded to two decimals; `L:C750_THROTTLE_INCREMENT` has no effect, and writing the variable directly is ignored). The engine itself follows every command. With an engine off, its handle also tops out at 0.95 and snaps near the top, and its reverse lever does not lift, so the two handles only match with both engines running.
- **Resolution:** `[LOCAL:...AXIS]` is a whole-number percentage; using it made thrust move in 67 steps and jump at the top. `[EVENT:VALUE]` gives the full reading. Whole-number literals in `Min(1, x)` also make SPAD's NCalc do integer maths, so the formula uses `1.0`.
- **Reverse deadband:** the aircraft ignores reverse commands inside `L:VTX_C750_DETENT_DEADBAND` (1 as loaded: nothing until -164, then the reverse lever jumps to 50 %). SPAD writes 0 with every lever movement, so the reverser deploys at once and the reverse lever and N1 target (68-87 %) follow the levers through their whole travel. Tested on the left engine: deadband 0.2 deploys at -40 (lever 12 %), deadband 0 at -5 (lever 2 %).
- The earlier on/off reverser on the second CP3 lever, which froze the throttles while pulled, is gone.
- **Confirmed from the hardware with both engines running (2026-11-05):** forward travel moved the aircraft's lever smoothly from 0 to 1.00 (N1 target 22 % to 83 %, thrust 270 lb to about 3,900 lb); on the detent it sat at 0 with idle N1; behind the detent the reverse levers rose with travel (57 % at a reading of 13,159, 75 % at 7,399, 100 % at 0), the nozzles went to 100 %, N1 target ran 79 % to 87 % and thrust reached -1,320 lb; pushing forward past the detent stowed the reversers. Speedbrake handle and panels both read 100 % with the CP3 lever back.
- MSFS side: the MSFS profiles assigned to the throttle and CP3 for this aircraft contain no bindings, so nothing competes with SPAD.

## Starting the engines with this layout

1. B1/B2 batteries, B5 standby power, B7/B8 IRS to NAV, B3/B4 avionics.
2. CP2 B1 APU master, B2 APU start; when it's running, B3 APU generator and B4 APU bleed.
3. Boost pumps NORM (switches down), beacon on. Fuel goes to RUN by itself when a CM3 thrust lever is moved; keep the levers on the idle detent for the start.
4. Turn the CP3 rotary to START (right engine), then the throttle selector to START (left engine). FADEC adds fuel at about 30 % N2 and the starter cuts out on its own. Leave the selectors on BOTH (NORM ignition) afterwards.
5. Shutdown: with the aircraft stopped, pull the CM3 levers hard against the rear stop (fuel CUTOFF); back on the detent is RUN.

The starter command only fires if that engine's starter isn't already turning, so moving through START twice won't abort a start. The engines start on APU bleed air: with the APU off, START engages the starter but N2 stays at 0 (seen live 2026-11-04).

## How this was verified (2026-11-04, aircraft parked)

- Every Citation input event and LVAR was read from the running aircraft. Switch positions were confirmed by moving each one and watching the simulator's systems respond, plus the aircraft's own cold/taxi/cruise state files.
- `verify-citation-x.py` reads each binding from the finished profile, executes its exact targets and values against the live aircraft and checks the result: **77 / 77 passed** (lights, electrics, APU start, fuel, anti-ice, ignition, flaps, speedbrake, reversers, fuel cutoff, heading sync, speed bug, transponder, AP modes). The aircraft was restored to its original state afterwards.
- Also tested live: a full engine start with the START command and a shutdown with fuel CUTOFF, reverse thrust deploy/stow with engines running, FMC key events and the map range knob on screen.

**Still to check in flight:** autopilot engage, yaw damper, flight director, VNAV and the ATS button can't engage on the ground with the IRS unaligned. They use the standard autopilot events that this avionics suite reads, so they should work, but they haven't been seen working yet. The range knob and FMC keys were proven through the simulator; SPAD's own dispatch of them gets its first live test when you press the hardware.

**Not mapped on purpose:** PFD navigation source. In this aircraft the source knob toggles only between VOR1 and VOR2 once it leaves FMS, and no command returns it to FMS. A hardware button would strand LNAV. Use the cockpit control for that.

Reference: WT21 H-event list (FMC keys), https://microsoft.github.io/msfs-avionics-mirror/2024/docs/avionics/wt21/h-event-list

## Range step repair (2026-11-07)

The Citation range input events require a step count of 1. SPAD previously sent 0, so knob turns reached the aircraft without changing its range. A direct pilot range increment with value 1 was confirmed working by the user. All 24 range actions across both RotAIR identities and display selections now specify a static parameter of 1. `repair-citation-range.py --installed` patches only those actions with SPAD closed and backs up the installed profile.

## PulsAIR pitch wheel (2026-11-07)

Nose up/down (buttons 11/12) now send AP_PITCH_REF_INC_UP / AP_PITCH_REF_INC_DN instead of AP_VS_VAR_INC / DEC. A live nose-up test changed the Citation pitch reference while leaving its selected vertical speed unchanged. The installed profile is patched with `repair-citation-pitch-wheel.py --installed` while SPAD is closed. Existing range and throttle repairs are preserved.

## Throttle wheel and PulsAIR nose controls: revised mapping

Citation only: CM3 BUTTON_2 (formerly elevator trim up) and BUTTON_3 (formerly elevator trim down), plus PulsAIR BUTTON_11/12, now follow the autopilot mode. In FLC, nose up decreases selected airspeed and nose down increases it; in VS, they increase/decrease selected vertical speed; otherwise they increase/decrease pitch reference. This supersedes the pitch-only mapping above. The CM3 wheel no longer commands manual elevator trim in this aircraft. All eight direction/mode combinations were checked for exactly one matching action. Aircraft-specific FLC/VS behavior still requires physical confirmation.
