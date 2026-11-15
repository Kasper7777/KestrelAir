from pathlib import Path
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import drone_precision as p
import restore_drone_bindings as rollback

root = p.ROOT
ns = {'s': 'http://www.fsgs.com/SPAD'}
folders = [root/'profiles', root/'portable-setup/profiles', Path.home()/'Documents/SPAD.neXt/profiles']
count = 0
for folder in folders:
    backups = [d / folder.parent.name for d in (root/'backups').glob('drone-precision-*')
               if (d/folder.parent.name).is_dir()]
    backup = max(backups, key=lambda d: d.parent.name)
    for path in folder.glob('*.xml'):
        before = (backup/path.name).read_bytes().decode('utf-8-sig')
        after = path.read_bytes().decode('utf-8-sig')
        # Recover the exact original drone actions, then compare XML. SPAD may
        # reserialize the edited actions on load; ignore only those six actions.
        expected = ET.fromstring(before)
        current = ET.fromstring(after)
        for tree in (expected, current):
            found = 0
            for dev in tree.findall('.//s:Device', ns):
                if dev.get('ProductID') != '0x03F5':
                    continue
                for event in dev.findall('.//s:Event', ns):
                    if event.get('BoundTo') not in ('X_AXIS','Y_AXIS','RZ_AXIS'):
                        continue
                    for actions in event.findall('.//s:EventActions', ns):
                        for action in list(actions):
                            if (action.tag.endswith('EventActionVirtualJoyStick') and action.get('JoystickAction')=='VJOY_AXIS'
                                or action.tag.endswith('EventActionChangeValue') and action.get('TargetDataDefinition','').startswith('LOCAL:JOY_0X12340XBEAD_')):
                                actions.remove(action)
                                found += 1
            assert found == 6, (path, found)
        assert ET.tostring(expected)==ET.tostring(current), f'Unrelated edit: {path}'
        assert 'KA_DRONE_TEST' not in after, path
        # Confirm rollback can recover all six exact backed-up actions.
        rollback.restore(after, before)
        count += 1
print(f'PASS: {count} profiles; only six drone actions changed; flight/cabin conditions preserved; no test bindings')
