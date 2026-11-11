"""Cross-check the illustrated guide against the FlightFX Citation X Full Checklist PDF, item by item.

Reads every bullet from the FlightFX PDF (all pages), groups them under their section headings, and
compares them in order with the guide's "item: response" text. Spacing around '/' and runs of spaces
are ignored; every other character must match.

Run: uv run --with reportlab --with pillow --with pymupdf --with svglib python verify-citation-checklist-guide.py <FlightFX full checklist.pdf>
"""
import importlib.util
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('guide', ROOT / 'build-citation-taxi-takeoff-guide.py')
guide = importlib.util.module_from_spec(spec); spec.loader.exec_module(guide)

HEADINGS = ['Before Start', 'APU Start', 'Starting Engines', 'Starting Second Engine: Cross Bleed',
            'Before Taxi', 'Taxi', 'Before Takeoff', 'Takeoff', 'After Takeoff/Climb', 'Cruise',
            'Descent', 'Approach', 'Before Landing', 'Landing', 'Shutdown']


def norm(text):
    text = re.sub(r'\s*/\s*', '/', text)
    return re.sub(r'\s+', ' ', text).strip()


def flightfx_sections(pdf):
    lines = []
    for page in pymupdf.open(pdf):
        text = re.sub(r'[‪-‮​]', '', page.get_text())
        lines += [l.strip() for l in text.splitlines() if l.strip()]
    sections, current = {}, None
    for line in lines:
        if line in HEADINGS or line == 'Method':
            if line != 'Method':
                current = line; sections[current] = []
            continue
        if line.startswith('●'):
            sections[current].append(line.lstrip('● ').strip())
        elif current and sections[current] and not line.startswith(('Textron', '2020', 'Not for')):
            sections[current][-1] += ' ' + line
    return sections


def main(pdf):
    source = flightfx_sections(pdf)
    by_phase = [[] for _ in guide.PHASES]
    for page in guide.PAGES:
        by_phase[page['phase']].extend(page['steps'])
    problems, total = [], 0
    for ph, heading in enumerate(HEADINGS):
        theirs = [norm(x) for x in source.get(heading, [])]
        ours = [norm(f'{item}: {response}') for _, item, response, _ in by_phase[ph]]
        total += len(theirs)
        if len(theirs) != len(ours):
            problems.append(f'{heading}: FlightFX has {len(theirs)} items, guide has {len(ours)}')
        for n, (a, b) in enumerate(zip(theirs, ours), 1):
            if a != b:
                problems.append(f'{heading} #{n}:\n   FlightFX: {a}\n   guide:    {b}')
        print(f'{heading:<38} FlightFX {len(theirs):>3}   guide {len(ours):>3}')
    print(f'TOTAL FlightFX items: {total}')
    if problems:
        print('\nMISMATCHES:'); print('\n'.join(problems)); sys.exit(1)
    print('All items match FlightFX word for word, in order.')


if __name__ == '__main__':
    main(sys.argv[1])
