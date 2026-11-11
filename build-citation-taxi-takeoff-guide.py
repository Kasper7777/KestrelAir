"""Citation X illustrated normal checklist: Before Start through Shutdown (A4 portrait, for print).

Every item is printed word for word, in order, from pages 1-5 of the FlightFX "Citation X Full Checklist
(Printer Friendly)" (https://bit.ly/msfsffx-c750-checklists): 169 items in 15 sections, asserted below.
Photos are genuine MSFS 2024 captures of the FlightFX C750 (tt-*.png, 2026-11-10; displays captured powered
and aligned). Cessna logo: Wikimedia Commons "Cessna Logo.svg" (public domain).

Run: uv run --with reportlab --with pillow --with pymupdf --with svglib python build-citation-taxi-takeoff-guide.py
"""
from io import BytesIO
from math import atan2, cos, hypot, pi, sin
import re
from pathlib import Path

import pymupdf
from PIL import Image, ImageEnhance
from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from svglib.svglib import svg2rlg

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'citation-guide-assets'
OUTPUT = ROOT / 'Citation_X_Illustrated_Checklist.pdf'
W, H = 595.28, 841.89               # A4 portrait
M = 30

for name, file in [('UI', 'segoeui.ttf'), ('UI-SB', 'seguisb.ttf'), ('UI-B', 'segoeuib.ttf'),
                   ('UI-BL', 'seguibl.ttf'), ('UI-L', 'segoeuil.ttf')]:
    pdfmetrics.registerFont(TTFont(name, rf'C:\Windows\Fonts\{file}'))

SKY = HexColor('#1EA7E8')           # the sky blue of the arrows and badges
SKY_DEEP = HexColor('#0B78BE')      # sky-blue text on white (prints with contrast)
SKY_TINT = HexColor('#EAF7FE')
SKY_LINE = HexColor('#BFE6FA')
NAVY = HexColor('#0B2238')
INK = HexColor('#1C2B39')
GREY = HexColor('#5A6B7B')

ITEM = ParagraphStyle('item', fontName='UI-B', fontSize=12, leading=14.5, textColor=NAVY)
RESP = ParagraphStyle('resp', fontName='UI-B', fontSize=12, leading=14.5, textColor=SKY_DEEP)
HOW = ParagraphStyle('how', fontName='UI', fontSize=10.5, leading=13.5, textColor=INK)

# ---- photos ---------------------------------------------------------------------------------------
QUAD, AFT, GLARE, LOWER = 'tt-quadrant.png', 'tt-aft-pedestal.png', 'tt-glareshield-powered.png', 'tt-lower-panels.png'
DISP, CTRL, PFDV, RADIO, COVER = ('tt-displays.png', 'tt-ctrlpos.png', 'tt-pfd-eicas-ctrlpos.png',
                                  'radio-mode.png', 'tt-cover.png')

# Targets in original 2560x1440 capture pixels, measured on gridded captures.
FLAP_HANDLE, FLAP_15, SPEEDBRAKE, PITCH_TRIM, TO_MC = (1715, 632), (1664, 836), (990, 75), (891, 410), (1354, 340)
TAXI_LT, LAND_L, LAND_R = (1370, 944), (1456, 944), (1544, 944)
PARK_BRAKE, RUDDER_TRIM, AIL_TRIM = (1880, 1292), (1760, 1110), (1555, 940)
YD, MTRIM, REV_LIGHTS = (1714, 421), (1714, 474), (2100, 490)
CAGE_KNOB = (854, 285)
PITOT_L, PITOT_R = (222, 530), (316, 530)
ENG_L, ENG_R, STAB_L, STAB_R, SLAT = (239, 868), (333, 868), (410, 868), (503, 868), (597, 868)
PASS_SAFETY, ALT_SEL, NAV_LT, BEACON = (1147, 712), (1514, 866), (1036, 868), (1029, 712)
CTRL_BTN, RUDDER_BAR = (1290, 1098), (1347, 846)
EICAS_FLAPS, EICAS_STAB, CAS_LIST, FAN_TO, FAN_TAPE = (1112, 927), (1072, 813), (1126, 765), (1088, 477), (1100, 575)
PFD_ATT, PFD_HDG, PFD_PITCH10 = (797, 505), (840, 652), (790, 474)
RADIO_KEY, RADIO_KNOB = (794, 1032), (1033, 1216)
MFD_WX = (456, 836)


def shot(name, crop, label, marks=(), lift=1.18):
    """marks: (badge, target or [targets], badge position as a fraction of the crop[, 'bracket'])."""
    return dict(name=name, crop=crop, label=label, marks=list(marks), lift=lift)


# ---- the checklist (word for word from FlightFX page 3) -------------------------------------------
PHASES = ['BEFORE START', 'APU START', 'STARTING ENGINES', 'CROSS BLEED',
          'BEFORE TAXI', 'TAXI', 'BEFORE TAKEOFF', 'TAKEOFF',
          'AFTER TAKEOFF', 'CRUISE', 'DESCENT', 'APPROACH',
          'BEFORE LANDING', 'LANDING', 'SHUTDOWN']
PHASE_NAMES = ['Before Start', 'APU Start', 'Starting Engines', 'Starting Second Engine: Cross Bleed Method',
               'Before Taxi', 'Taxi', 'Before Takeoff', 'Takeoff',
               'After Takeoff/Climb', 'Cruise', 'Descent', 'Approach',
               'Before Landing', 'Landing', 'Shutdown']
STAGES = [('ENGINE START', [0, 1, 2, 3]), ('DEPARTURE', [4, 5, 6, 7]),
          ('IN FLIGHT', [8, 9, 10, 11]), ('ARRIVAL', [12, 13, 14])]
EXPECTED = [20, 14, 22, 14, 12, 7, 18, 4, 10, 3, 7, 13, 6, 6, 13]   # FlightFX Full Checklist pages 1-5

PAGES = [
 dict(phase=4, part='1 of 3', title='Flight controls, flaps, speed brake',
  rows=[[
   shot(QUAD, (880, 0, 1860, 1250), 'THROTTLE QUADRANT  ·  Shift+6', [
    ('5', SPEEDBRAKE, (.30, .24)), ('2', FLAP_HANDLE, (.62, .40)), ('4', FLAP_15, (.62, .72))]),
   shot(CTRL, (1010, 380, 1500, 1140), 'EICAS  ·  Shift+4', [
    ('1', CTRL_BTN, (.80, .86)), ('3', RUDDER_BAR, (.92, .64)), ('4', EICAS_FLAPS, (.38, .70))]),
  ]],
  steps=[
   ('1', 'Flight Controls', 'FREE / CORRECT EICAS INDICATIONS',
    'Press the bezel button under <b>CTRL POS</b> (4th button). Move the yoke and rudder fully each way: the AILERON, ELEVATOR and RUDDER markers follow smoothly.'),
   ('2', 'Flaps/Slats Lever', 'UP', 'The SLATS FLAPS handle right of the throttles: fully forward.'),
   ('3', 'Rudder Control/EICAS', 'VERIFY UPPER RUDDER REMAINS CENTERED WITH FLAPS UP',
    'Feet off the pedals: the RUDDER marker on CTRL POS sits on the centre tick.'),
   ('4', 'Flaps/Slats', 'SET FOR TAKEOFF / CHECK EICAS INDICATIONS',
    'Pull the handle back to <b>15</b>. EICAS FLAPS reads 15. Then press the button under NORM (1st button).'),
   ('5', 'Speed Brakes', 'CHECK / STOWED / EICAS INDICATIONS',
    'Lever left of the throttles fully forward at 0. Your CP3 speedbrake lever fully forward too.'),
  ]),

 dict(phase=4, part='2 of 3', title='Alignment, warnings, standby gyro',
  rows=[[
   shot(PFDV, (590, 360, 1030, 780), 'PILOT PFD  ·  aligned, no flags', [
    ('6', PFD_ATT, (.13, .52))]),
   shot(DISP, (610, 25, 940, 340), 'STANDBY ATTITUDE  ·  Shift+4', [('8', CAGE_KNOB, (.13, .82))], lift=1.3),
  ], [
   shot(DISP, (1030, 690, 1350, 870), 'EICAS MESSAGES  ·  Shift+4', [('7', CAS_LIST, (.90, .78))]),
  ]],
  steps=[
   ('6', 'AHRS or IRS', 'ALIGNED / NO FLAGS',
    'Attitude and heading showing on both PFDs. No red HDG FAIL, ATT FAIL or FD FAIL flags.'),
   ('7', 'EICAS', 'CHECK (all messages either normal or resolved)',
    'Cyan PARK BRAKE ON and NO TAKEOFF are expected at this point.'),
   ('8', 'Standby Gyro', 'UNCAGED', 'The PULL TO CAGE knob is pushed in. No CAGE flag, horizon level.'),
  ]),

 dict(phase=4, part='3 of 3', title='Anti-ice, pressurization, cabin',
  rows=[[
   shot(LOWER, (830, 300, 1730, 1010), 'RIGHT LOWER PANEL  ·  Shift+5', [
    ('10', ALT_SEL, (.56, .94)), ('11', PASS_SAFETY, (.46, .58))]),
  ]],
  steps=[
   ('9', 'Anti-Ice Systems', 'AS REQUIRED',
    'Only in icing conditions: visible moisture at +10 °C or colder. The switch check is item 2 of Before Takeoff.'),
   ('10', 'Pressurization ALT SEL', 'NORM', 'The ALT SEL switch at the bottom of the PRESSURIZATION panel: DOWN.'),
   ('11', 'Passenger Advisory Lights', 'PASS SAFETY', 'The SEAT BELT LTS switch: DOWN. (Up = seat belts, middle = off.)'),
   ('12', 'Seats/Seat Belts/Shoulder Harnesses/Aft Divider Sliding Doors', 'CHECK/SECURE/LATCHED OPEN',
    'Nothing to click in the sim. Check it, say it, tick it.'),
  ]),

 dict(phase=5, part='', title='Lights, brakes, steering',
  rows=[[
   shot(QUAD, (1240, 800, 1640, 1060), 'TAXI LIGHT  ·  Shift+6', [('1', TAXI_LT, (.10, .365))]),
   shot(GLARE, (1960, 330, 2300, 640), 'THRUST REVERSER  ·  Shift+2', [('6', REV_LIGHTS, (.08, .29))], lift=1.1),
  ], [
   shot(AFT, (1420, 860, 2040, 1420), 'PARKING BRAKE  ·  Shift+7', [('3', PARK_BRAKE, (.25, .82))], lift=1.45),
   shot(LOWER, (880, 600, 1260, 950), 'BEACON + NAV  ·  Shift+5', [('1', [BEACON, NAV_LT], (.18, .45), 26)]),
  ]],
  steps=[
   ('1', 'Exterior Lights', 'AS REQUIRED', 'TAXI LIGHT up. Beacon: GND REC / ANTI-COLL to the middle. NAV up.'),
   ('2', 'Brakes', 'APPLY and HOLD', 'Press and hold both toe brakes.'),
   ('3', 'Parking Brake', 'RELEASE', 'Push the T-handle at the back of the pedestal DOWN. PARK BRAKE ON goes out.'),
   ('4', 'Brakes', 'CHECK', 'Roll forward slowly at idle, then brake: the aircraft slows evenly.'),
   ('5', 'Nose Wheel Steering', 'CHECK', 'Steer left and right with the rudder pedals at walking pace.'),
   ('6', 'Thrust Reversers', 'CHECK / STOWED', 'ARM, UNLOCK and DEPLOY all out. Reverser levers fully down.'),
   ('7', 'Flight Instruments', 'CHECK', 'In the turns, heading moves the right way on both PFDs and the standby.'),
  ]),

 dict(phase=6, part='1 of 4', title='Anti-ice check (icing only)',
  rows=[[
   shot(LOWER, (70, 300, 700, 1010), 'ANTI-ICE PANEL  ·  Shift+5', [
    ('2', [ENG_L, ENG_R, STAB_L, STAB_R, SLAT], (.10, .985), 34),
    ('5', [PITOT_L, PITOT_R], (.30, .12), 34)]),
   shot(DISP, (1040, 380, 1340, 1010), 'EICAS  ·  Shift+4', [
    ('3', FAN_TO, (.75, .27)), ('4', CAS_LIST, (.80, .70))]),
  ]],
  steps=[
   ('1', 'Anti-Ice Systems (if required)', 'CHECK', 'No icing? Do item 5 only, then go to the next page.'),
   ('2', 'LH and RH ENGINE, STABILIZER, and SLAT ANTI-ICE', 'ON / CHECK COLD MESSAGES (2-3 minutes)',
    'All five switches UP. Cyan COLD messages appear on EICAS.'),
   ('3', 'Throttles', 'APPROXIMATELY 40% N1', 'Brakes held. Advance both levers until FAN% reads about 40.'),
   ('4', 'Check CAS', 'COLD (messages go out, No HOT or LEAK messages)', 'Watch the EICAS message list.'),
   ('5', 'ANTI-ICE Switches', 'AS REQUIRED. It is suggested that Pitot/Static Anti-Ice be employed for all flights', 'PITOT/STATIC LH and RH up.'),
   ('6', 'Throttles', 'IDLE', 'Both levers back to idle.'),
  ]),

 dict(phase=6, part='2 of 4', title='Takeoff configuration',
  rows=[[
   shot(QUAD, (770, 0, 1850, 1250), 'THROTTLE QUADRANT  ·  Shift+6', [
    ('9', SPEEDBRAKE, (.34, .24)), ('10', PITCH_TRIM, (.10, .53)), ('8', FLAP_15, (.62, .72))]),
   [shot(DISP, (1030, 690, 1340, 950), 'EICAS  ·  Shift+4', [
     ('10', EICAS_STAB, (.30, .64)), ('8', EICAS_FLAPS, (.47, .90))]),
    shot(AFT, (1460, 860, 1880, 1200), 'TRIMS  ·  Shift+7', [
     ('10', RUDDER_TRIM, (.30, .86))], lift=1.45)],
  ]],
  steps=[
   ('7', 'Seats/Seat Belts/Shoulder Harnesses/Aft Divider Sliding Doors', 'CHECK / SECURE / LATCHED OPEN',
    'Nothing to click. Tick it.'),
   ('8', 'Flaps/Slats', 'SET FOR TAKEOFF', 'Handle at 15. EICAS FLAPS reads 15. V-speeds only appear with flaps 15.'),
   ('9', 'Speed Brakes', 'RETRACTED (0%)', 'Lever fully forward.'),
   ('10', 'Trims', 'SET FOR TAKEOFF',
    'Pitch trim until the EICAS STAB pointer is in the T/O band. Rudder trim knob on its centre mark; aileron trim switch beside it centred.'),
  ]),

 dict(phase=6, part='3 of 4', title='Yaw damper, briefing, transponder',
  rows=[[
   shot(GLARE, (1240, 300, 1800, 600), 'GUIDANCE PANEL  ·  Shift+2', [('11', [(1680, 421), (1680, 474)], (.955, .50), 36)], lift=1.1),
  ], [
   shot(RADIO, (745, 865, 1120, 1290), 'LEFT RADIO  ·  Shift+3', [('14', [RADIO_KEY, (900, 1032)], (.60, .53), 26)]),
   shot(DISP, (370, 560, 840, 1010), 'PILOT MFD  ·  Shift+4', [('13', MFD_WX, (.62, .30))]),
  ]],
  steps=[
   ('11', 'Yaw Damper and Mach Trim', 'CHECK ON', 'Press YD and M TRIM: each shows its lit bar.'),
   ('12', 'Crew Briefing', 'COMPLETE', 'Runway, departure, V1 / VR / V2, what you do if it goes wrong.'),
   ('13', 'Radar', 'AS REQUIRED', 'Weather radar only if there is weather. The MFD shows WX/OFF when it is off.'),
   ('14', 'Transponder', 'TA/RA', 'Press the left key level with the code (4th down), then turn the knob until TA/RA shows.'),
  ]),

 dict(phase=6, part='4 of 4', title='Pitot heat, lights, final check',
  rows=[[
   [shot(LOWER, (90, 420, 420, 660), 'PITOT / STATIC  ·  Shift+5', [('15', [PITOT_L, PITOT_R], (.07, .62), 34)]),
    shot(QUAD, (1240, 800, 1640, 1060), 'LANDING LIGHTS  ·  Shift+6', [('16', [LAND_L, LAND_R], (.66, .14), 34)])],
   shot(DISP, (1030, 390, 1500, 1010), 'EICAS  ·  Shift+4', [
    ('17', FAN_TAPE, (.42, .30)), ('18', CAS_LIST, (.62, .78))]),
  ]],
  steps=[
   ('15', 'LH and RH PITOT STATIC Anti Ice Switches', 'BOTH ON', 'Both switches UP.'),
   ('16', 'Exterior Lights', 'AS REQUIRED', 'LANDING LIGHT LH and RH up. GND REC / ANTI-COLL up for strobes.'),
   ('17', 'Engine Instruments', 'CHECK', 'FAN%, ITT, oil temperature and pressure normal on both engines.'),
   ('18', 'EICAS', 'CHECK', 'No NO TAKEOFF, amber or red message. Ready for takeoff.'),
  ]),

 dict(phase=7, part='', title='Thrust, release, rotate',
  rows=[[
   shot(QUAD, (1090, 270, 1560, 700), 'THRUST LEVERS  ·  Shift+6', [('1', TO_MC, (.80, .10))]),
  ], [
   shot(DISP, (1040, 420, 1200, 700), 'FAN% (N1)', [('3', FAN_TO, (.80, .55))]),
   shot(PFDV, (590, 360, 1030, 780), 'PILOT PFD', [('4', PFD_PITCH10, (.04, .97))]),
  ]],
  steps=[
   ('1', 'Throttles', 'TO/MC DETENT', 'Lined up and cleared: both levers forward into TO/MC, the 2nd notch (MAX, TO/MC, CLB, CRU).'),
   ('2', 'Brakes', 'RELEASE', 'Let go of the toe brakes.'),
   ('3', 'EICAS', 'CHECK NORMAL INDICATIONS, N1 matches command', 'FAN% rises to the T/O value shown above the tapes.'),
   ('4', 'Elevator Control', 'ROTATE AT VR to achieve 13 deg initial pitch',
    'At your VR (FMS TAKEOFF DATA), pull back smoothly to just above the 10° line.'),
  ]),
]

# ---- engine-start sections (FlightFX Full Checklist pages 1-2) -----------------------------------
RAD, APU, LEFTP, TAB = 'tt-radios.png', 'tt-apu-panel.png', 'tt-left-panel.png', 'tt-tablet-ground.png'
HIGHR, HIGHS, THR6 = 'tt-right-panel-high.png', 'tt-right-side-high.png', 'refresh-view-6.png'

LOAD_SHED, LH_GEN, BATT1, BATT2, RH_GEN = (177, 285), (246, 285), (318, 285), (378, 285), (447, 285)
AVIONICS, EICAS_PWR, BOOST_L, START_L, START_R, STBY_PWR = (591, 285), (654, 285), (222, 414), (375, 414), (507, 414), (621, 519)
FMS_GPS_LOAD, FMS_PERF, FMS_FPL, RTU_ATC = (1234, 428), (826, 557), (1062, 557), (880, 1012)
APU_BLEED, APU_GEN, APU_VOLTS = (1227, 401), (1474, 477), (1372, 728)
APU_LIGHTS = [(1367, 392), (1367, 443)]
APU_DISENG, APU_START, APU_TEST, APU_MASTER = (1231, 837), (1299, 864), (1389, 911), (1448, 928)
EMERG_LT, CTR_XFER = (810, 920), [(1130, 1080), (1225, 1080)]
IRS_A, IRS_B = (1318, 600), (1070, 855)
CHOCKS, MAIN_DOOR, GPU_BTN = (1196, 334), (1206, 422), (1898, 766)
PAC_ISOL, L_BLD, R_BLD, PAC_BLEED_SEL = (2265, 1154), (2057, 1248), (2442, 1248), (1721, 1206)
APU_AMPS = (1313, 227)
ENG_BTN, OIL_PSI, ITT_TAPE, HYD_PSI, FUEL_QTY, MFD_EICAS_SYS = (1350, 1098), (1391, 486), (1220, 570), (1347, 863), (1353, 625), (676, 968)
IDLE_LBL, TL_R = (1316, 636), (1433, 665)

START_PAGES = [
 dict(phase=0, part='1 of 4', title='Power up',
  rows=[[
   shot(RAD, (150, 150, 760, 640), 'DC POWER PANEL  ·  Shift+3', [
    ('1', STBY_PWR, (.975, .74)), ('3', [BATT1, BATT2], (.37, .05), 34), ('4', EICAS_PWR, (.965, .30))]),
  ], [
   shot(LEFTP, (700, 830, 1040, 1060), 'LIGHTS  ·  Shift+8', [('2', EMERG_LT, (.12, .85))], lift=1.12),
  ]],
  steps=[
   ('1', 'STBY PWR Switch', 'ON', 'Bottom right of the DC POWER panel: switch UP.'),
   ('2', 'EMERG LT Switch', 'ARM', 'Left side panel, LIGHTS: set the EMERG LT switch to ARM.'),
   ('3', 'BATT 1 and BATT 2 Switches', 'ON', 'Both switches UP.'),
   ('4', 'EICAS POWER Switch', 'ON', 'Right-hand switch under AVIONICS POWER: UP. This powers the engine display.'),
  ]),
 dict(phase=0, part='2 of 4', title='APU, avionics, IRS, FMS',
  rows=[[
   shot(RAD, (500, 170, 720, 360), 'AVIONICS POWER  ·  Shift+3', [('6', AVIONICS, (.10, .80))]),
   shot(RAD, (790, 230, 1290, 560), 'FMS  ·  Shift+3', [('8', FMS_GPS_LOAD, (.70, .90))]),
  ], [
   shot(AFT, (950, 520, 1450, 900), 'IRS SELECTORS  ·  Shift+7', [('7', IRS_A, (.93, .10)), ('7', IRS_B, (.06, .95))], lift=1.4),
  ]],
  steps=[
   ('5', 'APU START', 'REFER TO APU START CHECKLIST', 'Start the APU now: see the APU START pages.'),
   ('6', 'AVIONICS POWER Switch', 'ON', 'Left-hand switch under AVIONICS POWER: UP. The flight displays come on.'),
   ('7', 'IRS', 'ALIGN / NAV', 'Both IRS selectors behind the throttles to NAV. Stay parked while they align.'),
   ('8', 'FMS', 'INSERT PRESENT POSITION', 'NAV IDENT page: right key 4 opens POSITION INIT. When GPS 1 POS shows, press right key 3 (LOAD).'),
  ]),
 dict(phase=0, part='3 of 4', title='Parking brake, doors, cabin',
  rows=[[
   shot(TAB, (600, 40, 2020, 1400), 'TABLET  ·  Ground page', [('10', CHOCKS, (.55, .06)), ('11', MAIN_DOOR, (.18, .40))], lift=1.0),
   [shot(AFT, (1500, 1000, 2040, 1420), 'PARKING BRAKE  ·  Shift+7', [('9', PARK_BRAKE, (.30, .85))], lift=1.45),
    shot(LOWER, (880, 600, 1260, 950), 'BEACON + NAV  ·  Shift+5', [('14', [BEACON, NAV_LT], (.18, .45), 26)])],
  ]],
  steps=[
   ('9', 'Parking Brake', 'VERIFY SET', 'T-handle at the back of the pedestal is UP. Cyan PARK BRAKE ON on EICAS.'),
   ('10', 'Wheel Chocks', 'REMOVED - Use Settings page in Tablet', 'Tablet home, Ground: untick Chocks. Untick Instrument Covers and Engine Cover too.'),
   ('11', 'Cabin Door', 'CLOSE / LOCK', 'Tablet, Ground: Main Door shows an empty circle (closed).'),
   ('12', 'Passenger Briefing', 'COMPLETED', 'Nothing to click. Tick it.'),
   ('13', 'Seats/Belts/Harnesses/Pedals', 'ADJUST / SECURE', 'Nothing to click. Tick it.'),
   ('14', 'Exterior Lights', 'AS REQUIRED', 'NAV up. Beacon: GND REC / ANTI-COLL to the middle before the engines start.'),
  ]),
 dict(phase=0, part='4 of 4', title='Checks and FMS programming',
  rows=[[
   shot(DISP, (1030, 390, 1500, 1010), 'EICAS  ·  Shift+4', [('15', CAS_LIST, (.62, .80)), ('18', FUEL_QTY, (.93, .24))]),
   [shot(RAD, (790, 880, 1130, 1200), 'LEFT RADIO  ·  Shift+3', [('17', RTU_ATC, (.80, .82))]),
    shot(LEFTP, (1050, 960, 1300, 1160), 'CTR WING XFER  ·  Shift+8', [('19', CTR_XFER, (.10, .30), 40)], lift=1.12)],
  ], [
   shot(RAD, (780, 470, 1300, 640), 'FMS KEYS  ·  Shift+3', [('20', FMS_PERF, (.34, .12)), ('16', FMS_FPL, (.72, .12))]),
  ]],
  steps=[
   ('15', 'EICAS', 'CHECK for warnings', 'Read the message list. No red messages; understand every amber one.'),
   ('16', 'ATIS/Clearance/FMS', 'AS REQUIRED. Program FMS', 'Press FPL: origin, destination, runway, departure and route (or load from SimBrief).'),
   ('17', 'Instruments/Avionics/FLPN', 'Set course bugs and pointers as required for departure. COMM/NAV/ADF radios tuned and verified. Transponder set to STBY',
    'CRS and HDG knobs on the guidance panel. Frequencies on the radio units. Transponder in STBY for now.'),
   ('18', 'Fuel Quantity/Balance', 'CHECK - Maximum intentional fuel imbalance is 400 lbs', 'EICAS FUEL: left and right tank figures within 400 lbs of each other.'),
   ('19', 'CTR WING XFER Switches', 'NORM / AS REQUIRED', 'Left side panel, under FUEL: both switches DOWN to NORM.'),
   ('20', 'V-Speeds', 'SET - TAKEOFF DATA FMS page', 'Press PERF, then TAKEOFF DATA: enter the conditions to get V1, VR, V2.'),
  ]),

 dict(phase=1, part='1 of 2', title='APU: power and test',
  rows=[[
   shot(APU, (1100, 270, 1540, 1010), 'APU PANEL  ·  Shift+9', [
    ('3', APU_DISENG, (.08, .70)), ('4', APU_MASTER, (.97, .80)), ('5', APU_TEST, (.80, .66)),
    ('6', APU_GEN, (.95, .40)), ('7', APU_VOLTS, (.22, .60))], lift=1.3),
   shot(RAD, (150, 190, 560, 500), 'DC POWER + FUEL BOOST  ·  Shift+3', [
    ('1', [BATT1, BATT2], (.55, .07), 34), ('2', BOOST_L, (.08, .92))]),
  ]],
  steps=[
   ('1', 'BATT 1 and BATT 2 Switches', 'ON', 'Already on from Before Start.'),
   ('2', 'LH FUEL BOOST Switch', 'NORM', 'FUEL BOOST LH: DOWN to NORM. The APU feeds from the left side.'),
   ('3', 'APU STARTER DISENGAGE Switch', 'NORMAL', 'Bottom left of the APU panel: leave in NORMAL.'),
   ('4', 'APU MASTER Switch', 'ON', 'Bottom right of the APU SYSTEM panel: UP.'),
   ('5', 'APU TEST', 'PUSH', 'Press the round TEST button once.'),
   ('6', 'APU GENERATOR Switch', 'ON', 'GENERATOR switch, top right of the panel: UP.'),
   ('7', 'APU DC VOLTS', 'CHECK (22 volts minimum)', 'Read DC VOLTS on the APU display.'),
  ]),
 dict(phase=1, part='2 of 2', title='APU: start and bleed air',
  rows=[[
   shot(APU, (1100, 270, 1540, 1010), 'APU PANEL  ·  Shift+9', [
    ('8', APU_START, (.12, .93)), ('9 · 10', APU_LIGHTS, (.40, .32), 24), ('14', APU_BLEED, (.08, .30))], lift=1.3),
   [shot(RAD, (120, 200, 340, 330), 'LOAD SHED  ·  Shift+3', [('11', LOAD_SHED, (.80, .20))]),
    shot(HIGHS, (1160, 100, 1470, 370), 'APU AMPS  ·  Shift+5', [('13', APU_AMPS, (.88, .85))], lift=1.15)],
  ]],
  steps=[
   ('8', 'APU', 'START', 'APU START switch (bottom of the panel): UP and hold.'),
   ('9', 'Hold APU START switch up until APU RELAY ENGAGED light illuminates', 'APU RELAY ENGAGED light ON', 'Then let go.'),
   ('10', 'APU RELAY ENGAGED Light', 'ON, then OFF before READY TO LOAD light ON', 'Wait for READY TO LOAD before using APU power or bleed air.'),
   ('11', 'LOAD SHED Switch', 'NORM', 'Red-capped switch, top left of the DC POWER panel: middle.'),
   ('12', 'GPU', 'DISCONNECT / CLEAR (if used)', 'Tablet, Ground page (Before Start 3): Ground Power shows an empty circle.'),
   ('13', 'APU Ammeter', 'CHECK (400A max on ground/200A max in flight)', 'APU AMPS gauge, right side panel.'),
   ('14', 'APU BLEED AIR Switch', 'ON (for engine start) AS REQUIRED (for PAC bleed)', 'Top left of the APU panel: ON (middle). Not MAX COOL.'),
  ]),

 dict(phase=2, part='1 of 4', title='Start the right engine',
  rows=[[
   shot(HIGHR, (1880, 960, 2560, 1360), 'BLEED CONTROLS  ·  Shift+5', [('2', PAC_ISOL, (.57, .10))]),
   shot(RAD, (330, 330, 560, 470), 'ENGINE START  ·  Shift+3', [('4', START_R, (.92, .80))]),
  ], [
   shot(THR6, (1080, 560, 1600, 780), 'THRUST LEVERS  ·  Shift+6', [('5', IDLE_LBL, (.08, .30))]),
   shot(DISP, (1240, 940, 1500, 1140), 'EICAS  ·  Shift+4', [('3', ENG_BTN, (.86, .20))]),
  ]],
  steps=[
   ('1', 'APU START', 'REFER TO APU START CHECKLIST', 'APU running, READY TO LOAD, APU bleed ON.'),
   ('2', 'PAC ISOL VALVE Knob', 'CLOSED', 'ISOL VALVE knob, right lower panel: to CLSD.'),
   ('3', 'Start duct pressure', 'At least 30 PSI', 'EICAS: press the button under ENG and read START PRESS.'),
   ('4', 'Right Engine - START', 'PRESS (confirm START button and DISENGAGE button illuminate)', 'Right-hand of the three ENGINE START buttons.'),
   ('5', 'Throttle', 'IDLE (by 10% N2 RPM)', 'Right thrust lever from CUT OFF up to IDLE once N2 reaches 10%.'),
  ]),
 dict(phase=2, part='2 of 4', title='Watch the right engine start',
  rows=[[
   shot(DISP, (1030, 390, 1500, 1010), 'EICAS  ·  Shift+4', [
    ('6', FAN_TAPE, (.05, .45)), ('7', OIL_PSI, (.95, .25)), ('8', ITT_TAPE, (.52, .45)), ('9', HYD_PSI, (.92, .76))]),
  ]],
  steps=[
   ('6', 'N1 Rotation', 'CONFIRM', 'FAN% starts to rise.'),
   ('7', 'Oil Pressure', 'CHECK', 'OIL PSI rises into the green.'),
   ('8', 'ITT', 'MONITOR', 'ITT stays below the red line.'),
   ('9', 'Hydraulic Pressure', 'VERIFY', 'HYDRAULICS PSI rises.'),
  ]),
 dict(phase=2, part='3 of 4', title='Left engine and generators',
  rows=[[
   shot(RAD, (150, 150, 760, 500), 'DC POWER + ENGINE START  ·  Shift+3', [
    ('10', START_L, (.10, .96)), ('12', LH_GEN, (.10, .05)), ('12', RH_GEN, (.62, .05))]),
  ], [
   shot(DISP, (1250, 780, 1500, 900), 'HYDRAULICS  ·  Shift+4', [('11', HYD_PSI, (.88, .40))]),
   shot(APU, (1100, 300, 1400, 520), 'APU BLEED  ·  Shift+9', [('14', APU_BLEED, (.10, .82))], lift=1.3),
  ]],
  steps=[
   ('10', 'Left Engine - START', 'Same as right engine', 'Left START button, left lever to IDLE at 10% N2. Check N1, oil pressure, ITT.'),
   ('11', 'Hydraulic Pressure', 'VERIFY', 'HYDRAULICS PSI up on both systems.'),
   ('12', 'Generators', 'ON', 'LH GEN and RH GEN switches UP.'),
   ('13', 'Ground Air Service/GPU (if used)', 'DISCONNECT', 'Tablet, Ground page: Ground Power off.'),
   ('14', 'APU Bleed Air Switch', 'OFF (check bleed sources)', 'APU BLEED AIR switch DOWN.'),
  ]),
 dict(phase=2, part='4 of 4', title='Bleed air check',
  rows=[[
   shot(DISP, (370, 700, 860, 1140), 'PILOT MFD  ·  Shift+4', [('15', MFD_EICAS_SYS, (.62, .30))]),
   shot(HIGHR, (1880, 960, 2560, 1360), 'BLEED CONTROLS  ·  Shift+5', [
    ('16 · 21', R_BLD, (.88, .95)), ('17 · 20', PAC_ISOL, (.57, .10)), ('18 · 19', L_BLD, (.12, .95))]),
  ]],
  steps=[
   ('15', 'Select EICAS SYS, ENG on the MFD', 'Duct pressure is from right engine', 'MFD: button under EICAS SYS, then ENG. Watch duct pressure through items 16-21.'),
   ('16', 'R ENG BLD AIR Knob', 'OFF (pressure should be zero)', 'Right knob, bottom row: OFF.'),
   ('17', 'PAC ISOL VALVE Knob', 'OPEN (pressure is from left engine)', 'ISOL VALVE knob: open.'),
   ('18', 'L ENG BLD AIR Knob', 'OFF (pressure should be zero)', 'Left knob, bottom row: OFF.'),
   ('19', 'L ENG BLD AIR Knob', 'HP/LP (check pressure)', 'Left knob back to HP/LP.'),
   ('20', 'PAC ISOL VALVE Knob', 'CLOSED (pressure should be zero)', 'ISOL VALVE knob: CLSD.'),
   ('21', 'R ENG BLD AIR Knob', 'HP/LP (check pressure)', 'Right knob back to HP/LP.'),
   ('22', 'APU Bleed Air Switch', 'AS DESIRED', 'APU panel (APU Start 2): normally OFF once both engines run.'),
  ]),

 dict(phase=3, part='1 of 3', title='Second engine by cross bleed',
  rows=[[
   shot(HIGHR, (1600, 960, 2560, 1360), 'PRESSURIZATION + BLEED  ·  Shift+5', [
    ('1', PAC_ISOL, (.69, .10)), ('2', PAC_BLEED_SEL, (.20, .12)), ('3', R_BLD, (.97, .95))]),
  ], [
   shot(THR6, (1080, 560, 1600, 780), 'THRUST LEVERS  ·  Shift+6', [('4', TL_R, (.93, .20)), ('6', IDLE_LBL, (.08, .30))]),
   shot(RAD, (330, 330, 560, 470), 'ENGINE START  ·  Shift+3', [('5', START_L, (.08, .80))]),
  ]],
  steps=[
   ('1', 'PAC ISOL VALVE Knob', 'OPEN', 'ISOL VALVE knob: open.'),
   ('2', 'PAC BLEED SELECT Switch', 'HP', 'PAC BLEED SELECT switch: UP to HP.'),
   ('3', 'Opposite ENG BLD AIR Knob', 'HP/LP', 'The running (right) engine: R ENG BLD AIR to HP/LP.'),
   ('4', 'Opposite Engine', 'Adjust THR maintain 30 PSI minimum start pressure (approximately 55% N1)', 'Brakes held. Advance the right thrust lever until start pressure reads 30 PSI.'),
   ('5', 'Left Engine - START', 'PRESS (confirm START button and DISENGAGE button illuminate)', 'Left-hand ENGINE START button.'),
   ('6', 'Throttle', 'IDLE (by 10% N2 RPM)', 'Left thrust lever from CUT OFF to IDLE at 10% N2.'),
  ]),
 dict(phase=3, part='2 of 3', title='Watch the left engine start',
  rows=[[
   shot(DISP, (1030, 390, 1500, 1010), 'EICAS  ·  Shift+4', [
    ('7', FAN_TAPE, (.05, .45)), ('8', OIL_PSI, (.95, .25)), ('9', ITT_TAPE, (.52, .45)), ('11', HYD_PSI, (.92, .76))]),
  ], [
   shot(THR6, (1080, 560, 1600, 780), 'THRUST LEVERS  ·  Shift+6', [('10', TL_R, (.93, .20))]),
  ]],
  steps=[
   ('7', 'N1 Rotation', 'CONFIRM', 'Left FAN% starts to rise.'),
   ('8', 'Oil Pressure', 'CHECK', 'OIL PSI rises into the green.'),
   ('9', 'ITT', 'MONITOR', 'ITT stays below the red line.'),
   ('10', 'Opposite Engine', 'IDLE', 'Right thrust lever back to IDLE.'),
   ('11', 'Hydraulic Pressure', 'VERIFY', 'HYDRAULICS PSI up on both systems.'),
  ]),
 dict(phase=3, part='3 of 3', title='Generators and bleed back to normal',
  rows=[[
   shot(RAD, (150, 150, 560, 360), 'GENERATORS  ·  Shift+3', [('12', LH_GEN, (.08, .12)), ('12', RH_GEN, (.93, .12))]),
  ], [
   shot(HIGHR, (1600, 1100, 2400, 1360), 'PAC BLEED SELECT + ISOL VALVE  ·  Shift+5', [('13', PAC_BLEED_SEL, (.04, .85)), ('14', PAC_ISOL, (.97, .12))]),
  ]],
  steps=[
   ('12', 'Generators', 'ON', 'LH GEN and RH GEN switches UP.'),
   ('13', 'PAC BLEED SELECT Switch', 'NORMAL', 'PAC BLEED SELECT back DOWN to NORM.'),
   ('14', 'PAC ISOL VALVE Knob', 'CLOSED', 'ISOL VALVE knob: CLSD.'),
  ]),
]

# ---- in-flight and arrival sections (FlightFX Full Checklist pages 4-5) --------------------------
GEAR_HANDLE, GEAR_LIGHTS = (1857, 488), [(1835, 310), (1876, 268), (1915, 310)]
STD_BTN, BARO_KNOB = (943, 660), (1030, 687)
WINDOW_VENT = (954, 149)
MINIMUMS, RA_BARO, CROSSFEED, GRVTY_XFLOW = (1265, 740), (1360, 740), (1090, 925), (1230, 955)
IGN_L, IGN_R = (591, 414), (666, 414)
AP_BTN = (1714, 368)
PFD_SPEED = (677, 494)
CABIN_GAUGE, PASS_SAFETY_HI = (1714, 920), (1136, 1060)
WS_L, WS_R = (222, 701), (333, 701)
ANTI_ICE_PANEL = [(110, 415), (700, 945)]
CLB_DET, CRU_DET, ENG_SYNC = (1352, 367), (1352, 413), (1183, 935)
REV_L, REV_R = (1236, 420), (1425, 420)
CUTOFF_LBL = (1316, 714)

FLIGHT_PAGES = [
 dict(phase=8, part='1 of 2', title='Gear, flaps, climb thrust',
  rows=[[
   shot(RAD, (1760, 180, 2000, 620), 'LANDING GEAR  ·  Shift+3', [('1', GEAR_HANDLE, (.85, .93))]),
   shot(QUAD, (880, 0, 1860, 1250), 'THROTTLE QUADRANT  ·  Shift+6', [
    ('2', FLAP_HANDLE, (.62, .40)), ('3', CLB_DET, (.70, .14)), ('5', ENG_SYNC, (.12, .86))]),
  ]],
  steps=[
   ('1', 'Landing Gear', 'UP', 'Positive climb: gear handle UP. The three green lights go out.'),
   ('2', 'Flaps/Slats', 'UP (airspeed above 170 KIAS)', 'SLATS FLAPS handle fully forward.'),
   ('3', 'Throttles', 'CLB DETENT', 'Both levers back into CLB, the 3rd notch (MAX, TO/MC, CLB, CRU).'),
   ('4', 'Anti-Ice Systems', 'AS REQUIRED', 'Anti-ice panel switches as conditions need.'),
   ('5', 'ENG SYNC Knob', 'AS DESIRED', 'Knob below the throttles: FAN or TURBINE keeps the engines in step.'),
  ]),
 dict(phase=8, part='2 of 2', title='Pressurization, altimeters, APU',
  rows=[[
   shot(HIGHR, (850, 560, 1850, 1200), 'PRESSURIZATION + ALTIMETER  ·  Shift+5', [
    ('6', CABIN_GAUGE, (.68, .22)), ('7', PASS_SAFETY_HI, (.06, .95)), ('8', BARO_KNOB, (.36, .08))]),
  ], [
   shot(QUAD, (1240, 800, 1640, 1060), 'LANDING LIGHTS  ·  Shift+6', [('9', [LAND_L, LAND_R], (.66, .14), 34)]),
   shot(APU, (1300, 780, 1540, 1010), 'APU MASTER  ·  Shift+9', [('10', APU_MASTER, (.20, .25))], lift=1.3),
  ]],
  steps=[
   ('6', 'Pressurization', 'CHECK', 'CABIN gauge: cabin altitude climbing slowly. No warnings.'),
   ('7', 'Passenger Advisory Lights', 'AS REQUIRED', 'SEAT BELT LTS switch as you wish.'),
   ('8', 'Altimeters (transition altitude)', 'SET', 'Passing the transition altitude: press STD (1013 hPa / 29.92 inHg).'),
   ('9', 'Exterior Lights (FL180)', 'AS DESIRED', 'Passing FL180 the landing lights may go off.'),
   ('10', 'APU (prior to climb above FL310)', 'OFF', 'APU MASTER switch DOWN before FL310.'),
  ]),

 dict(phase=9, part='', title='Cruise',
  rows=[[
   shot(QUAD, (1090, 270, 1560, 700), 'THRUST LEVERS  ·  Shift+6', [('1', CRU_DET, (.80, .62))]),
   [shot(HIGHR, (1600, 780, 1850, 1060), 'CABIN  ·  Shift+5', [('2', CABIN_GAUGE, (.88, .88))]),
    shot(DISP, (1290, 540, 1500, 700), 'EICAS FUEL  ·  Shift+4', [('3', FUEL_QTY, (.85, .82))])],
  ]],
  steps=[
   ('1', 'Throttles', 'CRU detent or AS REQUIRED', 'Levers into CRU, the 4th notch, or as needed for your speed.'),
   ('2', 'Pressurization', 'CHECK', 'CABIN gauge steady, well below 8,000 ft.'),
   ('3', 'Fuel Transfer', 'VERIFY', 'EICAS FUEL: left and right balanced (CTR WING XFER as required).'),
  ]),

 dict(phase=10, part='', title='Descent',
  rows=[[
   shot(LOWER, (90, 600, 470, 790), 'WINDSHIELD  ·  Shift+5', [('1', [WS_L, WS_R], (.88, .30), 34)]),
   shot(APU, (850, 40, 1200, 300), 'WINDOW VENT  ·  Shift+9', [('2', WINDOW_VENT, (.72, .90))], lift=1.3),
  ], [
   shot(HIGHR, (850, 560, 1850, 1200), 'PRESSURIZATION + ALTIMETER  ·  Shift+5', [
    ('3', CABIN_GAUGE, (.68, .22)), ('7', BARO_KNOB, (.36, .08))]),
  ]],
  steps=[
   ('1', 'LH and RH WINDSHIELD ANTI-ICE Switches', 'BOTH ON', 'WINDSHIELD LH and RH: UP.'),
   ('2', 'Side Window Vent Knobs', 'CLOSED', 'Turn the vent knob to CLOSE (one each side).'),
   ('3', 'Pressurization', 'CHECK/SET LANDING ELEVATION', 'CABIN gauge descending smoothly; landing field elevation set.'),
   ('4', 'ANTI-ICE Switches', 'AS REQUIRED', 'As conditions need.'),
   ('5', 'APU', 'AS DESIRED', 'Start it now if you want it after landing.'),
   ('6', 'Exterior Lights (FL180)', 'AS REQUIRED', 'Passing FL180: LANDING LIGHT LH and RH up.'),
   ('7', 'Altimeter (transition level)', 'SET', 'Passing the transition level: BARO SET to the destination QNH.'),
  ]),

 dict(phase=11, part='1 of 2', title='Landing data, minimums, fuel',
  rows=[[
   shot(LEFTP, (1000, 690, 1450, 1010), 'MINIMUMS + CROSSFEED  ·  Shift+8', [
    ('4', [MINIMUMS, RA_BARO], (.34, .48), 30), ('5', CROSSFEED, (.06, .96))], lift=1.12),
   shot(PFDV, (590, 360, 1030, 780), 'PILOT PFD  ·  Shift+1', [('3', PFD_ATT, (.04, .97))]),
  ], [
   shot(RAD, (780, 470, 1300, 640), 'FMS KEYS  ·  Shift+3', [('1', FMS_PERF, (.34, .12))]),
   shot(QUAD, (1240, 800, 1640, 1060), 'LANDING LIGHTS  ·  Shift+6', [('6', [LAND_L, LAND_R], (.66, .14), 34)]),
  ]],
  steps=[
   ('1', 'Landing Data', 'CONFIRM', 'FMS PERF, then LANDING DATA: check VREF and landing distance.'),
   ('2', 'Crew Briefing', 'COMPLETE', 'Approach, minimums, missed approach.'),
   ('3', 'Avionics/Flight Instruments', 'CHECK/SET', 'Approach loaded, courses and frequencies set, no flags.'),
   ('4', 'Minimums', 'SET (RA/BARO)', 'RA/BARO button picks the type; MINIMUMS knob sets the value.'),
   ('5', 'FUEL CROSSFEED Switch', 'OFF', 'CROSSFEED knob on the FUEL panel: OFF (straight up).'),
   ('6', 'Exterior Lights', 'AS REQUIRED', 'LANDING LIGHT LH and RH up.'),
   ('7', 'Flaps/Slats', 'AS REQUIRED', 'SLATS FLAPS handle to 5, then 15, at the right speeds.'),
  ]),
 dict(phase=11, part='2 of 2', title='Cabin, ignition, engine sync',
  rows=[[
   shot(RAD, (520, 330, 720, 480), 'IGNITION  ·  Shift+3', [('11', [IGN_L, IGN_R], (.50, .12), 30)]),
   shot(QUAD, (1060, 850, 1320, 1010), 'ENG SYNC  ·  Shift+6', [('13', ENG_SYNC, (.90, .30))]),
  ], [
   shot(HIGHR, (1050, 780, 1850, 1150), 'LIGHTS + PRESSURIZATION  ·  Shift+5', [
    ('10', PASS_SAFETY_HI, (.30, .55)), ('12', CABIN_GAUGE, (.97, .12))]),
  ]],
  steps=[
   ('8', 'Passengers', 'BRIEF', 'Nothing to click. Tick it.'),
   ('9', 'Seats/Seat Belts/Shoulder Harnesses/Aft Divider Sliding Doors', 'CHECK/SECURE/LATCHED OPEN', 'Nothing to click. Tick it.'),
   ('10', 'Passenger Advisory Lights', 'PASS SAFETY', 'SEAT BELT LTS switch: DOWN.'),
   ('11', 'LH and RH IGNITION Switches', 'NORM', 'IGNITION LH and RH: DOWN to NORM.'),
   ('12', 'Pressurization', 'ZERO DIFFERENTIAL at touchdown', 'Cabin reaches field elevation as you land.'),
   ('13', 'ENG SYNC Knob', 'OFF', 'ENG SYNC knob straight up: OFF.'),
  ]),

 dict(phase=12, part='', title='Gear down, speed, autopilot off',
  rows=[[
   shot(RAD, (1760, 180, 2000, 620), 'LANDING GEAR  ·  Shift+3', [('1', GEAR_HANDLE, (.85, .93))]),
   shot(QUAD, (880, 0, 1860, 1250), 'THROTTLE QUADRANT  ·  Shift+6', [('3', SPEEDBRAKE, (.30, .24)), ('2', FLAP_15, (.62, .72))]),
  ], [
   shot(GLARE, (1240, 300, 1800, 600), 'AUTOPILOT  ·  Shift+2', [('6', AP_BTN, (.97, .45))], lift=1.1),
   shot(PFDV, (590, 360, 1030, 780), 'PILOT PFD', [('5', PFD_SPEED, (.04, .97))]),
  ]],
  steps=[
   ('1', 'Landing Gear', 'DOWN and LOCKED (3 green lights)', 'Gear handle DOWN. Three green lights above it: LH, NOSE, RH.'),
   ('2', 'Flaps', 'AS REQUIRED', 'Landing flaps set (15 or FULL).'),
   ('3', 'Speed Brakes', 'RETRACTED (0%)', 'Lever fully forward.'),
   ('4', 'EICAS', 'CHECK', 'No warnings. Gear and flaps indications correct.'),
   ('5', 'Airspeed', 'VREF', 'Hold VREF from LANDING DATA on the PFD speed tape.'),
   ('6', 'Autopilot', 'OFF above minimum use height', 'Press AP to disconnect it in time.'),
  ]),

 dict(phase=13, part='', title='Touchdown and rollout',
  rows=[[
   shot(QUAD, (770, 0, 1850, 1250), 'THROTTLE QUADRANT  ·  Shift+6', [
    ('2', SPEEDBRAKE, (.34, .24)), ('5 · 6', [REV_L, REV_R], (.62, .07), 30)]),
   shot(GLARE, (1960, 330, 2300, 640), 'REVERSER LIGHTS  ·  Shift+2', [('5', REV_LIGHTS, (.08, .29))], lift=1.1),
  ], [
   shot(THR6, (1080, 560, 1600, 780), 'THRUST LEVERS  ·  Shift+6', [('1', IDLE_LBL, (.08, .30))]),
  ]],
  steps=[
   ('1', 'Throttles', 'IDLE', 'Both levers to IDLE over the threshold.'),
   ('2', 'Speed Brakes', 'EXTEND at touchdown (100%)', 'Speed brake lever fully back.'),
   ('3', 'Elevator Control', 'FORWARD PRESSURE at touchdown', 'Gentle forward pressure keeps the nose wheel down.'),
   ('4', 'Brakes', 'APPLY after nose wheel ground contact', 'Toe brakes, smoothly.'),
   ('5', 'Thrust Reversers', 'DEPLOY after nose wheel ground contact', 'Lift the reverser levers. DEPLOY lights on the glareshield.'),
   ('6', 'Thrust Reversers', 'IDLE BY 65 KIAS', 'Reverser levers back to idle reverse by 65 knots.'),
  ]),

 dict(phase=14, part='1 of 3', title='Shutdown: brake, anti-ice, engines, IRS',
  rows=[[
   shot(AFT, (1500, 1000, 2040, 1420), 'PARKING BRAKE  ·  Shift+7', [('1', PARK_BRAKE, (.30, .85))], lift=1.45),
   shot(THR6, (1080, 560, 1600, 780), 'THRUST LEVERS  ·  Shift+6', [('3', CUTOFF_LBL, (.08, .85))]),
  ], [
   shot(LOWER, (60, 380, 720, 1000), 'ANTI-ICE  ·  Shift+5', [('2', ANTI_ICE_PANEL, (.88, .97), 0)]),
   shot(AFT, (950, 520, 1450, 900), 'IRS SELECTORS  ·  Shift+7', [('4', IRS_A, (.93, .30)), ('4', IRS_B, (.06, .95))], lift=1.4),
  ]],
  steps=[
   ('1', 'Parking Brake', 'SET', 'Pull the T-handle UP.'),
   ('2', 'Anti-Ice Systems', 'ALL OFF', 'Every anti-ice switch DOWN.'),
   ('3', 'Thrust Reversers', 'CUTOFF', 'Thrust levers back to CUT OFF: the engines stop.'),
   ('4', 'IRS Mode Control Knobs', 'OFF', 'Both IRS selectors to OFF.'),
  ]),
 dict(phase=14, part='2 of 3', title='Shutdown: cabin, gyro, power',
  rows=[[
   shot(LOWER, (880, 600, 1260, 950), 'SEAT BELT LTS  ·  Shift+5', [('5', PASS_SAFETY, (.90, .70))]),
   shot(DISP, (610, 25, 940, 340), 'STANDBY  ·  Shift+4', [('6', CAGE_KNOB, (.13, .82))], lift=1.3),
  ], [
   shot(RAD, (150, 150, 760, 640), 'DC POWER PANEL  ·  Shift+3', [
    ('7', STBY_PWR, (.975, .74)), ('8', [AVIONICS, EICAS_PWR], (.97, .45), 34)]),
   shot(LEFTP, (700, 830, 1040, 1060), 'LIGHTS  ·  Shift+8', [('9', EMERG_LT, (.12, .85))], lift=1.12),
  ]],
  steps=[
   ('5', 'Passenger Advisory Lights', 'OFF', 'SEAT BELT LTS switch: middle.'),
   ('6', 'Standby Gyro', 'CAGED', 'Pull the PULL TO CAGE knob.'),
   ('7', 'STBY PWR', 'OFF', 'STBY PWR switch DOWN.'),
   ('8', 'Avionics Power/EICAS Switches', 'OFF', 'Both switches under AVIONICS POWER: DOWN.'),
   ('9', 'EMERG LT Switch', 'ARM', 'EMERG LT switch at ARM.'),
  ]),
 dict(phase=14, part='3 of 3', title='Shutdown: fuel, APU, lights, batteries',
  rows=[[
   shot(LEFTP, (1050, 820, 1340, 1060), 'FUEL  ·  Shift+8', [('10', GRVTY_XFLOW, (.20, .90))], lift=1.12),
   shot(APU, (1300, 780, 1540, 1010), 'APU MASTER  ·  Shift+9', [('11', APU_MASTER, (.20, .30))], lift=1.3),
  ], [
   shot(LOWER, (880, 600, 1260, 950), 'EXTERIOR LIGHTS  ·  Shift+5', [('12', [BEACON, NAV_LT], (.18, .45), 26)]),
   shot(RAD, (150, 150, 560, 360), 'BATTERIES  ·  Shift+3', [('13', [BATT1, BATT2], (.62, .88), 34)]),
  ]],
  steps=[
   ('10', 'GRVTY XFLOW Switch', 'OFF', 'GRVTY XFLOW switch on the FUEL panel: OFF.'),
   ('11', 'APU MASTER Switch', 'OFF', 'APU MASTER switch DOWN (if the APU was running).'),
   ('12', 'Exterior Lights', 'OFF', 'Beacon, NAV, taxi and landing lights: all off.'),
   ('13', 'BATT 1 and BATT 2 Switches', 'OFF', 'Both switches DOWN. The aircraft is cold and dark.'),
  ]),
]

PAGES = START_PAGES + PAGES + FLIGHT_PAGES

# Completeness: every item, in FlightFX order, for each phase.
_counts = [0] * len(PHASES)
for _p in PAGES:
    for _s in _p['steps']:
        _counts[_p['phase']] += 1
        assert int(_s[0]) == _counts[_p['phase']], ('out of order', _p['title'], _s[0])
assert _counts == EXPECTED, _counts


# ---- drawing helpers ----------------------------------------------------------------------------
def breakable(text):
    return re.sub(r'(?<=[A-Za-z]{4})/(?=[A-Za-z]{4})', ' / ', text)


def para(c, text, x, top, width, style):
    p = Paragraph(breakable(text), style)
    _, h = p.wrap(width, 2000)
    p.drawOn(c, x, top - h)
    return h


def arrow(c, start, end, gap=2.5):
    """One solid arrow: a tapered shaft that flows into the head, white outline, soft shadow."""
    sx, sy = start; ex, ey = end
    d = hypot(ex - sx, ey - sy)
    if d < 20:
        return
    ux, uy = (ex - sx) / d, (ey - sy) / d
    nx, ny = -uy, ux
    tx, ty = ex - ux * gap, ey - uy * gap                  # tip, just short of the control
    hl, hw, w0, w1 = 15.0, 8.5, 1.8, 3.2                  # head length / half width, shaft half widths
    bx, by = tx - ux * hl, ty - uy * hl
    pts = [(sx + nx * w0, sy + ny * w0), (bx + nx * w1, by + ny * w1), (bx + nx * hw - ux * 2.5, by + ny * hw - uy * 2.5),
           (tx, ty), (bx - nx * hw - ux * 2.5, by - ny * hw - uy * 2.5), (bx - nx * w1, by - ny * w1),
           (sx - nx * w0, sy - ny * w0)]
    def shape(dx=0, dy=0):
        path = c.beginPath(); path.moveTo(pts[0][0] + dx, pts[0][1] + dy)
        for px, py in pts[1:]:
            path.lineTo(px + dx, py + dy)
        path.close(); return path
    c.saveState(); c.setLineJoin(1)
    c.setFillColor(Color(0.02, 0.1, 0.18, alpha=.35)); c.drawPath(shape(.9, -1.4), stroke=0, fill=1)
    c.setStrokeColor(white); c.setLineWidth(2.2); c.setFillColor(SKY)
    c.drawPath(shape(), stroke=1, fill=1)
    c.restoreState()


def badge(c, x, y, text, r=13.5):
    if len(text) > 2:                                      # e.g. "16 · 21": one control, two items
        c.saveState(); c.setFont('UI-B', 12)
        w = c.stringWidth(text, 'UI-B', 12) + 18
        c.setFillColor(Color(0.04, 0.13, 0.22, alpha=.35)); c.roundRect(x - w / 2 + .8, y - r - 2.6, w + 2, 2 * r + 2, r + 1, stroke=0, fill=1)
        c.setFillColor(SKY); c.setStrokeColor(white); c.setLineWidth(2.4)
        c.roundRect(x - w / 2, y - r, w, 2 * r, r, stroke=1, fill=1)
        c.setFillColor(white); c.drawCentredString(x, y - 4.3, text)
        c.restoreState(); return
    c.saveState()
    c.setFillColor(Color(0.04, 0.13, 0.22, alpha=.35)); c.circle(x + .8, y - 1.6, r + 1, stroke=0, fill=1)
    c.setFillColor(SKY); c.setStrokeColor(white); c.setLineWidth(2.4)
    c.circle(x, y, r, stroke=1, fill=1)
    c.setFillColor(white)
    size = 14 if len(text) == 1 else 12
    c.setFont('UI-B', size); c.drawCentredString(x, y - size * .36, text)
    c.restoreState()


def highlight(c, box):
    """Sky-blue outline round a group of switches that belong to one item."""
    x0, y0, x1, y1 = box
    c.saveState()
    c.setFillColor(Color(0.12, 0.65, 0.91, alpha=.14)); c.setStrokeColor(white); c.setLineWidth(5)
    c.roundRect(x0, y0, x1 - x0, y1 - y0, 7, stroke=1, fill=1)
    c.setStrokeColor(SKY); c.setLineWidth(2.6)
    c.roundRect(x0, y0, x1 - x0, y1 - y0, 7, stroke=1, fill=0)
    c.restoreState()


def box_edge(box, frm):
    """Where the line from `frm` to the box centre meets the box outline."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dx, dy = frm[0] - cx, frm[1] - cy
    t = min((x1 - cx) / abs(dx) if dx else 1e9, (y1 - cy) / abs(dy) if dy else 1e9)
    return cx + dx * t, cy + dy * t


def photo(c, spec, x, y, dw, dh):
    image = Image.open(ASSETS / spec['name']).convert('RGB').crop(spec['crop'])
    image = ImageEnhance.Contrast(ImageEnhance.Brightness(image).enhance(spec['lift'])).enhance(1.06)
    buf = BytesIO(); image.save(buf, format='JPEG', quality=93)
    c.saveState()
    c.setFillColor(SKY_LINE); c.roundRect(x - 2.2, y - 2.2, dw + 4.4, dh + 4.4, 10, stroke=0, fill=1)
    clip = c.beginPath(); clip.roundRect(x, y, dw, dh, 8); c.clipPath(clip, stroke=0)
    c.drawImage(ImageReader(BytesIO(buf.getvalue())), x, y, dw, dh)
    c.restoreState()

    # location tag: shrink the text until it fits the photo
    size = 10.0
    while pdfmetrics.stringWidth(spec['label'], 'UI-B', size) + 30 > dw and size > 7:
        size -= .25
    tw = pdfmetrics.stringWidth(spec['label'], 'UI-B', size)
    tag = (x, y + dh - 22, x + tw + 18, y + dh)            # tag area inside the photo

    left, top, right, bottom = spec['crop']
    s = dw / (right - left)
    to_pdf = lambda t: (x + (t[0] - left) * s, y + dh - (t[1] - top) * s)
    R = 15                                                 # badge radius plus breathing room
    def place(bx, by, wide):
        # never on the tag, never clipped by the photo edge
        hw = wide / 2 + 4
        if bx + hw > tag[0] and bx - hw < tag[2] and by + R > tag[1]:
            by = tag[1] - R - 2
        bx = min(max(bx, x + hw - 2), x + dw - hw + 2)
        by = min(max(by, y + R - 3), y + dh - R + 3)
        return bx, by
    marks = []
    for mark in spec['marks']:
        number, target, (fx, fy) = mark[:3]
        wide = 2 * 13.5 if len(number) <= 2 else pdfmetrics.stringWidth(number, 'UI-B', 12) + 18
        b = place(x + fx * dw, y + (1 - fy) * dh, wide)
        marks.append((mark, b))

    c.saveState()
    clip = c.beginPath(); clip.roundRect(x, y, dw, dh, 8); c.clipPath(clip, stroke=0)
    for mark, b in marks:                                  # outlines first, then arrows
        number, target = mark[:2]
        if isinstance(target, list):
            pad = mark[3] if len(mark) > 3 else 30
            for tx_, ty_ in target:
                assert left <= tx_ <= right and top <= ty_ <= bottom, (spec['name'], number)
            xs = [t[0] for t in target]; ys = [t[1] for t in target]
            p0 = to_pdf((max(left, min(xs) - pad), min(bottom, max(ys) + pad)))
            p1 = to_pdf((min(right, max(xs) + pad), max(top, min(ys) - pad)))
            highlight(c, (p0[0], p0[1], p1[0], p1[1]))
    for mark, b in marks:
        number, target = mark[:2]
        if isinstance(target, list):
            xs = [t[0] for t in target]; ys = [t[1] for t in target]
            pad = mark[3] if len(mark) > 3 else 30
            p0 = to_pdf((max(left, min(xs) - pad), min(bottom, max(ys) + pad)))
            p1 = to_pdf((min(right, max(xs) + pad), max(top, min(ys) - pad)))
            box = (p0[0], p0[1], p1[0], p1[1])
            arrow(c, b, box_edge(box, b), gap=1.0)
        else:
            assert left <= target[0] <= right and top <= target[1] <= bottom, (spec['name'], number, target)
            arrow(c, b, to_pdf(target))
    # tag over the outlines and arrows, badges over everything
    c.setFillColor(SKY); c.roundRect(x - 8, y + dh - 22, tw + 26, 30, 8, stroke=0, fill=1)
    c.setFillColor(white); c.setFont('UI-B', size); c.drawString(x + 9, y + dh - 15, spec['label'])
    c.restoreState()
    for mark, (bx, by) in marks:
        badge(c, bx, by, mark[0])


def layout_rows(rows, top, bottom, gap=12):
    """Each row fills the page width. A row item may be a list: those shots stack vertically in one column."""
    width = W - 2 * M
    asp = lambda sp: (sp['crop'][2] - sp['crop'][0]) / (sp['crop'][3] - sp['crop'][1])
    sized = []
    for row in rows:
        # item width at row height h:  shot -> a*h ;  stack -> (h - gap*(k-1)) / sum(1/a)
        k_h, const = 0.0, gap * (len(row) - 1)
        for item in row:
            if isinstance(item, list):
                inv = sum(1 / asp(sp) for sp in item)
                k_h += 1 / inv; const -= gap * (len(item) - 1) / inv
            else:
                k_h += asp(item)
        sized.append((row, (width - const) / k_h))
    gaps = gap * (len(rows) - 1)
    f = min(1, (top - bottom - gaps) / sum(h for _, h in sized))
    y = top
    for row, h in sized:
        h *= f
        widths = []
        for item in row:
            if isinstance(item, list):
                widths.append((h - gap * (len(item) - 1)) / sum(1 / asp(sp) for sp in item))
            else:
                widths.append(asp(item) * h)
        x = M + (width - sum(widths) - gap * (len(row) - 1)) / 2
        y -= h
        for item, w in zip(row, widths):
            if isinstance(item, list):
                yy = y + h
                for sp in item:
                    sh = w / asp(sp); yy -= sh
                    yield sp, x, yy, w, sh
                    yy -= gap
            else:
                yield item, x, y, w, h
            x += w + gap
        y -= gap


def logo(c, x, y, height):
    d = svg2rlg(str(ASSETS / 'cessna-logo.svg'))
    s = height / d.height
    c.saveState(); c.translate(x, y); c.scale(s, s); renderPDF.draw(d, c, 0, 0); c.restoreState()
    return d.width * s


def header(c, page_no, total, phase, part, label=None):
    c.setFillColor(SKY); c.rect(0, H - 62, W, 62, stroke=0, fill=1)
    c.setFillColor(SKY_DEEP); c.rect(0, H - 66, W, 4, stroke=0, fill=1)
    c.setFillColor(white); c.roundRect(M - 6, H - 54, 52, 46, 7, stroke=0, fill=1)
    logo(c, M - 1, H - 50, 38)
    c.setFillColor(white); c.setFont('UI-BL', 22); c.drawString(M + 56, H - 33, 'CITATION X')
    c.setFont('UI-SB', 9.5); c.drawString(M + 57, H - 47, 'ILLUSTRATED NORMAL CHECKLIST  ·  BY KAZBER')
    label = label or (PHASES[phase] + ('  ·  ' + part if part else ''))
    c.setFont('UI-B', 11)
    tw = c.stringWidth(label, 'UI-B', 11)
    c.setFillColor(white); c.roundRect(W - M - tw - 26, H - 44, tw + 26, 24, 12, stroke=0, fill=1)
    c.setFillColor(SKY_DEEP); c.drawRightString(W - M - 13, H - 36, label)
    c.setFillColor(white); c.setFont('UI-SB', 9.5); c.drawRightString(W - M - 13, H - 57, f'PAGE {page_no} OF {total}')


def tracker(c, phase, y):
    stage, members = next((n, m) for n, m in STAGES if phase in m)
    c.setFont('UI-B', 9.5)
    lw = c.stringWidth(stage, 'UI-B', 9.5) + 22
    c.setFillColor(SKY_DEEP); c.roundRect(M, y, lw, 20, 10, stroke=0, fill=1)
    c.setFillColor(white); c.drawCentredString(M + lw / 2, y + 6.3, stage)
    x0 = M + lw + 8
    seg = (W - M - x0 - 3 * 6) / 4
    for k, i in enumerate(members):
        x = x0 + k * (seg + 6)
        if i == phase:
            c.setFillColor(SKY); c.roundRect(x, y, seg, 20, 10, stroke=0, fill=1); c.setFillColor(white)
        else:
            c.setFillColor(SKY_TINT); c.roundRect(x, y, seg, 20, 10, stroke=0, fill=1)
            c.setFillColor(SKY_DEEP if i < phase else HexColor('#7FA9C4'))
        c.setFont('UI-B', 9.5)
        c.drawCentredString(x + seg / 2, y + 6.3, PHASES[i])


def step_block(c, x, top, width, step, measure=False):
    num, item, response, how = step
    tx = x + 38
    tw = width - 38
    one_line = pdfmetrics.stringWidth(breakable(item), 'UI-B', 12) + pdfmetrics.stringWidth(breakable(response), 'UI-B', 12) + 34 <= tw
    if one_line:
        h1 = 14.5
    else:
        h1 = Paragraph(breakable(item), ITEM).wrap(tw, 999)[1] + Paragraph(breakable(response), RESP).wrap(tw - 20, 999)[1] + 2
    h2 = Paragraph(how, HOW).wrap(tw, 999)[1]
    total = h1 + 3 + h2 + 12
    if measure:
        return total
    badge(c, x + 14, top - 10, num, r=13)
    if one_line:
        item_d, resp_d = breakable(item), breakable(response)
        c.setFont('UI-B', 12); c.setFillColor(NAVY); c.drawString(tx, top - 12, item_d)
        c.setFillColor(SKY_DEEP); c.drawRightString(x + width, top - 12, resp_d)
        a = tx + pdfmetrics.stringWidth(item_d, 'UI-B', 12) + 6
        b = x + width - pdfmetrics.stringWidth(resp_d, 'UI-B', 12) - 6
    else:
        hi = para(c, item, tx, top + 1.5, tw, ITEM)
        resp_w = min(tw - 20, pdfmetrics.stringWidth(breakable(response), 'UI-B', 12) + 4)
        hr = para(c, response, x + width - resp_w, top + 1.5 - hi - 2, resp_w, RESP)
        a, b = tx, x + width - resp_w - 6
        top_line = top - hi - 2 - hr + 1.5
        c.saveState(); c.setStrokeColor(SKY_LINE); c.setLineWidth(1.3); c.setDash(0.1, 3.6); c.setLineCap(1)
        c.line(a, top_line + 3.5, b, top_line + 3.5); c.restoreState()
        a = b = None
    if a is not None and b > a:
        c.saveState(); c.setStrokeColor(SKY_LINE); c.setLineWidth(1.3); c.setDash(0.1, 3.6); c.setLineCap(1)
        c.line(a, top - 9, b, top - 9); c.restoreState()
    para(c, how, tx, top - h1 - 3, tw, HOW)
    return total


def checklist_page(c, page_no, total, page):
    c.setFillColor(white); c.rect(0, 0, W, H, stroke=0, fill=1)
    header(c, page_no, total, page['phase'], page['part'])
    tracker(c, page['phase'], H - 96)
    c.setFillColor(NAVY); c.setFont('UI-B', 23); c.drawString(M, H - 128, page['title'])
    width = W - 2 * M
    heights = [step_block(c, M, 0, width, s, measure=True) for s in page['steps']]
    steps_h = sum(heights) + 26
    placed = list(layout_rows(page['rows'], H - 142, M + steps_h + 20))
    for spec, x, y, dw, dh in placed:
        photo(c, spec, x, y, dw, dh)
    top = min(p[2] for p in placed) - 16
    c.setFillColor(SKY_TINT); c.roundRect(M - 8, M - 6, width + 16, top - M + 8, 10, stroke=0, fill=1)
    c.setFillColor(SKY_DEEP); c.setFont('UI-B', 9.5)
    c.drawString(M + 2, top - 15, 'CHECKLIST  ·  ' + PHASE_NAMES[page['phase']].upper())
    c.drawRightString(M + width, top - 15, 'ITEM  ·  RESPONSE  ·  HOW')
    top -= 26
    for i, s in enumerate(page['steps']):
        if i:
            c.setStrokeColor(SKY_LINE); c.setLineWidth(.8); c.line(M + 38, top + 6, M + width, top + 6)
        top -= step_block(c, M, top, width, s)
    assert top >= M - 4, (page['title'], top)


def cover(c, total):
    c.setFillColor(white); c.rect(0, 0, W, H, stroke=0, fill=1)
    img = Image.open(ASSETS / COVER).convert('RGB').crop((690, 380, 1890, 1230))
    img = ImageEnhance.Contrast(img).enhance(1.05)
    buf = BytesIO(); img.save(buf, format='JPEG', quality=94)
    iw = W; ih = iw * img.height / img.width
    c.drawImage(ImageReader(BytesIO(buf.getvalue())), 0, H - ih, iw, ih)
    for i in range(80):                                   # fade the bottom of the photo to navy
        c.setFillColor(Color(0.043, 0.133, 0.22, alpha=(i / 80) ** 1.4 * .9))
        c.rect(0, H - ih + (80 - i) * 2.4 - 2.4, W, 2.5, stroke=0, fill=1)
    c.setFillColor(white); c.roundRect(M - 4, H - 104, 92, 82, 10, stroke=0, fill=1)
    logo(c, M + 4, H - 98, 70)
    c.setFillColor(white); c.setFont('UI-BL', 60); c.drawString(M - 2, H - ih + 64, 'CITATION X')
    c.setFont('UI-SB', 16); c.drawString(M, H - ih + 38, 'Illustrated normal checklist')
    c.setFillColor(SKY); c.rect(0, H - ih - 10, W, 10, stroke=0, fill=1)
    y = H - ih - 50
    c.setFillColor(NAVY); c.setFont('UI-B', 21); c.drawString(M, y, 'Before Start to Shutdown')
    starts = {}
    for n, pg in enumerate(PAGES, 2):
        starts.setdefault(pg['phase'], n)
    counts = EXPECTED
    y -= 16
    w = (W - 2 * M - 18) / 4
    for stage, members in STAGES:
        c.setFillColor(SKY_DEEP); c.setFont('UI-B', 9); c.drawString(M, y - 10, stage)
        y -= 14
        for k, i in enumerate(members):
            x = M + k * (w + 6)
            c.setFillColor(SKY_TINT); c.roundRect(x, y - 44, w, 44, 8, stroke=0, fill=1)
            c.setFillColor(SKY); c.roundRect(x, y - 4, w, 4, 2, stroke=0, fill=1)
            c.setFillColor(NAVY); c.setFont('UI-B', 9.5); c.drawString(x + 9, y - 17, PHASES[i])
            c.setFont('UI-BL', 15); c.drawString(x + 9, y - 36, str(counts[i]))
            c.setFont('UI-SB', 9); c.setFillColor(GREY)
            c.drawString(x + 12 + pdfmetrics.stringWidth(str(counts[i]), 'UI-BL', 15), y - 36, f'items  ·  page {starts[i]}')
        y -= 50
    c.setFillColor(GREY); c.setFont('UI', 11.5)
    c.drawString(M, y - 16, f'All {sum(EXPECTED)} items of the FlightFX Citation X Full Checklist, with photos from the cockpit.')
    c.setFillColor(SKY_DEEP); c.setFont('UI-SB', 11); c.drawString(M, M + 30, 'CREATED BY')
    c.setFillColor(NAVY); c.setFont('UI-BL', 26); c.drawString(M, M + 4, 'Kazber')
    c.setFillColor(GREY); c.setFont('UI', 9.5)
    c.drawRightString(W - M, M + 18, 'FlightFX Citation X  ·  Microsoft Flight Simulator 2024')
    c.drawRightString(W - M, M + 5, 'For simulator use only. Not for real-world use.')


def quick_pages(c=None, first_page=0, total=0):
    """Draw (or, with c=None, just count) the quick-checklist pages. Items flow down two columns per page."""
    small_item = ParagraphStyle('qi', fontName='UI-SB', fontSize=10.2, leading=12, textColor=NAVY)
    small_resp = ParagraphStyle('qr', fontName='UI-B', fontSize=10.2, leading=12, textColor=SKY_DEEP, alignment=2)
    col_w = (W - 2 * M - 16) / 2
    iw = col_w * .47
    rw = col_w - 32 - iw - 6
    entries = []
    for ph in range(len(PHASES)):
        entries.append(('H', ph, 26))
        for pg in PAGES:
            if pg['phase'] == ph:
                for st in pg['steps']:
                    h = max(Paragraph(breakable(st[1]), small_item).wrap(iw, 999)[1], Paragraph(breakable(st[2]), small_resp).wrap(rw, 999)[1])
                    entries.append(('I', st, h + 6))
        entries.append(('G', None, 8))
    pages, col, top_start = 1, 0, H - 118
    top = top_start
    def new_page(n):
        if c is not None:
            if n > 1:
                c.showPage()
            c.setFillColor(white); c.rect(0, 0, W, H, stroke=0, fill=1)
            header(c, first_page + n - 1, total, 14, '', label='QUICK CHECKLIST')
            c.setFillColor(NAVY); c.setFont('UI-B', 23)
            c.drawString(M, H - 100, f'All {sum(EXPECTED)} items at a glance')
    new_page(1)
    sections = []
    for kind, data, h in entries:
        if kind == 'H':
            sections.append([data, h, []])
        elif kind == 'I':
            sections[-1][2].append((data, h))
    for ph, head_h, items in sections:
        need = head_h + sum(h for _, h in items)
        if top - need < M:                                  # whole section to the next column / page
            col += 1; top = top_start
            if col == 2:
                col = 0; pages += 1; new_page(pages)
        assert top - need >= M, ('section taller than a column', ph)
        x = M + col * (col_w + 16)
        if c is not None:
            c.setFillColor(SKY); c.roundRect(x, top - 20, col_w, 20, 6, stroke=0, fill=1)
            c.setFillColor(white); c.setFont('UI-B', 10.5); c.drawString(x + 8, top - 14, 'SECOND ENGINE: CROSS BLEED METHOD' if ph == 3 else PHASE_NAMES[ph].upper())
        top -= head_h
        for data, h in items:
            if c is not None:
                num, item, response, _ = data
                c.setStrokeColor(SKY); c.setLineWidth(1.1); c.setFillColor(white)
                c.roundRect(x + 2, top - 10.5, 9, 9, 2, stroke=1, fill=1)
                c.setFillColor(GREY); c.setFont('UI-SB', 8.5); c.drawRightString(x + 28, top - 9, num)
                para(c, item, x + 32, top + 1, iw, small_item)
                para(c, response, x + 32 + iw + 6, top + 1, rw, small_resp)
                c.saveState(); c.setStrokeColor(SKY_LINE); c.setLineWidth(.6)
                c.line(x + 32, top - h + 3.5, x + col_w, top - h + 3.5); c.restoreState()
            top -= h
        top -= 10
    return pages


def build():
    total = len(PAGES) + 1 + quick_pages()
    c = canvas.Canvas(str(OUTPUT), pagesize=(W, H), pageCompression=1)
    c.setTitle('Citation X | Illustrated Normal Checklist')
    c.setAuthor('Kazber')
    c.setSubject('FlightFX Citation X, MSFS 2024: every Full Checklist item from Before Start to Shutdown')
    cover(c, total); c.showPage()
    for n, page in enumerate(PAGES, 2):
        c.bookmarkPage(f'p{n}'); c.addOutlineEntry(f"{PHASES[page['phase']]} {page['part']} - {page['title']}", f'p{n}', 0)
        checklist_page(c, n, total, page); c.showPage()
    quick_pages(c, len(PAGES) + 2, total); c.showPage()
    c.save()

    doc = pymupdf.open(OUTPUT)
    assert len(doc) == total
    previews = ASSETS / 'previews-taxi'; previews.mkdir(exist_ok=True)
    for old in previews.glob('page-*.png'):
        old.unlink()
    for i, page in enumerate(doc):
        for block in page.get_text('blocks'):
            assert block[0] >= 0 and block[1] >= 0 and block[2] <= W + .5 and block[3] <= H + .5, (i, block)
        page.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).save(previews / f'page-{i + 1:02}.png')
    print(f'Created {OUTPUT.name}: {len(doc)} pages, {OUTPUT.stat().st_size:,} bytes; items per phase {_counts}.')


if __name__ == '__main__':
    build()
