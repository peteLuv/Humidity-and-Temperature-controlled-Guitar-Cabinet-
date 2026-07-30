#!/usr/bin/env python3
"""22-storey patio building, Derech HaAtzma'ut, Haifa - presentation model.

Geometry pipeline
-----------------
trace_siteplan.py   digitizes the client's site plan (zone, patio, garden,
                    paving) into world metres, street-fitted to OSM.
plan_family.py      turns the zone into a floor-plate family: a curved bar
                    whose NW end face is solved per level for the tabled area.
this file           assembles the whole scene - building, raised plaza deck,
                    terraced garden, Sail Tower, city fabric, terrain - and
                    exports OBJ / STL / schedule / mesh.json + previews.

Datums (z = 0 is ground at the Sail Tower per SRTM):
  building grade  g0            from terrain under the bar
  plaza deck      g0 + DECK_H   the existing raised plaza the Sail Tower
                                stands on ("a few storeys, garden on top")
  Sail Tower      base at deck, published heights above its own zero
"""

import csv
import json
import math
import os

import numpy as np
import mapbox_earcut
from shapely.geometry import Polygon

import city
import plan_family

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --- storey heights (client notes + Sail Tower derivation) ------------------
BASEMENT_H = 2.80
GROUND_H = 5.00
LEVEL1_H = 5.00
TYPICAL_H = 3.20        # (95 m roof / 29 storeys, less a 5 m lobby) ~ 3.2
N_BASEMENTS = 5

# --- massing rules ----------------------------------------------------------
PODIUM_SETBACK = 7.0    # G+1 face sits this far inside level 2's end face
RAKE_FIT_FROM = 4       # the straight rake is fitted on levels 4..21
STRAIGHT_FROM = 2       # ...and extended down to here (2-3 gain area)

# --- the existing raised plaza ("a few storeys with a garden on top") ------
DECK_H = 10.0           # deck above the new building's grade  ** assumption **
TERRACE_N = 6           # garden terraces stepping deck -> grade
TERRACE_W = 7.0         # metres per terrace band

# --- facade -----------------------------------------------------------------
BAND_OUT = 0.32         # spandrel ribbon proud of the glass line
BAND_H = 0.95
PARAPET_H = 1.15

# --- Sail Tower (surveyed footprint, published heights) --------------------
SAIL_ROOF, SAIL_TIP, SAIL_ANTENNA = 95.0, 113.0, 137.0
SAIL_FLOORS = 29

CITY_RADIUS_M = 900.0


# ==========================================================================
# mesh accumulator
# ==========================================================================

class Mesh:
    def __init__(self):
        self.v = []
        self.groups = {}
        self.lines = []
        self.line_tags = []
        self._cur = None

    def group(self, name):
        self._cur = name
        self.groups.setdefault(name, [])
        return self

    def face(self, pts):
        idx = []
        for p in pts:
            self.v.append((float(p[0]), float(p[1]), float(p[2])))
            idx.append(len(self.v) - 1)
        self.groups[self._cur].append(tuple(idx))

    def strip(self, lower, upper, z_lo, z_hi, flip=False, close=True):
        n = len(lower)
        last = n if close else n - 1
        for i in range(last):
            j = (i + 1) % n
            a = (lower[i][0], lower[i][1], z_lo)
            b = (lower[j][0], lower[j][1], z_lo)
            c = (upper[j][0], upper[j][1], z_hi)
            d = (upper[i][0], upper[i][1], z_hi)
            self.face([b, a, d, c] if flip else [a, b, c, d])

    def cap(self, outer, z, holes=(), down=False):
        """Earcut cap for an arbitrary ring with optional holes."""
        rings = [np.asarray(outer)[:, :2]] + [np.asarray(h)[:, :2] for h in holes]
        verts = np.vstack(rings)
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        tris = mapbox_earcut.triangulate_float64(verts, ends)
        for k in range(0, len(tris), 3):
            i, j, l = tris[k], tris[k + 1], tris[k + 2]
            p = [(verts[i][0], verts[i][1], z), (verts[j][0], verts[j][1], z),
                 (verts[l][0], verts[l][1], z)]
            e1 = np.subtract(p[1], p[0])[:2]
            e2 = np.subtract(p[2], p[0])[:2]
            up = (e1[0] * e2[1] - e1[1] * e2[0]) > 0
            if up == down:
                p.reverse()
            self.face(p)

    def polyline(self, pts, z, tag=""):
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            self.lines.append((a[0], a[1], z, b[0], b[1], z))
            self.line_tags.append(tag)

    def weld(self, tol=1e-4):
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


def ring_ccw(ring):
    r = np.asarray(ring, dtype=float)
    area = 0.5 * np.sum(r[:, 0] * np.roll(r[:, 1], -1) -
                        np.roll(r[:, 0], -1) * r[:, 1])
    return r if area > 0 else r[::-1]


def ring_offset(ring, d):
    """Push every vertex outward (CCW ring) along its averaged edge normal."""
    r = np.asarray(ring, dtype=float)
    prv = np.roll(r, 1, axis=0)
    nxt = np.roll(r, -1, axis=0)
    t = nxt - prv
    ln = np.linalg.norm(t, axis=1, keepdims=True)
    ln[ln < 1e-9] = 1
    n = np.column_stack([t[:, 1], -t[:, 0]]) / ln   # outward for CCW
    return r + n * d


def resample_ring(poly, n):
    """Fixed-count arclength resampling of a shapely polygon exterior."""
    ext = poly.exterior
    return np.array([ext.interpolate(i / n, normalized=True).coords[0]
                     for i in range(n)])


def poly_prism(m, poly, z0, z1, simplify=0.8, top=True, bottom=False):
    """Extrude a (multi)polygon; walls + earcut top cap with holes."""
    geoms = poly.geoms if poly.geom_type.startswith("Multi") else [poly]
    for g in geoms:
        if g.area < 4:
            continue
        g = g.simplify(simplify)
        outer = ring_ccw(np.asarray(g.exterior.coords)[:-1])
        m.strip(outer, outer, z0, z1)
        holes = [ring_ccw(np.asarray(r.coords)[:-1])[::-1] for r in g.interiors]
        for h in holes:
            m.strip(h, h, z0, z1, flip=True)
        if top:
            m.cap(outer, z1, holes=holes)
        if bottom:
            m.cap(outer, z0, holes=holes, down=True)


def band(m, ring, z0, h, out=BAND_OUT):
    """A spandrel ribbon proud of the facade line."""
    r = ring_ccw(ring)
    o = ring_offset(r, out)
    m.strip(o, o, z0, z0 + h)                    # outer face
    m.strip(o, r, z0 + h, z0 + h)                # top return
    m.strip(r, o, z0, z0)                        # soffit


# ==========================================================================
# build
# ==========================================================================

def load_areas():
    path = os.path.join(HERE, "data", "floor_areas.csv")
    rows = [l.rstrip("\n") for l in open(path, encoding="utf-8")
            if not l.startswith("#") and l.strip()]
    return {r["level"]: float(r["area_sqm"]) for r in csv.DictReader(rows)}


def build(quality="high"):
    S = 100 if quality == "high" else 48         # samples per bar side
    PS = 56 if quality == "high" else 32         # patio ring samples
    areas = load_areas()
    total = sum(areas.values())
    assert abs(total - 69240) < 0.5, "schedule does not match the sheet total"
    print(f"schedule total ......... {total:,.0f} m2 (sheet: 69,240)")

    fam = plan_family.Family()
    print(f"zone ................... {fam.zone.area:,.0f} m2, spine {fam.length:.0f} m")
    print(f"patio void ............. {fam.patio_area:,.0f} m2")

    # ---- terrain first: the datums come from it ---------------------------
    terr = city.Terrain(city._load("terrain.json"), 0.0, 0.0)

    # ---- solve the floor lengths ------------------------------------------
    Ls, zs = {}, {}
    z = 0.0  # provisional, relative to building grade
    for lbl in ["G", "1"] + [str(i) for i in range(2, 22)]:
        h = GROUND_H if lbl == "G" else (LEVEL1_H if lbl == "1" else TYPICAL_H)
        zs[lbl] = z
        z += h
    roof_rel = z

    for i in range(2, 22):
        Ls[str(i)] = fam.solve(areas[str(i)])

    fit_lv = [str(i) for i in range(RAKE_FIT_FROM, 22)]
    A = np.polyfit([zs[l] for l in fit_lv], [Ls[l] for l in fit_lv], 1)
    resid = np.polyval(A, [zs[l] for l in fit_lv]) - np.array([Ls[l] for l in fit_lv])
    print(f"SE rake ................ straight to {np.abs(resid).max():.2f} m over "
          f"{zs['21'] - zs[str(RAKE_FIT_FROM)]:.0f} m "
          f"({math.degrees(math.atan(A[0])):.1f} deg lean)")
    gained = []
    for i in range(STRAIGHT_FROM, RAKE_FIT_FROM):
        lbl = str(i)
        Lline = float(np.polyval(A, zs[lbl]))
        got = fam.outline(Lline).difference(fam.patio).area
        gained.append((lbl, Lline - Ls[lbl], got - areas[lbl]))
        Ls[lbl] = Lline
    if gained:
        print("straightened ........... " + ", ".join(
            f"lv{l} +{d:.1f} m (+{a:.0f} m2)" for l, d, a in gained))

    L_pod = Ls["2"] - PODIUM_SETBACK
    hw_pod = {lbl: fam.solve_hw(areas[lbl], L_pod) for lbl in ("G", "1")}
    hw_bsmt = fam.solve_hw(areas["B1"] - fam.patio_area, L_pod)  # gross plate
    # basements have no patio: widen until gross area = 3200
    lo, hi = -4.0, 40.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if fam.outline(L_pod, mid).area < areas["B1"]:
            lo = mid
        else:
            hi = mid
    hw_bsmt = (lo + hi) / 2

    rings = {lbl: fam.ring(Ls[lbl], samples=S) for lbl in Ls}
    rings["G"] = fam.ring(L_pod, hw_pod["G"], samples=S)
    rings["1"] = fam.ring(L_pod, hw_pod["1"], samples=S)
    ring_bs = fam.ring(L_pod, hw_bsmt, samples=S)
    patio_ring = resample_ring(fam.patio, PS)

    # ---- datums ------------------------------------------------------------
    g0 = float(np.median([terr.sample(x, y) for x, y in rings["G"]]))
    deck_z = g0 + DECK_H
    print(f"building grade ......... {g0:+.2f} m vs the Sail Tower site")
    print(f"plaza deck ............. {deck_z:+.2f} m  (Sail Tower ground zero)")
    Z = {lbl: g0 + zv for lbl, zv in zs.items()}
    z_roof = g0 + roof_rel
    z_bsmt = g0 - BASEMENT_H * N_BASEMENTS

    # ---- schedule ----------------------------------------------------------
    schedule = []
    for k in range(N_BASEMENTS, 0, -1):
        zb = g0 - k * BASEMENT_H
        schedule.append(dict(level=f"B{k}", z_bottom=round(zb - g0, 2),
                             z_top=round(zb - g0 + BASEMENT_H, 2),
                             height=BASEMENT_H, plan_length=round(L_pod, 1),
                             target_sqm=areas[f"B{k}"],
                             achieved_sqm=round(fam.outline(L_pod, hw_bsmt).area, 1)))
    order = ["G", "1"] + [str(i) for i in range(2, 22)]
    for lbl in order:
        h = GROUND_H if lbl == "G" else (LEVEL1_H if lbl == "1" else TYPICAL_H)
        if lbl in ("G", "1"):
            net = fam.outline(L_pod, hw_pod[lbl]).difference(fam.patio).area
            Lx = L_pod
        else:
            net = fam.outline(Ls[lbl]).difference(fam.patio).area
            Lx = Ls[lbl]
        schedule.append(dict(level=lbl, z_bottom=round(Z[lbl] - g0, 2),
                             z_top=round(Z[lbl] - g0 + h, 2), height=h,
                             plan_length=round(Lx, 1), target_sqm=areas[lbl],
                             achieved_sqm=round(net, 1)))
    for r in schedule:
        r["error_sqm"] = round(r["achieved_sqm"] - r["target_sqm"], 2)
    worst = max(abs(r["error_sqm"]) for r in schedule
                if r["level"] not in [str(i) for i in
                                      range(STRAIGHT_FROM, RAKE_FIT_FROM)])
    print(f"area error ............. {worst:.2f} m2 worst "
          f"(straightened floors excluded)")

    # ---- assemble ----------------------------------------------------------
    m = Mesh()

    # basement box
    m.group("new_basement")
    bs = ring_ccw(ring_bs)
    m.cap(bs, z_bsmt, down=True)
    m.strip(bs, bs, z_bsmt, g0)
    m.strip(bs, ring_ccw(rings["G"]), g0, g0)     # ledge out to the podium line

    # shell: podium -> tower -> roof -> patio shaft
    m.group("new_glass")
    seq = ["G", "1"] + [str(i) for i in range(2, 22)]
    for k, lbl in enumerate(seq):
        r0 = ring_ccw(rings[lbl])
        h = GROUND_H if lbl == "G" else (LEVEL1_H if lbl == "1" else TYPICAL_H)
        z0 = Z[lbl]
        if lbl in ("G", "1"):
            m.strip(r0, r0, z0, z0 + h)           # vertical podium
            nxt = ring_ccw(rings[seq[k + 1]])
            m.strip(r0, nxt, z0 + h, z0 + h)      # ledge / soffit to next plate
        elif lbl != "21":
            nxt = ring_ccw(rings[seq[k + 1]])
            m.strip(r0, nxt, z0, z0 + h)          # the continuous rake
        else:
            m.strip(r0, r0, z0, z0 + h)           # top floor vertical
    pr = ring_ccw(patio_ring)
    m.strip(pr, pr, g0, z_roof, flip=True)        # patio shaft
    m.group("new_roof")
    m.cap(ring_ccw(rings["21"]), z_roof, holes=[pr[::-1]])
    m.cap(pr, g0)                                  # courtyard floor

    # spandrel bands + parapet
    m.group("new_bands")
    for lbl in seq[1:]:
        src = rings[lbl]
        band(m, src, Z[lbl] - 0.1, BAND_H)
    band(m, rings["21"], z_roof - 0.05, PARAPET_H, out=0.18)

    # ---- plaza deck structure and its garden ------------------------------
    paving = fam.paving.simplify(1.0).buffer(2, join_style=1).buffer(-2)
    m.group("deck_structure")
    poly_prism(m, paving, g0 - 1.0, deck_z, top=False)
    m.group("deck_top")
    sail_ring = sail_footprint()
    deck_top = paving.difference(Polygon(sail_ring).buffer(0.5))
    geoms = deck_top.geoms if deck_top.geom_type.startswith("Multi") else [deck_top]
    for g in geoms:
        g = g.simplify(0.8)
        m.cap(ring_ccw(np.asarray(g.exterior.coords)[:-1]), deck_z,
              holes=[ring_ccw(np.asarray(r.coords)[:-1])[::-1]
                     for r in g.interiors])

    m.group("landscape_terraces")
    tree_pts = []
    garden = fam.green.union(fam.zone.difference(
        fam.outline(Ls["21"], 4.0)).intersection(
        fam.green.buffer(60)))
    for k in range(TERRACE_N):
        bandk = garden.intersection(
            paving.buffer((k + 1) * TERRACE_W).difference(
                paving.buffer(k * TERRACE_W)))
        if bandk.is_empty:
            continue
        hk = deck_z - (k + 1) * (DECK_H - 1.0) / TERRACE_N
        poly_prism(m, bandk, g0 - 0.5, hk, simplify=1.2)
        tree_pts += scatter(bandk, 8.0, hk)
    rest = garden.difference(paving.buffer(TERRACE_N * TERRACE_W))
    if not rest.is_empty:
        poly_prism(m, rest, g0 - 0.5, g0 + 0.45, simplify=1.2)
        tree_pts += scatter(rest, 9.0, g0 + 0.45)

    m.group("plot_plate")
    poly_prism(m, fam.plot.simplify(1.0), g0 - 0.9, g0 + 0.03)

    m.group("trees")
    for x, y, zt in tree_pts:
        tree(m, x, y, zt)
    print(f"garden ................. {TERRACE_N} terraces, {len(tree_pts)} trees")

    # ---- the Sail Tower on its deck ---------------------------------------
    sr = ring_ccw(sail_ring)
    m.group("sail_glass")
    m.strip(sr, sr, deck_z - 2.0, deck_z + SAIL_ROOF)
    m.cap(sr, deck_z + SAIL_ROOF)
    m.group("sail_bands")
    sail_typ = (SAIL_ROOF - 5.0) / (SAIL_FLOORS - 1)
    for k in range(1, SAIL_FLOORS):
        band(m, sr, deck_z + 5.0 + (k - 1) * sail_typ, 0.8, out=0.25)
    m.group("sail_sails")
    sails(m, sr, deck_z)
    m.group("sail_mast")
    cx, cy = sr[:, 0].mean(), sr[:, 1].mean()
    mast = np.array([(cx - .8, cy - .8), (cx + .8, cy - .8),
                     (cx + .8, cy + .8), (cx - .8, cy + .8)])
    m.strip(mast, mast * 0.2 + np.array([cx, cy]) * 0.8,
            deck_z + SAIL_TIP - 6, deck_z + SAIL_ANTENNA)

    # ---- city --------------------------------------------------------------
    nland, nsea = city.add_terrain(m, terr)
    nroads = city.add_roads(m, lambda la, lo: city_proj(la, lo), terr,
                            CITY_RADIUS_M)
    stats, tallest = city.add_buildings(
        m, lambda la, lo: city_proj(la, lo), terr,
        skip_ids={city.SAIL_TOWER_OSM_ID}, radius=CITY_RADIUS_M,
        exclude_poly=fam.plot)
    print(f"city ................... {sum(stats.values()):,} buildings, "
          f"{nroads} streets (site cleared)")

    # ---- slab lines for the viewer ----------------------------------------
    for lbl in seq:
        m.polyline(rings[lbl][::3], Z[lbl], tag=lbl)
    m.polyline(rings["21"][::3], z_roof, tag="21")
    for k in range(N_BASEMENTS + 1):
        m.polyline(ring_bs[::4], z_bsmt + k * BASEMENT_H,
                   tag=f"B{N_BASEMENTS - k}" if k < N_BASEMENTS else "B1")
    m.polyline(patio_ring, z_roof)

    m.weld()
    decl = None
    p = os.path.join(HERE, "data", "declination.json")
    if os.path.exists(p):
        decl = json.load(open(p))

    meta = dict(roof_m=round(roof_rel, 2), storeys=22, basements=N_BASEMENTS,
                above_sqm=sum(areas[l] for l in order),
                below_sqm=sum(areas[f"B{k}"] for k in range(1, 6)),
                patio_sqm=round(fam.patio_area, 0), typical_floor_h=TYPICAL_H,
                deck_h=DECK_H, grade_vs_tower=round(g0, 2),
                bar_len=round(Ls["21"], 1), site_asl=round(terr.site_asl, 1),
                carmel_m=float(terr.z.max()),
                declination=(decl or {}).get("declination_deg"),
                declination_date=(decl or {}).get("date"),
                sail=dict(roof=SAIL_ROOF, tip=SAIL_TIP, antenna=SAIL_ANTENNA,
                          base=round(deck_z, 1)),
                city_buildings=sum(stats.values()), city_roads=nroads,
                heights_assumed=stats.get("assumed", 0),
                city_radius_m=CITY_RADIUS_M, bearing_deg=None,
                straightened={l: round(a, 0) for l, _, a in gained})
    return dict(mesh=m, schedule=schedule, meta=meta, g0=g0, z_roof=z_roof)


def city_proj(lat, lon):
    la0, lo0 = 32.816258, 35.002768
    mx = 111320 * math.cos(math.radians(la0))
    return ((lon - lo0) * mx, (lat - la0) * 110574)


def sail_footprint(n=72):
    d = city._load("osm_buildings.json")
    el = next(e for e in d["elements"] if e["id"] == city.SAIL_TOWER_OSM_ID)
    pts = [city_proj(p["lat"], p["lon"]) for p in el["geometry"]]
    poly = Polygon(pts).buffer(0).simplify(0.3)
    poly = poly.buffer(1.5, join_style=1).buffer(-1.5)   # smooth the lens
    return resample_ring(poly, n)


def sails(m, ring, base_z):
    """The two sail blades above the roof, arcing up to the tips."""
    r = np.asarray(ring)
    cx, cy = r[:, 0].mean(), r[:, 1].mean()
    i0 = int(np.argmax((r[:, 0] - cx) ** 2 + (r[:, 1] - cy) ** 2))
    d0 = r[i0] - [cx, cy]
    proj = (r - [cx, cy]) @ d0
    i1 = int(np.argmin(proj))
    a, b = sorted((i0, i1))
    chains = [r[a:b + 1], np.vstack([r[b:], r[:a + 1]])]
    for ch in chains:
        if len(ch) < 3:
            continue
        seg = np.linalg.norm(np.diff(ch, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] < 1:
            continue
        top = base_z + SAIL_ROOF + (SAIL_TIP - SAIL_ROOF) * \
            np.sin(math.pi * s / s[-1])
        for i in range(len(ch) - 1):
            m.face([(ch[i][0], ch[i][1], base_z + SAIL_ROOF),
                    (ch[i + 1][0], ch[i + 1][1], base_z + SAIL_ROOF),
                    (ch[i + 1][0], ch[i + 1][1], top[i + 1]),
                    (ch[i][0], ch[i][1], top[i])])


def scatter(poly, spacing, z):
    """Jittered grid of tree positions inside a (multi)polygon."""
    rng = np.random.default_rng(7)
    out = []
    minx, miny, maxx, maxy = poly.bounds
    from shapely.geometry import Point
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            px = x + rng.uniform(-2, 2)
            py = y + rng.uniform(-2, 2)
            if poly.buffer(-2).contains(Point(px, py)):
                out.append((px, py, z))
            x += spacing
        y += spacing
    return out


def tree(m, x, y, z, r=2.1, h=6.5):
    """Low-poly tree: trunk + faceted crown."""
    t = 0.25
    trunk = np.array([(x - t, y - t), (x + t, y - t), (x + t, y + t), (x - t, y + t)])
    m.strip(trunk, trunk, z, z + h - r * 1.6)
    zc = z + h - r * 1.6
    prev = None
    for k, (f, zz) in enumerate([(0.45, 0), (1.0, 0.8), (0.95, 1.9), (0.4, 2.6)]):
        ring = np.array([(x + r * f * math.cos(a), y + r * f * math.sin(a))
                         for a in np.linspace(0, 2 * math.pi, 7, endpoint=False)])
        if prev is not None:
            m.strip(prev[0], ring, prev[1], zc + zz)
        prev = (ring, zc + zz)
    m.cap(ring_ccw(prev[0]), prev[1])


# ==========================================================================
# exports
# ==========================================================================

GROUP_MATS = {
    "new_glass": (0.42, 0.58, 0.57), "new_roof": (0.82, 0.80, 0.76),
    "new_bands": (0.88, 0.76, 0.50), "new_basement": (0.62, 0.58, 0.50),
    "deck_structure": (0.72, 0.69, 0.64), "deck_top": (0.78, 0.75, 0.70),
    "landscape_terraces": (0.55, 0.66, 0.42), "trees": (0.34, 0.48, 0.27),
    "plot_plate": (0.80, 0.79, 0.75),
    "sail_glass": (0.62, 0.68, 0.74), "sail_bands": (0.85, 0.86, 0.88),
    "sail_sails": (0.92, 0.93, 0.94), "sail_mast": (0.55, 0.57, 0.60),
    "city_buildings": (0.79, 0.77, 0.73), "city_roads": (0.42, 0.42, 0.42),
    "terrain": (0.72, 0.70, 0.61), "sea": (0.36, 0.51, 0.58),
}


def write_obj(m, path):
    with open(path, "w") as fh:
        fh.write("# patio building massing, Derech HaAtzma'ut, Haifa\n"
                 "# metres; +Y true north; z=0 = grade at the Sail Tower site\n"
                 "mtllib new_tower.mtl\n")
        for x, y, z in m.v:
            fh.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
        for name, faces in m.groups.items():
            fh.write(f"o {name}\nusemtl {name}\n")
            for f in faces:
                fh.write("f " + " ".join(str(i + 1) for i in f) + "\n")
    with open(os.path.join(os.path.dirname(path), "new_tower.mtl"), "w") as fh:
        for name, kd in GROUP_MATS.items():
            fh.write(f"newmtl {name}\nKd {kd[0]:.3f} {kd[1]:.3f} {kd[2]:.3f}\n"
                     f"Ka {kd[0]*0.2:.3f} {kd[1]*0.2:.3f} {kd[2]*0.2:.3f}\n\n")


def write_stl(m, path, groups):
    import struct
    v = np.array(m.v)
    tris = m.triangles(only=groups)
    with open(path, "wb") as fh:
        fh.write(b"patio building, Derech HaAtzma'ut, Haifa".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            p, q, r = v[a], v[b], v[c]
            n = np.cross(q - p, r - p)
            ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-12 else np.zeros(3)
            fh.write(struct.pack("<12fH", *n, *p, *q, *r, 0))
    return len(tris)


def write_mesh_json(m, meta, schedule, path):
    v = np.array(m.v)
    data = {"meta": meta, "schedule": schedule,
            "vertices": [round(float(c), 2) for c in v.flatten()],
            "lines": [round(float(c), 2) for s in m.lines for c in s],
            "line_tags": m.line_tags, "groups": {}}
    for name in m.groups:
        data["groups"][name] = [i for t in m.triangles(only=(name,)) for i in t]
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    return os.path.getsize(path)


# ==========================================================================
# quick previews (matplotlib QA; the heroes come from Cycles)
# ==========================================================================

def V(f, elev, azim, title, span, zc=None, zs=1.0):
    return dict(f=f, elev=elev, azim=azim, title=title, span=span, zc=zc, zs=zs)


VIEWS = [
    V("preview_axo.png", 22, -145, "From the south-east — the diagonal wall on the far side", 160),
    V("preview_aerial.png", 40, -60, "Aerial — the bar, garden and deck", 220),
    V("preview_plan.png", 90, 0, "Plan — traced zone, bar and garden", 240),
    V("preview_elevation.png", 2, 0, "East elevation — prow left, diagonal wall right", 170),
    V("preview_city.png", 18, -105, "In the Lower City, Carmel behind", 700,
      120, 0.35),
]


def render(m, meta, views=VIEWS):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    v = np.array(m.v)
    key = np.array([-0.45, -0.62, 0.64]); key /= np.linalg.norm(key)
    fill = np.array([0.7, 0.3, 0.65]); fill /= np.linalg.norm(fill)

    focus_idx = {i for f in m.groups["new_glass"] for i in f}
    fv = v[list(focus_idx)]
    focus = (fv.min(axis=0) + fv.max(axis=0)) / 2

    polys, cols = [], []
    for name, faces in m.groups.items():
        rgb = GROUP_MATS.get(name, (0.7, 0.7, 0.7))
        for f in faces:
            pts = v[list(f)]
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            n = n / ln
            lam = 0.35 + 0.5 * max(0, float(n @ key)) + 0.15 * max(0, float(n @ fill))
            polys.append(pts)
            cols.append(tuple(min(1, c * lam) for c in rgb))

    for vw in views:
        fig = plt.figure(figsize=(11, 8.5), dpi=130)
        ax = fig.add_subplot(111, projection="3d")
        try:
            ax.set_proj_type("ortho")
        except Exception:
            pass
        ax.add_collection3d(Poly3DCollection(polys, facecolors=cols,
                                             edgecolors=(0, 0, 0, 0.06),
                                             linewidths=0.1, zsort="average"))
        span, zsq = vw["span"], vw["zs"]
        cz = focus[2] if vw["zc"] is None else vw["zc"]
        ax.set_xlim(focus[0] - span, focus[0] + span)
        ax.set_ylim(focus[1] - span, focus[1] + span)
        ax.set_zlim(cz - span * zsq, cz + span * zsq)
        ax.set_box_aspect((1, 1, zsq))
        ax.view_init(elev=vw["elev"], azim=vw["azim"])
        ax.set_axis_off()
        ax.set_title(f"{vw['title']}\n22 storeys · roof +{meta['roof_m']:.0f} m · "
                     f"{meta['above_sqm']:,.0f} m² above grade", fontsize=10.5)
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, vw["f"]), bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        print(f"  {vw['f']}")


# ==========================================================================

def main():
    os.makedirs(OUT, exist_ok=True)
    r = build("high")
    m = r["mesh"]
    ntri = len(m.triangles())
    print(f"mesh ................... {len(m.v):,} verts, {ntri:,} tris")

    write_obj(m, os.path.join(OUT, "new_tower.obj"))
    shell = ("new_glass", "new_roof", "new_basement")
    write_stl(m, os.path.join(OUT, "new_tower.stl"), shell)
    with open(os.path.join(OUT, "floor_schedule.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(r["schedule"][0]))
        w.writeheader()
        w.writerows(r["schedule"])
    n = write_mesh_json(m, r["meta"], r["schedule"],
                        os.path.join(OUT, "mesh.json"))
    print(f"mesh.json .............. {n/1024:,.0f} kB")

    lite = build("lite")
    n = write_mesh_json(lite["mesh"], lite["meta"], lite["schedule"],
                        os.path.join(OUT, "mesh_lite.json"))
    print(f"mesh_lite.json ......... {n/1024:,.0f} kB")

    render(m, r["meta"])
    print("done ->", OUT)


if __name__ == "__main__":
    main()
