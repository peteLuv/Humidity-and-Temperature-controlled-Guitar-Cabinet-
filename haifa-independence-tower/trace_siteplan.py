#!/usr/bin/env python3
"""Digitize the client's site plan into world-scale curves.

The drawing (data/site_plan.jpg) is colour-coded: yellow = the new building,
pale yellow = its atrium bands, white wedge inside = the patio, green = the
terraced garden, tan = the existing plaza paving, blue = the plot boundary.

Segmentation by colour -> contours -> simplification, then one similarity
transform maps pixels to metres:

  scale     the drawn Sail Tower lens vs its surveyed 39.9 m long axis
  rotation  the drawn lens axis vs the surveyed footprint's axis (OSM)
  origin    lens centroid -> the tower's centroid, which is the model's (0,0)

Everything downstream (build_model.py) consumes data/traced_geometry.json,
so the drawing is digitized once and the result is inspectable.
"""

import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
import shapely
from shapely.geometry import Polygon, LineString

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SAIL_LEN_M = None  # filled from OSM below
SAIL_TOWER_OSM_ID = 605918311

# ---------------------------------------------------------------- masks

def load(max_h=2400):
    im = Image.open(os.path.join(DATA, "site_plan.jpg")).convert("RGB")
    f = max_h / im.height
    im = im.resize((int(im.width * f), max_h), Image.BILINEAR)
    return np.asarray(im).astype(np.int16)


def masks(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = {}
    m["yellow"] = (R > 225) & (G > 195) & (G < 240) & (B < 170) & (R - B > 70)
    m["pale"] = (R > 235) & (G > 232) & (B > 155) & (B < 220) & (R - B > 25) & ~m["yellow"]
    m["green"] = (G > 220) & (G - R > 8) & (G - B > 40)
    m["tan"] = (abs(R - 216) < 22) & (abs(G - 194) < 22) & (abs(B - 172) < 22) & \
               (R - B > 25) & (R - B < 70) & (G - B > 8)
    m["blue"] = (B - R > 60) & (B > 150)
    m["dark"] = (R + G + B) < 330
    return m


def region(mask, close=6, min_frac=0.001):
    """Largest filled connected region of a mask."""
    st = ndi.generate_binary_structure(2, 2)
    m = ndi.binary_closing(mask, structure=np.ones((close, close), bool))
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m, structure=st)
    if n == 0:
        return np.zeros_like(mask)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < mask.size * min_frac:
        return np.zeros_like(mask)
    return lab == k


def outline(binary, tol=3.0, keep=0):
    """Contours of a binary region as simplified px rings, longest first."""
    cs = measure.find_contours(binary.astype(float), 0.5)
    cs.sort(key=len, reverse=True)
    rings = []
    for c in cs[:keep + 1 if keep else 1]:
        ring = LineString(np.column_stack([c[:, 1], c[:, 0]]))  # (x, y)
        ring = ring.simplify(tol)
        rings.append(np.asarray(ring.coords))
    return rings if keep else rings[0]


# ------------------------------------------------------------- transform

def osm_lens():
    with open(os.path.join(DATA, "osm_buildings.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    el = next(e for e in d["elements"] if e["id"] == SAIL_TOWER_OSM_ID)
    la0, lo0 = 32.816258, 35.002768
    mx = 111320 * math.cos(math.radians(la0))
    pts = np.array([[(p["lon"] - lo0) * mx, (p["lat"] - la0) * 110574]
                    for p in el["geometry"]])
    pts = pts - pts.mean(axis=0)
    u, s, vt = np.linalg.svd(pts, full_matrices=False)
    axis = vt[0]
    length = pts @ axis
    return float(length.max() - length.min()), math.atan2(axis[1], axis[0])


def pca_axis(pts):
    p = pts - pts.mean(axis=0)
    u, s, vt = np.linalg.svd(p, full_matrices=False)
    a = vt[0]
    ext = p @ a
    return math.atan2(a[1], a[0]), float(ext.max() - ext.min())


# ------------------------------------------------------------------ main

def main():
    a = load()
    H, W, _ = a.shape
    m = masks(a)
    print(f"image {W}x{H}")

    building_px = region(m["yellow"] | m["pale"], close=8)
    green_px = region(m["green"], close=8)
    tan_px = region(m["tan"], close=8)

    # The plot boundary is a thin blue line with gaps where labels cross it.
    # Seal it by dilation, then flood outward from the building: everything
    # reachable without crossing the sealed line is inside the plot.
    seal = ndi.binary_dilation(m["blue"], np.ones((17, 17), bool))
    cy, cx = ndi.center_of_mass(building_px)
    lab, _ = ndi.label(~seal)
    plot_px = (lab == lab[int(cy), int(cx)]) | seal
    plot_px = ndi.binary_fill_holes(plot_px)
    # trim the dilation slack back off the boundary
    plot_px = ndi.binary_erosion(plot_px, np.ones((9, 9), bool))

    # patio = the big hole inside the yellow mass
    solid = region(m["yellow"] | m["pale"], close=8)
    raw = ndi.binary_closing(m["yellow"] | m["pale"], structure=np.ones((8, 8), bool))
    holes = solid & ~raw
    lab, n = ndi.label(holes)
    sizes = ndi.sum(holes, lab, range(1, n + 1)) if n else []
    patio_px = (lab == (int(np.argmax(sizes)) + 1)) if n else np.zeros_like(solid)

    for name, msk in [("building", building_px), ("plot", plot_px),
                      ("green", green_px), ("tan", tan_px),
                      ("patio", patio_px)]:
        print(f"  {name:<9} {msk.sum()/msk.size*100:5.2f}% of image")

    # ---- the drawn tower lens: densest dark linework NW of the building ----
    # The tower plan is drawn with its window grid, far denser than any text.
    by, bx = np.nonzero(building_px)
    search = plot_px & ~building_px & ~green_px
    search[int(by.mean()):, :] = False          # NW half only
    dens = ndi.uniform_filter((m["dark"] & search).astype(float), 31)
    lab, n = ndi.label(dens > dens.max() * 0.5)
    cands = []
    for k in range(1, n + 1):
        blob = lab == k
        if blob.sum() < 400:
            continue
        py, px_ = np.nonzero(blob)
        pts = np.column_stack([px_, py]).astype(float)
        ang, ln = pca_axis(pts)
        wd = pts.shape[0] / max(ln, 1)          # crude mean width
        cands.append((blob.sum(), ln, ang, pts.mean(axis=0), ln / max(wd, 1)))
    cands.sort(reverse=True)
    size, len_px, ang_px, lens_c, aspect = cands[0]
    print(f"  lens: {len_px:.0f} px long at {math.degrees(ang_px):.1f} deg "
          f"(px frame), blob {size} px, {len(cands)} candidates")

    # ---- similarity transform px -> world ----
    # Initial guess from the lens; then refine by fitting the plot boundary
    # to the surveyed streets. The teardrop is bounded by kerbs on every
    # side, so each boundary sample should sit about half a carriageway from
    # its nearest street centreline. That objective pins scale, rotation and
    # position far better than any single drawn object.
    global SAIL_LEN_M
    SAIL_LEN_M, ang_world = osm_lens()
    scale0 = SAIL_LEN_M / len_px
    rot0 = ang_world - (-ang_px)

    # the building must land SE (south) of the tower; PCA is 180-ambiguous
    bcy, bcx = ndi.center_of_mass(building_px)
    def raw_world(px_pts, scale, rot, tx=0.0, ty=0.0):
        p = np.asarray(px_pts, dtype=float) - lens_c
        p = p * scale
        p[:, 1] = -p[:, 1]
        ca, sa = math.cos(rot), math.sin(rot)
        return np.column_stack([p[:, 0] * ca - p[:, 1] * sa + tx,
                                p[:, 0] * sa + p[:, 1] * ca + ty])
    if raw_world([[bcx, bcy]], scale0, rot0)[0][1] > 0:
        rot0 += math.pi

    # street centrelines with their half-widths
    with open(os.path.join(DATA, "osm_roads.json"), encoding="utf-8") as fh:
        roads = json.load(fh)
    la0, lo0 = 32.816258, 35.002768
    mx = 111320 * math.cos(math.radians(la0))
    segs, segw = [], []
    HW = {"trunk": 11.0, "primary": 9.0, "secondary": 7.0, "tertiary": 6.0,
          "residential": 5.0, "unclassified": 5.0}
    for el in roads["elements"]:
        g = el.get("geometry")
        w = HW.get(el.get("tags", {}).get("highway"))
        if not g or w is None:
            continue
        pts = [((p["lon"] - lo0) * mx, (p["lat"] - la0) * 110574) for p in g]
        for i in range(len(pts) - 1):
            if abs(pts[i][0]) < 350 and abs(pts[i][1]) < 350:
                segs.append((pts[i], pts[i + 1]))
                segw.append(w)
    segs_a = np.array([s[0] for s in segs])
    segs_b = np.array([s[1] for s in segs])
    segw = np.array(segw)

    def seg_dist(P):
        d = segs_b - segs_a
        L2 = (d ** 2).sum(axis=1)
        best = np.full(len(P), 1e9)
        wsel = np.zeros(len(P))
        for i in range(len(segs_a)):
            t = ((P - segs_a[i]) @ d[i]) / max(L2[i], 1e-9)
            t = np.clip(t, 0, 1)
            proj = segs_a[i] + np.outer(t, d[i])
            dist = np.hypot(*(P - proj).T)
            m = dist < best
            best[m] = dist[m]
            wsel[m] = segw[i]
        return best, wsel

    ring0 = outline(plot_px, 3.0)
    step = max(1, len(ring0) // 80)
    samples = ring0[::step]

    from scipy.optimize import minimize
    def cost(v):
        s, r, tx, ty = v
        P = raw_world(samples, s, r, tx, ty)
        dist, w = seg_dist(P)
        return float(((dist - w) ** 2).mean())

    x0 = np.array([scale0, rot0, 0.0, 0.0])
    res = minimize(cost, x0, method="Nelder-Mead",
                   options=dict(xatol=1e-4, fatol=0.01, maxiter=2000))
    scale, rot, tx, ty = res.x
    print(f"  street fit: scale {scale0:.4f} -> {scale:.4f} m/px, "
          f"rot {math.degrees(rot0):.1f} -> {math.degrees(rot):.1f} deg, "
          f"shift ({tx:+.1f}, {ty:+.1f}) m, rms gap "
          f"{math.sqrt(res.fun):.1f} m")

    def to_world(px_pts):
        return raw_world(px_pts, scale, rot, tx, ty)

    out = {"meta": dict(scale_m_per_px=scale, rot_deg=math.degrees(rot),
                        lens_len_px=len_px, sail_len_m=SAIL_LEN_M)}
    for name, msk, tol in [("plot", plot_px, 4), ("building", building_px, 3),
                           ("patio", patio_px, 2), ("green", green_px, 4),
                           ("paving", tan_px, 4)]:
        if not msk.any():
            print(f"  !! {name} empty")
            continue
        ring = to_world(outline(msk, tol))
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        out[name] = np.asarray(poly.exterior.coords).round(2).tolist()
        print(f"  {name:<9} {len(out[name]):>4} pts  area {poly.area:8,.0f} m2")

    with open(os.path.join(DATA, "traced_geometry.json"), "w") as fh:
        json.dump(out, fh)
    print("-> data/traced_geometry.json")

    # ---- overlay check against the OSM streets ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 10), dpi=110)
    with open(os.path.join(DATA, "osm_roads.json"), encoding="utf-8") as fh:
        roads = json.load(fh)
    la0, lo0 = 32.816258, 35.002768
    mx = 111320 * math.cos(math.radians(la0))
    for el in roads["elements"]:
        g = el.get("geometry")
        if not g:
            continue
        xs = [(p["lon"] - lo0) * mx for p in g]
        ys = [(p["lat"] - la0) * 110574 for p in g]
        if min(map(abs, xs)) < 300 and min(map(abs, ys)) < 300:
            ax.plot(xs, ys, color="0.55", lw=2.2, alpha=0.7, zorder=1)
    colors = dict(plot="#1E6FD9", building="#D9A400", patio="#8a6d00",
                  green="#5CA53C", paving="#8B7B6B")
    for name, col in colors.items():
        if name in out:
            r = np.asarray(out[name])
            ax.plot(r[:, 0], r[:, 1], color=col, lw=2, label=name, zorder=2)
    ax.plot(0, 0, "k+", ms=14, mew=2)
    ax.set_xlim(-220, 220); ax.set_ylim(-320, 120)
    ax.set_aspect("equal"); ax.legend(loc="lower left", fontsize=9)
    ax.set_title("traced site plan vs OSM streets (grey) — tower centroid at +")
    fig.savefig(os.path.join(HERE, "out", "trace_overlay.png"),
                bbox_inches="tight", facecolor="white")
    print("-> out/trace_overlay.png")


if __name__ == "__main__":
    main()
