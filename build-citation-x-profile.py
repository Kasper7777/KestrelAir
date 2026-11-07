"""Build the FlightFX Cessna Citation X (C750) SPAD profile from the Baron GNS530/TDS650 profile.

Kept from the Baron: both WarBRD sticks (flight controls, ATC, windows, drone), rudder pedals,
throttle axes/flaps/zoom/gear/trims/mouse/Tobii/drone keys, CP3 view keys and squawk encoder,
CP2 gear lever and trim encoders, and the RotAIR radio/transponder/altitude rotaries.
Everything aircraft-specific is replaced with Citation controls that were tested live on
2026-11-04 (see citation-x-profile.md). Run with SPAD closed or with SPAD running; it only writes
a new profile file. Use --install to copy it into Documents/SPAD.neXt/profiles.
"""
from pathlib import Path
import copy, shutil, sys, uuid
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
NS = 'http://www.fsgs.com/SPAD'
E.register_namespace('', NS)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
N = {'s': NS}
SPAD_PROFILES = Path.home() / 'Documents/SPAD.neXt/profiles'
SOURCE = SPAD_PROFILES / 'Baron - GNS 530 + TDS GTNxi 650.xml'
NAME = 'Citation X - FlightFX C750.xml'

THR, CP2, CP3 = '0x0194', '0x025A', '0x025C'
TOP, TOP_ANA, BOT, BOT_ANA, AP, DISP = '0x1290', '0x128F', '0x13E4', '0x13E3', '0x14CA', '0x14CB'


def tag(name): return '{' + NS + '}' + name


# ---- action / condition helpers -------------------------------------------------------------
def lv(name, value): return ('cv', 'LVAR:' + name, str(value), None)
def lvx(name, expr): return ('cv', 'LVAR:' + name, None, expr)
def pv(name, value): return ('cv', 'PROFILE:' + name, str(value), None)
def k(event, param=None, expr=None): return ('ctl', 'SIMCONNECT:' + event, param, expr)
def h(event): return ('ctl', 'H:' + event, None, None)
def b(event): return ('ctl', 'B:' + event, None, None)
def chord(*keys): return ('kb', list(keys), None, None)   # one macro, keys held together 80 ms (as the Baron's)
def eq(src, val): return (src, None, val)
def ne(src, val): return (src, 'Unequal', val)
def lt(src, val): return (src, 'Less', val)
def ge(src, val): return (src, 'GreaterOrEqual', val)
SFS = ne('LVAR:KA_SFS_MONITOR', 1)
PFD, MFD = ne('PROFILE:KA_AVIONICS_FOCUS', 1), eq('PROFILE:KA_AVIONICS_FOCUS', 1)


def D(trigger, acts, *conds): return (trigger, list(conds), acts)
def press(*acts, conds=()): return D('PRESS', list(acts), *conds)


def device(root, product):
    return next(d for d in root.findall('./s:Devices/s:Device', N) if d.get('ProductID') == product)


def events(root, product):
    return device(root, product).find('s:DevicePage/s:Events', N)


def remove(root, product, *bounds):
    parent = events(root, product)
    for event in list(parent):
        if event.get('BoundTo') in bounds:
            parent.remove(event)


def put(root, product, bound, *defs, sfs=False):
    """Replace an input's bindings with the given definitions."""
    remove(root, product, bound)
    event = E.SubElement(events(root, product), tag('Event'), BoundTo=bound)
    edefs = E.SubElement(event, tag('EventDefinitions'))
    for trigger, conds, acts in defs:
        ed = E.SubElement(edefs, tag('EventDefinition'), Trigger=trigger)
        conds = conds + ([SFS] if sfs else [])
        if conds:
            ec = E.SubElement(ed, tag('EventConditions'))
            for src, cmp, val in conds:
                attrs = {'ConditionTargetValue': str(val), 'ConditionValueSource': src}
                if cmp:
                    attrs = {'ConditionComparator': cmp, **attrs}
                E.SubElement(ec, tag('EventCondition'), attrs)
        ea = E.SubElement(ed, tag('EventActions'))
        for kind, target, value, expr in acts:
            if kind == 'kb':
                a = E.SubElement(ea, tag('EventActionKeyboard'), MacroType='PRESSANDRELEASE', TargetWindow='__ACTIVEWINDOW__')
                m = E.SubElement(a, tag('KeyboardMacro'), Duration='80', Repeat='1', Pause='25')
                keys = E.SubElement(m, tag('Keys'))
                for key in target:
                    E.SubElement(keys, tag('Keys')).text = key
                continue
            if kind == 'cv':
                attrs = {'TargetDataDefinition': target}
                if expr is not None:
                    attrs = {'SourceType': 'Exp', 'TargetDataDefinition': target, 'SourceDataDefinition': expr}
                else:
                    attrs['Value'] = value
                E.SubElement(ea, tag('EventActionChangeValue'), attrs)
            else:
                a = E.SubElement(ea, tag('EventActionControl'), TargetDataDefinition=target)
                if expr is not None:
                    E.SubElement(a, tag('Parameter'), Type='Exp', Value=expr)
                elif value is not None:
                    E.SubElement(a, tag('Parameter'), Type='Static', Value=str(value))


def two_pos(root, product, on_btn, off_btn, lvars, on=0, off=1):
    """Latched toggle: up = on, down = off (Citation switches: 0 = up/ON, 1 = down/OFF)."""
    put(root, product, on_btn, press(*[lv(n, on) for n in lvars]))
    put(root, product, off_btn, press(*[lv(n, off) for n in lvars]))


def toggle(root, product, btn, name, a, b_):
    """Push button that flips a switch between positions a and b_."""
    put(root, product, btn, press(lvx(name, f'If([LVAR:{name}] == {a}, {b_}, {a})')))


def axis_condition(root, product, bound, *conds):
    ed = device(root, product).find(f'.//s:Event[@BoundTo="{bound}"]/s:EventDefinitions/s:EventDefinition', N)
    ec = ed.find('s:EventConditions', N)
    if ec is None:
        ec = E.Element(tag('EventConditions'))
        ed.insert(0, ec)
    for src, cmp, val in conds:
        attrs = {'ConditionTargetValue': str(val), 'ConditionValueSource': src}
        if cmp:
            attrs = {'ConditionComparator': cmp, **attrs}
        E.SubElement(ec, tag('EventCondition'), attrs)


def build():
    root = copy.deepcopy(E.parse(SOURCE).getroot())

    # ---- profile variables ---------------------------------------------------------------
    variables = root.find('s:Variables', N)
    for var in list(variables):
        if var.get('Name') in ('PROFILE:KA_AVIONICS_FOCUS', 'PROFILE:KA_XPDR_DIGIT'):
            var.set('Value', '0' if var.get('Name').endswith('FOCUS') else '1')
    for var in list(variables):
        if var.get('Name') in ('PROFILE:KA_REV1', 'PROFILE:KA_REV2'):
            variables.remove(var)

    # ---- MongoosT-50CM3 throttle ---------------------------------------------------------
    # Thrust levers, reversers and fuel cutoff (measured 2026-11-05 on this throttle and aircraft).
    #   Hardware: [EVENT:VALUE] is the raw lever reading at full resolution: 60000 = full forward, 0 = the rear stop
    #   behind the mechanical finger lifts; from forward the levers stop on the idle detent at about 19300, coming
    #   forward again they have been left anywhere from 16800 to 18600.  ([LOCAL:...AXIS] is the same reading as a
    #   whole-number percentage: fine for a button press, too coarse for the lever itself.)
    #   Aircraft: K:THROTTLEn_SET drives the Citation's own thrust lever, linear, 0..16383 = idle..full forward
    #   (the cockpit handle is drawn in whole 1 % steps whatever is sent; with an engine off it tops out at 0.95).
    #   Negative values are the reverse lever, 0..-328 = stowed..fully up, once L:VTX_C750_DETENT_DEADBAND is 0
    #   (1 as loaded, which hides everything short of -164; it resets with every flight, so it is written each time).
    #   L:ENG_CUTOFFn = 0 moves the cockpit handle back into fuel CUTOFF; an idle-or-forward THROTTLEn_SET puts it
    #   back to RUN by itself.
    #   Lever: 20040..60000 = idle..full forward; 15000..20040 = idle; 600..15000 = idle, fuel RUN; the last bit
    #   against the rear stop (600 or less) = fuel CUTOFF.  No throttle command is sent below 15000, so nothing
    #   races the cutoff write.
    #   Reversers: the three-way switch on each throttle grip, held (2026-11-05, recorded from the hardware):
    #   press down = medium reverse, pull back = full, push forward = low.  Left grip = buttons 5 / 7 / 6 -> engine 1,
    #   right grip (the one with the mini-stick) = 8 / 11 / 9 -> engine 2.  Commands -168 / -328 / -8, which with
    #   the deadband at 0 are the reverse lever at 51 % / 100 % / 2 % and an N1 target of about 78 % / 87 % / 68 %.
    #   While one is held PROFILE:KA_REVn is 1 and that lever's forward-thrust command is paused; releasing it stows
    #   the reverser and sends the forward value for where the lever is.  They only act with that engine running:
    #   with it off the aircraft answers a reverse command by throwing the main handle backwards.
    def fraction(source, low, span):
        return f'Min(1.0, Max(0.0, ({source} - {low}) / {span}))'
    for axis, engine, switch in [('X', 1, {5: 168, 7: 328, 6: 8}), ('Y', 2, {8: 168, 11: 328, 9: 8})]:
        local = fraction(f'[LOCAL:JOY_0X33440X0194_{axis}_AXIS]', '33.4', '66.6')
        raw = fraction('[EVENT:VALUE]', '20040.0', '39960.0')
        # Read the physical switches: saved PROFILE flags can remain set after a missed release.
        reverse_released = [eq(f'LOCAL:JOY_0X33440X0194_BUTTON_{button}', 0) for button in switch]
        put(root, THR, f'{axis}_AXIS',
            D('VALUE', [lv('VTX_C750_DETENT_DEADBAND', 0), k(f'THROTTLE{engine}_SET', expr=f'Round({raw} * 16383.0, 0)')],
              ('EVENT:VALUE', 'Greater', 15000), *reverse_released),
            # At the forward stop also set the aircraft's own handle (what the mouse drags) to 1: with the engines
            # off the K event above only takes the handle to 0.95, the input event takes it to the end (measured).
            D('VALUE', [('cv', f'B:ENGINE_THROTTLE_{engine}', '1', None)], ('EVENT:VALUE', 'GreaterOrEqual', 59900), *reverse_released),
            D('VALUE', [lv(f'ENG_CUTOFF_{engine}', 1)], ('EVENT:VALUE', 'Greater', 600), ('EVENT:VALUE', 'LessOrEqual', 15000)),
            D('VALUE', [lv(f'ENG_CUTOFF_{engine}', 0)], ('EVENT:VALUE', 'LessOrEqual', 600)))
        for button, level in switch.items():
            put(root, THR, f'BUTTON_{button}',
                D('PRESS', [lv('VTX_C750_DETENT_DEADBAND', 0), k(f'THROTTLE{engine}_SET', expr=f'0 - {level}')],
                  eq(f'SIMCONNECT:GENERAL ENG COMBUSTION:{engine}', 1)),
                D('RELEASE', [k(f'THROTTLE{engine}_SET', expr=f'Round({local} * 16383.0, 0)')]))
    # T1 (buttons 34/35) and T2 (36/37) are unassigned: T1 duplicated the parking brake (T4) and T2 the gear lever
    # on the CP2.  The mouse click is the mini-stick press (13) alone, handled by ka-mouse.
    remove(root, THR, 'BUTTON_34', 'BUTTON_35', 'BUTTON_36', 'BUTTON_37')
    for btn, val in [(40, 0), (41, 1)]:   # parking brake (T4)
        put(root, THR, f'BUTTON_{btn}', press(k('PARKING_BRAKE_SET', val)))
    # Tobii B3 (BUTTON_44, Alt+7 toggle) is inherited unchanged from the Baron.  B6 (BUTTON_47, tracking
    # reset) sends the Baron's Alt+8 and then Shift+Space.  MSFS picks the keyboard profile per aircraft, and
    # the Citation is on the sim default, which resets tracking on Shift+Space (and recentres the cockpit view
    # with the same key); the custom profile the Baron uses resets it on Alt+8.  Sending both works on either,
    # on any computer.  Each is ONE macro holding both keys; separate Alt-down / digit / Alt-up macros failed.
    # The Baron and Bonanza profiles keep Alt+8 only (user: the Baron works, leave it alone).
    put(root, THR, 'BUTTON_47', press(chord('LMenu', 'D8'), chord('LShiftKey', 'Space')))
    put(root, THR, 'BUTTON_48', press(lv('lights_knob_flood', 80)))          # T5 cockpit flood
    put(root, THR, 'BUTTON_49', press(lv('lights_knob_flood', 0)))
    put(root, THR, 'BUTTON_50', press(*[lv(n, 60) for n in ('lights_knob_lh', 'lights_knob_ctr', 'lights_knob_rh', 'lights_knob_el')]))
    put(root, THR, 'BUTTON_51', press(*[lv(n, 0) for n in ('lights_knob_lh', 'lights_knob_ctr', 'lights_knob_rh', 'lights_knob_el')]))
    two_pos(root, THR, 'BUTTON_52', 'BUTTON_53', ['knob_eng_sync'])          # T7 engine sync
    put(root, THR, 'BUTTON_55', press(lvx('knob_pressurization_rate', 'Max(0, [LVAR:knob_pressurization_rate] - 5)')))
    put(root, THR, 'BUTTON_56', press(lvx('knob_pressurization_rate', 'Min(100, [LVAR:knob_pressurization_rate] + 5)')))
    remove(root, THR, 'BUTTON_58', 'BUTTON_59')
    # Five-position selector = LEFT engine ignition: OFF, NORM, ON (continuous), NORM, START.
    ign_start(root, THR, ['BUTTON_60', 'BUTTON_61', 'BUTTON_62', 'BUTTON_63', 'BUTTON_64'], 'l', 1)

    # ---- VPC Control Panel #3 ------------------------------------------------------------
    for btn, n in [(1, 1), (2, 2)]:
        toggle(root, CP3, f'BUTTON_{btn}', f'ELECTRICAL_Switch_Battery_{n}', 0, 1)
    for btn, n in [(3, 1), (4, 2)]:
        toggle(root, CP3, f'BUTTON_{btn}', f'ELECTRICAL_Switch_Avionics_Master_{n}', 0, 1)
    # Fuel boost pumps mirror the cockpit switch position for position: up = ON (0), centre = OFF (1),
    # down = NORM (2).  (Until 2026-11-04 centre and down were swapped, so the switch moved in the wrong order.)
    for btns, side in [((14, 15, 16), 'lh'), ((34, 35, 36), 'rh')]:
        for btn, val in zip(btns, (0, 1, 2)):
            put(root, CP3, f'BUTTON_{btn}', press(lv(f'switch_fuel_boost_{side}', val)))
    two_pos(root, CP3, 'BUTTON_17', 'BUTTON_18', ['switch_pitot_static_lh'])
    two_pos(root, CP3, 'BUTTON_19', 'BUTTON_20', ['switch_pitot_static_rh'])
    two_pos(root, CP3, 'BUTTON_21', 'BUTTON_22', ['switch_engine_ai_lh', 'switch_engine_ai_rh'])
    two_pos(root, CP3, 'BUTTON_23', 'BUTTON_24', ['switch_slats_ai'])
    two_pos(root, CP3, 'BUTTON_25', 'BUTTON_26', ['switch_stabilizer_ai_lh', 'switch_stabilizer_ai_rh'])
    two_pos(root, CP3, 'BUTTON_27', 'BUTTON_28', ['switch_windshield_lh', 'switch_windshield_rh'], on=0, off=2)
    two_pos(root, CP3, 'BUTTON_29', 'BUTTON_30', ['switch_seatBelt'])
    # B8-B12 = Citation instrument views 8/5/4/3/6, matched on screen 2026-11-04 (the Citation numbers its
    # views differently from the Baron).  Same kind of macro as the Baron: Shift+N held together.  Measured
    # live in the Citation: Shift+N goes to the view, the same key again returns to the pilot view.  Keep it a
    # key macro; writing the camera SimVars directly loses that press-again-for-pilot-view behaviour.
    # B13 (Backspace = outside/cockpit toggle) is inherited from the Baron.
    for btn, digit in [(8, 'D8'), (9, 'D5'), (10, 'D4'), (11, 'D3'), (12, 'D6')]:
        put(root, CP3, f'BUTTON_{btn}', press(chord('LShiftKey', digit)))
    put(root, CP3, 'BUTTON_6', D('PRESS', [lv('AUTOPILOT_push_Ats', 1)]), D('RELEASE', [lv('AUTOPILOT_push_Ats', 0)]))
    # Rotary selector = RIGHT engine ignition, physical OFF is button 47 (as for the Baron magneto).
    ign_start(root, CP3, ['BUTTON_47', 'BUTTON_46', 'BUTTON_45', 'BUTTON_44', 'BUTTON_43'], 'r', 2)
    # L / R switch (BUTTON_31 left, 32 centre, 33 right; unbound in the Baron): engine START left / right.
    # Same command as the START position of each selector, and only while that engine isn't already running.
    for btn, side, engine in [(31, 'l', 1), (33, 'r', 2)]:
        idle = eq(f'SIMCONNECT:GENERAL ENG COMBUSTION:{engine}', 0)
        put(root, CP3, f'BUTTON_{btn}',
            press(lv(f'Switch_ignition_{side}', 2), conds=[idle]),
            press(k(f'TOGGLE_STARTER{engine}'), conds=[idle, eq(f'SIMCONNECT:GENERAL ENG STARTER:{engine}', 0)]))
    # First inner lever (X, the Baron's left prop lever) = speedbrake, forward = retracted.
    ext = 'Min(100.0, Max(0.0, (95.0 - [LOCAL:JOY_0X33440X025C_X_AXIS]) * 100.0 / 90.0))'
    # This aircraft's spoiler axis runs 0 (stowed) .. 16383 (full), measured live.
    put(root, CP3, 'X_AXIS', D('VALUE', [k('AXIS_SPOILER_SET', expr=f'Round({ext} * 163.83, 0)')]))
    # The second inner lever (Y, the Baron's right prop lever) is unassigned: reverse thrust lives on the CM3 thrust
    # levers behind the idle detent.  (Until 2026-11-05 this lever was an on/off reverser that froze the throttles.)
    remove(root, CP3, 'Y_AXIS')
    # Outer lever pair (the Baron's mixtures) is unassigned too.  It used to be fuel RUN / CUTOFF, but in the Citation
    # cutoff is a position of the thrust levers, so those CP3 levers visibly moved the throttles; the user wants
    # the CP3 levers to do the speedbrake and nothing else (2026-11-05).  Moving a CM3 thrust lever puts that
    # engine's fuel to RUN by itself (seen live); CUTOFF is done in the cockpit.
    remove(root, CP3, 'RX_AXIS', 'RY_AXIS')

    # ---- VPC Control Panel #2 ------------------------------------------------------------
    put(root, CP2, 'BUTTON_1', press(k('GEAR_UP')))
    put(root, CP2, 'BUTTON_3', press(k('GEAR_DOWN')))
    ac = 'switch_lights_recognition_antiCollision'          # 0 = beacon + strobe, 1 = beacon, 2 = off
    put(root, CP2, 'BUTTON_17', press(lv(ac, 0)))
    put(root, CP2, 'BUTTON_18', press(lvx(ac, f'If([LVAR:{ac}] == 0, 1, [LVAR:{ac}])')))
    put(root, CP2, 'BUTTON_19', press(lvx(ac, f'If([LVAR:{ac}] == 2, 1, [LVAR:{ac}])')))
    put(root, CP2, 'BUTTON_20', press(lv(ac, 2)))
    two_pos(root, CP2, 'BUTTON_21', 'BUTTON_22', ['switch_lights_nav'])
    two_pos(root, CP2, 'BUTTON_23', 'BUTTON_24', ['switch_landing_taxi'])
    two_pos(root, CP2, 'BUTTON_25', 'BUTTON_26', ['switch_landing_light_lh'])
    two_pos(root, CP2, 'BUTTON_27', 'BUTTON_28', ['switch_landing_light_rh'])
    two_pos(root, CP2, 'BUTTON_29', 'BUTTON_30', ['electrical_switch_generator_l'])
    two_pos(root, CP2, 'BUTTON_31', 'BUTTON_32', ['electrical_switch_generator_r'])
    two_pos(root, CP2, 'BUTTON_33', 'BUTTON_34', ['switch_lights_recog'])
    two_pos(root, CP2, 'BUTTON_35', 'BUTTON_36', ['switch_lights_flood'])     # tail logo floodlight
    toggle(root, CP2, 'BUTTON_4', 'electrical_switch_apu_master', 1, 0)
    put(root, CP2, 'BUTTON_5', D('PRESS', [lv('electrical_switch_apu_starter', 0)]),
        D('RELEASE', [lv('electrical_switch_apu_starter', 1)]))
    toggle(root, CP2, 'BUTTON_6', 'electrical_switch_apu', 0, 1)              # APU generator
    toggle(root, CP2, 'BUTTON_7', 'switch_apu_bleed', 1, 2)
    toggle(root, CP2, 'BUTTON_37', 'switch_stby_pwr', 0, 1)
    toggle(root, CP2, 'BUTTON_38', 'lights_emerg_lt', 0, 2)                   # emergency lights ARM / OFF
    toggle(root, CP2, 'BUTTON_39', 'knob_irs_l', 2, 0)                        # IRS NAV / OFF
    toggle(root, CP2, 'BUTTON_40', 'knob_irs_r', 2, 0)

    # ---- RotAIR top (GC and ANA identities) ---------------------------------------------
    for dev in (TOP, TOP_ANA):
        # Transponder ALT is state 4 here; the Black Square value 3 is forced back to STBY (tested).
        put(root, dev, 'BUTTON_4', press(('cv', 'SIMCONNECT:TRANSPONDER STATE:1', '4', None)), sfs=True)
        put(root, dev, 'BUTTON_2', press(k('HEADING_BUG_SET', expr='Round([SIMCONNECT:PLANE HEADING DEGREES MAGNETIC], 0)')), sfs=True)
        for btn, d_ in [(19, 'INC'), (20, 'DEC')]:                            # former gyro ring = speed bug
            put(root, dev, f'BUTTON_{btn}',
                press(k(f'AP_MACH_VAR_{d_}'), conds=[eq('SIMCONNECT:AUTOPILOT MANAGED SPEED IN MACH', 1)]),
                press(k(f'AP_SPD_VAR_{d_}'), conds=[ne('SIMCONNECT:AUTOPILOT MANAGED SPEED IN MACH', 1)]), sfs=True)

    # ---- RotAIR bottom (GC and ANA identities) ------------------------------------------
    def fmc(key, conds=()):
        return [press(h(f'WT21_FMC_1_BTN_{key}'), conds=[PFD, *conds]),
                press(h(f'WT21_FMC_2_BTN_{key}'), conds=[MFD, *conds])]
    def both(event_fmt, conds=()):
        return [press(b(event_fmt.format(1)), conds=[PFD, *conds]), press(b(event_fmt.format(2)), conds=[MFD, *conds])]
    # NAV source is deliberately not on hardware: its knob only toggles VOR1/VOR2 once off FMS,
    # and no input reaches FMS again (tested), so a button would strand LNAV.  CDI opens TUN.
    for dev in (BOT, BOT_ANA):
        for btn in (13, 21, 29):
            put(root, dev, f'BUTTON_{btn}', *both('AS3000_UPPER_{}_RANGE_INC'), sfs=True)
        for btn in (14, 22, 30):
            put(root, dev, f'BUTTON_{btn}', *both('AS3000_UPPER_{}_RANGE_DEC'), sfs=True)
        # FMS knob: either ring pages the FMC (clockwise = next), push = MFD ADV.  The GC identity
        # uses 34-40 for COM2 / course 2, so the alternate FMS bank 34-38 is ANA-only.
        fms_bank = dev == BOT_ANA
        for btn in (15, 23) + ((34, 36) if fms_bank else ()):
            put(root, dev, f'BUTTON_{btn}', *fmc('NEXTPAGE'), sfs=True)
        for btn in (16, 24) + ((35, 37) if fms_bank else ()):
            put(root, dev, f'BUTTON_{btn}', *fmc('PREVPAGE'), sfs=True)
        for btn in (4,) + ((38,) if fms_bank else ()):
            put(root, dev, f'BUTTON_{btn}', *fmc('MFD_ADV'), sfs=True)
        put(root, dev, 'BUTTON_3', *fmc('FPLN'), sfs=True)
        put(root, dev, 'BUTTON_8', *fmc('TUN'), sfs=True)
        put(root, dev, 'BUTTON_2', *fmc('LEGS'), sfs=True)
        put(root, dev, 'BUTTON_6', *fmc('MFD_DATA'), sfs=True)
        put(root, dev, 'BUTTON_7', *fmc('DSPL_MENU'), sfs=True)

    # ---- PulsAIR autopilot module ---------------------------------------------------------
    put(root, AP, 'BUTTON_9', press(b('AUTOPILOT_VNAV_MODE_Push')), sfs=True)
    put(root, AP, 'BUTTON_10', press(k('YAW_DAMPER_TOGGLE')), sfs=True)

    # ---- PulsAIR display module: FMC keys; PFD = left side (FMC 1), MFD = right side (FMC 2) --
    keys = {'DIR': (26, 1, 13, 19), 'FPLN': (27, 2, 14, 20), 'CLR': (3, 15, 21), 'CLR_LONG': (28,),
            'IDX': (32, 7, 16, 22), 'DEPARR': (33, 8, 17, 23), 'EXEC': (34, 9, 18, 24),
            'LEGS': (6, 31), 'PERF': (11, 36), 'MSG': (12, 37), 'MFD_ADV': (29,), 'DSPL_MENU': (35,)}
    for key, btns in keys.items():
        for btn in btns:
            put(root, DISP, f'BUTTON_{btn}', *fmc(key), sfs=True)
    for btn in (5, 25, 30):
        put(root, DISP, f'BUTTON_{btn}', *fmc('TUN'), sfs=True)
    put(root, DISP, 'BUTTON_4', press(pv('KA_AVIONICS_FOCUS', 0)), sfs=True)
    put(root, DISP, 'BUTTON_10', press(pv('KA_AVIONICS_FOCUS', 1)), sfs=True)

    # ---- profile information -------------------------------------------------------------
    info = root.find('s:ProfileInformation', N)
    info.set('ProfileID', str(uuid.uuid4()))
    info.set('Version', '1.0')
    info.find('s:Description', N).text = ('<HTML><BODY><P>FlightFX Cessna Citation X (C750); derived from the Baron '
        'GNS530/TDS650 hardware layout. Controls verified live 2026-11-04; see citation-x-profile.md.</P></BODY></HTML>')

    xml = E.tostring(root, encoding='unicode')
    for forbidden in ['bksq', 'BKSQ', 'LVAR:var_', 'TDSGTNXI', 'AS530', 'B:LIGHTING_', 'B:ELECTRICAL_', 'B:ENGINE_COWL',
                      'B:INSTRUMENT_HEADING_BUG', 'B:LANDING_GEAR_PARKINGBRAKE', 'GYRO_DRIFT', 'RECIP ENG', 'PITOT_HEAT_TOGGLE',
                      'BATTERY2_SET', 'AVIONICS_MASTER_2_SET', 'BKSQ_IGNITION', 'MIXTURE']:
        assert forbidden not in xml, forbidden
    E.indent(root, space='  ')
    return root


def ign_start(root, product, bounds, side, engine):
    """OFF / NORM / ON / NORM / START.  START also presses the engine START button once."""
    sw = f'Switch_ignition_{side}'
    for bound, val in zip(bounds[:4], (1, 2, 0, 2)):
        put(root, product, bound, press(lv(sw, val)))
    put(root, product, bounds[4],
        press(lv(sw, 2)),
        press(k(f'TOGGLE_STARTER{engine}'), conds=[eq(f'SIMCONNECT:GENERAL ENG STARTER:{engine}', 0)]))


if __name__ == '__main__':
    root = build()
    out = ROOT / 'profiles' / NAME
    E.ElementTree(root).write(out, encoding='utf-8', xml_declaration=False)
    print('Created', out)
    if '--install' in sys.argv:
        shutil.copy2(out, SPAD_PROFILES / NAME)
        print('Installed', SPAD_PROFILES / NAME)
