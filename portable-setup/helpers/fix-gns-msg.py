"""PulsAIR display-module MSG key (0x14CB buttons 12 and 37, PFD/GNS focus) -> aircraft's native B:AS530_MSG.

2026-11-04: SPAD's log showed every MSG press sending H:AS530_1_MSG_Push, but the GNS 530 did not react.
The aircraft advertises the input event B:AS530_MSG (SPAD log "new B: 'AS530_MSG'"), the same family as
B:AS530_RANGE_ZOOM_Inc/_Dec that RANGE already uses. Only that one action string changes; focus and
SFS-Monitor gate conditions stay. Close SPAD first (it rewrites profiles on exit). Idempotent.
Usage: python fix-gns-msg.py <profile.xml> [...]
"""
from pathlib import Path
import subprocess
import sys

OLD = 'TargetDataDefinition="H:AS530_1_MSG_Push"'
NEW = 'TargetDataDefinition="B:AS530_MSG_Push"'


def main():
    if 'SPAD.neXt.exe' in subprocess.run(['tasklist'], capture_output=True, text=True).stdout:
        sys.exit('SPAD.neXt is running: close it first, or it will overwrite this change.')
    for name in sys.argv[1:]:
        path = Path(name)
        raw = path.read_bytes()
        n = raw.count(OLD.encode())
        path.write_bytes(raw.replace(OLD.encode(), NEW.encode()))
        print(f'{path}: {n} MSG binding(s) changed, {raw.count(NEW.encode()) + n} now native')


if __name__ == '__main__':
    main()
