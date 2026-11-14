"""Generates the glass lens displacement map used by the liquid-glass filter.

Red = horizontal shift, green = vertical shift (128 = none). Near each edge the
map pushes sampling inward with a curved falloff, so the background seen through
a panel bends towards its rim like light through thick, rounded glass. The PNG is
inlined into web/index.html (an SVG feImage), so it needs no extra request.
    uv run --no-project --with pillow python pipeline/icon/lens_map.py
"""
import base64
import io
import os
import re

from PIL import Image

N = 256
EDGE = 0.24      # how far in from the rim the bending reaches (fraction of the panel)


def shift(t):
    left = max(0.0, 1 - t / EDGE)
    right = max(0.0, 1 - (1 - t) / EDGE)
    return left ** 2.2 - right ** 2.2           # +1 at the left/top rim, -1 at the right/bottom rim


def main():
    img = Image.new('RGB', (N, N))
    px = img.load()
    for y in range(N):
        gy = shift(y / (N - 1))
        for x in range(N):
            gx = shift(x / (N - 1))
            px[x, y] = (int(128 + 127 * gx), int(128 + 127 * gy), 128)
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    uri = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, 'web', 'index.html')
    html = open(path, encoding='utf-8').read()
    html = re.sub(r'(<feImage id="lens-map" href=")[^"]*(")', lambda m: m.group(1) + uri + m.group(2), html)
    open(path, 'w', encoding='utf-8').write(html)
    print(f'lens map: {len(buf.getvalue())} bytes inlined')


if __name__ == '__main__':
    main()
