from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from drone_precision import action

root = Path(__file__).resolve().parent.parent
profile = Path.home() / 'Documents/SPAD.neXt/profiles/Citation X - FlightFX C750.xml'
backup = root / '.tools/drone-precision-test-before.xml'
if '--remove' in sys.argv:
    profile.write_bytes(backup.read_bytes())
    print('Removed isolated test binding')
else:
    raw = profile.read_bytes()
    backup.write_bytes(raw)
    text = raw.decode('utf-8-sig')
    start = text.index('<Device VendorID="0x3344" ProductID="0x03F5"')
    end = text.index('</Device>', start)
    grip = text[start:end]
    assert 'BoundTo="BUTTON_32"' not in grip
    test = ('<Event BoundTo="BUTTON_32"><EventDefinitions><EventDefinition Trigger="PRESS">'
            '<EventActions>' + action('PROFILE:KA_DRONE_TEST', 'DIAL') +
            '</EventActions></EventDefinition></EventDefinitions></Event>')
    grip = grip.replace('</Events>', test + '</Events>')
    text = text[:start] + grip + text[end:]
    text = text.replace('</Variables>', '<Variable Name="PROFILE:KA_DRONE_TEST" Value="50" ValueType="Decimal" /></Variables>')
    profile.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + text.encode())
    print('Installed isolated button-32 test on drone-only Dial output')
