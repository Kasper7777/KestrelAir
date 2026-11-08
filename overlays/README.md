# VIRPIL Control Panel overlays (CP1 / CP2 / CP3)

VIRPIL doesn't publish faceplate drawings or CAD for the Control Panels. Their manuals and stores give only the overall
housing size (CP2 236×201×164 mm, CP3 236×201×130.5 mm, CP1 236×202×83 mm). Those figures include the legs and
levers, so they're no use for hole positions. The geometry has to come from your own panels. This folder turns your
measurements into true-scale files.

| File | Use |
|---|---|
| `panels.json` | Your measurements (mm). `EXAMPLE` shows every feature type. |
| `make-overlays.js` | Generator. No dependencies. |
| `out/<panel>.dxf` | **Import this into Fusion.** It's true scale in mm, with layers CUT (red), ENGRAVE (blue) and CHECK (green). |
| `out/<panel>.svg` | For LightBurn or Inkscape. The units are mm. |
| `out/<panel>.pdf` | 1:1 paper test print. |

Run it with:

```
..\.tools\playwright-runtime\node-v26.13.0-win-x64\node.exe make-overlays.js
```

## Getting accurate numbers (±0.1–0.2 mm)

1. **Scan, don't photograph.** Pull the knobs and switch caps off and lay the panel face-down on a flatbed scanner.
   Scan at 600 dpi with no scaling. A scanner is orthographic, so it has no lens distortion and no perspective error.
   A phone photo has both.
2. Put a steel ruler or a caliper-checked object in the scan. It confirms the scale and lets you calibrate the image.
3. **Fusion, if you trace:** Insert → Canvas. Right-click the canvas → Calibrate, and click two points a known
   distance apart on the ruler. Then sketch over it.
   **This generator, if you prefer typing numbers:** read hole centres off the scan (in GIMP or Fusion) and enter them
   in `panels.json`.
4. Use **calipers** to check the scan on 2–3 things: the plate width, one hole diameter, and one centre-to-centre
   distance. Calipers beat the scan on hole diameters, so type those in directly.
5. For toggle switches, note any anti-rotation key tab or flat on the bushing. Model a tab as a small `slot` next to
   the hole (see `SW1-key` in the example).

### Feature types (`x`, `y` = centre, origin = bottom-left of the plate, Y up)

- `circle`: `d`
- `rect`: `w`, `h`, optional corner radius `r`, optional `angle`
- `slot`: `w`, `h`, with fully rounded ends (gear-lever channels)
- `text`: `text`, `h` (cap height). It goes on the ENGRAVE layer.
- `"no_clearance": true` keeps a hole at its exact size, which is right for screw holes.

`hole_clearance_mm` (0.4 by default) is added to every opening's diameter or width so the overlay slips over the
bushings. Kerf compensation is a separate setting: make it in your laser software (LightBurn's kerf offset), not here.

## Before you cut acrylic

1. Print the PDF at **100% / Actual size**, not fit-to-page. Measure the green 50 mm bar. Larger panels need A3 paper,
   or tile the PDF.
2. Cut the print out and lay it over the real panel. Fix anything that's off, regenerate, and repeat.
3. Next, cut it once in card or 3 mm MDF. When it fits, set `"verified": true` and cut the real material.
