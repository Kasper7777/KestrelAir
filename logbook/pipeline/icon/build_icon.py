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

# the glass tile: deep tinted glass with coloured light glowing through from behind
# (like the map under the app's panels), a frosted luminous vulture, a curved
# specular highlight and a lit rim
_bird_glass = inner.replace('fill="#141414"', 'fill="url(#bird)"').replace('#f3eee6', '#1b2236')
TILE = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="base" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#26324f"/><stop offset="1" stop-color="#0c1120"/></linearGradient>
    <radialGradient id="g1" cx=".22" cy=".88" r=".55"><stop offset="0" stop-color="#ffb547" stop-opacity=".95"/><stop offset="1" stop-color="#ffb547" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx=".9" cy=".25" r=".5"><stop offset="0" stop-color="#4ec7ff" stop-opacity=".75"/><stop offset="1" stop-color="#4ec7ff" stop-opacity="0"/></radialGradient>
    <radialGradient id="g3" cx=".75" cy="1" r=".45"><stop offset="0" stop-color="#ff5d8f" stop-opacity=".55"/><stop offset="1" stop-color="#ff5d8f" stop-opacity="0"/></radialGradient>
    <linearGradient id="bird" x1=".2" y1="0" x2=".6" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#ffeccc"/><stop offset="1" stop-color="#ffbe5c"/></linearGradient>
    <linearGradient id="sheen" x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".55"/><stop offset=".5" stop-color="#fff" stop-opacity=".08"/><stop offset=".52" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".35" stop-color="#fff" stop-opacity=".18"/>
      <stop offset=".7" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#ffd59a" stop-opacity=".7"/></linearGradient>
    <linearGradient id="foot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".28"/></linearGradient>
    <filter id="blur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="28"/></filter>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur in="SourceAlpha" stdDeviation="9" result="b"/>
      <feFlood flood-color="#ffc77a" flood-opacity=".75"/><feComposite in2="b" operator="in" result="g"/>
      <feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <clipPath id="tile"><rect x="16" y="16" width="480" height="480" rx="112"/></clipPath>
  </defs>
  <g clip-path="url(#tile)">
    <rect x="16" y="16" width="480" height="480" fill="url(#base)"/>
    <g filter="url(#blur)"><rect x="16" y="16" width="480" height="480" fill="url(#g1)"/><rect x="16" y="16" width="480" height="480" fill="url(#g2)"/>
      <rect x="16" y="16" width="480" height="480" fill="url(#g3)"/></g>
    <rect x="16" y="16" width="480" height="480" fill="#ffffff" opacity=".06"/>
    <g filter="url(#glow)" transform="translate(38 30) scale(.86)">{_bird_glass}</g>
    <path d="M16 16 H496 V210 C390 250 150 255 16 222 Z" fill="url(#sheen)"/>
    <rect x="16" y="360" width="480" height="136" fill="url(#foot)"/>
  </g>
  <rect x="19" y="19" width="474" height="474" rx="109" fill="none" stroke="url(#rim)" stroke-width="5"/>
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
