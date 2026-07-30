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

The sketches set the **shape**; the area schedule sets the **dimensions**.

Every floor is the same trapezoid seen from a fixed blunt south-east tip. Only
the north-west end face moves: its distance from the tip is solved per level so
the slab makes its tabled area. Nothing else changes, so that face is a single
raked plane rather than a stack of steps.

- **Levels 2–21 are one straight diagonal.** From level 4 up the tabled areas
  grow almost perfectly linearly (+15.6 m² a floor), so solving each floor for
  its exact area lands on a straight line all by itself — straight to **0.31 m
  over 54 m of height**, a 6.1° lean. It was never constrained to be straight;
  the schedule is simply describing a raked plane.
- **Ground and level 1 are a straight-sided podium**, extruded vertically, set
  back 7 m inside level 2's end face and spread ~0.5 m sideways to make their
  own tabled areas.
- **Basements** are the podium plate pushed out to 3,200 m², no patio void.

### Where the schedule and the sketch disagree

Levels 2 and 3 cannot sit on that line. At 1,820 and 2,040 m² against 2,370 at
level 4, they are far too small — holding their tabled areas would kink the
facade sharply just above the podium.

The sketches show one unbroken diagonal, so the line is **extended down to
level 2** and those two floors take the area the geometry gives them:

| Level | Pushed out | Area gained |
|---|---|---|
| 2 | 12.6 m | +534 m² |
| 3 | 7.6 m | +329 m² |
| | | **+862 m² — 1.6% on the above-grade area** |

Every other floor still lands on its tabled area to 0.00 m². Set
`STRAIGHT_FROM = 4` in `build_model.py` to hold all 27 tabled areas exactly and
accept the kink instead.

## Landscape between the two buildings

The site plan shows the strip between the new building and the government
complex hatched with parallel curved lines, and the sketches show a run of
steps there. It is modelled as **six terraces** climbing 26 m from the new
building's grade to the existing raised plaza, widening toward the north-west
with the plot. Terrace count, depth and the plaza level are parameters —
`LAND_*` and `PLAZA_RISE` — since none of them is dimensioned on the drawings.

## Verified against the source

| Check | Result |
|---|---|
| Schedule total vs. sheet ("סיכום חלופה 2") | 69,240 m² — exact |
| Per-level area error, all levels except the two straightened | 0.00 m² |
| Tower solid | closed, consistently wound (watertight STL) |
| Compass vs. plot bearing, measured in plan | 146.02° against a 146° plot axis |
| NW facade straightness, levels 4–21 | 0.31 m over 54 m |
| Footprint clearance to the nearest road kerb | 16.0 m |

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
Change `TYPICAL_FLOOR_H` and every level above moves with it; floor areas are
unaffected.

### How much higher is the Sail Tower?

| Typical storey | New roof | Sail Tower main roof is higher by |
|---|---|---|
| 3.20 m (current) | +74.0 m | 21.0 m ≈ 6.6 floors |
| 3.60 m | +82.0 m | 13.0 m ≈ 3.6 floors |
| 3.75 m | +85.0 m | 10.0 m ≈ 2.7 floors |

Against the **sail tips** at 113 m rather than the main roof, add another 18 m
to each. Both buildings stand on effectively the same grade — SRTM puts the
plot 1.1 m below the tower, which is inside the data's own noise — so the
difference is height, not topography.

## Surroundings and the compass

The model is georeferenced, so **+Y in the scene is true north** and the plot
sits on its real bearing.

- **Plot bearing 146°**, and the building sits **91 m from the Sail Tower at
  bearing 162°**, with **16 m of clearance to the nearest kerb**. See
  *Placement* below.
- **988 building footprints and 518 streets** within 900 m, extruded from OSM.
- **Terrain** from SRTM sampled at its native **30 m** across a 3.0 km square,
  running from the bay up to +305 m on Mount Carmel. Heights in the model are
  relative to grade at the site, which SRTM puts at +8.9 m above sea level.
- **Magnetic declination 5.1° E** (NOAA World Magnetic Model), drawn as the
  dashed second needle — a hand compass on site reads about 5° off the
  drawing's north. Grid north on the Israeli ITM grid sits within about 7′ of
  true north here, so the two are interchangeable at this scale.

The viewer's compass is not computed from the camera angles. The north vector
is pushed through the same matrix that draws the geometry, so the needle cannot
drift from the model. Checked in plan view: the angle from the needle to the
plot's long axis is 146.02°.

## Placement

An earlier version put the building in the carriageway. The cause: Derech
HaAtzma'ut **curves around the south-east end of the block**, so averaging its
centrelines gave a plot bearing of 133° that no part of the plot actually
follows.

Both numbers now come from the vacant land itself — the open parcels
south-east of the Sail Tower, which are what a tender site here would be:

- **Bearing 146°** — the principal axis of those parcels (their combined
  centroid lies 103 m from the tower at bearing 155°).
- **Position** — a search over ±24 m around that centroid for the placement
  with the greatest clearance to any road kerb, which lands the footprint
  **16.0 m clear** and 91 m from the tower at bearing 162°.

The building is also sat on **its own ground** rather than the tower's: SRTM
reads the plot 1.1 m below the tower, so the whole mass and its basements are
shifted by that amount. Without it the building sank into the terrain.

There are existing structures inside that footprint in OSM — a tender site
would be cleared.

## Read with care

- Plan proportions of the new building still come from the sketches, not from a
  survey. Only the bearing, position and grade are externally sourced.
- **963 of the 988 context buildings have no height in OSM** and are drawn at an
  assumed 4 storeys. Indicative urban fabric, not survey data.
- **How accurate is the topography?** Good for the Carmel, not for site levels.
  Four free global DEMs were compared at this location — SRTM 30 m, SRTM 90 m,
  ASTER 30 m and Mapzen — and they agree within ~4 m at the site (6–10 m ASL)
  and ~10 m on the ridge (287–295 m). Across the building's own footprint SRTM
  varies by 4.5 m on ground that is flat, which is noise, not slope; the model
  uses the median. Nothing better is freely available for Israel through these
  services, so **for anything at site-level precision you need the surveyed
  levels from the tender documents**, not this.
- SRTM cannot resolve individual port quays at 30 m; a majority filter cleans
  the shoreline at the cost of the narrowest piers.
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
- `X_TIP`, `TIP_HALF`, `TAPER` — the plan's proportions
- `STRAIGHT_FROM` — 2 for one unbroken diagonal (default), 4 to hold every
  tabled area exactly
- `PODIUM_SETBACK` — how far the podium sits inside level 2
- `LAND_DEPTH`, `LAND_TERRACES`, `PLAZA_RISE` — the landscaped steps
- `TYPICAL_FLOOR_H`, `GROUND_H`, `LEVEL1_H`, `BASEMENT_H` — storey heights
- `SITE_BEARING_DEG` — plot orientation
- `CONTEXT_MODE` — `city` (real data), `schematic` (hand-proportioned stand-in)
  or `none`; `CITY_RADIUS_M` sets how much fabric is extruded
- `data/floor_areas.csv` — the areas themselves; the build asserts the total

## Data credits

Buildings, streets and shoreline © OpenStreetMap contributors, ODbL.
Terrain: SRTM 30 m via OpenTopoData. Declination: NOAA NCEI World Magnetic
Model.
