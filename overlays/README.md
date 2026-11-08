# VIRPIL Control Panel overlays (CP1 / CP2 / CP3)

These are ready-made, true-scale faceplate drawings. All three panels share the same plate: **170 × 200 mm with
20 mm corner radii**. Origin is the bottom-left corner as you look at the panel.

## Files in `out/`

| File | Use |
|---|---|
| `CP1.dxf`, `CP2.dxf`, `CP3.dxf` | **Import into Fusion:** Insert → Insert DXF, pick a plane, units **mm**. |
| `*.svg` | For LightBurn or Inkscape. The units are mm. |
| `*.pdf` | 1:1 paper test print. Use 100% / Actual size and check the green 50 mm bar. The page is larger than A4, so use A3 or tile it. |

DXF layers:
- **CUT** (red): the plate edge and every control opening.
- **POCKET** (magenta): screw-head recesses. The original is a 3 mm plate with 2 mm-deep recesses on the back so the panel's faceplate screw heads don't lift it. You can engrave them from the back, cut them through, or delete them.
- **IDS** (grey): control names, for reference only. Don't cut this layer.
- **CHECK** (green): the scale bar and square, for checking scale only. Don't cut this layer.

Some shapes deliberately overlap the plate edge: the CP3 lever slots, the side notches, and the CP3 selector keyhole,
which is a circle plus two tabs. They still cut correctly. In Fusion, select all the regions of each opening when you
extrude-cut.

## Where the numbers come from

| Panel | Source | Accuracy |
|---|---|---|
| CP1, CP2 | Exact CAD values from xchrishawk's FreeCAD model, [Virpil Throttle / Control Panel Label Plates](https://www.printables.com/model/1106661) (CC BY-NC-SA, personal non-commercial use). The designer modelled every control by VIRPIL's name (B1, T7, E2, Gear Handle…), and the openings are already clearance-sized. | Exact to that model. |
| CP3 | Nobody publishes CP3 CAD, so I measured it from DeathDonky Prints' [SharKa-50 template](https://www.deathdonkyprints.com/downloads). The CP3 uses the SharKa-50 faceplate. The template is to scale at 5.68 px/mm. When I ran the same method on DeathDonky's CP2 template, its holes landed within about 0.8 mm of the exact CP2 CAD. | About ±0.5–0.8 mm. The IDs are generic: SQ = button, R = toggle/encoder, LEVER = axis slot, SEL = rotary selector, SS = screw-head clearance, M = corner mounting hole. |

The original downloads are in `source/`. That folder also has DeathDonky's CP1 and CP2 templates, which show a second
designer's take. That design uses through-holes for the screw heads and small corner holes, so it can be screwed on
with the panel's own corner screws.

## Changing things

Edit `panels.json`, then run:

```
..\.tools\playwright-runtime\node-v26.13.0-win-x64\node.exe make-overlays.js
```

Feature types (`x`, `y` = centre):
- `circle` takes `d`.
- `rect` takes `w`, `h`, an optional corner radius `r` and an optional `angle`.
- `slot` takes `w` and `h` and has round ends.
- `poly` takes `points` relative to `x`/`y`, plus `fillet`.
- `text` takes `text` and `h`. It goes on the ENGRAVE layer.

`hole_clearance_mm` is added to every opening. It's 0 here because the source cutouts already include clearance.
Kerf compensation is a separate setting: make it in your laser software, not here.

## Before cutting acrylic

1. Print the PDF at 100%, cut it out, and lay it over the panel. This is especially important for CP3.
2. Cut one in card or 3 mm MDF.
3. When it fits, set `"verified": true` for that panel and cut the real material.
