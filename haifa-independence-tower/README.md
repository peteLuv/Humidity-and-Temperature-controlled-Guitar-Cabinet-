# Patio building — Derech HaAtzma'ut, Haifa

Presentation-grade 3D model of the proposed 22-storey building next to the
**Sail Tower**, generated end-to-end from the client's drawings, the tabled
floor areas, and public survey data. Nothing is hand-modelled: every curve
traces back to a source, and re-running the pipeline regenerates everything.

```
python3 fetch_context.py    # once: OSM + SRTM + declination        -> data/
python3 trace_siteplan.py   # digitize the client's site plan       -> data/
python3 build_model.py      # geometry, exports, QA previews        -> out/
python3 make_viewer.py      # interactive page                      -> out/viewer.html
python3 render_cycles.py    # Blender Cycles hero renders           -> out/hero_*.png
```

`data/` is committed, so everything after `fetch_context.py` runs offline.

## How the drawings become geometry

**The site plan is digitized, not eyeballed.** `trace_siteplan.py` segments
the drawing by colour — plot boundary, building zone, patio, garden, plaza
paving — then fits one similarity transform by requiring the plot boundary to
hug the surveyed OSM street kerbs. Scale, rotation and position come out of
that fit; the Sail Tower's drawn plan is only the initial guess.

**The zone is not the building.** The drawing's yellow region measures
13,500 m² once street-fitted — five times any tabled floor plate. It is the
building *zone*. On a zone ~180 m long, plates of 2,000–2,600 m² mean the
building is a **long, slender curved bar** — exactly the proportion of the
hand sketches. So the bar follows the zone's own curved spine, its prow at
the zone's rounded SE tip, and each floor is the bar cut at the length that
nets its tabled area (`plan_family.py`).

**The straight rake is not imposed — it emerges.** The tabled areas grow
linearly from level 4 up, so the per-floor solve lands the NW end face on a
straight raked plane by itself (10.5° lean, straight to 0.5 m over 54 m).
Levels 2–3 are too small for that line; per the sketches' unbroken diagonal
they are pushed onto it, gaining ~860 m² (1.6% above-grade — declared in the
schedule; set `STRAIGHT_FROM = 4` to hold every tabled area instead). Ground
and level 1 are a vertical podium set back 7 m beneath the rake.

**The patio** is a rounded wedge on the spine, positioned from the drawn
patio's stations and capped to stay inside the smallest plate (281 m²).

## The datum — why the Sail Tower stands higher

The Sail Tower's ground zero is **not the street**: it stands on the existing
raised plaza, a multi-storey structure between the two sites whose roof is
the plaza deck (the section's כיכר עילית קיימת with its 0/−1/−2/−3 levels).
SRTM cannot see it because it is a built deck, not ground.

Modelled: deck at **+10 m** over the new building's grade (`DECK_H` — an
assumption; no level is given on the drawings), the Sail Tower based on the
deck with its published heights (95 / 113 / 137 m) above its own zero, and
the **garden terraces** — traced from the drawing's green — stepping down
from the deck to the new building's forecourt, with trees.

## The neighbour

The Sail Tower (מגדל המפרש), Building B of the Rabin Government Complex —
the brief's בניין הטיל. Amer–Curiel Architects, 1999–2002; 29 storeys, roof
95 m, sail tips 113 m, antenna 137 m (still Haifa's highest point). Its
surveyed OSM footprint (way 605918311) anchors the whole model at the origin,
and its 95 m over 29 storeys supplies the typical floor the brief references:
(95 − 5) / 28 ≈ **3.20 m**, so the new roof lands at **+74.0 m** over grade.

## Verified

| Check | Result |
|---|---|
| Schedule total vs. the sheet | 69,240 m² — exact |
| Per-level area error (straightened floors excluded) | 0.00 m² |
| Exported STL shell | watertight — 0 boundary edges |
| Site-plan trace vs. surveyed streets | fitted, rms gap ~11 m against centre-line half-widths |
| Compass | north vector projected through the render matrix itself |

`out/floor_schedule.csv` lists per-level heights, bar lengths and target vs.
achieved area.

## Outputs

| Path | What |
|---|---|
| `out/hero_*.png` | Cycles renders — bay, street, aerial, dusk — real Haifa sun (21 June solar geometry), Nishita sky, glass + champagne band materials |
| `out/sketch_view_*.png` | cameras matched to the two hand-sketch viewpoints |
| `out/viewer.html` | interactive: orbit, presets, layers, per-floor area explorer, true-north compass with magnetic declination, scale bar |
| `out/new_tower.obj` + `.mtl` | whole scene, 17 named groups/materials |
| `out/new_tower.stl` | building shell, watertight, binary |
| `out/trace_overlay.png` | the digitized drawing over the OSM streets |
| `out/preview_*.png` | fast QA views |

## Read with care

- The deck height (+10 m) and the typical storey (3.20 m) are each one
  constant, flagged in the viewer, awaiting the tender's surveyed levels.
- Bar width/taper (`TIP_HALFWIDTH`, `TAPER`) are proportion choices matched
  to the sketches; lengths and areas are solved, not chosen.
- Most OSM context buildings carry no height and are drawn at 4 storeys.
- SRTM (30 m native) is good for the Carmel, not for site levels — four free
  DEMs agree only to ~4 m at the site.
- This is a massing-plus-articulation model: bands and glass lines, no cores,
  no mullion-level facade engineering.

## Data credits

OpenStreetMap contributors (ODbL) · SRTM 30 m via OpenTopoData · NOAA NCEI
World Magnetic Model · renders by Blender Cycles (headless bpy).
