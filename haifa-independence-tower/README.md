# Patio building — Derech HaAtzma'ut, Haifa

Parametric 3D massing model of the proposed 22-storey building (the yellow mass
in the sketches), georeferenced into the real Lower City next to the **Sail
Tower**. Built from the "patio building" alternative in
`מכרז חיפה נתוני חלופות.xlsx`.

Nothing here is hand-modelled. One script reads the floor-area schedule and the
cached map data and generates the geometry, so changing an area, a storey
height or the plot bearing and re-running regenerates every output.

```
python3 fetch_context.py   # once: downloads OSM + SRTM + declination -> data/
python3 build_model.py     # geometry, exports and preview renders  -> out/
python3 make_viewer.py     # self-contained interactive page        -> out/viewer.html
```

`data/` is committed, so `build_model.py` runs offline and reproducibly.

## The neighbouring tower

The lens-shaped tower with the mast is the **Sail Tower** (מגדל המפרש) —
officially Building B of the Rabin Government Complex, קריית הממשלה ע״ש רבין,
on Derech HaAtzma'ut in the Lower City. It is the building the brief calls
בניין הטיל, "the missile", which is what people in Haifa actually call it.

| | |
|---|---|
| Architects | Amer–Curiel (Dina Amer, Avraham Curiel), Haifa |
| Built | 1999 – February 2002 |
| Storeys | 29 |
| Main roof | 95 m |
| Sail tips | 113 m |
| Antenna | 137 m — still the highest point in Haifa |
| OSM way | 605918311, centroid 32.816258 N, 35.002768 E |

It is modelled on that surveyed footprint at those published heights, and it is
the geodetic anchor for the whole model.

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
| Compass vs. plot bearing, measured in plan | 133.02° against a surveyed 133° |

`out/floor_schedule.csv` lists target vs. achieved area and the level heights
for every floor.

## Storey heights

| Levels | Height | Source |
|---|---|---|
| 5 basements | 2.80 m | given in the brief |
| Ground, level 1 | 5.00 m | given in the brief |
| Levels 2–21 | **3.20 m** | **derived — see below** |

The brief says levels 2–21 match "a typical floor in בניין הטיל" without giving
a number. Now that the building is identified, its own geometry supplies one:
a 95 m main roof over 29 storeys, less a 5 m lobby, is (95 − 5) / 28 = 3.21 m
floor to floor. The model uses **3.20 m**, which puts the roof at **+74.00 m**
and the lowest basement at −14.00 m.

This is still an estimate from published totals, not a measured floor-to-floor.
Change `TYPICAL_FLOOR_H` in `build_model.py` and every level above moves with
it; floor areas are unaffected. (At the 3.60 m originally assumed, the roof
would be +82.00 m.)

## Surroundings and the compass

The model is georeferenced, so **+Y in the scene is true north** and the plot
sits on its real bearing.

- **Plot bearing 133°**, measured from the OSM centrelines of Derech
  HaAtzma'ut, whose long segments run 131.8–134.6°. The site plan's north arrow
  suggested ~138°; the street geometry is the better source.
- **908 building footprints and 514 streets** within 900 m, extruded from OSM.
- **Terrain** from SRTM 30 m on a 50 m grid, 3.6 km across, running from the bay
  up to +305 m on Mount Carmel. Heights in the model are relative to grade at
  the site, which SRTM puts at +6.6 m above sea level.
- **Magnetic declination 5.1° E** (NOAA World Magnetic Model), drawn as the
  dashed second needle — a hand compass on site reads about 5° off the
  drawing's north. Grid north on the Israeli ITM grid sits within about 7′ of
  true north here, so the two are interchangeable at this scale.

The viewer's compass is not computed from the camera angles. The north vector
is pushed through the same matrix that draws the geometry, so the needle cannot
drift from the model. Checked in plan view: the angle from the needle to the
plot's long axis is 133.02°.

## Read with care

- Plan proportions of the new building still come from the sketches, not from a
  survey. Only its bearing and its position relative to the Sail Tower are
  externally sourced.
- The plot's position is fixed relative to the Sail Tower as drawn on the
  client's site plan; OSM then fixes the Sail Tower on the globe. There are
  existing structures on that footprint in OSM — the tender site would be
  cleared.
- **884 of the 908 context buildings have no height in OSM** and are drawn at an
  assumed 4 storeys. Indicative urban fabric, not survey data.
- SRTM at 50 m sampling cannot resolve individual port quays; a majority filter
  cleans the shoreline at the cost of the narrowest piers.
- Basements are shown as one plate enlarged symmetrically about the tower
  centroid. In reality they would run asymmetrically under the plaza.
- This is a massing study: no cores, structure, facade or setbacks.

## Files

| Path | What it is |
|---|---|
| `build_model.py` | the generator; all inputs in the parameter block at the top |
| `city.py` | terrain, bay, streets, city fabric and the Sail Tower |
| `fetch_context.py` | one-time download of OSM, SRTM and declination |
| `data/floor_areas.csv` | the area schedule transcribed from the spreadsheet |
| `data/osm_*.json`, `terrain.json`, `declination.json` | cached map data |
| `viewer_template.html`, `make_viewer.py` | interactive viewer source |
| `out/new_tower.obj` + `.mtl` | whole scene, grouped by layer |
| `out/new_tower.stl` | new building only, watertight, binary |
| `out/floor_schedule.csv` | per-level heights, scale factors, target vs. achieved |
| `out/viewer.html` | self-contained page — orbit, layers, compass, area profile |
| `out/preview_*.png` | four building views, two of the site in the city |

The OBJ imports into SketchUp, Rhino, Blender or Revit with the groups intact,
so terrain, fabric and context can each be switched off in one click.

## Changing the model

- `FOOTPRINT_BASE` / `PATIO_BASE` — plan shape and the patio
- `ANCHOR_MODE` — `se_tip` (default), `nw_edge` or `centroid`; decides which
  facades rake as the building grows
- `TYPICAL_FLOOR_H`, `GROUND_H`, `LEVEL1_H`, `BASEMENT_H` — storey heights
- `SITE_BEARING_DEG` — plot orientation
- `CONTEXT_MODE` — `city` (real data), `schematic` (hand-proportioned stand-in)
  or `none`; `CITY_RADIUS_M` sets how much fabric is extruded
- `data/floor_areas.csv` — the areas themselves; the build asserts the total

## Data credits

Buildings, streets and shoreline © OpenStreetMap contributors, ODbL.
Terrain: SRTM 30 m via OpenTopoData. Declination: NOAA NCEI World Magnetic
Model.
