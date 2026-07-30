#!/usr/bin/env python3
"""
Parametric massing model - new 22-storey "patio building" on Derech HaAtzma'ut, Haifa.

Method
------
The hand sketches are directionally accurate only, so they are used for SHAPE
(plan proportions, where the patio sits, which way the mass flares).  All
absolute sizes come from the floor-area schedule in data/floor_areas.csv, which
is authoritative:

  1. A schematic plan polygon + patio polygon are drawn in local metres.
  2. One global scale k is solved so the GROUND floor nets exactly 2150 m2
     (outline area minus patio area).
  3. Every upper floor outline is that ground outline scaled about a fixed
     anchor by s_i = sqrt((A_i + A_patio) / A_outline_ground), so each slab
     hits its tabled area exactly while the mass pinches at level 2 and flares
     continuously to level 21 - the profile drawn in the section.
  4. Basements are the ground outline scaled about its centroid to 3200 m2,
     with no patio void (full parking plate).

Every ring is resampled by ray-casting from a common centre, so the whole
building is one clean quad grid -> trivial to loft, triangulate and export.

The result is georeferenced (see city.py): the plot sits on its real bearing
next to the Sail Tower, on OSM fabric and SRTM terrain, with +Y true north.

Outputs (out/):
  new_tower.obj / .mtl   whole scene, grouped by layer
  new_tower.stl          new building only, watertight
  floor_schedule.csv     verification: target vs achieved area, per level
  preview_*.png          building views plus two of the site in the city
  mesh.json              geometry for the interactive viewer
"""

import csv
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --------------------------------------------------------------------------
# 1. INPUT PARAMETERS  (everything you might want to change lives here)
# --------------------------------------------------------------------------

# --- storey heights, from the client's notes (WhatsApp 7/29) ---------------
#   "5 קומות מרתף: 2.80 כל קומה"        -> 5 basements @ 2.80 m
#   "ק״ק וקומה 1: 5 מ׳ כל קומה"          -> ground + level 1 @ 5.00 m
#   "כל שאר הקומות ... כמו בבניין הטיל"  -> typical = same as the neighbouring
#                                            government tower.  ASSUMPTION below.
BASEMENT_H = 2.80
GROUND_H = 5.00
LEVEL1_H = 5.00

# The brief pins the typical storey to the Sail Tower without giving a number.
# That tower's published figures are a 95 m main roof over 29 storeys; taking a
# 5 m lobby leaves (95 - 5) / 28 = 3.21 m floor to floor, so 3.20 m is used
# here. STILL AN ESTIMATE - replace it with the measured value if you have one.
# Only the level heights depend on it; the floor areas do not.
TYPICAL_H = 3.20

# --- schematic plan, local metres. +X runs NW -> SE along the plot ---------
# Convex tapering quadrilateral with a clipped SE tip, traced off the site plan.
FOOTPRINT_BASE = [
    (0.0, -22.0),
    (28.0, -19.0),
    (56.0, -14.5),
    (84.0, -8.0),
    (88.0, -1.0),
    (82.0, 5.5),
    (64.0, 12.0),
    (34.0, 18.5),
    (0.0, 23.0),
]

# The patio: a wedge-shaped void, wide at the NW, narrowing to the SE, open
# from grade all the way through the roof (the triangular hole in the sketches).
PATIO_BASE = [
    (30.0, -9.0),
    (58.0, -3.5),
    (58.0, 3.5),
    (30.0, 9.0),
]

# Which point stays put as the tower grows with height.  The section shows one
# near-vertical face and one strongly flaring face, so the mass is anchored at
# the tight SE tip and opens toward the NW / the government building.
ANCHOR_MODE = "se_tip"  # "se_tip" | "nw_edge" | "centroid"

# Plot bearing: the long axis runs parallel to Derech HaAtzma'ut. Measured at
# 133.0 deg from the OSM centrelines of the street's long segments, which run
# 131.8-134.6 deg. (The site plan's north arrow suggested ~138; the street
# geometry is the better source.)
SITE_BEARING_DEG = 133.0

# Context: "city" uses the real OSM + SRTM data cached in data/ (terrain, bay,
# streets, 900 m of built fabric and the Sail Tower on its surveyed footprint).
# "schematic" falls back to the hand-proportioned stand-in; "none" drops it.
CONTEXT_MODE = "city"
CITY_RADIUS_M = 900.0

RING_SAMPLES = 72  # extra uniform samples per ring (polygon corners are exact)

# --- schematic context: the existing government tower ("בניין הטיל") -------
# Reference massing only, so the new building can be read in its setting.
CONTEXT_ENABLED = True
CTX_CENTER = (-62.0, 4.0)  # local metres, pre-scale
CTX_LENS_LENGTH = 46.0  # long axis of the lens-shaped plan
CTX_LENS_WIDTH = 30.0
CTX_FLOORS = 26
CTX_FLOOR_H = 3.60
CTX_BULGE = 0.12  # barrel profile: widest at mid-height
CTX_MAST_H = 28.0
CTX_PODIUM_RX = 52.0
CTX_PODIUM_RY = 34.0
CTX_PODIUM_TOP = 1.0
CTX_PODIUM_BOTTOM = -9.0

# Plot outline, as (x_along_axis, half_width) in pre-scale local metres.
SITE_PROFILE = [(-128, 0), (-119, 24), (-107, 39), (-91, 46), (-58, 48),
                (-18, 42), (22, 34), (62, 24), (89, 13), (100, 0)]
SITE_THICKNESS = 0.6
SITE_TOP_Z = -0.15  # just under grade, so it is not coplanar with the podium deck


# --------------------------------------------------------------------------
# 2. PLANAR HELPERS
# --------------------------------------------------------------------------

def poly_area(pts):
    """Signed shoelace area; positive for counter-clockwise rings."""
    p = np.asarray(pts, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def poly_centroid(pts):
    p = np.asarray(pts, dtype=float)
    x, y = p[:, 0], p[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cross = x * yn - xn * y
    a = 0.5 * cross.sum()
    cx = ((x + xn) * cross).sum() / (6.0 * a)
    cy = ((y + yn) * cross).sum() / (6.0 * a)
    return np.array([cx, cy])


def scale_poly(pts, s, anchor):
    p = np.asarray(pts, dtype=float)
    a = np.asarray(anchor, dtype=float)
    return a + (p - a) * s


def ray_hit(ring, center, theta):
    """First boundary crossing of the ray center + t*(cos,sin), t > 0."""
    d = np.array([math.cos(theta), math.sin(theta)])
    c = np.asarray(center, dtype=float)
    best = None
    n = len(ring)
    for i in range(n):
        a = ring[i]
        b = ring[(i + 1) % n]
        e = b - a
        den = d[0] * (-e[1]) - d[1] * (-e[0])
        if abs(den) < 1e-12:
            continue
        rhs = a - c
        t = (rhs[0] * (-e[1]) - rhs[1] * (-e[0])) / den
        u = (d[0] * rhs[1] - d[1] * rhs[0]) / den
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            if best is None or t < best:
                best = t
    if best is None:
        raise RuntimeError(f"ray at {math.degrees(theta):.1f} deg escaped the ring")
    return c + best * d


def resample(ring, center, angles):
    return np.array([ray_hit(ring, center, th) for th in angles])


def point_in_poly(pt, ring):
    x, y = pt
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


# --------------------------------------------------------------------------
# 3. MESH ACCUMULATOR
# --------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.v = []
        self.groups = {}  # name -> list of vertex-index tuples
        self.lines = []  # (x1,y1,z1,x2,y2,z2) slab / corner lines for the viewer
        self.line_tags = []  # level label per segment, "" for non-slab lines
        self._cur = None

    def polyline(self, pts, z, tag="", closed=True):
        n = len(pts)
        last = n if closed else n - 1
        for i in range(last):
            a, b = pts[i], pts[(i + 1) % n]
            self.lines.append((a[0], a[1], z, b[0], b[1], z))
            self.line_tags.append(tag)

    def vline(self, pt, z_lo, z_hi, tag=""):
        self.lines.append((pt[0], pt[1], z_lo, pt[0], pt[1], z_hi))
        self.line_tags.append(tag)

    def group(self, name):
        self._cur = name
        self.groups.setdefault(name, [])
        return self

    def _add(self, p):
        self.v.append(tuple(float(c) for c in p))
        return len(self.v) - 1

    def face(self, pts):
        idx = [self._add(p) for p in pts]
        self.groups[self._cur].append(tuple(idx))

    def strip(self, lower, upper, z_lo, z_hi, flip=False, div=1):
        """Quad band between two same-length rings at two heights.

        ``div`` splits the band vertically; keeping quads storey-sized stops
        the preview renderer's painter sort from mis-ordering tall faces.
        """
        n = len(lower)
        lower = np.asarray(lower, dtype=float)
        upper = np.asarray(upper, dtype=float)
        for k in range(div):
            t0, t1 = k / div, (k + 1) / div
            r0 = lower + (upper - lower) * t0
            r1 = lower + (upper - lower) * t1
            za, zb = z_lo + (z_hi - z_lo) * t0, z_lo + (z_hi - z_lo) * t1
            for i in range(n):
                j = (i + 1) % n
                a = (r0[i][0], r0[i][1], za)
                b = (r0[j][0], r0[j][1], za)
                c = (r1[j][0], r1[j][1], zb)
                d = (r1[i][0], r1[i][1], zb)
                self.face([b, a, d, c] if flip else [a, b, c, d])

    def annulus(self, outer, inner, z, flip=False):
        """Horizontal ring-with-hole at one height; +Z normal unless flipped."""
        n = len(outer)
        for i in range(n):
            j = (i + 1) % n
            a = (outer[i][0], outer[i][1], z)
            b = (outer[j][0], outer[j][1], z)
            c = (inner[j][0], inner[j][1], z)
            d = (inner[i][0], inner[i][1], z)
            self.face([d, c, b, a] if flip else [a, b, c, d])

    def cap(self, ring, z, center, flip=False):
        n = len(ring)
        cz = (center[0], center[1], z)
        for i in range(n):
            j = (i + 1) % n
            a = (ring[i][0], ring[i][1], z)
            b = (ring[j][0], ring[j][1], z)
            self.face([b, a, cz] if flip else [a, b, cz])

    def weld(self, tol=1e-4):
        """Merge coincident vertices so the OBJ imports as one continuous solid."""
        seen, remap, newv = {}, [], []
        for p in self.v:
            key = (round(p[0] / tol), round(p[1] / tol), round(p[2] / tol))
            if key not in seen:
                seen[key] = len(newv)
                newv.append(p)
            remap.append(seen[key])
        self.v = newv
        for name, faces in self.groups.items():
            kept = []
            for f in faces:
                nf = []
                for i in f:
                    r = remap[i]
                    if not nf or nf[-1] != r:
                        nf.append(r)
                if len(nf) > 2 and nf[0] == nf[-1]:
                    nf.pop()
                if len(nf) >= 3:
                    kept.append(tuple(nf))
            self.groups[name] = kept
        return self

    def triangles(self, only=None):
        tris = []
        for name, faces in self.groups.items():
            if only and name not in only:
                continue
            for f in faces:
                for k in range(1, len(f) - 1):
                    tris.append((f[0], f[k], f[k + 1]))
        return tris


# --------------------------------------------------------------------------
# 4. BUILD
# --------------------------------------------------------------------------

def load_areas():
    path = os.path.join(HERE, "data", "floor_areas.csv")
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            rows.append(line.rstrip("\n"))
    rdr = csv.DictReader(rows)
    return {r["level"]: float(r["area_sqm"]) for r in rdr}


def build():
    areas = load_areas()
    basements = [f"B{i}" for i in (5, 4, 3, 2, 1)]
    uppers = ["G"] + [str(i) for i in range(1, 22)]

    total = sum(areas[k] for k in basements + uppers)
    print(f"schedule total ......... {total:,.0f} m2   (sheet says 69,240)")
    assert abs(total - 69240) < 0.5, "area schedule does not match the sheet total"

    # --- global scale: ground floor nets exactly its tabled area -----------
    a_out_base = poly_area(FOOTPRINT_BASE)
    a_pat_base = poly_area(PATIO_BASE)
    k = math.sqrt(areas["G"] / (a_out_base - a_pat_base))

    foot = scale_poly(FOOTPRINT_BASE, k, (0, 0))
    patio = scale_poly(PATIO_BASE, k, (0, 0))
    a_out_g = poly_area(foot)
    a_pat = poly_area(patio)
    print(f"global scale k ......... {k:.4f}")
    print(f"ground outline ......... {a_out_g:,.1f} m2")
    print(f"patio void ............. {a_pat:,.1f} m2  (constant, grade to roof)")

    center = poly_centroid(patio)

    anchor = {
        "se_tip": np.array(foot[4]),
        "nw_edge": np.array([foot[0][0], 0.0]),
        "centroid": poly_centroid(foot),
    }[ANCHOR_MODE]

    # --- per-level outlines -------------------------------------------------
    levels = []  # (label, z_bottom, z_top, outline, target_area)
    z = -BASEMENT_H * len(basements)
    s_bsmt = math.sqrt(areas["B1"] / a_out_g)
    bsmt_ring = scale_poly(foot, s_bsmt, poly_centroid(foot))
    z_grade = 0.0
    z_base_bottom = z
    for lbl in basements:
        levels.append((lbl, z, z + BASEMENT_H, bsmt_ring, areas[lbl], None))
        z += BASEMENT_H

    tower = []  # (label, z_level, outline, target)
    z = 0.0
    for lbl in uppers:
        h = GROUND_H if lbl == "G" else (LEVEL1_H if lbl == "1" else TYPICAL_H)
        s = math.sqrt((areas[lbl] + a_pat) / a_out_g)
        ring = scale_poly(foot, s, anchor)
        tower.append((lbl, z, z + h, ring, areas[lbl], s))
        z += h
    z_roof = z
    print(f"roof level ............. +{z_roof:.2f} m   ({len(uppers)} storeys)")
    print(f"lowest basement ........ {z_base_bottom:.2f} m")

    # patio must stay inside the pinched levels
    for lbl, _, _, ring, _, _ in tower:
        for p in patio:
            if not point_in_poly(p, ring):
                raise SystemExit(f"patio breaks the outline at level {lbl}")

    # --- shared angle set: exact at every polygon corner -------------------
    angles = {2 * math.pi * i / RING_SAMPLES for i in range(RING_SAMPLES)}
    for ring in [foot, patio, bsmt_ring] + [t[3] for t in tower]:
        for p in ring:
            angles.add(math.atan2(p[1] - center[1], p[0] - center[0]))
    angles = sorted(a % (2 * math.pi) for a in angles)

    R_patio = resample(patio, center, angles)
    R_bsmt = resample(bsmt_ring, center, angles)
    R_tower = [(lbl, zb, zt, resample(r, center, angles), tgt, s)
               for lbl, zb, zt, r, tgt, s in tower]

    # --- assemble the mesh -------------------------------------------------
    m = Mesh()

    # basement box (separate group so it can be switched off when viewing)
    m.group("new_tower_basement")
    m.cap(R_bsmt, z_base_bottom, center, flip=True)
    m.strip(R_bsmt, R_bsmt, z_base_bottom, z_grade, div=len(basements))
    # plaza deck over the basement, outside the tower
    m.annulus(R_bsmt, R_tower[0][3], z_grade)
    # courtyard floor at grade
    m.cap(R_patio, z_grade, center)

    m.group("new_tower")
    # tower shell: loft level to level, then a vertical top storey
    for i in range(len(R_tower)):
        lo = R_tower[i][3]
        z_lo = R_tower[i][1]
        z_hi = R_tower[i][2]
        hi = R_tower[i + 1][3] if i + 1 < len(R_tower) else lo
        m.strip(lo, hi, z_lo, z_hi)

    # patio shaft (solid normals face into the void) and roof annulus
    m.strip(R_patio, R_patio, z_grade, z_roof, flip=True, div=len(R_tower))
    m.annulus(R_tower[-1][3], R_patio, z_roof)

    # slab lines, drawn from the exact polygons rather than the resampled rings
    for lbl, zb, _, ring, _, _ in tower:
        m.polyline(ring, zb, tag=lbl)
    m.polyline(tower[-1][3], z_roof, tag="21")
    for i, lbl in enumerate(basements):
        m.polyline(bsmt_ring, z_base_bottom + i * BASEMENT_H, tag=lbl)
    m.polyline(bsmt_ring, z_grade, tag="B1")
    m.polyline(patio, 0.0)
    m.polyline(patio, z_roof)
    for p in patio:
        m.vline(p, 0.0, z_roof)
    for p in tower[0][3]:
        m.vline(p, 0.0, tower[0][2])

    if CONTEXT_MODE == "schematic":
        add_context(m, k)
        add_site(m, k)

    # --- world orientation: rotate the plot onto its real bearing ----------
    # After this the frame is geographic: +X east, +Y true north, +Z up.
    rot = math.radians(90.0 - SITE_BEARING_DEG)
    ca, sa = math.cos(rot), math.sin(rot)
    m.v = [(x * ca - y * sa, x * sa + y * ca, zz) for x, y, zz in m.v]
    m.lines = [(x1 * ca - y1 * sa, x1 * sa + y1 * ca, z1,
                x2 * ca - y2 * sa, x2 * sa + y2 * ca, z2)
               for x1, y1, z1, x2, y2, z2 in m.lines]

    # --- real surroundings, generated straight into the geographic frame ---
    city_info = None
    if CONTEXT_MODE == "city":
        import city
        if not city.available():
            raise SystemExit("no cached context — run fetch_context.py first")
        # The site plan fixes the plot relative to the Sail Tower, and OSM
        # fixes the Sail Tower on the globe; composing the two georeferences
        # the model. CTX_CENTER is that offset, in pre-scale local metres.
        ax, ay = CTX_CENTER[0] * k, CTX_CENTER[1] * k
        anchor_world = (ax * ca - ay * sa, ax * sa + ay * ca)
        city_info = city.build_context(m, anchor_world, CITY_RADIUS_M)

    m.weld()

    schedule = []
    for lbl, zb, zt, ring, tgt, s in R_tower:
        got = poly_area(ring) - a_pat
        schedule.append(dict(level=lbl, z_bottom=round(zb, 2), z_top=round(zt, 2),
                             height=round(zt - zb, 2), scale=round(s, 5),
                             target_sqm=tgt, achieved_sqm=round(got, 1),
                             error_sqm=round(got - tgt, 2)))
    zb = z_base_bottom
    for lbl in basements:
        got = poly_area(R_bsmt)
        schedule.insert(0, dict(level=lbl, z_bottom=round(zb, 2),
                                z_top=round(zb + BASEMENT_H, 2), height=BASEMENT_H,
                                scale=round(s_bsmt, 5), target_sqm=areas[lbl],
                                achieved_sqm=round(got, 1),
                                error_sqm=round(got - areas[lbl], 2)))
        zb += BASEMENT_H
    schedule.sort(key=lambda r: r["z_bottom"])

    worst = max(abs(r["error_sqm"]) for r in schedule)
    print(f"worst area error ....... {worst:.2f} m2")

    if city_info:
        s = city_info["height_sources"]
        print(f"city context ........... {city_info['buildings']:,} buildings "
              f"({s['height tag']} measured, {s['levels tag']} by storeys, "
              f"{s['assumed']} assumed), {city_info['roads']} streets")
        print(f"terrain ................ site +{city_info['site_asl']} m ASL, "
              f"Carmel to +{city_info['terrain_max']:.0f} m")

    return dict(mesh=m, schedule=schedule, z_roof=z_roof,
                z_base_bottom=z_base_bottom, above_total=sum(areas[l] for l in uppers),
                below_total=sum(areas[l] for l in basements), k=k, patio_area=a_pat,
                city=city_info)


def add_context(m, k):
    """Schematic massing of the existing government tower + its raised plaza."""
    cx, cy = CTX_CENTER[0] * k, CTX_CENTER[1] * k
    L = CTX_LENS_LENGTH * k / 2.0
    W = CTX_LENS_WIDTH * k / 2.0
    n = 72

    # lens plan: intersection of two circles, expressed as two circular arcs
    r = (L * L + W * W) / (2.0 * W)
    off = r - W

    def lens(t):
        # t in [0,1) around the lens
        if t < 0.5:
            u = t / 0.5
            th0 = math.asin(L / r)
            a = -th0 + 2 * th0 * u
            return (r * math.sin(a), r * math.cos(a) - off)
        u = (t - 0.5) / 0.5
        th0 = math.asin(L / r)
        a = th0 - 2 * th0 * u
        return (r * math.sin(a), -(r * math.cos(a) - off))

    base = [lens(i / n) for i in range(n)]
    H = CTX_FLOORS * CTX_FLOOR_H
    nz = 24
    rings = []
    for i in range(nz + 1):
        t = i / nz
        f = 1.0 + CTX_BULGE * (1.0 - (2.0 * t - 1.0) ** 2) - 0.06 * t
        rings.append((t * H, np.array([(cx + p[0] * f, cy + p[1] * f) for p in base])))

    m.group("context_existing_tower")
    ctr = np.array([cx, cy])
    m.cap(rings[0][1], 0.0, ctr, flip=True)
    for i in range(nz):
        m.strip(rings[i][1], rings[i + 1][1], rings[i][0], rings[i + 1][0])
    m.cap(rings[-1][1], H, ctr)

    # mast
    ms = 0.9
    mast = np.array([(cx - ms, cy - ms), (cx + ms, cy - ms),
                     (cx + ms, cy + ms), (cx - ms, cy + ms)])
    tip = np.array([(cx - 0.15, cy - 0.15), (cx + 0.15, cy - 0.15),
                    (cx + 0.15, cy + 0.15), (cx - 0.15, cy + 0.15)])
    m.group("context_mast")
    m.strip(mast, tip, H, H + CTX_MAST_H)
    m.cap(tip, H + CTX_MAST_H, ctr)

    # raised plaza (כיכר עילית קיימת) between the two buildings
    m.group("context_podium")
    pod = np.array([(cx + CTX_PODIUM_RX * k * math.cos(2 * math.pi * i / n),
                     cy + CTX_PODIUM_RY * k * math.sin(2 * math.pi * i / n))
                    for i in range(n)])
    m.cap(pod, CTX_PODIUM_BOTTOM, ctr, flip=True)
    m.strip(pod, pod, CTX_PODIUM_BOTTOM, CTX_PODIUM_TOP)
    m.cap(pod, CTX_PODIUM_TOP, ctr)


def add_site(m, k):
    """Thin plate showing the plot boundary from the site plan."""
    prof = [(x * k, w * k) for x, w in SITE_PROFILE]
    ring = [(x, w) for x, w in prof if w > 0]
    ring = ([(prof[0][0], 0.0)] + [(x, -w) for x, w in ring] +
            [(prof[-1][0], 0.0)] + [(x, w) for x, w in reversed(ring)])
    ring = np.array(ring)
    ctr = poly_centroid(ring)
    m.group("site")
    m.cap(ring, SITE_TOP_Z - SITE_THICKNESS, ctr, flip=True)
    m.strip(ring, ring, SITE_TOP_Z - SITE_THICKNESS, SITE_TOP_Z)
    m.cap(ring, SITE_TOP_Z, ctr)


# --------------------------------------------------------------------------
# 5. EXPORTERS
# --------------------------------------------------------------------------

MTL = """newmtl new_tower
Kd 0.98 0.84 0.35
Ka 0.20 0.17 0.07
Ks 0.10 0.10 0.10
Ns 12

newmtl context
Kd 0.80 0.80 0.82
Ka 0.18 0.18 0.19
Ks 0.05 0.05 0.05
Ns 8

newmtl site
Kd 0.90 0.90 0.88
Ka 0.20 0.20 0.20
Ks 0.00 0.00 0.00
Ns 1
"""


def write_obj(m, path):
    with open(path, "w") as fh:
        fh.write("# new 22-storey patio building, Derech HaAtzma'ut, Haifa\n")
        fh.write("# units: metres. +Z up, +Y north.\n")
        fh.write("mtllib new_tower.mtl\n")
        for x, y, z in m.v:
            fh.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
        for name, faces in m.groups.items():
            mat = name if name in ("new_tower", "site") else "context"
            fh.write(f"o {name}\n")
            fh.write(f"usemtl {mat}\n")
            for f in faces:
                fh.write("f " + " ".join(str(i + 1) for i in f) + "\n")
    with open(os.path.join(os.path.dirname(path), "new_tower.mtl"), "w") as fh:
        fh.write(MTL)


def write_stl(m, path, only=("new_tower",)):
    """Binary STL — a quarter the size of ASCII and read by every CAD tool."""
    import struct
    v = np.array(m.v)
    tris = [t for t in m.triangles(only=only)]
    with open(path, "wb") as fh:
        fh.write(b"new 22-storey patio building, Derech HaAtzma'ut, Haifa"
                 .ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p, q, r = v[a], v[b], v[c]
            nrm = np.cross(q - p, r - p)
            ln = np.linalg.norm(nrm)
            nrm = nrm / ln if ln > 1e-12 else np.zeros(3)
            fh.write(struct.pack("<12fH", *nrm, *p, *q, *r, 0))
    return len(tris)


def check_closed(m, groups):
    """Every directed edge must appear exactly once and have its reverse twin.

    That is what makes the STL watertight and consistently wound, so it can be
    printed or booleaned in CAD without repair.
    """
    seen = set()
    tris = m.triangles(only=groups)
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            if e in seen:
                return len(tris), f"edge {e} used twice in the same direction"
            seen.add(e)
    unmatched = sum(1 for (a, b) in seen if (b, a) not in seen)
    return len(tris), (f"{unmatched} unmatched edges" if unmatched else "closed")


def write_schedule(schedule, path):
    cols = ["level", "z_bottom", "z_top", "height", "scale",
            "target_sqm", "achieved_sqm", "error_sqm"]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in schedule:
            w.writerow(r)


def write_mesh_json(m, path, meta, schedule):
    v = np.array(m.v)
    data = {"meta": meta, "schedule": schedule,
            "vertices": [round(float(c), 2) for c in v.flatten()],
            "lines": [round(float(c), 2) for seg in m.lines for c in seg],
            "line_tags": m.line_tags,
            "groups": {}}
    for name in m.groups:
        tris = m.triangles(only=(name,))
        data["groups"][name] = [i for t in tris for i in t]
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    return os.path.getsize(path)


# --------------------------------------------------------------------------
# 6. PREVIEW RENDERS
# --------------------------------------------------------------------------

def V(f, elev, azim, title, span, zc=None, zs=1.0):
    """span = half-width framed, zc = height at frame centre, zs = vertical
    squash (city views are wide and shallow, so a cube wastes the canvas)."""
    return dict(f=f, elev=elev, azim=azim, title=title, span=span, zc=zc, zs=zs)


VIEWS = [
    V("preview_axo_a.png", 25, 200,
      "Axonometric — raked NW end and the long SW facade", 95),
    V("preview_axo_b.png", 40, 235,
      "Aerial three-quarter — roof, patio void and the Sail Tower", 105),
    V("preview_plan.png", 90, 133,
      "Roof plan — tapering plate with the patio void through it", 85),
    V("preview_elevation.png", 1, 223,
      "Elevation across the plot — compare with the section", 100),
    V("preview_city_aerial.png", 24, 250,
      "The site in the Lower City, Mount Carmel rising behind", 640, 105, 0.34),
    V("preview_city_bay.png", 7, 18,
      "From Haifa Bay — the site against the Carmel ridge", 680, 100, 0.30),
]


def render(m, meta, views=VIEWS, prefix=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    v = np.array(m.v)
    key = np.array([-0.42, -0.72, 0.55])
    key /= np.linalg.norm(key)
    fill = np.array([0.65, 0.35, 0.67])
    fill /= np.linalg.norm(fill)

    def collect(names, base_rgb):
        """Returns polys, face colours and a flat/upright flag per face.

        Horizontal faces (roofs, decks, the site plate) are fan- or
        ring-triangulated, so drawing their edges produces a radial moire.
        They get near-invisible edges; only the facade grid is lined.
        """
        polys, cols, flat = [], [], []
        for name in names:
            for f in m.groups.get(name, []):
                pts = v[list(f)]
                nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                ln = np.linalg.norm(nrm)
                if ln < 1e-12:
                    continue
                n = nrm / ln
                lam = 0.34 + 0.52 * max(0.0, float(n @ key)) \
                    + 0.18 * max(0.0, float(n @ fill))
                polys.append(pts)
                cols.append(tuple(min(1.0, c * lam) for c in base_rgb))
                flat.append(abs(float(n[2])) > 0.95)
        return polys, cols, flat

    # One collection for everything: matplotlib sorts each collection
    # independently, so separate layers interleave wrongly at a shared depth.
    layers = [
        (["sea"], (0.50, 0.62, 0.70), (0, 0, 0, 0.0), 0.0),
        (["terrain"], (0.76, 0.75, 0.66), (0, 0, 0, 0.0), 0.0),
        (["city_roads"], (0.56, 0.56, 0.55), (0, 0, 0, 0.0), 0.0),
        (["site"], (0.91, 0.91, 0.89), (0, 0, 0, 0.05), 0.10),
        (["city_buildings"], (0.82, 0.81, 0.77), (0, 0, 0, 0.14), 0.10),
        (["sail_tower", "sail_mast"], (0.88, 0.89, 0.91), (0, 0, 0, 0.16), 0.12),
        ([n for n in m.groups if n.startswith("context")], (0.87, 0.87, 0.90),
         (0, 0, 0, 0.10), 0.15),
        (["new_tower_basement"], (0.80, 0.70, 0.34), (0.30, 0.24, 0.05, 0.25), 0.18),
        (["new_tower"], (1.00, 0.83, 0.26), (0.30, 0.22, 0.0, 0.30), 0.25),
    ]
    all_p, all_c, all_e, all_w = [], [], [], []
    for names, rgb, edge, lw in layers:
        polys, cols, flat = collect(names, rgb)
        all_p += polys
        all_c += cols
        all_e += [(*edge[:3], 0.0) if fl else edge for fl in flat]
        all_w += [0.0 if fl else lw for fl in flat]

    # Frame on the new building, not the whole 3.6 km of terrain.
    tv = np.array([v[i] for f in m.groups["new_tower"] for i in f])
    focus = (tv.min(axis=0) + tv.max(axis=0)) / 2

    for vw in views:
        fname, elev, azim = vw["f"], vw["elev"], vw["azim"]
        title, span, zs = vw["title"], vw["span"], vw["zs"]
        fig = plt.figure(figsize=(11, 8.5), dpi=135)
        ax = fig.add_subplot(111, projection="3d")
        try:
            ax.set_proj_type("ortho")
        except Exception:
            pass
        ax.add_collection3d(Poly3DCollection(
            all_p, facecolors=all_c, edgecolors=all_e,
            linewidths=all_w, zsort="average"))
        cz = focus[2] if vw["zc"] is None else vw["zc"]
        ax.set_xlim(focus[0] - span, focus[0] + span)
        ax.set_ylim(focus[1] - span, focus[1] + span)
        ax.set_zlim(cz - span * zs, cz + span * zs)
        ax.set_box_aspect((1, 1, zs))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(
            f"{title}\n22 storeys · roof +{meta['roof_m']:.1f} m · "
            f"{meta['above_sqm']:,.0f} m² above grade · "
            f"{meta['below_sqm']:,.0f} m² in 5 basements",
            fontsize=10.5, pad=0)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, prefix + fname), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"  {prefix + fname}")


# --------------------------------------------------------------------------

def main():
    os.makedirs(OUT, exist_ok=True)
    r = build()
    m = r["mesh"]

    meta = dict(roof_m=r["z_roof"], lowest_m=r["z_base_bottom"],
                above_sqm=r["above_total"], below_sqm=r["below_total"],
                storeys=22, basements=5, patio_sqm=round(r["patio_area"], 1),
                typical_floor_h=TYPICAL_H, bearing_deg=SITE_BEARING_DEG,
                context_mode=CONTEXT_MODE)
    c = r.get("city")
    if c:
        meta.update(
            site_asl=c["site_asl"], carmel_m=c["terrain_max"],
            city_buildings=c["buildings"], city_roads=c["roads"],
            heights_assumed=c["height_sources"]["assumed"],
            declination=(c["declination"] or {}).get("declination_deg"),
            declination_date=(c["declination"] or {}).get("date"),
            city_radius_m=CITY_RADIUS_M,
            anchor=[__import__("city").ANCHOR_LAT, __import__("city").ANCHOR_LON],
            sail=c["sail"])

    write_obj(m, os.path.join(OUT, "new_tower.obj"))
    ntri = write_stl(m, os.path.join(OUT, "new_tower.stl"),
                     only=("new_tower", "new_tower_basement"))
    write_schedule(r["schedule"], os.path.join(OUT, "floor_schedule.csv"))
    nbytes = write_mesh_json(m, os.path.join(OUT, "mesh.json"), meta, r["schedule"])
    _, state = check_closed(m, ("new_tower", "new_tower_basement"))
    print(f"mesh ................... {len(m.v):,} verts, {ntri:,} tris (tower), "
          f"{len(m.lines):,} slab lines")
    print(f"tower solid ............ {state}")
    print(f"mesh.json .............. {nbytes/1024:,.0f} kB")
    render(m, meta)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
