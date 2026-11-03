"""Give every SPAD profile the KestrelAir default stick ATC controls and rudder pedals.

WarBRD-D grips (Constellation ALPHA Prime, VID 3344 / PID 03F5; DeviceIndex 0 = right, 1 = left),
identical routing on both:

    Grip control          HID button   Action
    Top push button       7            vJoy 1 button 1  -> vPilot push-to-talk (VATSIM)
    Bottom push button    18           vJoy 1 button 2  -> BeyondATC PushToTalk1
    Main trigger (stage1) 4            vJoy 1 button 3  -> BeyondATC DoAction1 (auto respond)
    Flip trigger squeeze  3            vJoy 1 button 3  -> BeyondATC DoAction1 (auto respond)
    vPilot window button  8            .tools/ka-front/ka-front-vpilot.exe    (toggle vPilot / MSFS)
    BATC window button    13           .tools/ka-front/ka-front-beyondatc.exe (toggle BeyondATC / MSFS)
    Wheel up / down       22 / 21      .tools/ka-front/ka-menu-prev/next.exe  (BeyondATC reply list)
    Wheel press           19           .tools/ka-front/ka-menu-select.exe     (send reply, back to MSFS)

Saitek Pro Flight Rudder Pedals (VID 06A3 / PID 0763), raw HID values measured live 2026-11-03:

    Axis    Function           Raw range                     SPAD lever
    RZ      Rudder             5 (full left) .. 501, centre 253   LEVER_RUDDER (inverted)
    X       Left toe brake     0 (released) .. 125           LEVER_BRAKELEFT
    Y       Right toe brake    0 (released) .. 125 (127 max)  LEVER_BRAKERIGHT

Missing device blocks are created; only the listed events are replaced, everything else in a
profile is left untouched. Trigger stage 2 (HID 5) stays unbound so a full pull doesn't fire twice.
Close SPAD before running (it rewrites profiles on save).

Usage: python bind-sticks-and-pedals.py <profile.xml> [...]   (edits in place; idempotent)
"""
from pathlib import Path
import re
import sys

PAGE_ID = '72c73483-060e-4a22-94be-a6d0c6e32179'  # SPAD's default device page ID, same in every profile
HID_GUID = '{4d1e55b2-f16f-11cf-88cb-001111000030}'
GRIPS = {  # DeviceIndex -> HID instance (from firmware-repair-notes.md; right grip on the unchanged USB port)
    0: r'\\?\hid#vid_3344&pid_03f5&mi_00#a&1aa429cf&0&0000#' + HID_GUID,
    1: r'\\?\hid#vid_3344&pid_03f5&mi_00#a&22ba5017&0&0000#' + HID_GUID,
}
PEDALS = r'\\?\hid#vid_06a3&pid_0763#9&2a71f0e4&0&0000#' + HID_GUID
THROTTLE = r'\\?\hid#vid_3344&pid_0194&mi_00#8&1d037022&0&0000#' + HID_GUID  # VIRPIL MongoosT-50CM3
# Camera zoom: the CM3's Rz lever (0..60000, identified live 2026-11-03) feeds vJoy Slider X (HID 0x36),
# which the KestrelAir vJoy preset binds to cockpit and external-view zoom (build-vjoy-preset.py).
ZOOM_AXIS, ZOOM_VJOY = 'RZ_AXIS', 0x36

VJOY_ROUTES = {7: 1, 18: 2, 4: 3, 3: 3}
TOOLS = Path(__file__).resolve().parent / '.tools' / 'ka-front'
# BeyondATC's reply list is mouse-only (Tab/Enter/arrows/vJoy didn't reach it), so the wheel runs helpers.
PROGRAMS = {8: 'ka-front-vpilot.exe', 13: 'ka-front-beyondatc.exe',
            22: 'ka-menu-prev.exe', 21: 'ka-menu-next.exe', 19: 'ka-menu-select.exe'}
PEDAL_AXES = {  # BoundTo -> (lever, min, max, centre or None, invert)
    # Rudder inverted: SPAD's LEVER_RUDDER treats low raw values as right rudder; the user confirmed
    # the uninverted mapping was reversed in the sim on 2026-11-03.
    'RZ_AXIS': ('LEVER_RUDDER', 5, 501, 253, True),
    'X_AXIS': ('LEVER_BRAKELEFT', 0, 125, None, False),
    'Y_AXIS': ('LEVER_BRAKERIGHT', 0, 125, None, False),
}


def block(lines, indent):
    return ''.join('\n' + indent + line for line in lines)


def vjoy_event(hid, button, indent):
    def action(mode):
        return (f'<EventActionVirtualJoyStick JoystickAction="VJOY_BUTTON" JoystickNumber="1" '
                f'JoystickTarget="{button}" JoystickMode="{mode}" />')
    return block([
        f'<Event BoundTo="BUTTON_{hid}">',
        '  <EventDefinitions>',
        '    <EventDefinition Trigger="PRESS">',
        '      <EventActions>',
        '        ' + action('PRESS'),
        '      </EventActions>',
        '    </EventDefinition>',
        '    <EventDefinition Trigger="RELEASE">',
        '      <EventActions>',
        '        ' + action('RELEASE'),
        '      </EventActions>',
        '    </EventDefinition>',
        '  </EventDefinitions>',
        '</Event>',
    ], indent)


def program_event(hid, exe, indent):
    return block([
        f'<Event BoundTo="BUTTON_{hid}">',
        '  <EventDefinitions>',
        '    <EventDefinition Trigger="PRESS">',
        '      <EventActions>',
        '        <EventActionCommand>',
        '          <Parameter Value="SPAD_neXt.RunProgram" />',
        f'          <Parameter1 Value="{TOOLS / exe}" />',
        '        </EventActionCommand>',
        '      </EventActions>',
        '    </EventDefinition>',
        '  </EventDefinitions>',
        '</Event>',
    ], indent)


def axis_event(bound, lever, lo, hi, centre, invert, indent):
    options = ['USERAWVALUE" Value="True', f'MIN" Value="{lo}', f'MAX" Value="{hi}']
    if centre is not None:
        options.append(f'IDLE" Value="{centre}')
    options.append(f'INVERTAXIS" Value="{invert}')
    return block([
        f'<Event BoundTo="{bound}">',
        '  <EventDefinitions>',
        '    <EventDefinition Trigger="VALUE">',
        '      <EventActions>',
        f'        <EventActionRangedAxis ConfigID="{lever}">',
        '          <Options>',
        *[f'            <Option Key="{o}" />' for o in options],
        '          </Options>',
        '        </EventActionRangedAxis>',
        '      </EventActions>',
        '    </EventDefinition>',
        '  </EventDefinitions>',
        '</Event>',
    ], indent)


def strip_event(body, bound):
    return re.sub(rf'\s*<Event BoundTo="{bound}">.*?</Event>', '', body, flags=re.S)


def device_re(vid, pid, index):
    return re.compile(
        rf'(<Device VendorID="{vid}" ProductID="{pid}"[^>]*DeviceIndex="{index}"[^>]*>\s*'
        r'<DevicePage[^>]*>\s*<Events)(\s*/>|>(.*?)(\s*</Events>))', re.S)


def ensure_device(text, vid, pid, index, path):
    if device_re(vid, pid, index).search(text):
        return text
    esc = path.replace('&', '&amp;')
    dev = block([
        f'<Device VendorID="{vid}" ProductID="{pid}" DevicePath="{esc}" Serial="" DeviceIndex="{index}" Version="3">',
        f'  <DevicePage ID="{PAGE_ID}" IsDefaultPage="true" Name="Default">',
        '    <Events>',
        '    </Events>',
        '  </DevicePage>',
        '</Device>',
    ], '    ')
    if re.search(r'<Devices\s*/>', text):
        return re.sub(r'<Devices\s*/>', lambda m: '<Devices>' + dev + '\n  </Devices>', text, count=1)
    new, n = re.subn(r'\n([ \t]*)</Devices>', lambda m: dev + '\n' + m.group(1) + '</Devices>', text, count=1)
    if n != 1:
        raise ValueError('no <Devices> element')
    return new


def edit_events(text, vid, pid, index, build):
    def repl(m):
        head = m.group(1)
        body = m.group(3) or ''
        indent = re.search(r'\n([ \t]*)<Event ', body)
        indent = indent.group(1) if indent else '          '
        body = build(body, indent)
        close = m.group(4) or '\n        </Events>'
        return head + '>' + body + close
    new, n = device_re(vid, pid, index).subn(repl, text)
    if n != 1:
        raise ValueError(f'expected one {vid}/{pid} index {index} device, found {n}')
    return new


def grip_events(body, indent):
    for hid in (*VJOY_ROUTES, *PROGRAMS):
        body = strip_event(body, f'BUTTON_{hid}')
    for hid, button in VJOY_ROUTES.items():
        body += vjoy_event(hid, button, indent)
    for hid, exe in PROGRAMS.items():
        body += program_event(hid, exe, indent)
    return body


def pedal_events(body, indent):
    for bound, (lever, lo, hi, centre, invert) in PEDAL_AXES.items():
        body = strip_event(body, bound) + axis_event(bound, lever, lo, hi, centre, invert, indent)
    return body


def throttle_events(body, indent):
    return strip_event(body, ZOOM_AXIS) + block([
        f'<Event BoundTo="{ZOOM_AXIS}">',
        '  <EventDefinitions>',
        '    <EventDefinition Trigger="VALUE">',
        '      <EventActions>',
        f'        <EventActionVirtualJoyStick JoystickAction="VJOY_AXIS" JoystickNumber="1" '
        f'JoystickTarget="{ZOOM_VJOY}" JoystickMode="RESPONSECURVE" />',
        # Direct cockpit zoom: SPAD's axis percentage (0..100) written to the settable simvar
        # COCKPIT CAMERA ZOOM (percentage), so no MSFS binding is needed. Verified settable 2026-11-03.
        '        <EventActionChangeValue SourceType="Exp" TargetDataDefinition="SIMCONNECT:COCKPIT CAMERA ZOOM" '
        'SourceDataDefinition="[LOCAL:JOY_0X33440X0194_RZ_AXIS]" />',
        '      </EventActions>',
        '    </EventDefinition>',
        '  </EventDefinitions>',
        '</Event>',
    ], indent)


def patch(text):
    for index, path in GRIPS.items():
        text = ensure_device(text, '0x3344', '0x03F5', index, path)
        text = edit_events(text, '0x3344', '0x03F5', index, grip_events)
    text = ensure_device(text, '0x06A3', '0x0763', 0, PEDALS)
    text = edit_events(text, '0x06A3', '0x0763', 0, pedal_events)
    text = ensure_device(text, '0x3344', '0x0194', 0, THROTTLE)
    return edit_events(text, '0x3344', '0x0194', 0, throttle_events)


def main():
    for name in sys.argv[1:]:
        path = Path(name)
        raw = path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        crlf = '\r\n' in text
        new = patch(text.replace('\r\n', '\n'))
        if crlf:
            new = new.replace('\n', '\r\n')
        path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
        print(f"{path}: grips, rudder pedals and throttle zoom set")


if __name__ == '__main__':
    main()
