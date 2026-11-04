"""CP3 B13 = pilot-view / outside-view toggle, and CP3 instrument views, in every SPAD profile.

B13 (CP3 BUTTON_13), decided from the live camera:
  in the cockpit, pilot view (any look direction)  -> outside view   (bare Backspace, works as a SPAD macro)
  in the cockpit, an instrument view (Shift+N)     -> pilot view     (MSFS "Reset cockpit view", Shift+Space)
  anywhere else (outside, drone, ...)              -> pilot view     (CAMERA STATE = 2, then Shift+Space)
Shift+Space has to go through ka-key: MSFS 2024 ignores a Shift sent by a SPAD keyboard macro.  The
definitions are ordered so the only one that writes CAMERA STATE comes last, so no later definition can
see that write on the same press.  Measured live 2026-11-04 (Citation X): instrument view (2,5,2,7) and
outside (3,1,0,0) both returned to the pilot view (2,1,1,4); pilot view + Backspace went outside.

Instrument views: any CP3 button whose only action is a Shift+digit macro (never reached MSFS as Shift)
becomes CAMERA STATE = 2, CAMERA VIEW TYPE AND INDEX:0 = 2, :1 = digit-1, which is what Shift+digit does.

Profiles without a CP3 page (the default Profile.xml) get one, copied empty from Aerostar.xml.

Usage: pilot_view_toggle.py [profile.xml ...]   (no arguments: installed SPAD profiles, repo profiles,
portable-setup/profiles and portable-setup/camera-profiles-pending).  Run with SPAD closed: SPAD saves its
cached copy over the installed files.  Idempotent.
"""
from pathlib import Path
import copy, sys
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
NS = 'http://www.fsgs.com/SPAD'
E.register_namespace('', NS)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
N = {'s': NS}
CP3 = '0x025C'
SHIFT_SPACE = str(ROOT / '.tools' / 'ka-key' / 'ka-key-shift-space.exe')
DONOR = ROOT / 'profiles' / 'Aerostar.xml'


def tag(name): return '{' + NS + '}' + name


def cp3_events(root):
    for d in root.findall('./s:Devices/s:Device', N):
        if d.get('ProductID') == CP3:
            return d.find('s:DevicePage/s:Events', N)
    donor = next(d for d in E.parse(DONOR).getroot().findall('./s:Devices/s:Device', N) if d.get('ProductID') == CP3)
    donor = copy.deepcopy(donor)
    events = donor.find('s:DevicePage/s:Events', N)
    for e in list(events):
        events.remove(e)
    root.find('s:Devices', N).append(donor)
    return events


def definition(edefs, conds, acts):
    ed = E.SubElement(edefs, tag('EventDefinition'), Trigger='PRESS')
    ec = E.SubElement(ed, tag('EventConditions'))
    for src, cmp, val in conds:
        attrs = {'ConditionTargetValue': str(val), 'ConditionValueSource': src}
        if cmp:
            attrs = {'ConditionComparator': cmp, **attrs}
        E.SubElement(ec, tag('EventCondition'), attrs)
    ea = E.SubElement(ed, tag('EventActions'))
    for act in acts:
        ea.append(act)


def set_simvar(name, value):
    return E.Element(tag('EventActionChangeValue'), TargetDataDefinition='SIMCONNECT:' + name, Value=str(value))


def run(path):
    a = E.Element(tag('EventActionCommand'))
    E.SubElement(a, tag('Parameter'), Value='SPAD_neXt.RunProgram')
    E.SubElement(a, tag('Parameter1'), Value=path)
    return a


def backspace():
    a = E.Element(tag('EventActionKeyboard'), MacroType='PRESSANDRELEASE', TargetWindow='__ACTIVEWINDOW__')
    m = E.SubElement(a, tag('KeyboardMacro'), Duration='80', Repeat='1', Pause='25')
    E.SubElement(E.SubElement(m, tag('Keys')), tag('Keys')).text = 'Back'
    return a


def replace(events, bound):
    for e in list(events):
        if e.get('BoundTo') == bound:
            events.remove(e)
    e = E.SubElement(events, tag('Event'), BoundTo=bound)
    return E.SubElement(e, tag('EventDefinitions'))


def shift_digit(event):
    """The digit of an event that only sends Shift+digit, else None."""
    acts = list(event.iter(tag('EventActionKeyboard')))
    others = [a for a in event.iter() if a.tag.startswith(tag('EventAction')) and a.tag not in (tag('EventActionKeyboard'), tag('EventActions'))]
    if len(acts) != 1 or others or len(list(event.iter(tag('EventDefinition')))) != 1:
        return None
    keys = [k.text for k in acts[0].iter(tag('Keys')) if k.text and k.text.strip()]
    if len(keys) == 2 and keys[0] in ('LShiftKey', 'ShiftKey') and len(keys[1]) == 2 and keys[1][0] == 'D' and keys[1][1].isdigit():
        return int(keys[1][1])
    return None


def apply(root):
    events = cp3_events(root)
    views = []
    for e in list(events):
        digit = shift_digit(e)
        if digit:
            bound = e.get('BoundTo')
            edefs = replace(events, bound)
            ed = E.SubElement(edefs, tag('EventDefinition'), Trigger='PRESS')
            ea = E.SubElement(ed, tag('EventActions'))
            for name, val in [('CAMERA STATE', 2), ('CAMERA VIEW TYPE AND INDEX:0', 2), ('CAMERA VIEW TYPE AND INDEX:1', digit - 1)]:
                ea.append(set_simvar(name, val))
            views.append(f'{bound}=view {digit}')
    edefs = replace(events, 'BUTTON_13')
    cockpit = ('SIMCONNECT:CAMERA STATE', None, 2)
    definition(edefs, [cockpit, ('SIMCONNECT:CAMERA VIEW TYPE AND INDEX:0', 'Unequal', 2)], [backspace()])
    definition(edefs, [cockpit, ('SIMCONNECT:CAMERA VIEW TYPE AND INDEX:0', None, 2)], [run(SHIFT_SPACE)])
    definition(edefs, [('SIMCONNECT:CAMERA STATE', 'Unequal', 2)], [set_simvar('CAMERA STATE', 2), run(SHIFT_SPACE)])
    return views


def main(paths):
    if not paths:
        paths = sorted((Path.home() / 'Documents/SPAD.neXt/profiles').glob('*.xml'))
        for sub in ('profiles', 'portable-setup/profiles', 'portable-setup/camera-profiles-pending'):
            paths += sorted((ROOT / sub).glob('*.xml'))
    for p in map(Path, paths):
        root = E.parse(p).getroot()
        views = apply(root)
        E.ElementTree(root).write(p, encoding='utf-8', xml_declaration=False)
        print(f'{p}: B13 toggle' + (', views ' + ', '.join(views) if views else ''))


if __name__ == '__main__':
    main(sys.argv[1:])
