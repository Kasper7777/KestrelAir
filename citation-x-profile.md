# FlightFX Cessna Citation X (C750) profile

Profile: **Citation X - FlightFX C750.xml**. SPAD selects it automatically for the `Citation X Winglets` and `Citation X` aircraft. It uses the same hardware layout as the Baron GNS 530 + TDS GTNxi 650 profile. The sticks (flight controls, vPilot/BeyondATC, window buttons, drone), rudder pedals, throttle mouse, Tobii and drone keys, CP3 view keys, squawk encoder, trims, gear and all RotAIR radio rotaries work exactly as in the Baron. Everything aircraft-specific has been redone for the Citation X.

Build: `build-citation-x-profile.py --install` (derives the profile from the installed Baron profile). Live check: `verify-citation-x.py`; latest result is in `verify-citation-x-results.txt`.

## Throttle (MongoosT-50CM3)

| Control | Citation X function |
|---|---|
| Left / right throttle | Thrust levers 1 / 2 (ignored while the reversers are deployed) |
| Flap lever (Z) | Flaps: the aircraft's five flap-handle positions, lever forward = UP, snapping to the nearest |
| Gear buttons | Gear up / down |
| T4 | Parking brake (toward you = set) |
| T5 | Cockpit flood lights on / off |
| T6 | Panel lighting (L, centre, R, EL) on / off |
| T7 | Engine (fan) sync on / off |
| E1 encoder | Pressurization rate knob − / + |
| Five-position selector | **Left engine:** OFF = ignition off, R = NORM, L = ignition ON (continuous), BOTH = NORM, **START = starts engine 1** |
| B3 / B6 | Tobii head-tracking toggle (Alt+7) / eye-tracking reset (Alt+8): the Baron's macros, unchanged (one macro holding Alt + digit) |
| Trim, rudder trim, mouse, drone, zoom | Unchanged |

## CP3

| Control | Citation X function |
|---|---|
| B1 / B2 (red) | Battery 1 / 2 (LED follows battery state) |
| B3 / B4 (white) | Avionics 1 / 2 (LED follows) |
| T1 (3-position) | Left fuel boost: up ON, centre NORM, down OFF |
| Master ARM (3-position) | Right fuel boost: same positions |
| T2 / T3 | Left / right pitot-static heat |
| T4 | Engine anti-ice, both engines |
| T5 | Wing (slat) anti-ice |
| T6 | Stabilizer anti-ice, both sides |
| T7 | Windshield heat, both sides |
| T8 | Seat belt sign |
| B6 (red, was STEP) | Autothrottle (ATS) engage/disengage button |
| Rotary selector | **Right engine**, same positions as the throttle selector; START starts engine 2 |
| Inner lever, left (was prop) | **Speedbrake**: forward stowed, pull back to extend |
| Inner lever, right (was prop) | **Thrust reversers, both engines**: pull below 10 % to deploy, push above 15 % to stow |
| Outer levers (were mixtures) | **Fuel RUN / CUTOFF** left / right: below 10 % is CUTOFF |
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

## Starting the engines with this layout

1. B1/B2 batteries, B5 standby power, B7/B8 IRS to NAV, B3/B4 avionics.
2. CP2 B1 APU master, B2 APU start; when it's running, B3 APU generator and B4 APU bleed.
3. Outer CP3 levers forward (fuel RUN), boost pumps NORM, beacon on.
4. Turn the CP3 rotary to START (right engine), then the throttle selector to START (left engine). FADEC adds fuel at about 30 % N2 and the starter cuts out on its own. Leave the selectors on BOTH (NORM ignition) afterwards.
5. Shutdown: outer levers back to CUTOFF.

The starter command only fires if that engine's starter isn't already turning, so moving through START twice won't abort a start.

## How this was verified (2026-11-04, aircraft parked)

- Every Citation input event and LVAR was read from the running aircraft. Switch positions were confirmed by moving each one and watching the simulator's systems respond, plus the aircraft's own cold/taxi/cruise state files.
- `verify-citation-x.py` reads each binding from the finished profile, executes its exact targets and values against the live aircraft and checks the result: **77 / 77 passed** (lights, electrics, APU start, fuel, anti-ice, ignition, flaps, speedbrake, reversers, fuel cutoff, heading sync, speed bug, transponder, AP modes). The aircraft was restored to its original state afterwards.
- Also tested live: a full engine start with the START command and a shutdown with fuel CUTOFF, reverse thrust deploy/stow with engines running, FMC key events and the map range knob on screen.

**Still to check in flight:** autopilot engage, yaw damper, flight director, VNAV and the ATS button can't engage on the ground with the IRS unaligned. They use the standard autopilot events that this avionics suite reads, so they should work, but they haven't been seen working yet. The range knob and FMC keys were proven through the simulator; SPAD's own dispatch of them gets its first live test when you press the hardware.

**Not mapped on purpose:** PFD navigation source. In this aircraft the source knob toggles only between VOR1 and VOR2 once it leaves FMS, and no command returns it to FMS. A hardware button would strand LNAV. Use the cockpit control for that.

Reference: WT21 H-event list (FMC keys), https://microsoft.github.io/msfs-avionics-mirror/2024/docs/avionics/wt21/h-event-list
