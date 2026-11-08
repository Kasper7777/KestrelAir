"""Live check of the Citation X SPAD profile against the running FlightFX C750 (MSFS 2024).

For each test the script reads the binding straight out of the generated profile XML, evaluates its
conditions, executes its actions (LVAR writes via SimConnect, K/H/B events via the MobiFlight WASM
calculator bridge) and checks the aircraft's response.  It does not press hardware or go through SPAD,
so it proves the targets and values, not the physical button numbers.  The aircraft must be parked
cold and dark; the original switch state is restored at the end.  Results go to
verify-citation-x-results.txt.
"""
import ctypes as c, re, struct, sys, time
from pathlib import Path
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / 'profiles' / 'Citation X - FlightFX C750.xml'
NS = {'s': 'http://www.fsgs.com/SPAD'}
T = '{http://www.fsgs.com/SPAD}'

d = c.WinDLL(r'D:\SteamLibrary\steamapps\common\MSFS2024\SimConnect_internal.dll')
d.SimConnect_Open.argtypes = [c.POINTER(c.c_void_p), c.c_char_p, c.c_void_p, c.c_uint, c.c_void_p, c.c_uint]
d.SimConnect_GetNextDispatch.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_uint)]
d.SimConnect_AddToDataDefinition.argtypes = [c.c_void_p, c.c_uint, c.c_char_p, c.c_char_p, c.c_uint, c.c_float, c.c_uint]
d.SimConnect_RequestDataOnSimObject.argtypes = [c.c_void_p] + [c.c_uint] * 8
d.SimConnect_SetDataOnSimObject.argtypes = [c.c_void_p, c.c_uint, c.c_uint, c.c_uint, c.c_uint, c.c_uint, c.c_void_p]
d.SimConnect_MapClientDataNameToID.argtypes = [c.c_void_p, c.c_char_p, c.c_uint]
d.SimConnect_AddToClientDataDefinition.argtypes = [c.c_void_p, c.c_uint, c.c_uint, c.c_uint, c.c_float, c.c_uint]
d.SimConnect_SetClientData.argtypes = [c.c_void_p, c.c_uint, c.c_uint, c.c_uint, c.c_uint, c.c_uint, c.c_void_p]
h = c.c_void_p()
assert d.SimConnect_Open(c.byref(h), b'KestrelAir C750 profile check', None, 0, None, 0) == 0
assert d.SimConnect_MapClientDataNameToID(h, b'MobiFlight.Command', 9) == 0
assert d.SimConnect_AddToClientDataDefinition(h, 90, 0, 1024, 0, 0xffffffff) == 0
_defs = [100]
UNITS = {'PLANE HEADING DEGREES MAGNETIC': b'degrees', 'AUTOPILOT HEADING LOCK DIR': b'degrees',
         'AUTOPILOT ALTITUDE LOCK VAR': b'feet'}


def pump(t):
    end = time.monotonic() + t
    while time.monotonic() < end:
        p, n = c.c_void_p(), c.c_uint()
        if d.SimConnect_GetNextDispatch(h, c.byref(p), c.byref(n)) == 0:
            yield c.string_at(p, n.value)
        else:
            time.sleep(0.005)


def name_unit(src):
    if src.startswith('LVAR:'):
        return 'L:' + src[5:], b'number'
    if src.startswith('SIMCONNECT:'):
        n = src[11:]
        return n, UNITS.get(n.split(':')[0], b'number')
    return src, b'number'


def read(srcs):
    _defs[0] += 1
    did = _defs[0]
    for s in srcs:
        n, u = name_unit(s)
        d.SimConnect_AddToDataDefinition(h, did, n.encode(), u, 4, 0, 0xffffffff)
    d.SimConnect_RequestDataOnSimObject(h, did, did, 0, 1, 0, 0, 0, 0)
    for raw in pump(4):
        if struct.unpack_from('<I', raw, 8)[0] == 8 and struct.unpack_from('<I', raw, 12)[0] == did:
            return dict(zip(srcs, struct.unpack_from(f'<{len(srcs)}d', raw, 40)))
    raise RuntimeError('no data for ' + ', '.join(srcs))


def write(src, value):
    _defs[0] += 1
    did = _defs[0]
    n, u = name_unit(src)
    d.SimConnect_AddToDataDefinition(h, did, n.encode(), u, 4, 0, 0xffffffff)
    v = c.c_double(value)
    d.SimConnect_SetDataOnSimObject(h, did, 0, 0, 0, 8, c.byref(v))


_nop = [0]
def calc(code):
    _nop[0] += 1   # MobiFlight ignores a command identical to the previous one
    buf = c.create_string_buffer(f'MF.SimVars.Set.{_nop[0]} (>L:KA_VERIFY_NOP) {code}'.encode(), 1024)
    d.SimConnect_SetClientData(h, 9, 90, 0, 0, 1024, buf)
    list(pump(0.12))


# ---- SPAD semantics --------------------------------------------------------------------------
profile_vars = {}
tree = E.parse(PROFILE).getroot()
for v in tree.findall('s:Variables/s:Variable', NS):
    profile_vars['PROFILE:' + v.get('Name').split(':', 1)[1]] = float(v.get('Value'))
DEVICES = {}
for dev in tree.findall('s:Devices/s:Device', NS):
    for ev in dev.findall('.//s:Event', NS):
        DEVICES.setdefault(dev.get('ProductID'), {}).setdefault(ev.get('BoundTo'), ev)


def value_of(src, ctx):
    if src in ctx:
        return ctx[src]
    if src.startswith('PROFILE:'):
        return profile_vars.get(src, 0.0)
    return read([src])[src]


def evaluate(expr, ctx):
    names = re.findall(r'\[([^\]]+)\]', expr)
    py = expr
    for n in set(names):
        py = py.replace(f'[{n}]', repr(value_of(n, ctx)))
    py = re.sub(r'\bIf\(', '_if(', py, flags=re.I)
    return eval(py, {'_if': lambda a, b, c_: b if a else c_, 'Round': lambda x, n=0: round(x, int(n)),
                     'Min': min, 'Max': max, 'if': None})


def conditions_ok(ed, ctx):
    for cond in ed.findall('s:EventConditions/s:EventCondition', NS):
        val = value_of(cond.get('ConditionValueSource'), ctx)
        tgt = float(cond.get('ConditionTargetValue'))
        cmp = cond.get('ConditionComparator', 'Equals')
        ok = {'Equals': abs(val - tgt) < 1e-6, 'Unequal': abs(val - tgt) >= 1e-6, 'Less': val < tgt,
              'Greater': val > tgt, 'GreaterOrEqual': val >= tgt, 'LessOrEqual': val <= tgt}[cmp]
        if not ok:
            return False
    return True


def fire(product, bound, trigger='PRESS', **ctx):
    """Run every matching definition of one input, as SPAD would."""
    ev = DEVICES[product][bound]
    ctx = {('EVENT:VALUE' if k == 'value' else k): v for k, v in ctx.items()}
    sent = []
    for ed in ev.findall('s:EventDefinitions/s:EventDefinition', NS):
        if ed.get('Trigger') != trigger or not conditions_ok(ed, ctx):
            continue
        for a in ed.find('s:EventActions', NS):
            tgt = a.get('TargetDataDefinition')
            if a.tag == T + 'EventActionChangeValue':
                val = evaluate(a.get('SourceDataDefinition'), ctx) if a.get('SourceType') == 'Exp' else float(a.get('Value'))
                if tgt.startswith('PROFILE:'):
                    profile_vars[tgt] = val
                else:
                    write(tgt, val)
                sent.append(f'{tgt}={val:g}')
            elif a.tag == T + 'EventActionControl':
                p = a.find('s:Parameter', NS)
                param = '' if p is None else f"{evaluate(p.get('Value'), ctx) if p.get('Type') == 'Exp' else p.get('Value')} "
                kind, name = tgt.split(':', 1)
                calc(f'{param}(>{"K" if kind == "SIMCONNECT" else kind}:{name})')
                sent.append(f'{tgt}({param.strip()})')
        time.sleep(0.15)
    return sent


# ---- tests -----------------------------------------------------------------------------------
THR, CP2, CP3 = '0x0194', '0x025A', '0x025C'
TOP, BOT, AP, DISP = '0x1290', '0x13E4', '0x14CA', '0x14CB'
log, failures = [], []


def check(label, product, bound, expect, trigger='PRESS', settle=1.2, **ctx):
    sent = fire(product, bound, trigger, **ctx)
    time.sleep(settle)
    got = read(list(expect))
    bad = {k: round(got[k], 3) for k, want in expect.items() if not (want(got[k]) if callable(want) else abs(got[k] - want) < 0.02)}
    line = f"{'PASS' if not bad else 'FAIL'}  {label:<44} {product} {bound:<10} -> {', '.join(sent) or '(no action)'}"
    if bad:
        line += f'   got {bad}'
        failures.append(label)
    print(line, flush=True)
    log.append(line)


SAVE = ['LVAR:' + n for n in ('ELECTRICAL_Switch_Battery_1', 'ELECTRICAL_Switch_Battery_2', 'ELECTRICAL_Switch_Avionics_Master_1',
        'ELECTRICAL_Switch_Avionics_Master_2', 'switch_lights_recognition_antiCollision', 'switch_lights_nav', 'switch_landing_taxi',
        'switch_landing_light_lh', 'switch_landing_light_rh', 'switch_lights_recog', 'switch_lights_flood', 'switch_fuel_boost_lh',
        'switch_fuel_boost_rh', 'switch_pitot_static_lh', 'switch_pitot_static_rh', 'switch_engine_ai_lh', 'switch_engine_ai_rh',
        'switch_slats_ai', 'switch_stabilizer_ai_lh', 'switch_stabilizer_ai_rh', 'switch_windshield_lh', 'switch_windshield_rh',
        'switch_seatBelt', 'Switch_ignition_l', 'Switch_ignition_r', 'electrical_switch_generator_l', 'electrical_switch_generator_r',
        'electrical_switch_apu_master', 'electrical_switch_apu', 'switch_apu_bleed', 'switch_stby_pwr', 'lights_emerg_lt',
        'knob_irs_l', 'knob_irs_r', 'knob_eng_sync', 'lights_knob_flood', 'lights_knob_lh', 'lights_knob_ctr', 'lights_knob_rh',
        'lights_knob_el', 'knob_pressurization_rate', 'ENG_CUTOFF_1', 'ENG_CUTOFF_2')]
state = read(SAVE)
sim0 = read(['SIMCONNECT:BRAKE PARKING POSITION', 'SIMCONNECT:TRANSPONDER STATE:1', 'SIMCONNECT:FLAPS HANDLE INDEX'])
assert read(['SIMCONNECT:SIM ON GROUND'])['SIMCONNECT:SIM ON GROUND'] == 1, 'aircraft must be on the ground'
try:
    S = 'SIMCONNECT:'
    check('CP3 B1 battery 1 on', CP3, 'BUTTON_1', {S + 'ELECTRICAL MASTER BATTERY:1': 1})
    check('CP3 B2 battery 2 on', CP3, 'BUTTON_2', {S + 'ELECTRICAL MASTER BATTERY:2': 1})
    check('CP3 B3 avionics 1 on', CP3, 'BUTTON_3', {S + 'AVIONICS MASTER SWITCH:1': 1})
    check('CP3 B4 avionics 2 on', CP3, 'BUTTON_4', {S + 'AVIONICS MASTER SWITCH:2': 1})
    check('CP2 T2 beacon on', CP2, 'BUTTON_19', {S + 'LIGHT BEACON': 1, S + 'LIGHT STROBE': 0})
    check('CP2 T1 strobe on', CP2, 'BUTTON_17', {S + 'LIGHT BEACON': 1, S + 'LIGHT STROBE': 1})
    check('CP2 T1 strobe off, beacon stays', CP2, 'BUTTON_18', {S + 'LIGHT BEACON': 1, S + 'LIGHT STROBE': 0})
    check('CP2 T2 beacon off', CP2, 'BUTTON_20', {S + 'LIGHT BEACON': 0, S + 'LIGHT STROBE': 0})
    check('CP2 T3 nav on', CP2, 'BUTTON_21', {S + 'LIGHT NAV': 1})
    check('CP2 T3 nav off', CP2, 'BUTTON_22', {S + 'LIGHT NAV': 0})
    check('CP2 T4 taxi on', CP2, 'BUTTON_23', {S + 'LIGHT TAXI': 1})
    check('CP2 T4 taxi off', CP2, 'BUTTON_24', {S + 'LIGHT TAXI': 0})
    check('CP2 T5 left landing on', CP2, 'BUTTON_25', {S + 'LIGHT LANDING ON:2': 1})
    check('CP2 T5 left landing off', CP2, 'BUTTON_26', {S + 'LIGHT LANDING ON:2': 0})
    check('CP2 T6 right landing on', CP2, 'BUTTON_27', {S + 'LIGHT LANDING ON:1': 1})
    check('CP2 T6 right landing off', CP2, 'BUTTON_28', {S + 'LIGHT LANDING ON:1': 0})
    check('CP2 T9 recognition on', CP2, 'BUTTON_33', {S + 'LIGHT RECOGNITION': 1})
    check('CP2 T9 recognition off', CP2, 'BUTTON_34', {S + 'LIGHT RECOGNITION': 0})
    check('CP2 T10 logo light on', CP2, 'BUTTON_35', {S + 'LIGHT LOGO': 1})
    check('CP2 T10 logo light off', CP2, 'BUTTON_36', {S + 'LIGHT LOGO': 0})
    check('CP3 T1 left boost OFF', CP3, 'BUTTON_15', {S + 'GENERAL ENG FUEL PUMP SWITCH:1': 0})
    check('CP3 T1 left boost NORM', CP3, 'BUTTON_16', {S + 'GENERAL ENG FUEL PUMP SWITCH:1': 1})
    check('CP3 ARM right boost OFF', CP3, 'BUTTON_35', {S + 'GENERAL ENG FUEL PUMP SWITCH:2': 0})
    check('CP3 ARM right boost NORM', CP3, 'BUTTON_36', {S + 'GENERAL ENG FUEL PUMP SWITCH:2': 1})
    check('CP3 T2 left pitot on', CP3, 'BUTTON_17', {S + 'PITOT HEAT SWITCH:2': 1})
    check('CP3 T2 left pitot off', CP3, 'BUTTON_18', {S + 'PITOT HEAT SWITCH:2': 0})
    check('CP3 T3 right pitot on', CP3, 'BUTTON_19', {S + 'PITOT HEAT SWITCH:1': 1})
    check('CP3 T3 right pitot off', CP3, 'BUTTON_20', {S + 'PITOT HEAT SWITCH:1': 0})
    check('CP3 T4 engine anti-ice on', CP3, 'BUTTON_21', {S + 'ENG ANTI ICE:1': 1, S + 'ENG ANTI ICE:2': 1})
    check('CP3 T4 engine anti-ice off', CP3, 'BUTTON_22', {S + 'ENG ANTI ICE:1': 0, S + 'ENG ANTI ICE:2': 0})
    check('CP3 T5 slat anti-ice on', CP3, 'BUTTON_23', {'LVAR:switch_slats_ai': 0})
    check('CP3 T5 slat anti-ice off', CP3, 'BUTTON_24', {'LVAR:switch_slats_ai': 1})
    check('CP3 T6 stab anti-ice on', CP3, 'BUTTON_25', {'LVAR:switch_stabilizer_ai_lh': 0, 'LVAR:switch_stabilizer_ai_rh': 0})
    check('CP3 T6 stab anti-ice off', CP3, 'BUTTON_26', {'LVAR:switch_stabilizer_ai_lh': 1, 'LVAR:switch_stabilizer_ai_rh': 1})
    check('CP3 T7 windshield heat on', CP3, 'BUTTON_27', {S + 'WINDSHIELD DEICE SWITCH': 1})
    check('CP3 T7 windshield heat off', CP3, 'BUTTON_28', {S + 'WINDSHIELD DEICE SWITCH': 0})
    check('CP3 T8 seat belt sign on', CP3, 'BUTTON_29', {S + 'CABIN SEATBELTS ALERT SWITCH': 1})
    check('CP3 T8 seat belt sign off', CP3, 'BUTTON_30', {S + 'CABIN SEATBELTS ALERT SWITCH': 0})
    for product, buttons, side in [(THR, range(60, 65), 'l'), (CP3, range(47, 42, -1), 'r')]:
        for button, mode in zip(buttons, (0, 1, 2, 3, 3)):
            check(f'IRS {side} selector button {button}', product, f'BUTTON_{button}', {f'LVAR:knob_irs_{side}': mode})
    check('Throttle T4 parking brake off', THR, 'BUTTON_40', {S + 'BRAKE PARKING POSITION': 0})
    check('Throttle T4 parking brake on', THR, 'BUTTON_41', {S + 'BRAKE PARKING POSITION': 1})
    check('Throttle T7 engine sync on', THR, 'BUTTON_52', {'LVAR:knob_eng_sync': 0})
    check('Throttle T7 engine sync off', THR, 'BUTTON_53', {'LVAR:knob_eng_sync': 1})
    check('Throttle T5 cockpit flood on', THR, 'BUTTON_48', {'LVAR:lights_knob_flood': 80})
    check('Throttle T6 panel lights off', THR, 'BUTTON_51', {'LVAR:lights_knob_lh': 0, 'LVAR:lights_knob_ctr': 0})
    check('Throttle E1 pressurization rate +5', THR, 'BUTTON_56', {'LVAR:knob_pressurization_rate': lambda v: v >= 5})
    check('CP2 B5 standby power on', CP2, 'BUTTON_37', {'LVAR:switch_stby_pwr': 0})
    check('CP2 B6 emergency lights ARM', CP2, 'BUTTON_38', {'LVAR:EMERGENCY_LIGHTS_IS_ARM': 1})
    check('CP2 B1 APU master on', CP2, 'BUTTON_4', {'LVAR:electrical_switch_apu_master': 1})
    fire(CP2, 'BUTTON_5'); time.sleep(0.8)
    check('CP2 B2 APU start (press+release)', CP2, 'BUTTON_5', {S + 'APU PCT RPM': lambda v: v > 0.05}, trigger='RELEASE', settle=6)
    check('CP2 B4 APU bleed on', CP2, 'BUTTON_7', {'LVAR:switch_apu_bleed': 1})
    check('CP2 B4 APU bleed off', CP2, 'BUTTON_7', {'LVAR:switch_apu_bleed': 2})
    check('CP2 B1 APU master off', CP2, 'BUTTON_4', {'LVAR:electrical_switch_apu_master': 0})
    check('CP3 X speedbrake extended', CP3, 'X_AXIS', {S + 'SPOILERS HANDLE POSITION': lambda v: v > 0.95}, trigger='VALUE',
          **{'LOCAL:JOY_0X33440X025C_X_AXIS': 0})
    check('CP3 X speedbrake half', CP3, 'X_AXIS', {S + 'SPOILERS HANDLE POSITION': lambda v: 0.4 < v < 0.6}, trigger='VALUE',
          **{'LOCAL:JOY_0X33440X025C_X_AXIS': 50})
    check('CP3 X speedbrake stowed (lever forward)', CP3, 'X_AXIS', {S + 'SPOILERS HANDLE POSITION': 0}, trigger='VALUE',
          **{'LOCAL:JOY_0X33440X025C_X_AXIS': 100})
    check('Throttle Z flaps full', THR, 'Z_AXIS', {S + 'FLAPS HANDLE INDEX': 4}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_Z_AXIS': 0})
    check('Throttle Z flaps up', THR, 'Z_AXIS', {S + 'FLAPS HANDLE INDEX': 0}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_Z_AXIS': 100})
    # Thrust levers: XMLVAR_ThrottlePosition is the aircraft's own lever, -1..1 with engines off (2026-11-05).
    check('Throttle X full forward', THR, 'X_AXIS', {'LVAR:XMLVAR_ThrottlePosition_1': lambda v: v > 0.98}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_X_AXIS': 100})
    check('Throttle X idle detent', THR, 'X_AXIS', {'LVAR:XMLVAR_ThrottlePosition_1': 0}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_X_AXIS': 32.2})
    check('Throttle X full back = reverse', THR, 'X_AXIS', {'LVAR:XMLVAR_ThrottlePosition_1': lambda v: v < 0}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_X_AXIS': 0})
    check('Throttle X back to idle', THR, 'X_AXIS', {'LVAR:XMLVAR_ThrottlePosition_1': 0}, trigger='VALUE', **{'LOCAL:JOY_0X33440X0194_X_AXIS': 32.2})
    hdg = read(['SIMCONNECT:PLANE HEADING DEGREES MAGNETIC'])['SIMCONNECT:PLANE HEADING DEGREES MAGNETIC']
    check('RotAIR heading push = sync', TOP, 'BUTTON_2', {'SIMCONNECT:AUTOPILOT HEADING LOCK DIR': lambda v: abs(v - round(hdg)) < 1.1})
    check('RotAIR heading ring 2 = speed bug +', TOP, 'BUTTON_19', {'SIMCONNECT:AUTOPILOT AIRSPEED HOLD VAR': lambda v: v > 0})
    check('RotAIR ALT push = transponder ALT', TOP, 'BUTTON_4', {'SIMCONNECT:TRANSPONDER STATE:1': 4})
    check('RotAIR ALT hold = transponder STBY', TOP, 'BUTTON_8', {'SIMCONNECT:TRANSPONDER STATE:1': 1})
    check('PulsAIR AP HDG mode', AP, 'BUTTON_2', {'SIMCONNECT:AUTOPILOT HEADING LOCK': 1})
    check('PulsAIR AP FLC mode', AP, 'BUTTON_6', {'SIMCONNECT:AUTOPILOT FLIGHT LEVEL CHANGE': 1})
    check('PulsAIR AP VS mode', AP, 'BUTTON_5', {'SIMCONNECT:AUTOPILOT VERTICAL HOLD': 1})
    check('PulsAIR AP ALT mode', AP, 'BUTTON_8', {'SIMCONNECT:AUTOPILOT ALTITUDE LOCK': 1})
finally:
    for src, val in state.items():
        write(src, val)
    time.sleep(1)
    write('SIMCONNECT:TRANSPONDER STATE:1', sim0['SIMCONNECT:TRANSPONDER STATE:1'])
    calc(f"{int(sim0['SIMCONNECT:BRAKE PARKING POSITION'])} (>K:PARKING_BRAKE_SET)")
    calc('-16383 (>K:AXIS_FLAPS_SET)' if sim0['SIMCONNECT:FLAPS HANDLE INDEX'] == 0 else '')
    calc('-16383 (>K:AXIS_SPOILER_SET)')
    for c_ in ['(>K:THROTTLE1_CUT)', '(>K:THROTTLE2_CUT)', '(>K:AP_HDG_HOLD_OFF)', '(>K:FLIGHT_LEVEL_CHANGE_OFF)',
               '(>K:AP_PANEL_VS_OFF)', '(>K:AP_ALT_HOLD_OFF)', '0 (>K:AP_SPD_VAR_SET)', '0 (>K:AP_VS_VAR_SET_ENGLISH)']:
        calc(c_)
    time.sleep(2)
    after = read(SAVE)
    left = {k: (round(after[k], 2), round(v, 2)) for k, v in state.items() if abs(after[k] - v) > 0.01}
    log.append(f'Restored switch state; differences remaining: {left or "none"}')
    print(log[-1])

summary = f'{len(log) - 1 - len(failures)} passed, {len(failures)} failed' + (f': {failures}' if failures else '')
print(summary)
(ROOT / 'verify-citation-x-results.txt').write_text(
    f'Citation X profile live check {time.strftime("%Y-%m-%d %H:%M")}\n' + '\n'.join(log) + '\n' + summary + '\n', encoding='utf-8')
