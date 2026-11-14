# Kestrel Air Logbook

An interactive map of every flight: NeoFly career legs as glowing great-circle
routes on a 3D globe, a boarding-pass card per leg, MSFS screenshots pinned to
the place they were taken, and a replay that flies the whole journey.

## Use it

Double-click **`Kestrel Air Logbook.exe`** in this folder (the kestrel icon). The
desktop and Start-menu shortcuts point at the same exe.

It reads NeoFly and your screenshot folders, rebuilds the logbook and opens it in
the browser. Nothing has to be typed in by hand. Refresh the page after a session
to pick up new flights and screenshots. It runs hidden and stops by itself a few
minutes after you close the tab.

## Backups, and opening it on another PC

Every launch, and the **💾 Back up** button, copies into `backup/`:

- `backup/neofly/std-<date>.bin`: your NeoFly save. A new copy is made only when it changed, and old ones are kept.
- `backup/neofly/flights.csv`: every leg as a spreadsheet.
- `backup/photos/<source>/`: full-quality original screenshots. Nothing is ever deleted here.
- `backup/airports.json`: airport names and positions, so no NeoFly install is needed.

`backup/` is meant to be committed with the repo. On another PC, clone the repo
and double-click the exe. If that PC has no NeoFly or Steam, it builds the whole
logbook from `backup/`. The first time, it offers to install **uv** (a small Python
runner), which then downloads Python by itself.

> The GitHub repo is public at the moment, so anything committed in `backup/`
> (save file, screenshots) is visible to anyone. Make the repo private first if
> that matters.

| Key / control | Does |
|---|---|
| Click a route, list row or timeline segment | Open that leg |
| ← / → | Previous / next leg |
| Space or ▶ | Replay from the selected leg (1× to 8×). The aircraft's own silhouette flies the route, and your photos drop onto the map as prints where they were taken |
| Follow button (next to speed) | Cinematic replay: tilted camera riding along behind the aircraft |
| Logbook | Every flight written up as an EASA-style paper logbook with Casper as pilot in command: page totals carried forward, night time from the sun's position, page tabs. **Company** shows the flights your hired pilots flew. Click an entry to see it on the map |
| Diary | For every stop of 8 hours or more: an Instagram-style, day-by-day account of Casper on the ground. The restaurants (OpenStreetMap) and sights (Wikipedia) are real and near the airport; the day out is imagined |
| Layer strip (right edge of the map) | Turn country flags, flights, transfers, airports, codes and photo pins on or off |
| Photos | Photo wall of every screenshot as prints, month by month |
| Insights | Records (longest, farthest, softest landing, best-paid job…), hours per month, landing spread, most-visited airports |
| Hover a list row | Lights its route up on the map |
| View | Satellite / dark / light map, globe or flat, colour by aircraft or month, layer switches (countries visited, flights, transfers, airports, codes, photo pins) |
| Fleet tab | Your aircraft with photos; tap to hide or show its flights |
| Countries tab | Every country you've landed in (also shaded on the map) |
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

| Wikipedia (looked up once, cached in `backup/wiki/`) | airport photo, summary and facts; aircraft-type photos |
| OpenStreetMap + Wikipedia (once, cached in `backup/places/`) | restaurants and sights near layover airports, local dishes, for the diary |
| flagcdn + Natural Earth (once, cached in `backup/flags/`, `web/geo/`) | each visited country filled in with its flag |

The pilot's character name (pilot in command in the logbook, the diary handle) is
`pilot.character` in `config.json`. The app icon is drawn from `pipeline/icon/vulture.svg`
by `pipeline/icon/build_icon.py`.

**Gaps are worked out from NeoFly's own records.** When one flight ends somewhere
other than where the next starts:

1. If the same aircraft flew the leg before and after with no paid NeoFly move, you
   flew it. It's added as an **unlogged** flight, with times taken from NeoFly's
   landing fees or your screenshots.
2. If the aircraft you arrived in next departs from the new airport (your own flight
   or a hired pilot's), you flew it there.
3. If NeoFly charged to move the aircraft, it's a **NeoFly reposition** (no travel).
4. Only otherwise is it a taxi, train, ferry or airline transfer, chosen by distance and geography.

Each leg card says why. Jobs NeoFly completed but never logged are marked
*recovered*. Paths are direct great-circle lines: no actual flight tracks exist in
NeoFly or MSFS for past flights, and nothing extra is recorded.

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
  serve.py                local server: rebuild on change, auto-backup, Back up button
  backup.py               copies sources into backup/
  launcher/               Kestrel Air Logbook.exe source (build.ps1 rebuilds it)
  make_icon.py            draws kestrel.ico
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

`web/data` and `web/media` are rebuilt on every launch, so they're git-ignored.
`backup/` holds the real data and is committed.
