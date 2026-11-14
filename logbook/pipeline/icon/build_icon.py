"""Builds the app icon: the vulture (vulture.svg) on a glossy glass tile.

Writes logbook/app.ico (exe + shortcuts), web/icon.png (browser tab, boot
screen) and web/mark.svg (the bird alone, for the title bar).
    uv run --no-project --with pillow --with playwright python pipeline/icon/build_icon.py
Rendering uses Edge through Playwright, so the SVG is drawn exactly as a browser would.
"""
import io
import os
import re

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
bird = open(os.path.join(HERE, 'vulture.svg'), encoding='utf-8').read()
inner = re.search(r'<svg[^>]*>(.*)</svg>', bird, re.S).group(1)

TILE = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="paper" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fbf6ec"/><stop offset=".55" stop-color="#f1e6d2"/><stop offset="1" stop-color="#dcc7a4"/>
    </linearGradient>
    <radialGradient id="glow" cx=".5" cy="1.05" r=".75"><stop offset="0" stop-color="#ffb547" stop-opacity=".55"/><stop offset="1" stop-color="#ffb547" stop-opacity="0"/></radialGradient>
    <linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity=".85"/><stop offset=".45" stop-color="#fff" stop-opacity=".18"/><stop offset=".46" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".4" stop-color="#fff" stop-opacity=".15"/>
      <stop offset=".7" stop-color="#7a5a2a" stop-opacity=".25"/><stop offset="1" stop-color="#fff" stop-opacity=".6"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="10" stdDeviation="10" flood-color="#3a2a10" flood-opacity=".35"/></filter>
    <clipPath id="tile"><rect x="16" y="16" width="480" height="480" rx="112"/></clipPath>
  </defs>
  <g clip-path="url(#tile)">
    <rect x="16" y="16" width="480" height="480" fill="url(#paper)"/>
    <rect x="16" y="16" width="480" height="480" fill="url(#glow)"/>
    <g filter="url(#shadow)" transform="translate(38 30) scale(.86)">{inner.replace('#f3eee6', '#f1e6d2')}</g>
    <path d="M16 16 H496 V196 C380 236 140 236 16 196 Z" fill="url(#sheen)" opacity=".75"/>
  </g>
  <rect x="18" y="18" width="476" height="476" rx="110" fill="none" stroke="url(#rim)" stroke-width="4"/>
</svg>'''


def render(svg, size, page):
    page.set_viewport_size({'width': size, 'height': size})
    page.set_content(f'<html><body style="margin:0;background:transparent">{svg.replace("<svg ", f"<svg width=\"{size}\" height=\"{size}\" ", 1)}</body></html>')
    return Image.open(io.BytesIO(page.screenshot(omit_background=True))).convert('RGBA')


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge')
        pg = b.new_page()
        big = render(TILE, 1024, pg)
        b.close()
    big.resize((256, 256), Image.LANCZOS).save(os.path.join(ROOT, 'app.ico'),
                                               sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)])
    big.resize((192, 192), Image.LANCZOS).save(os.path.join(ROOT, 'web', 'icon.png'))
    big.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, 'web', 'icon-512.png'))
    mark = re.sub(r'#141414', 'currentColor', bird)
    mark = re.sub(r'<g fill="none" stroke="#f3eee6".*?</g>', '', mark, flags=re.S)  # solid bird for small sizes
    with open(os.path.join(ROOT, 'web', 'mark.svg'), 'w', encoding='utf-8') as fh:
        fh.write(mark)
    print('icon written')


if __name__ == '__main__':
    main()
