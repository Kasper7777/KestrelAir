# VIRPIL overlays: Control Panels CP1 / CP2 / CP3 and the CM3 throttle

These are ready-made, true-scale faceplate drawings. Every plate fits a **170 × 200 mm** footprint with 20 mm outer
corners. The CM3 throttle plate is L-shaped, because the throttle-lever area is cut away. Origin is the bottom-left corner as you look at the panel.

## Files in `out/`

| File | Use |
|---|---|
| `CP1.dxf`, `CP2.dxf`, `CP3.dxf`, `CM3.dxf` | **Import into Fusion:** Insert → Insert DXF, pick a plane, units **mm**. |
| `*.svg` | For LightBurn or Inkscape. The units are mm. |
| `*.stl` | The same part as the laser cut: the DXF's CUT layer extruded 3 mm. It is watertight and ready to slice. The designer's own 3D-print versions of CP1, CP2 and CM3, with blind screw recesses, are the 3MFs in `source/printables/`. |
| `*.pdf` | 1:1 paper test print on **A4 portrait**. Choose "Actual size" or 100%, never "Fit". Afterwards, check that the green bar measures 50 mm and the green square 20 × 20 mm. |

DXF layers:
- **CUT** (red): the plate edge and every control opening.
- **POCKET** (magenta): screw-head recesses. This layer is empty, because the screw holes are drawn on CUT as
  **through-holes for laser cutting** (`"screw_holes": "through"` in `panels.json`). They sit exactly where the
  Printables design has its 2 mm back recesses.
  - `true` puts them back on POCKET as recesses.
  - `false` leaves them out.

The CUT layer is **one clean contour per opening plus the plate edge**. Overlapping shapes are already merged, nothing
is cut twice, and arcs are true arcs. In Fusion that gives one profile, so a single extrude-cut does the job.

Some screw holes needed adjusting, because cutting a screw recess right through leaves geometry a laser can't cut
cleanly:
- **Joins.** A screw hole that would leave less than 1 mm of material (`min_web_mm`) is joined to its neighbour.
  Otherwise you'd get a sliver that snaps or burns away. The same rule applies everywhere, so every joint on a panel
  looks alike:
  - **Screw diagonally off a button's corner:** a full-width bridge aimed straight at that corner. This is how all the
    button screws on CP1, CP2 and CM3 are done.
  - **Screw at the plate edge:** a straight notch, square to the edge.
  - **Corner screw, button screw and button in a row** (CP1 by B5, CP2 by B10): one straight channel the width of the
    corner screw, from the plate corner to the button corner.
  - **Screw overlapping a square's edge** (CP3): kept as a round ear. Where it grazes the corner, tangent lines fill
    the 0.07 mm neck.
- **Removed strip on CP2.** The 2.5 mm strip left of the Gear Handle is cut free by screw holes LS3 and LS5, so it would
  drop out. It's left out, which opens the Gear Handle cut-out to the left edge.

The generator prints every bridge and note when it runs.
- **IDS** (grey): control names, for reference only. Don't cut this layer.
- **CHECK** (green): the scale bar and square, for checking scale only. Don't cut this layer.

## Where the numbers come from

| Panel | Source | Accuracy |
|---|---|---|
| CP1, CP2 | Exact CAD values from xchrishawk's FreeCAD model, [Virpil Throttle / Control Panel Label Plates](https://www.printables.com/model/1106661) (CC BY-NC-SA, personal non-commercial use). The designer modelled every control by VIRPIL's name (B1, T7, E2, Gear Handle…), and the openings are already clearance-sized. | Exact to that model. |
| CM3 throttle | Exact CAD values from the same author's throttle plate model, for the MongoosT-50CM3 base panel: T1–T7, B1–B6, E1/E2, Mode selector, Flaps slot. | Exact to that model. Matches DeathDonky's independent throttle template to a median of 0.86 mm. |
| CP3 | Nobody publishes CP3 CAD, so I measured it from DeathDonky Prints' [SharKa-50 template](https://www.deathdonkyprints.com/downloads). The CP3 uses the SharKa-50 faceplate. The template is to scale at 5.68 px/mm. When I ran the same method on DeathDonky's CP2 template, its holes landed within about 0.8 mm of the exact CP2 CAD. | About ±0.5–0.8 mm. The IDs are generic: SQ = button, R = toggle/encoder, LEVER = axis slot, SEL = rotary selector, SS = screw-head clearance, M = corner mounting hole. |

The original downloads are in `source/printables/`. These are all six files from the Printables page: the 3MF and the FreeCAD model for CP1, CP2 and the throttle. That folder also has DeathDonky's CP1 and CP2 templates, which show a second
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

## Verification

`verify-overlays.js` re-checks the outputs against the sources and prints PASS or FAIL. Run it the same way as
`make-overlays.js`. It checks:
- **PDFs:** the page is A4, the scale bar prints at 50.000 mm, and the plate prints at 170.000 × 200.000 mm.
- **CP1/CP2/CM3 DXFs:** every cut line lies within 0.006 mm of the original 3D model's edges, and every model edge is
  present in the DXF.
- **CP2 template:** each control on DeathDonky's independent CP2 template lines up with ours to a median of 0.65 mm.
  T7/T8 differ by about 2 mm because the Printables design cuts those slots longer, which adds clearance.
- **CP3:** it matches the SharKa-50 template, with 99% of edges within 0.44 mm.
- **Laser-ready geometry:**
  - The CUT layer is closed contours, with no loose ends or doubled lines.
  - No openings overlap.
  - The plate is one piece.
  - The thinnest strip of material is at least 1 mm.
  - The sharpest corner of material is at least 15°.
- **Screw holes:** every screw hole is cut right through. On CP1, CP2 and CM3, each one sits on its screw-head recess on
  the back of the original model (median 0.001 mm).
- **Rest of the plate:** away from the screw holes, bridges and removed strips, the plate still matches the original
  model to 0.006 mm.

`make-stl.js` (run after `make-overlays.js`) writes the STLs and checks each one:
- It is watertight with outward normals.
- It measures 170 × 200 × 3 mm.
- Its volume equals the plate area × 3 mm.
- Every top-face vertex lies on the DXF cut lines.

It needs `polygon-clipping` and `earcut` in `..\.tools\stl-deps`.

## Before cutting acrylic

1. Print the PDF at 100%, cut it out, and lay it over the panel. This is especially important for CP3.
2. Cut one in card or 3 mm MDF.
3. When it fits, set `"verified": true` for that panel and cut the real material.
