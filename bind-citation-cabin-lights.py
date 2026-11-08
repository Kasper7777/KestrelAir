"""Patch only Citation X CP2 B9/B10; preserve all existing profile settings."""
from pathlib import Path
import importlib.util
import shutil
import sys
import time
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('citation', ROOT / 'build-citation-x-profile.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def patch(root):
    for button, index in [(41, 22), (42, 23)]:
        on = '100' if index == 22 else 'If([LVAR:cabin_overhead_brightness] > 0, [LVAR:cabin_overhead_brightness], 10)'
        expr = f'If([SIMCONNECT:LIGHT POTENTIOMETER:{index}] == 0, {on}, 0)'
        b.put(root, b.CP2, f'BUTTON_{button}', b.press(b.k(f'LIGHT_POTENTIOMETER_{index}_SET', expr=expr)))

if __name__ == '__main__':
    folders = [ROOT / 'profiles', ROOT / 'portable-setup/profiles']
    if '--installed' in sys.argv:
        folders = [b.SPAD_PROFILES]
    backup = ROOT / 'backups' / ('citation-cabin-lights-' + time.strftime('%Y%m%d-%H%M%S'))
    for i, folder in enumerate(folders):
        path = folder / b.NAME
        tree = E.parse(path)
        before = E.tostring(tree.getroot())
        patch(tree.getroot())
        # Removing just these two events must leave the rest of the profile identical.
        original = E.fromstring(before)
        for root in (original, tree.getroot()):
            b.remove(root, b.CP2, 'BUTTON_41', 'BUTTON_42')
        assert E.tostring(original) == E.tostring(tree.getroot()), 'Unrelated profile change'
        patch(tree.getroot())
        target = backup / str(i)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / path.name)
        E.indent(tree, space='  ')
        tree.write(path, encoding='utf-8')
        print('Patched', path)
