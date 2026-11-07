"""Replace persistent reverse gates without rebuilding unrelated Citation bindings."""
from pathlib import Path
import shutil
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
    root = E.parse(path).getroot()
    variables = root.find('s:Variables', N)
    for var in list(variables):
        if var.get('Name') in ('PROFILE:KA_REV1', 'PROFILE:KA_REV2'):
            variables.remove(var)
    dev = next(d for d in root.findall('./s:Devices/s:Device', N) if d.get('ProductID') == '0x0194')
    for engine, axis, buttons in [(1, 'X', (5, 7, 6)), (2, 'Y', (8, 11, 9))]:
        for conditions in dev.findall(f'.//s:Event[@BoundTo="{axis}_AXIS"]//s:EventConditions', N):
            for condition in list(conditions):
                if condition.get('ConditionValueSource') == f'PROFILE:KA_REV{engine}':
                    conditions.remove(condition)
                    for button in buttons:
                        E.SubElement(conditions, f'{{{NS}}}EventCondition', ConditionTargetValue='0',
                                     ConditionValueSource=f'LOCAL:JOY_0X33440X0194_BUTTON_{button}')
        for button in buttons:
            for actions in dev.findall(f'.//s:Event[@BoundTo="BUTTON_{button}"]//s:EventActions', N):
                for action in list(actions):
                    if action.get('TargetDataDefinition') == f'PROFILE:KA_REV{engine}':
                        actions.remove(action)
    assert 'PROFILE:KA_REV' not in E.tostring(root, encoding='unicode')
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / path.name)
    E.indent(root, space='  ')
    E.ElementTree(root).write(path, encoding='utf-8')
    print('Repaired', path)

if __name__ == '__main__':
    base = ROOT / 'backups' / ('citation-reverse-flags-' + time.strftime('%Y%m%d-%H%M%S'))
    paths = [ROOT / 'profiles' / NAME, ROOT / 'portable-setup/profiles' / NAME]
    if '--installed' in sys.argv:
        paths = [Path.home() / 'Documents/SPAD.neXt/profiles' / NAME]
    for i, path in enumerate(paths):
        repair(path, base / str(i))
