"""Screenshot importer.

Scans the folders listed in config.json -> photos.sources, works out when each
image was taken (from the filename when the capture tool encodes it, otherwise
the file's modified time) and copies it into web/media as a web-friendly JPEG
plus a small thumbnail. Copies are incremental: an image already imported is
skipped, so re-running the build is cheap.

Placing photos on the journey happens later in journey.py, from the timestamp.
"""
import hashlib
import os
import re
from datetime import datetime

try:
    from PIL import Image, ImageOps
except ImportError:  # the build still works, photos are just copied as-is
    Image = None

EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
NAME_PATTERNS = [
    # Steam: 20261110195225_1.jpg
    (re.compile(r'(?<!\d)(\d{14})_\d+'), '%Y%m%d%H%M%S'),
    # Windows Snipping Tool / Win+PrtScn: Screenshot 2026-05-16 005654.png
    (re.compile(r'(\d{4}-\d{2}-\d{2} \d{6})'), '%Y-%m-%d %H%M%S'),
    # Xbox Game Bar: Microsoft Flight Simulator 2024 2026-11-10 19-52-25.png
    (re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})'), '%Y-%m-%d %H-%M-%S'),
    # NVIDIA: ... 2026.11.10 - 19.52.25.03.png
    (re.compile(r'(\d{4}\.\d{2}\.\d{2} - \d{2}\.\d{2}\.\d{2})'), '%Y.%m.%d - %H.%M.%S'),
]


def taken_at(path):
    name = os.path.basename(path)
    for rx, fmt in NAME_PATTERNS:
        m = rx.search(name)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt), 'filename'
            except ValueError:
                pass
    return datetime.fromtimestamp(os.path.getmtime(path)), 'modified'


STEAM_APPS = {'2537590': 'MSFS 2024 (Steam)', '1250410': 'MSFS 2020 (Steam)'}


def steam_sources():
    """Every Steam account's screenshot folder for MSFS 2020/2024, found via the
    registry, so nothing is tied to one Steam ID or install path."""
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ('SteamPath', 'InstallPath'):
                        try:
                            roots.append(os.path.normpath(winreg.QueryValueEx(k, name)[0]))
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots.append(os.path.expandvars(r'%ProgramFiles(x86)%\Steam'))
    found, seen = [], set()
    for root in roots:
        ud = os.path.join(root, 'userdata')
        if not os.path.isdir(ud):
            continue
        for user in os.listdir(ud):
            for app, label in STEAM_APPS.items():
                p = os.path.normcase(os.path.join(ud, user, '760', 'remote', app, 'screenshots'))
                if os.path.isdir(p) and p not in seen:
                    seen.add(p)
                    found.append({'label': label, 'path': p})
    return found


def expand_sources(sources):
    out = []
    for s in sources:
        if s.get('auto') == 'steam':
            out.extend(steam_sources())
        else:
            out.append(s)
    return out


def scan(sources, media_dir, rel_prefix='media'):
    photos_dir = os.path.join(media_dir, 'photos')
    thumbs_dir = os.path.join(media_dir, 'thumbs')
    os.makedirs(photos_dir, exist_ok=True)
    os.makedirs(thumbs_dir, exist_ok=True)
    out = []
    seen = set()
    for src in sources:
        root = os.path.expandvars(os.path.expanduser(src['path']))
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() != 'thumbnails']
            for fn in sorted(files):
                if not fn.lower().endswith(EXTS):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if st.st_size < src.get('minBytes', 20000):
                    continue  # skip tiny UI snips
                when, how = taken_at(full)
                # id from name + size, so the same shot found in Steam and in the
                # repo's backup folder is one photo, and ids match on every PC
                pid = hashlib.sha1(f'{fn.lower()}|{st.st_size}'.encode()).hexdigest()[:12]
                if pid in seen:
                    continue
                seen.add(pid)
                photo = os.path.join(photos_dir, pid + '.jpg')
                thumb = os.path.join(thumbs_dir, pid + '.jpg')
                size = _export(full, photo, thumb)
                if not size:
                    continue
                out.append({
                    'id': pid, 'takenAt': when.strftime('%Y-%m-%dT%H:%M:%S'), 'timeFrom': how,
                    'source': src.get('label', 'Screenshots'), 'original': full,
                    'src': f'{rel_prefix}/photos/{pid}.jpg', 'thumb': f'{rel_prefix}/thumbs/{pid}.jpg',
                    'width': size[0], 'height': size[1],
                })
    out.sort(key=lambda p: p['takenAt'])
    return out


def _export(src, photo, thumb):
    if Image is None:
        if not os.path.exists(photo):
            import shutil
            shutil.copy2(src, photo)
            shutil.copy2(src, thumb)
        return (0, 0)
    try:
        if os.path.exists(photo) and os.path.exists(thumb):
            with Image.open(photo) as im:
                return im.size
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            if max(im.size) > 2560:
                im.thumbnail((2560, 2560), Image.LANCZOS)
            im.save(photo, 'JPEG', quality=88, optimize=True, progressive=True)
            size = im.size
            im.thumbnail((560, 560), Image.LANCZOS)
            im.save(thumb, 'JPEG', quality=80, optimize=True)
            return size
    except Exception as e:  # unreadable image: skip it, keep building
        print(f'  ! could not import {src}: {e}')
        return None
