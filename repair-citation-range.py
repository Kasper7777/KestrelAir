"""Set Citation range input-event steps to one, preserving other bindings."""
from pathlib import Path
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
NS = 'http://www.fsgs.com/SPAD'
N = {'s': NS}
E.register_namespace('', NS)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
NAME = 'Citation X - FlightFX C750.xml'

def repair(path, backup):
    tree = E.parse(path)
    count = 0
    for action in tree.findall('.//s:EventActionControl', N):
        target = action.get('TargetDataDefinition', '').upper()
        if target in {f'B:AS3000_UPPER_{side}_RANGE_{direction}' for side in (1, 2) for direction in ('INC', 'DEC')}:
            param = action.find('s:Parameter', N)
            if param is None:
                param = E.SubElement(action, f'{{{NS}}}Parameter')
            param.attrib.clear()
            param.set('Type', 'Static')
            param.set('Value', '1')
            count += 1
    assert count == 24, f'Expected 24 range actions, found {count}'
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / path.name)
    E.indent(tree, space='  ')
    tree.write(path, encoding='utf-8')
    print(f'Repaired {count} range actions: {path}')

if __name__ == '__main__':
    paths = [ROOT / 'profiles' / NAME, ROOT / 'portable-setup/profiles' / NAME]
    if '--installed' in sys.argv:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SPAD.neXt.exe', '/NH'], capture_output=True, text=True)
        if 'spad.next.exe' in result.stdout.lower():
            raise SystemExit('Exit SPAD completely before repairing its installed profile.')
        paths = [Path.home() / 'Documents/SPAD.neXt/profiles' / NAME]
    backup = ROOT / 'backups' / ('citation-range-' + time.strftime('%Y%m%d-%H%M%S'))
    for i, path in enumerate(paths):
        repair(path, backup / str(i))
