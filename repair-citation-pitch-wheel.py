"""Map PulsAIR nose up/down to the Citation autopilot pitch wheel."""
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as E
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parent
spec = spec_from_file_location('range_repair', ROOT / 'repair-citation-range.py')
helpers = module_from_spec(spec)
spec.loader.exec_module(helpers)
N, NAME = helpers.N, helpers.NAME
spec = spec_from_file_location('citation_builder', ROOT / 'build-citation-x-profile.py')
builder = module_from_spec(spec)
spec.loader.exec_module(builder)

def repair(path, backup):
    tree = E.parse(path)
    root = tree.getroot()
    for product, button, up in [('0x0194', 2, True), ('0x0194', 3, False),
                                ('0x14CA', 11, True), ('0x14CA', 12, False)]:
        builder.put(root, product, f'BUTTON_{button}', *builder.pitch_wheel(up), sfs=product == '0x14CA')
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / path.name)
    E.indent(tree, space='  ')
    tree.write(path, encoding='utf-8')
    print('Pitch wheel repaired:', path)

if __name__ == '__main__':
    paths = [ROOT / 'profiles' / NAME, ROOT / 'portable-setup/profiles' / NAME]
    if '--installed' in sys.argv:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SPAD.neXt.exe', '/NH'], capture_output=True, text=True)
        if 'spad.next.exe' in result.stdout.lower():
            raise SystemExit('Exit SPAD before installing the pitch-wheel repair.')
        paths = [Path.home() / 'Documents/SPAD.neXt/profiles' / NAME]
    base = ROOT / 'backups' / ('citation-pitch-wheel-' + time.strftime('%Y%m%d-%H%M%S'))
    for i, path in enumerate(paths):
        repair(path, base / str(i))
