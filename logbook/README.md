# Kestrel Air Logbook

An interactive map of every flight: NeoFly career legs as glowing great-circle
routes on a 3D globe, a boarding-pass card per leg, MSFS screenshots pinned to
the place they were taken, and a replay that flies the whole journey.

## Use it

Double-click **Kestrel Air Logbook** on the desktop (or `Logbook.vbs` in this folder).

It reads NeoFly and your screenshot folders, rebuilds the logbook and opens it in
the browser. Nothing has to be typed in by hand. Refresh the page after a session
to pick up new flights and screenshots. The launcher runs hidden and stops by
itself a few minutes after you close the tab.

| Key / control | Does |
|---|---|
| Click a route, list row or timeline segment | Open that leg |
| ← / → | Previous / next leg |
| Space or ▶ | Replay the journey from the selected leg (1× to 8×) |
| Fleet chips | Hide or show an aircraft |
| Airport dot | Airport info, every arrival and photos taken on the ground there |
| Yellow dots | Photos, placed along the route by the time they were taken |

## Where the data comes from

| Source | What's used |
|---|---|
| NeoFly `std.bin` (`%LOCALAPPDATA%\Programs\Neofly`) | flight log, job log (missions, pay, pax, cargo), hangar (aircraft), finance ledger (relocations, hotel stays) |
| NeoFly `navdata.sqlite` | airport names, cities, coordinates, runways |
| Steam screenshots (found automatically for every Steam account, MSFS 2020 + 2024) | photos; the time comes from the filename |
| Windows / Game Bar / NVIDIA capture folders | photos, kept only if taken during a flight or layover |

NeoFly's files are copied to a temp folder and opened read-only, so the logbook
never locks or changes your save.

**Gaps are linked automatically.** If one flight ends somewhere other than where
the next starts, a transfer leg fills the gap: taxi, train/coach, ferry (island
hops) or an airline seat for long distances. NeoFly relocations from the ledger are
noted on the leg. Jobs that NeoFly completed but never wrote to the flight log are
recovered as flights and marked *recovered*.

## Corrections (optional)

`overrides.json` is applied on every rebuild:

```json
{
  "gaps":     { "LTCO>LTPU": { "mode": "taxi", "note": "Shared a taxi with the cargo" } },
  "legs":     { "nf-fl-80": { "title": "The Spruce Creek arrival" } },
  "aircraft": { "neofly:9": { "name": "Baron 'Lima Whiskey'", "colorOverride": "#43e97b" } }
}
```

`config.json` lists the NeoFly folder, the pilot photo and the screenshot sources.

## How it's built (for adding stages later)

```
pipeline/               Python, standard library + Pillow (for thumbnails)
  importers/neofly.py     NeoFly -> flights, aircraft, ledger events, airports
  importers/screenshots.py capture folders -> web/media (full JPEG + thumbnail)
  journey.py              orders legs, fills gaps, places photos, builds stops
  build.py                merges everything into web/data/logbook.json
  serve.py                one-click launcher: rebuild on change + local server
web/                    static site, no build step (ES modules + MapLibre GL)
  js/core/                store (state + events), data loader, geo maths, formatting
  js/features/            map, header, journey-list, detail, timeline (replay), lightbox
  js/features/registry.js the plug-in point for new features
```

- **New data source** (another sim, a CSV logbook): add an importer in
  `pipeline/importers/`, merge it in `build.py`. The web app only reads
  `logbook.json`, so it needs no changes.
- **New feature** (scrapbook, journal, stickers): add `web/js/features/<name>.js`
  exporting `{ id, init(ctx), legSections(leg, ctx) }` and list it in `js/main.js`.
  `legSections` returns extra blocks for the leg card. Key anything you store by
  leg id (`nf-fl-12`, `gap-nf-fl-80`): ids come from NeoFly record numbers, so they
  stay the same across rebuilds.

Generated files (`web/data`, `web/media`, `logbook.log`) are git-ignored.
