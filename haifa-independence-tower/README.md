# Patio building — Derech HaAtzma'ut, Haifa

Parametric 3D massing model of the proposed 22-storey building (the yellow mass
in the sketches), shown next to the existing government tower on Derech
HaAtzma'ut. Built from the "patio building" alternative in
`מכרז חיפה נתוני חלופות.xlsx`.

Nothing here is hand-modelled. One script reads the floor-area schedule and
generates the geometry, so changing an area or a storey height and re-running
regenerates every output.

```
python3 build_model.py     # geometry, exports and preview renders -> out/
python3 make_viewer.py     # self-contained interactive page       -> out/viewer.html
```

## What drives the shape

The sketches are directionally accurate, so they set the **shape**; the area
schedule is exact, so it sets every **dimension**.

1. A schematic plan polygon and a patio polygon are traced off the site plan in
   local metres.
2. One global scale factor is solved so the ground floor nets exactly its
   tabled 2,150 m² (outline area minus patio area).
3. Each upper slab is that ground outline scaled about the tight south-east tip
   until it nets its own tabled area. Because the anchor is at the narrow end,
   the north-west facade rakes outward while the sides stay near-vertical —
   which is what the section drawing shows.
4. Basements are the ground outline scaled about its centroid to 3,200 m², with
   no patio void (full parking plate).

That single rule reproduces the profile in the section without being told to:
a wider podium at ground and level 1, a waist at level 2 (1,820 m², the
smallest floor), then a steady flare to 2,640 m² at level 21.

## Verified against the source

| Check | Result |
|---|---|
| Schedule total vs. sheet ("סיכום חלופה 2") | 69,240 m² — exact |
| Worst per-level area error across all 27 levels | 0.00 m² |
| Tower solid | closed, consistently wound (watertight STL) |

`out/floor_schedule.csv` lists target vs. achieved area and the level heights
for every floor.

## Storey heights

From the client's notes:

| Levels | Height | Source |
|---|---|---|
| 5 basements | 2.80 m | given |
| Ground, level 1 | 5.00 m | given |
| Levels 2–21 | **3.60 m** | **assumed** |

The note says levels 2–21 match "a typical floor in the government tower"
(בניין הטיל), but no number was given, so **3.60 m is an assumption**. Change
`TYPICAL_FLOOR_H` in `build_model.py` and re-run — every level above moves with
it and the roof height changes; floor areas are unaffected.

With 3.60 m the roof lands at **+82.00 m** and the lowest basement at −14.00 m.

## Read with care

- Plan proportions and the plot bearing (145°) are scaled off the sketches, not
  surveyed. Swap in surveyed coordinates by editing `FOOTPRINT_BASE` and
  `SITE_BEARING_DEG`.
- The patio is modelled as a constant-plan void from grade through the roof.
  Its size (319 m²) follows from `PATIO_BASE` and the global scale.
- Basements are one plate enlarged symmetrically about the tower centroid. In
  reality they would run asymmetrically under the plaza.
- The grey tower, its mast and the raised plaza are **schematic context only** —
  proportions from the sketches, not measured drawings.
- This is a massing study: no cores, structure, facade or setbacks.

## Files

| Path | What it is |
|---|---|
| `build_model.py` | the generator; all inputs are in the parameter block at the top |
| `data/floor_areas.csv` | the area schedule transcribed from the spreadsheet |
| `viewer_template.html`, `make_viewer.py` | interactive viewer source |
| `out/new_tower.obj` + `.mtl` | full scene, grouped: new building, basements, context, plot |
| `out/new_tower.stl` | new building only, watertight |
| `out/floor_schedule.csv` | per-level heights, scale factors, target vs. achieved area |
| `out/viewer.html` | self-contained page — orbit, layer toggles, area profile |
| `out/preview_*.png` | shaded axonometric, aerial, roof plan and elevation |

The OBJ imports into SketchUp, Rhino, Blender or Revit with the groups intact,
so the context can be switched off in one click.

## Changing the model

Everything worth adjusting is in the parameter block at the top of
`build_model.py`:

- `FOOTPRINT_BASE` / `PATIO_BASE` — plan shape and the patio
- `ANCHOR_MODE` — `se_tip` (default), `nw_edge` or `centroid`; this decides
  which facades rake as the building grows
- `TYPICAL_FLOOR_H`, `GROUND_H`, `LEVEL1_H`, `BASEMENT_H` — storey heights
- `SITE_BEARING_DEG` — plot orientation
- `CONTEXT_ENABLED` — drop the neighbouring tower and plot plate
- `data/floor_areas.csv` — the areas themselves; the build asserts the total
