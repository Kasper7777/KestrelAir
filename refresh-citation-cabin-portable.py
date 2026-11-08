"""Refresh only the portable artifacts affected by the Citation cabin controls."""
from pathlib import Path
import hashlib, json, shutil
root = Path(__file__).resolve().parent
portable = root / 'portable-setup'
files = ['helpers/KestrelAirLEDs.lua', 'helpers/KestrelAir-myOffsets.txt',
         'helpers/citation-x-profile.md', 'profiles/Citation X - FlightFX C750.xml']
for filename in ['KestrelAirLEDs.lua', 'KestrelAir-myOffsets.txt', 'citation-x-profile.md']:
    shutil.copy2(root / filename, portable / 'helpers' / filename)
manifest = portable / 'sha256.json'
data = json.loads(manifest.read_text(encoding='utf-8-sig'))
for filename in files:
    data[filename] = hashlib.sha256((portable / filename).read_bytes()).hexdigest()
manifest.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
