#!/usr/bin/env python3
"""Real Haifa context built from the cached OSM + SRTM data in data/.

World frame used throughout: +X east, +Y true north, +Z up, metres.
Heights are relative to grade at the site, which SRTM puts at about +6 m above
sea level — so the bay surface sits at roughly -6 in model units.

Run fetch_context.py once to populate data/. This module never touches the
network.
"""

import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# must match fetch_context.py
ANCHOR_LAT = 32.816258
ANCHOR_LON = 35.002768
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(ANCHOR_LAT))

SEA_LEVEL_ASL = 0.5      # at or below this the SRTM sample is treated as water
DEFAULT_LEVELS = 4       # used when OSM gives neither height nor levels
LEVEL_H = 3.2            # metres per storey for OSM buildings without a height
ROAD_WIDTH = {"motorway": 16, "trunk": 14, "primary": 12, "secondary": 10,
              "tertiary": 8, "residential": 6, "living_street": 5,
              "pedestrian": 5, "unclassified": 6}

SAIL_TOWER_OSM_ID = 605918311
# From the published figures for the Sail Tower (Amer-Curiel, 1999-2002):
# main roof 95 m, sail tips 113 m, antenna 137 m, 29 storeys.
SAIL_ROOF = 95.0
SAIL_TIP = 113.0
SAIL_ANTENNA = 137.0


def available():
    return all(os.path.exists(os.path.join(DATA, f)) for f in
               ("osm_buildings.json", "osm_roads.json", "terrain.json"))


def _load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# terrain
# --------------------------------------------------------------------------

class Terrain:
    """Bilinear sampler over the cached SRTM grid, in world metres."""

    def __init__(self, grid, ox, oy):
        self.n = grid["n"]
        self.half = grid["half_m"]
        self.step = grid["step_m"]
        self.z = np.array(grid["elev"], dtype=float).reshape(self.n, self.n)
        self.ox, self.oy = ox, oy  # world position of the geodetic anchor
        self.site_asl = float(self.sample_asl(0.0, 0.0))

    def sample_asl(self, wx, wy):
        """Elevation above sea level at a world point."""
        fx = (wx - self.ox + self.half) / self.step
        fy = (wy - self.oy + self.half) / self.step
        fx = min(max(fx, 0.0), self.n - 1.001)
        fy = min(max(fy, 0.0), self.n - 1.001)
        i, j = int(fx), int(fy)
        tx, ty = fx - i, fy - j
        z = self.z
        return ((z[j, i] * (1 - tx) + z[j, i + 1] * tx) * (1 - ty) +
                (z[j + 1, i] * (1 - tx) + z[j + 1, i + 1] * tx) * ty)

    def sample(self, wx, wy):
        """Elevation relative to grade at the site."""
        return float(self.sample_asl(wx, wy)) - self.site_asl


def _majority(mask, passes=2):
    """Denoise the land/sea mask.

    At 50 m sampling, SRTM alternates between 0 and a few metres across the
    port quays, which turns the shoreline into a checkerboard. A 3x3 majority
    filter resolves each cell the way its neighbourhood already reads. It
    costs the narrowest piers, which a massing model does not need.
    """
    m = mask.copy()
    for _ in range(passes):
        p = np.pad(m.astype(np.int8), 1, mode="edge")
        s = sum(p[1 + dj:1 + dj + m.shape[0], 1 + di:1 + di + m.shape[1]]
                for dj in (-1, 0, 1) for di in (-1, 0, 1))
        m = s >= 5
    return m


def add_terrain(m, terr):
    """Dry land as a graded surface; the bay as one flat plane beneath it."""
    n, step, half = terr.n, terr.step, terr.half
    zs = np.maximum(terr.z, 0.0)  # SRTM noise dips below zero over water
    xs = terr.ox - half + np.arange(n) * step
    ys = terr.oy - half + np.arange(n) * step
    base = terr.site_asl

    corner_wet = zs <= SEA_LEVEL_ASL
    cell_wet = _majority(corner_wet[:-1, :-1] & corner_wet[1:, :-1] &
                         corner_wet[:-1, 1:] & corner_wet[1:, 1:])

    # Water is part of the same surface, its cells flattened to exactly sea
    # level. A separate sea plane would overlap the shoreline and the painter
    # sort would interleave the two into stripes.
    land, sea = [], []
    for j in range(n - 1):
        for i in range(n - 1):
            if cell_wet[j, i]:
                sea.append([(xs[i], ys[j]), (xs[i + 1], ys[j]),
                            (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])])
            else:
                land.append([(xs[i], ys[j], zs[j, i]),
                             (xs[i + 1], ys[j], zs[j, i + 1]),
                             (xs[i + 1], ys[j + 1], zs[j + 1, i + 1]),
                             (xs[i], ys[j + 1], zs[j + 1, i])])
    m.group("terrain")
    for q in land:
        m.face([(p[0], p[1], p[2] - base) for p in q])
    m.group("sea")
    for q in sea:
        m.face([(p[0], p[1], -base) for p in q])
    return len(land), len(sea)


# --------------------------------------------------------------------------
# polygons
# --------------------------------------------------------------------------

def _area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] -
                     p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def earclip(poly):
    """Triangulate a simple polygon. OSM footprints are often L- or U-shaped,
    so a centroid fan would put roof triangles outside the building."""
    pts = list(poly)
    idx = list(range(len(pts)))
    if _area(pts) < 0:
        idx.reverse()

    def cross(a, b, c):
        return ((pts[b][0] - pts[a][0]) * (pts[c][1] - pts[a][1]) -
                (pts[b][1] - pts[a][1]) * (pts[c][0] - pts[a][0]))

    def inside(p, a, b, c):
        d1, d2, d3 = cross(a, b, p), cross(b, c, p), cross(c, a, p)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    tris, guard = [], 0
    while len(idx) > 3 and guard < 4 * len(pts) + 40:
        guard += 1
        for i in range(len(idx)):
            a, b, c = idx[i - 1], idx[i], idx[(i + 1) % len(idx)]
            if cross(a, b, c) <= 0:
                continue
            if any(inside(p, a, b, c) for p in idx if p not in (a, b, c)):
                continue
            tris.append((a, b, c))
            idx.pop(i)
            guard = 0
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return [tuple(pts[k] for k in t) for t in tris]


def _prism(m, ring, z0, z1):
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        m.face([(a[0], a[1], z0), (b[0], b[1], z0),
                (b[0], b[1], z1), (a[0], a[1], z1)])
    for t in earclip(ring):
        m.face([(p[0], p[1], z1) for p in t])


# --------------------------------------------------------------------------
# buildings
# --------------------------------------------------------------------------

def _height(tags):
    h = tags.get("height") or tags.get("building:height")
    if h:
        try:
            return float(str(h).split()[0].replace("m", "")), "height tag"
        except ValueError:
            pass
    lv = tags.get("building:levels")
    if lv:
        try:
            return float(str(lv).split(";")[0]) * LEVEL_H, "levels tag"
        except ValueError:
            pass
    return DEFAULT_LEVELS * LEVEL_H, "assumed"


def add_buildings(m, proj, terr, skip_ids=(), radius=900.0):
    data = _load("osm_buildings.json")
    m.group("city_buildings")
    stats = {"height tag": 0, "levels tag": 0, "assumed": 0}
    tallest = []
    for el in data["elements"]:
        g = el.get("geometry")
        if not g or el["id"] in skip_ids:
            continue
        ring = [proj(p["lat"], p["lon"]) for p in g]
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 3 or abs(_area(ring)) < 12:
            continue
        cx = sum(p[0] for p in ring) / len(ring)
        cy = sum(p[1] for p in ring) / len(ring)
        if math.hypot(cx, cy) > radius:
            continue
        h, src = _height(el.get("tags", {}))
        stats[src] += 1
        ground = min(terr.sample(*p) for p in ring)
        _prism(m, ring, ground - 4.0, ground + h)
        nm = el.get("tags", {}).get("name")
        if nm and h >= 40:
            tallest.append((h, nm))
    return stats, sorted(tallest, reverse=True)[:6]


def add_sail_tower(m, proj, terr):
    """The Sail Tower on its real footprint, with the sails and the antenna."""
    data = _load("osm_buildings.json")
    el = next((e for e in data["elements"] if e["id"] == SAIL_TOWER_OSM_ID), None)
    if el is None:
        return None
    ring = [proj(p["lat"], p["lon"]) for p in el["geometry"]]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    ground = min(terr.sample(*p) for p in ring)

    m.group("sail_tower")
    _prism(m, ring, ground - 4.0, ground + SAIL_ROOF)

    # The sails: a blade following each long edge of the plan, its top edge
    # arcing from the roof at the ends up to the tips over the middle.
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    ang = [math.atan2(p[1] - cy, p[0] - cx) for p in ring]
    # long axis of the footprint
    far = max(range(len(ring)), key=lambda i: (ring[i][0] - cx) ** 2 +
              (ring[i][1] - cy) ** 2)
    axis = math.atan2(ring[far][1] - cy, ring[far][0] - cx)
    for side in (0, 1):
        blade = [p for p, a in zip(ring, ang)
                 if math.sin(a - axis) * (1 if side else -1) > 0]
        if len(blade) < 3:
            continue
        blade.sort(key=lambda p: (p[0] - cx) * math.cos(axis) +
                   (p[1] - cy) * math.sin(axis))
        L = len(blade) - 1
        for i in range(L):
            a, b = blade[i], blade[i + 1]
            ta = ground + SAIL_ROOF + (SAIL_TIP - SAIL_ROOF) * \
                math.sin(math.pi * i / L)
            tb = ground + SAIL_ROOF + (SAIL_TIP - SAIL_ROOF) * \
                math.sin(math.pi * (i + 1) / L)
            m.face([(a[0], a[1], ground + SAIL_ROOF),
                    (b[0], b[1], ground + SAIL_ROOF),
                    (b[0], b[1], tb), (a[0], a[1], ta)])

    m.group("sail_mast")
    s = 0.8
    mast = [(cx - s, cy - s), (cx + s, cy - s), (cx + s, cy + s), (cx - s, cy + s)]
    _prism(m, mast, ground + SAIL_TIP - 6, ground + SAIL_ANTENNA)
    return dict(roof=SAIL_ROOF, tip=SAIL_TIP, antenna=SAIL_ANTENNA,
                footprint_verts=len(ring))


# --------------------------------------------------------------------------
# streets
# --------------------------------------------------------------------------

def add_roads(m, proj, terr, radius=900.0):
    data = _load("osm_roads.json")
    m.group("city_roads")
    count = 0
    for el in data["elements"]:
        g = el.get("geometry")
        if not g or len(g) < 2:
            continue
        w = ROAD_WIDTH.get(el.get("tags", {}).get("highway"), 6) / 2.0
        # Split into contiguous in-range runs. Filtering points out of the
        # list instead would weld the survivors together, throwing a ribbon
        # straight across the bay wherever a road left and re-entered range.
        runs, cur = [], []
        for p in (proj(q["lat"], q["lon"]) for q in g):
            if math.hypot(*p) < radius * 1.15:
                cur.append(p)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        for pts in runs:
            if len(pts) < 2:
                continue
            count += 1
            _road_run(m, pts, w, terr)
    return count


def _road_run(m, pts, w, terr):
    for i in range(len(pts) - 1):
        a, b = np.array(pts[i]), np.array(pts[i + 1])
        d = b - a
        L = float(np.hypot(*d))
        if L < 0.5:
            continue
        nrm = np.array([-d[1], d[0]]) / L * w
        # Subdivide: OSM segments run 100 m+, and a straight ribbon over the
        # Carmel slope submerges at one end and floats at the other.
        steps = max(1, int(L // 20) + 1)
        for s in range(steps):
            p0 = a + d * (s / steps)
            p1 = a + d * ((s + 1) / steps)
            quad = [p0 + nrm, p1 + nrm, p1 - nrm, p0 - nrm]
            m.face([(float(c[0]), float(c[1]),
                     terr.sample(float(c[0]), float(c[1])) + 0.9)
                    for c in quad])


# --------------------------------------------------------------------------

def build_context(m, anchor_world, radius=900.0):
    """Add terrain, bay, streets, city fabric and the Sail Tower to `m`."""
    ox, oy = anchor_world

    def proj(lat, lon):
        return (ox + (lon - ANCHOR_LON) * M_PER_DEG_LON,
                oy + (lat - ANCHOR_LAT) * M_PER_DEG_LAT)

    terr = Terrain(_load("terrain.json"), ox, oy)
    nland, nsea = add_terrain(m, terr)
    nroads = add_roads(m, proj, terr, radius)
    sail = add_sail_tower(m, proj, terr)
    stats, tallest = add_buildings(m, proj, terr,
                                   skip_ids={SAIL_TOWER_OSM_ID}, radius=radius)

    decl = None
    p = os.path.join(DATA, "declination.json")
    if os.path.exists(p):
        decl = _load("declination.json")

    return dict(site_asl=round(terr.site_asl, 1),
                terrain_min=round(float(terr.z.min()), 0),
                terrain_max=round(float(terr.z.max()), 0),
                land_quads=nland, sea_quads=nsea, roads=nroads,
                buildings=sum(stats.values()), height_sources=stats,
                tallest=tallest, sail=sail, declination=decl,
                sample=lambda x, y: terr.sample(x, y))
