"""Assign installed Black Square liveries to their matching KestrelAir profiles."""
from pathlib import Path
import os
import shutil
from datetime import datetime
import xml.etree.ElementTree as E

base = Path(__file__).resolve().parent
conf = Path(os.environ['APPDATA']) / 'SPAD.neXt/conf'
ns = 'http://www.fsgs.com/SPAD'
n = {'s': ns}
E.register_namespace('', ns)
E.register_namespace('xsd', 'http://www.w3.org/2001/XMLSchema')
E.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
tag = lambda x: '{'+ns+'}'+x
path = conf / 'AircraftAssignments_MSFS24.xml'
root = E.parse(path).getroot()
aircraft = E.parse(conf / 'aircraftlist.xml')
assignments = []
for entry in aircraft.findall('.//s:AircraftEntry', n):
    name = entry.text or ''
    profile = None
    for variant in ['A36', 'A36TC', 'B36TP']:
        if name.startswith(f'Black Square {variant} Bonanza Professional '):
            profile = f'Bonanza {variant} - GNS 530 + TDS GTNxi 650.xml'
    if name.startswith('Black Square Baron 58P Professional '):
        profile = 'Baron - GNS 530 + TDS GTNxi 650.xml'
    if not profile:
        continue
    assert (Path.home() / 'Documents/SPAD.neXt/profiles' / profile).is_file()
    matches = [a for a in root.findall('s:AircraftAssignment', n) if a.findtext('s:Key', namespaces=n) == name]
    assert len(matches) <= 1, name
    assignment = matches[0] if matches else E.SubElement(root, tag('AircraftAssignment'))
    if not matches:
        E.SubElement(assignment, tag('Key')).text = name
        E.SubElement(assignment, tag('Profile'))
    assignment.find('s:Profile', n).text = profile
    assignments.append((name, profile))
assert len(assignments) >= 20, 'Expected all installed Black Square variants'
backup = base / 'backups' / ('aircraft-assignments-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
shutil.copy2(path, backup / path.name)
E.indent(root, space='  ')
E.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
(base / 'portable-setup/aircraft-assignments.csv').write_text('Aircraft,Profile\n'+'\n'.join(f'"{a}","{p}"' for a,p in assignments), encoding='utf-8')
print(f'Assigned {len(assignments)} installed liveries. Backup: {backup}')
