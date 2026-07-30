#!/usr/bin/env python3
"""Floor-plate family for the new building, derived from the traced site plan.

Reconciling the sources:

  * The drawing's yellow region is the BUILDING ZONE - 13,551 m2 once the
    tracing is street-fitted, five times any tabled floor plate. It cannot be
    a floor plan; it is the envelope the building may occupy.
  * The tabled areas (2,000-2,600 m2 per floor) on a zone ~170 m long mean
    the building is a long, slender bar - which is exactly the proportion the
    hand sketches show.

So the bar follows the ZONE's curved spine: its centreline is the zone's own
centreline, its SE end sits at the zone's rounded tip, and its width profile
tapers from a blunt prow to a wider NW end. Each floor is the same bar cut at
length L, with L solved so the plate nets its tabled area. The patio void is
a rounded wedge on the centreline, positioned by the drawn patio's stations.

All output is in world metres (Sail Tower centroid = origin, +Y true north).
"""

import json
import math
import os

import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# ---- bar proportions (metres) ---------------------------------------------
TIP_HALFWIDTH = 8.0     # half-width of the blunt SE prow
TAPER = 0.038           # half-width gained per metre of length
PROW_R = 10.0           # rounded-prow length
TIP_SETBACK = 6.0       # bar tip inside the zone tip

# ---- patio void -----------------------------------------------------------
PATIO_FROM = 0.44       # start/end as fractions of the drawn patio stations
PATIO_HW0, PATIO_HW1 = 3.0, 6.5   # half-width, narrow SE -> wide NW
PATIO_ROUND = 2.0


class Family:
    def __init__(self):
        with open(os.path.join(DATA, "traced_geometry.json")) as fh:
            t = json.load(fh)
        self.zone = Polygon(t["building"]).buffer(0)
        self.plot = Polygon(t["plot"]).buffer(0)
        self.green = Polygon(t["green"]).buffer(0)
        self.paving = Polygon(t["paving"]).buffer(0)
        self.patio_drawn = Polygon(t["patio"]).buffer(0)
        self._centreline()
        # Two passes: the patio's NW end must stay inside the smallest floor
        # plate (level 2), whose length itself depends on the patio area.
        self._patio(cap=None)
        L2 = self.solve(1820.0)
        self._patio(cap=L2 - 7.0)

    # -- the zone's curved spine, tip at s = 0 ------------------------------
    def _centreline(self):
        z = self.zone
        c = np.asarray(z.exterior.coords)
        mean = c.mean(axis=0)
        u, s, vt = np.linalg.svd(c - mean, full_matrices=False)
        axis, cross = vt[0], vt[1]
        proj = (c - mean) @ axis
        lo, hi = proj.min(), proj.max()
        # slice the zone perpendicular to the axis; midpoints form the spine
        stations, mids = [], []
        for f in np.linspace(0.02, 0.98, 45):
            d = lo + (hi - lo) * f
            p0 = mean + axis * d - cross * 400
            p1 = mean + axis * d + cross * 400
            cut = z.intersection(LineString([p0, p1]))
            if cut.is_empty:
                continue
            cut = max(cut.geoms, key=lambda g: g.length) \
                if cut.geom_type == "MultiLineString" else cut
            mids.append(np.asarray(cut.interpolate(0.5, normalized=True).coords[0]))
            stations.append(d)
        mids = np.asarray(mids)
        # tip = the southern end (away from the tower at the origin)
        if np.linalg.norm(mids[0]) < np.linalg.norm(mids[-1]):
            mids = mids[::-1]
        # A smoothing spline keeps the drawn banana but kills the slice
        # jitter that would make the offset edges self-intersect at the prow.
        from scipy.interpolate import splprep, splev
        tck, _ = splprep(mids.T, s=len(mids) * 4.0, k=3)
        sm = np.column_stack(splev(np.linspace(0, 1, 160), tck))
        # extend the smooth end along its tangent out to the zone boundary
        tipdir = sm[0] - sm[4]
        tipdir /= np.linalg.norm(tipdir)
        p = sm[0].copy()
        for _ in range(60):
            if not self.zone.contains(Point(p + tipdir)):
                break
            p = p + tipdir
        self.spine = np.vstack([[p], sm])
        seg = np.linalg.norm(np.diff(self.spine, axis=0), axis=1)
        keep = np.concatenate([[True], seg > 1e-6])
        self.spine = self.spine[keep]
        seg = np.linalg.norm(np.diff(self.spine, axis=0), axis=1)
        self.s = np.concatenate([[0], np.cumsum(seg)])
        self.length = float(self.s[-1])

    def at(self, l):
        """Point and unit tangent/normal on the spine at arclength l from tip."""
        l = np.clip(l, 0, self.length - 1e-6)
        i = int(np.searchsorted(self.s, l, side="right") - 1)
        i = min(i, len(self.spine) - 2)
        t = (l - self.s[i]) / max(self.s[i + 1] - self.s[i], 1e-9)
        p = self.spine[i] * (1 - t) + self.spine[i + 1] * t
        d = self.spine[i + 1] - self.spine[i]
        d = d / np.linalg.norm(d)
        return p, d, np.array([-d[1], d[0]])

    # -- bar outline at length L, CCW, tip rounded --------------------------
    # ring() keeps a stable parameterisation (same sample count and ordering
    # for every L), which lets floors loft vertex-to-vertex with no resampling.
    def ring(self, L, extra_hw=0.0, samples=100):
        L = float(L)
        left, right = [], []
        for l in np.linspace(TIP_SETBACK, TIP_SETBACK + L, samples):
            lb = l - TIP_SETBACK
            hw = TIP_HALFWIDTH + TAPER * lb + extra_hw
            if lb < PROW_R:  # elliptical prow cap
                hw *= math.sqrt(max(1e-4, 1 - ((PROW_R - lb) / PROW_R) ** 2))
                hw = max(hw, 0.8)
            p, d, n = self.at(l)
            left.append(p + n * hw)
            right.append(p - n * hw)
        return np.vstack([right, left[::-1]])

    def outline(self, L, extra_hw=0.0, samples=100):
        poly = Polygon(self.ring(L, extra_hw, samples))
        return poly if poly.is_valid else poly.buffer(0)

    def _patio(self, cap=None):
        """Patio stations from the drawn patio, projected onto the spine."""
        pc = np.asarray(self.patio_drawn.exterior.coords)
        ls = []
        for q in pc:
            d = np.linalg.norm(self.spine - q, axis=1)
            i = int(np.argmin(d))
            ls.append(self.s[i])
        l0, l1 = min(ls), max(ls)
        span = l1 - l0
        a = l0 + span * 0.08
        b = l1 - span * 0.08
        if cap is not None and b > cap:
            b = cap
            a = min(a, b - 30.0)
        pts_l, pts_r = [], []
        for f in np.linspace(0, 1, 24):
            l = a + (b - a) * f
            hw = PATIO_HW0 + (PATIO_HW1 - PATIO_HW0) * f
            p, d, n = self.at(l)
            pts_l.append(p + n * hw)
            pts_r.append(p - n * hw)
        poly = Polygon(np.vstack([pts_r, pts_l[::-1]])).buffer(0)
        self.patio = poly.buffer(-PATIO_ROUND).buffer(2 * PATIO_ROUND)\
                         .buffer(-PATIO_ROUND)
        self.patio_area = self.patio.area
        self.patio_l0, self.patio_l1 = a, b

    # -- solve L for a net tabled area --------------------------------------
    def solve(self, net_area, extra_hw=0.0):
        lo, hi = 20.0, self.length - TIP_SETBACK - 1
        for _ in range(70):
            mid = (lo + hi) / 2
            a = self.outline(mid, extra_hw).difference(self.patio).area
            if a < net_area:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def solve_hw(self, net_area, L):
        """Widen a fixed-length plate to a target net area (podium floors)."""
        lo, hi = -4.0, 30.0
        for _ in range(70):
            mid = (lo + hi) / 2
            a = self.outline(L, mid).difference(self.patio).area
            if a < net_area:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2


if __name__ == "__main__":
    f = Family()
    print(f"zone {f.zone.area:,.0f} m2, spine {f.length:.0f} m")
    print(f"patio {f.patio_area:.0f} m2 at l = {f.patio_l0:.0f}..{f.patio_l1:.0f}")
    for a in (1820, 2150, 2370, 2640):
        L = f.solve(a)
        o = f.outline(L)
        print(f"  net {a:>5} -> L {L:6.1f} m  gross {o.area:7.0f}  "
              f"width NW {2*(TIP_HALFWIDTH+TAPER*L):.1f} m  "
              f"net check {o.difference(f.patio).area:7.1f}")
