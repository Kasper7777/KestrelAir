"""Bind WarBRD-D (Constellation ALPHA Prime) grip buttons to vJoy buttons for ATC apps.

Both grips (VID 3344 / PID 03F5, DeviceIndex 0 = right, 1 = left) get identical routing:

    Grip control          HID button   vJoy 1 button   Listener
    Top push button       7            1               vPilot push-to-talk (VATSIM)
    Bottom push button    18           2               BeyondATC PushToTalk1
    Main trigger (stage1) 4            3               BeyondATC DoAction1 (auto respond)
    Flip trigger squeeze  3            3               BeyondATC DoAction1 (auto respond)
    Wheel up              22           4               BeyondATC TabKey (next dialogue option)
    Wheel down            21           4               BeyondATC TabKey (BeyondATC has no 'previous')
    Wheel press           19           5               BeyondATC EnterKey (send selected option)
    vPilot window button  8            -               runs .tools/ka-front/ka-front-vpilot.exe
    BATC window button    13           -               runs .tools/ka-front/ka-front-beyondatc.exe

Button numbers were read live from both grips on 2026-11-03 (watch-warbrd-buttons.ps1,
warbrd-button-map-20261103*.txt). ka-front toggles: pressing again returns focus to MSFS.
Trigger stage 2 (HID 5) is left unbound so a full pull does not fire twice.
The old right-grip BUTTON_7 action (CJ4 flood light toggle) is replaced.

Usage: python bind-stick-ptt.py <profile.xml> [...]   (edits in place; idempotent)
"""
from pathlib import Path
import re
import sys

ROUTES = {7: 1, 18: 2, 4: 3, 3: 3, 22: 4, 21: 4, 19: 5}
FRONT_DIR = Path(__file__).resolve().parent / '.tools' / 'ka-front'
WINDOWS = {8: 'ka-front-vpilot.exe', 13: 'ka-front-beyondatc.exe'}
DEVICE_RE = re.compile(
    r'(<Device VendorID="0x3344" ProductID="0x03F5"[^>]*>\s*<DevicePage[^>]*>\s*<Events>)(.*?)(\s*</Events>)',
    re.S,
)


def event_xml(hid: int, vjoy: int, indent: str) -> str:
    def action(mode: str) -> str:
        return (f'<EventActionVirtualJoyStick JoystickAction="VJOY_BUTTON" JoystickNumber="1" '
                f'JoystickTarget="{vjoy}" JoystickMode="{mode}" />')
    i = indent
    return (
        f'\n{i}<Event BoundTo="BUTTON_{hid}">'
        f'\n{i}  <EventDefinitions>'
        f'\n{i}    <EventDefinition Trigger="PRESS">'
        f'\n{i}      <EventActions>'
        f'\n{i}        {action("PRESS")}'
        f'\n{i}      </EventActions>'
        f'\n{i}    </EventDefinition>'
        f'\n{i}    <EventDefinition Trigger="RELEASE">'
        f'\n{i}      <EventActions>'
        f'\n{i}        {action("RELEASE")}'
        f'\n{i}      </EventActions>'
        f'\n{i}    </EventDefinition>'
        f'\n{i}  </EventDefinitions>'
        f'\n{i}</Event>'
    )


def run_xml(hid: int, exe: str, indent: str) -> str:
    lines = [
        f'<Event BoundTo="BUTTON_{hid}">',
        '  <EventDefinitions>',
        '    <EventDefinition Trigger="PRESS">',
        '      <EventActions>',
        '        <EventActionCommand>',
        '          <Parameter Value="SPAD_neXt.RunProgram" />',
        f'          <Parameter1 Value="{FRONT_DIR / exe}" />',
        '        </EventActionCommand>',
        '      </EventActions>',
        '    </EventDefinition>',
        '  </EventDefinitions>',
        '</Event>',
    ]
    return ''.join('\n' + indent + line for line in lines)


def strip_event(body: str, hid: int) -> str:
    return re.sub(rf'\s*<Event BoundTo="BUTTON_{hid}">.*?</Event>', '', body, flags=re.S)


def patch(text: str) -> tuple[str, int]:
    def repl(m: re.Match) -> str:
        head, body, tail = m.groups()
        indent = re.search(r'\n([ \t]*)<Event ', body)
        indent = indent.group(1) if indent else '          '
        for hid in (*ROUTES, *WINDOWS):
            body = strip_event(body, hid)
        for hid, vjoy in ROUTES.items():
            body += event_xml(hid, vjoy, indent)
        for hid, exe in WINDOWS.items():
            body += run_xml(hid, exe, indent)
        return head + body + tail
    return DEVICE_RE.subn(repl, text)


def main() -> None:
    for name in sys.argv[1:]:
        path = Path(name)
        raw = path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        crlf = '\r\n' in text
        new, count = patch(text.replace('\r\n', '\n'))
        if crlf:
            new = new.replace('\n', '\r\n')
        if count != 2:
            sys.exit(f'{path}: expected 2 WarBRD devices, found {count}; not changed')
        path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
        print(f'{path}: patched both grips')


if __name__ == '__main__':
    main()
