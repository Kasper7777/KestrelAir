"""Move only the Citation X IRS bindings onto the two rotary mode selectors."""
from pathlib import Path
import importlib.util, shutil, sys, time
import xml.etree.ElementTree as E
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('citation', ROOT / 'build-citation-x-profile.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
SELECTORS = [(b.THR, list(range(60, 65)), 'l'), (b.CP3, list(range(47, 42, -1)), 'r')]
def patch(root):
    for product, buttons, side in SELECTORS:
        b.irs_selector(root, product, [f'BUTTON_{i}' for i in buttons], side)
    b.remove(root, b.CP2, 'BUTTON_39', 'BUTTON_40')
def strip(root):
    for product, buttons, side in SELECTORS:
        b.remove(root, product, *[f'BUTTON_{i}' for i in buttons])
    b.remove(root, b.CP2, 'BUTTON_39', 'BUTTON_40')
if __name__ == '__main__':
    folders = [ROOT / 'profiles', ROOT / 'portable-setup/profiles']
    if '--installed' in sys.argv: folders = [b.SPAD_PROFILES]
    backup = ROOT / 'backups' / ('citation-irs-' + time.strftime('%Y%m%d-%H%M%S'))
    for i, folder in enumerate(folders):
        path = folder / b.NAME
        tree = E.parse(path)
        original = E.fromstring(E.tostring(tree.getroot()))
        patch(tree.getroot())
        stripped = E.fromstring(E.tostring(tree.getroot()))
        strip(original); strip(stripped)
        assert E.tostring(original) == E.tostring(stripped), 'Unrelated profile change'
        for product, buttons, side in SELECTORS:
            for button, value in zip(buttons, (0, 1, 2, 3, 3)):
                event = next(e for e in b.events(tree.getroot(), product) if e.get('BoundTo') == f'BUTTON_{button}')
                actions = event.findall('.//s:EventActions/*', b.N)
                assert len(actions) == 1
                assert actions[0].get('TargetDataDefinition') == f'LVAR:knob_irs_{side}'
                assert actions[0].get('Value') == str(value)
        target = backup / str(i); target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target / path.name)
        E.indent(tree, space='  '); tree.write(path, encoding='utf-8')
        print('IRS selectors patched and unrelated bindings verified:', path)
