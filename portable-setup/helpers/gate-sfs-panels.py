"""Hand the RotAIR / PulsAIR panels to SimFlight's SFS Monitor whenever it is running.

Every SPAD event definition on the SimFlight Services panels (VID 16D0: RotAIR Type-1/Type-2 and
PulsAIR Type-1/Type-2, in both ANA and GC modes) gets one extra condition:

    LVAR:KA_SFS_MONITOR  Unequal  1

.tools/ka-sfs/ka-sfs-watch.exe sets L:KA_SFS_MONITOR to 1 while SFSmonitor_V5_0.exe runs and 0 when
it doesn't, so SPAD drives the panels only while SFS Monitor is closed. If the watcher isn't running
the variable reads 0 and SPAD keeps the panels (safe default). SPAD ANDs an event's conditions, so
existing conditions (avionics focus, hold states...) keep working.

Run with SPAD closed. Idempotent; --remove takes the gate out again.
Usage: python gate-sfs-panels.py [--remove] <profile.xml> [...]
"""
from pathlib import Path
import re
import sys

PANELS = ('0x1290', '0x13E4', '0x14CA', '0x14CB', '0x128F', '0x13E3')  # ANA and GC product IDs
GATE = '<EventCondition ConditionComparator="Unequal" ConditionTargetValue="1" ConditionValueSource="LVAR:KA_SFS_MONITOR" />'
DEVICE_RE = re.compile(r'<Device VendorID="0x16D0" ProductID="(0x[0-9A-F]+)".*?</Device>', re.S)
DEF_RE = re.compile(r'(?P<indent>[ \t]*)<EventDefinition\b[^>]*>.*?</EventDefinition>', re.S)


def gate_definition(m):
    block, indent = m.group(0), m.group('indent')
    if 'LVAR:KA_SFS_MONITOR' in block:
        return block
    if '<EventConditions>' in block:
        ci = re.search(r'\n([ \t]*)<EventCondition ', block).group(1)
        return re.sub(r'\n([ \t]*)</EventConditions>',
                      lambda c: f'\n{ci}{GATE}\n{c.group(1)}</EventConditions>', block, count=1)
    inner = indent + '  '
    return re.sub(r'\n([ \t]*)<EventActions>', lambda a: f'\n{inner}<EventConditions>\n{inner}  {GATE}\n{inner}</EventConditions>\n{a.group(1)}<EventActions>', block, count=1)


def ungate_definition(m):
    block = m.group(0)
    block = re.sub(r'\n[ \t]*' + re.escape(GATE), '', block)
    return re.sub(r'\n[ \t]*<EventConditions>\s*</EventConditions>', '', block)


def patch(text, remove=False):
    count = 0

    def device(m):
        nonlocal count
        if m.group(1) not in PANELS:
            return m.group(0)
        new, n = DEF_RE.subn(ungate_definition if remove else gate_definition, m.group(0))
        count += n
        return new
    return DEVICE_RE.sub(device, text), count


def main():
    args = sys.argv[1:]
    remove = '--remove' in args
    for name in [a for a in args if a != '--remove']:
        path = Path(name)
        raw = path.read_bytes()
        bom = raw.startswith(b'\xef\xbb\xbf')
        text = raw.decode('utf-8-sig')
        crlf = '\r\n' in text
        new, n = patch(text.replace('\r\n', '\n'), remove)
        if crlf:
            new = new.replace('\n', '\r\n')
        path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + new.encode('utf-8'))
        print(f'{path}: {"ungated" if remove else "gated"} {n} panel event definitions')


if __name__ == '__main__':
    main()
