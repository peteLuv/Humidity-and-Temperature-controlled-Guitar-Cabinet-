#!/usr/bin/env python3
"""Download the real Haifa context once and cache it under data/.

Sources
-------
OpenStreetMap via Overpass  - building footprints, streets, coastline, port
                              (c) OpenStreetMap contributors, ODbL
SRTM 30 m via OpenTopoData  - terrain grid covering the Carmel slope
NOAA NCEI WMM               - magnetic declination for the compass

Everything is cached as JSON so build_model.py runs offline and reproducibly.
Re-run this only when you want fresher data.
"""

import json
import math
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Geodetic anchor: centroid of the Sail Tower footprint in OSM (way 605918311).
# Everything in the model is expressed in metres from here.
ANCHOR_LAT = 32.816258
ANCHOR_LON = 35.002768

BUILDING_RADIUS_M = 900     # footprints are extruded out to here
TERRAIN_HALF_M = 1500      # terrain grid half-width (3.0 km across)
TERRAIN_N = 101             # samples per side -> 30 m, SRTM native resolution
OVERPASS = "https://overpass-api.de/api/interpreter"

M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(ANCHOR_LAT))


def bbox(half_m):
    dlat = half_m / M_PER_DEG_LAT
    dlon = half_m / M_PER_DEG_LON
    return (ANCHOR_LAT - dlat, ANCHOR_LON - dlon,
            ANCHOR_LAT + dlat, ANCHOR_LON + dlon)


UA = "haifa-massing-study/1.0"


def _curl(args, tries=4):
    """curl rather than urllib: the sandbox's HTTPS proxy only speaks to curl."""
    for attempt in range(tries):
        p = subprocess.run(["curl", "-sS", "-m", "180", "-A", UA] + args,
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().startswith(("{", "[")):
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError:
                pass
        if attempt == tries - 1:
            raise RuntimeError(f"request failed: {p.stderr[:300] or p.stdout[:300]}")
        time.sleep(2 ** attempt)


def overpass(query, dst):
    payload = _curl([OVERPASS, "--data-urlencode", "data=" + query])
    n = len(payload.get("elements", []))
    with open(os.path.join(DATA, dst), "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    print(f"  {dst:<24} {n:>6} elements")
    return payload


def fetch_osm():
    s, w, n, e = bbox(BUILDING_RADIUS_M)
    b = f"{s},{w},{n},{e}"
    overpass(f"[out:json][timeout:120];way[building]({b});out geom tags;",
             "osm_buildings.json")
    overpass(
        f'[out:json][timeout:120];'
        f'way[highway~"^(motorway|trunk|primary|secondary|tertiary|residential|'
        f'unclassified|pedestrian|living_street)$"]({b});out geom tags;',
        "osm_roads.json")

    s, w, n, e = bbox(TERRAIN_HALF_M)
    b2 = f"{s},{w},{n},{e}"
    overpass(
        f'[out:json][timeout:150];'
        f'(way[natural=coastline]({b2});'
        f' way[natural=water]({b2});'
        f' way[landuse=harbour]({b2});'
        f' way[waterway=dock]({b2});'
        f' way[railway=rail]({b2}););out geom tags;',
        "osm_water.json")


def fetch_terrain():
    """SRTM 30 m on a regular grid, in batches the free API accepts."""
    step = 2 * TERRAIN_HALF_M / (TERRAIN_N - 1)
    pts = []
    for j in range(TERRAIN_N):
        for i in range(TERRAIN_N):
            x = -TERRAIN_HALF_M + i * step
            y = -TERRAIN_HALF_M + j * step
            pts.append((ANCHOR_LAT + y / M_PER_DEG_LAT,
                        ANCHOR_LON + x / M_PER_DEG_LON))
    out = []
    for k in range(0, len(pts), 100):
        chunk = pts[k:k + 100]
        loc = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in chunk)
        res = _curl(["https://api.opentopodata.org/v1/srtm30m",
                     "--data-urlencode", "locations=" + loc, "-G"])["results"]
        out += [(p["elevation"] if p["elevation"] is not None else 0.0)
                for p in res]
        print(f"\r  terrain {len(out):>5}/{len(pts)}", end="", flush=True)
        time.sleep(1.05)  # free tier: 1 call/second
    print()
    grid = dict(n=TERRAIN_N, half_m=TERRAIN_HALF_M, step_m=step,
                anchor=[ANCHOR_LAT, ANCHOR_LON], elev=out)
    with open(os.path.join(DATA, "terrain.json"), "w") as fh:
        json.dump(grid, fh)
    print(f"  terrain.json             {min(out):.0f} m to {max(out):.0f} m")


def fetch_declination():
    """Magnetic declination from the NOAA World Magnetic Model."""
    url = ("https://www.ngdc.noaa.gov/geomag-web/calculators/calculateDeclination"
           f"?lat1={ANCHOR_LAT}&lon1={ANCHOR_LON}&key=zNEw7&resultFormat=json"
           "&model=WMM")
    try:
        res = _curl([url], tries=2)["result"][0]
        rec = dict(declination_deg=round(res["declination"], 2),
                   annual_change_deg=round(res.get("declination_sv", 0.0), 3),
                   date=f'{res["date"]:.2f}', model="WMM", source="NOAA NCEI")
    except Exception as exc:
        print(f"  declination lookup failed ({exc}); leaving it unset")
        rec = dict(declination_deg=None, note=str(exc))
    with open(os.path.join(DATA, "declination.json"), "w") as fh:
        json.dump(rec, fh, indent=1)
    print(f"  declination.json         {rec.get('declination_deg')}")


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    print("OpenStreetMap:")
    fetch_osm()
    print("Magnetic declination:")
    fetch_declination()
    print("Terrain (SRTM 30 m, ~1 request/second):")
    fetch_terrain()
    print("done ->", DATA)
