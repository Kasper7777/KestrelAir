"""Writing to NeoFly's save (std.bin) - the groundwork for the logbook taking over
from NeoFly one feature at a time.

Every change goes through write(), which refuses unless it is safe:
  - "Write to NeoFly" is switched on in Settings (config.json features.neoflyWrite)
  - NeoFly itself is closed (it keeps its own copy in memory and would overwrite ours,
    or see a half-written file)
  - a full copy of the save is taken first (backup/pilots/<pilot>/neofly/before-changes/)
  - the change runs in one transaction; the save's integrity is checked afterwards,
    and if anything is wrong the copy is put back.

    with neofly_write.write('Refuel N513LW') as db:
        db.execute('update hangar set currentFuel=? where id=?', (1212, 9))
"""
import contextlib
import json
import os
import shutil
import sqlite3
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEEP_PRE_WRITE = 10          # newest pre-write copies kept per pilot


class NotAllowed(Exception):
    """Writing isn't possible right now; the message says why, in plain words."""


def _cfg():
    try:
        with open(os.path.join(ROOT, 'config.json'), encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save_path():
    d = os.path.expandvars(_cfg().get('neofly', {}).get('dir', r'%LOCALAPPDATA%\Programs\Neofly'))
    return os.path.join(d, 'std.bin')


def enabled():
    return bool((_cfg().get('features') or {}).get('neoflyWrite'))


def neofly_running():
    if os.name != 'nt':
        return False
    try:
        out = subprocess.run(['tasklist', '/NH', '/FO', 'CSV', '/FI', 'IMAGENAME eq Neofly.exe'], capture_output=True, text=True,
                             timeout=10, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.lower()
        return '"neofly.exe"' in out
    except Exception:
        return False


def status():
    """What the Settings page shows: can the logbook write to NeoFly right now?"""
    path = save_path()
    reasons = []
    if not enabled():
        reasons.append('Switched off')
    if not os.path.exists(path):
        reasons.append('No NeoFly save on this PC')
    if neofly_running():
        reasons.append('NeoFly is open - close it first')
    return {'enabled': enabled(), 'save': path if os.path.exists(path) else None, 'neoflyRunning': neofly_running(),
            'ready': not reasons, 'reasons': reasons, 'lastBackup': _last_pre_write()}


def _backup_dir():
    import backup
    return os.path.join(backup.current_dest(), 'neofly', 'before-changes')


def _last_pre_write():
    try:
        d = _backup_dir()
        files = sorted(f for f in os.listdir(d) if f.startswith('pre-write-') and f.endswith('.bin'))
        return files[-1] if files else None
    except Exception:
        return None


def _check_allowed():
    if not enabled():
        raise NotAllowed('Writing to NeoFly is switched off in Settings.')
    if not os.path.exists(save_path()):
        raise NotAllowed('There is no NeoFly save on this PC.')
    if neofly_running():
        raise NotAllowed('NeoFly is open. Close it first - it would overwrite the change.')


def _snapshot(reason):
    d = _backup_dir()
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, f'pre-write-{time.strftime("%Y%m%d-%H%M%S")}-{int(time.time() * 1000) % 1000:03d}.bin')
    src = sqlite3.connect(f'file:{save_path()}?mode=ro', uri=True)
    out = sqlite3.connect(dst)
    try:
        src.backup(out)                     # consistent copy even if something has the file open
    finally:
        out.close()
        src.close()
    with open(dst + '.txt', 'w', encoding='utf-8') as fh:
        fh.write(reason + '\n')
    old = sorted(f for f in os.listdir(d) if f.startswith('pre-write-') and f.endswith('.bin'))
    for f in old[:-KEEP_PRE_WRITE]:
        for p in (f, f + '.txt'):
            with contextlib.suppress(OSError):
                os.remove(os.path.join(d, p))
    return dst


@contextlib.contextmanager
def write(reason):
    """One safe change to the NeoFly save. `reason` is kept beside the backup copy."""
    _check_allowed()
    copy = _snapshot(reason)
    con = sqlite3.connect(save_path(), timeout=5, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute('begin immediate')
        try:
            yield con
            con.execute('commit')
        except BaseException:
            con.execute('rollback')
            raise
        ok = con.execute('pragma integrity_check').fetchone()[0]
    finally:
        con.close()
    if ok != 'ok':
        shutil.copy2(copy, save_path())
        raise RuntimeError(f'NeoFly save failed its check after the change ({ok}); the copy from before was put back.')


def test():
    """Dry run for Settings: prove the save can be opened for writing, change nothing."""
    _check_allowed()
    con = sqlite3.connect(save_path(), timeout=5, isolation_level=None)
    try:
        con.execute('begin immediate')
        con.execute('rollback')
        ok = con.execute('pragma quick_check').fetchone()[0]
    finally:
        con.close()
    if ok != 'ok':
        raise RuntimeError(f'NeoFly save check: {ok}')
    return True
