"""Bind a VIRPIL CM3 throttle button (PID 0x0194) to F12 (MSFS screenshot) in every SPAD profile.

Usage: python bind-throttle-screenshot.py <button-number>     (the red button is 33)
SPAD rewrites its cached profile on exit, so restart SPAD afterwards and answer No to saving.
Backs up each profile first to backups/throttle-screenshot-<timestamp>/. Replaces any existing
binding on that button only; everything else in each profile is left byte-for-byte unchanged
(text splice keeping the file's own line endings, not re-serialised).
"""
from pathlib import Path
import re, shutil, sys, time

ROOT = Path(__file__).resolve().parent
PROFILES = Path.home() / 'Documents/SPAD.neXt/profiles'
BTN = int(sys.argv[1])

EVENT = f'''          <Event BoundTo="BUTTON_{BTN}">
            <EventDefinitions>
              <EventDefinition Trigger="PRESS">
                <EventActions>
                  <EventActionKeyboard MacroType="PRESSANDRELEASE" TargetWindow="__ACTIVEWINDOW__">
                    <KeyboardMacro Duration="80" Repeat="1" Pause="25">
                      <Keys>
                        <Keys>F12</Keys>
                      </Keys>
                    </KeyboardMacro>
                  </EventActionKeyboard>
                </EventActions>
              </EventDefinition>
            </EventDefinitions>
          </Event>
'''
LF, CRLF = chr(10), chr(13) + chr(10)
BOM = b'\xef\xbb\xbf'

backup = ROOT / 'backups' / time.strftime('throttle-screenshot-%Y%m%d-%H%M%S')
backup.mkdir(parents=True)
dev_re = re.compile(r'<Device VendorID="0x3344" ProductID="0x0194".*?</Device>', re.S)
old_re = re.compile(rf'[ \t]*<Event BoundTo="BUTTON_{BTN}">.*?</Event>\r?\n', re.S)

for f in sorted(PROFILES.glob('*.xml')):
    raw = f.read_bytes()
    bom = raw.startswith(BOM)
    text = raw.decode('utf-8-sig')
    nl = CRLF if CRLF in text else LF
    ev = EVENT.replace(LF, nl)
    devices = list(dev_re.finditer(text))
    if not devices:
        print(f'skip (no throttle): {f.name}')
        continue
    shutil.copy2(f, backup / f.name)
    for m in reversed(devices):
        dev = old_re.sub('', m.group(0))
        if '<Events />' in dev:
            dev = dev.replace('<Events />', '<Events>' + nl + ev + '        </Events>', 1)
        elif '</Events>' in dev:
            i = dev.index('</Events>')
            i = dev.rfind(LF, 0, i) + 1
            dev = dev[:i] + ev + dev[i:]
        else:
            raise SystemExit(f'no <Events> in throttle device of {f.name}')
        text = text[:m.start()] + dev + text[m.end():]
    f.write_bytes((BOM if bom else b'') + text.encode('utf-8'))
    print(f'bound BUTTON_{BTN} -> F12 in {len(devices)} throttle device(s): {f.name}')
print('backup:', backup)
