"""Step 5: trace asphalt edges and the centreline of each layout from the orthophoto.

Inputs
  build/classes.tif             surface classes from prepare.py (0 other, 1 asphalt, 2 white)
  track/waypoints_<layout>.csv  ordered control points (EPSG:4083) in driving direction;
                                seeded from a skeleton of the asphalt mask, checked by eye
Outputs (per layout)
  track/<layout>_trace_4083.csv  s, centre, left/right edge (EPSG:4083), width, flags
  track/centerline.csv           Senior: x, y, z, width per metre, local coords (z filled in step 6)
  track/centerline_junior.csv    Junior, same local system
  track/origin.json              local origin = centre of the Senior S/F line
  track/trace_stats.json         lengths and widths
Check images are made by scripts/trace_check.py.
"""
import json

import numpy as np
import rasterio
from scipy import ndimage as ndi
from skimage import morphology
from skimage.graph import MCP_Geometric

from config import BUILD, TRACK

LAYOUTS = {
    # West loop: the closed, kerbed loop with grid and S/F line as photographed (2024-04)
    "senior": dict(nominal=1281.0, sf_approx=(633997.1, 3203023.3)),
    # East loop, assumed clockwise (direction unconfirmed)
    "junior": dict(nominal=865.0, sf_approx=None),
    # Candidate: West main straight -> straight on into the east track -> east left snake
    # -> mid service crossing -> rest of the West loop. Both crossings are barred by tyres
    # in the 2024 photo; traced to test it against the published 1,281 m.
    "senior_b": dict(nominal=1281.0, sf_approx=(633997.1, 3203023.3)),
}
STEP = 0.1          # ray sampling step (m)
RAY_MAX = 12.0      # max half-width searched (m)
MARK_MAX = 0.5      # non-asphalt runs shorter than this, followed by asphalt, are paint marks
LINE_MAX = 0.45     # a white run up to this wide, followed by non-asphalt, is the edge line


class Raster:
    def __init__(self, path):
        with rasterio.open(path) as ds:
            self.a = ds.read(1)
            self.t = ds.transform
        self.g = self.t.a
        self.x0, self.y1 = self.t.c, self.t.f

    def rc(self, x, y):
        col = np.floor((np.asarray(x) - self.x0) / self.g).astype(int)
        row = np.floor((self.y1 - np.asarray(y)) / self.g).astype(int)
        return row, col

    def xy(self, row, col):
        return self.x0 + (np.asarray(col) + 0.5) * self.g, self.y1 - (np.asarray(row) + 0.5) * self.g

    def sample(self, x, y):
        r, c = self.rc(x, y)
        ok = (r >= 0) & (r < self.a.shape[0]) & (c >= 0) & (c < self.a.shape[1])
        out = np.zeros(r.shape, self.a.dtype)
        out[ok] = self.a[r[ok], c[ok]]
        return out


def route(R, wps):
    """Least-cost path through the waypoints (closed loop), staying central on asphalt."""
    surf = R.a > 0
    surf = morphology.binary_closing(surf & (R.a == 1) | surf, morphology.disk(2))
    surf = morphology.binary_opening(surf, morphology.disk(4))
    dt = ndi.distance_transform_edt(surf)
    cost = np.where(surf, 1.0 + 30.0 / (1.0 + dt), 200.0)
    rows, cols = R.rc(wps[:, 0], wps[:, 1])
    pts = []
    n = len(wps)
    for i in range(n):
        r0, c0, r1, c1 = rows[i], cols[i], rows[(i + 1) % n], cols[(i + 1) % n]
        m = 150
        ra, rb = max(min(r0, r1) - m, 0), min(max(r0, r1) + m, cost.shape[0])
        ca, cb = max(min(c0, c1) - m, 0), min(max(c0, c1) + m, cost.shape[1])
        mcp = MCP_Geometric(cost[ra:rb, ca:cb])
        mcp.find_costs([(r0 - ra, c0 - ca)], [(r1 - ra, c1 - ca)])
        p = np.array(mcp.traceback((r1 - ra, c1 - ca))) + [ra, ca]
        pts.append(p[:-1])
    p = np.vstack(pts)
    return np.c_[R.xy(p[:, 0], p[:, 1])]


def resample_closed(P, step=1.0):
    Q = np.vstack([P, P[:1]])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(Q, axis=0).T))]
    L = d[-1]
    n = int(round(L / step))
    s = np.linspace(0, L, n, endpoint=False)
    return np.c_[np.interp(s, d, Q[:, 0]), np.interp(s, d, Q[:, 1])], L


def smooth_closed(P, sigma):
    return np.c_[ndi.gaussian_filter1d(P[:, 0], sigma, mode="wrap"),
                 ndi.gaussian_filter1d(P[:, 1], sigma, mode="wrap")]


def normals(P):
    t = np.roll(P, -1, 0) - np.roll(P, 1, 0)
    t /= np.hypot(*t.T)[:, None]
    return t, np.c_[-t[:, 1], t[:, 0]]          # tangent, left normal


def edge_distance(cls):
    """Distance along a ray to the asphalt edge, from a 1-D class profile; NaN if none."""
    n = len(cls)
    j = 0
    while j < n:
        if cls[j] == 1:
            j += 1
            continue
        k = j
        while k < n and cls[k] != 1:
            k += 1
        run = (k - j) * STEP
        if k < n and run < MARK_MAX:             # paint mark / grid box on the asphalt
            j = k
            continue
        w = 0
        while j + w < n and cls[j + w] == 2:
            w += 1
        if 0 < w * STEP <= LINE_MAX and w < k - j:   # edge line, then kerb/grass: include line
            return (j + w) * STEP
        return j * STEP
    return np.nan


def find_edges(R, P):
    t, nl = normals(P)
    d = np.arange(0, RAY_MAX + STEP / 2, STEP)
    out = {}
    for side, sgn in (("left", 1), ("right", -1)):
        xs = P[:, 0, None] + sgn * nl[:, 0, None] * d[None, :]
        ys = P[:, 1, None] + sgn * nl[:, 1, None] * d[None, :]
        cls = R.sample(xs, ys)
        out[side] = np.array([edge_distance(c) for c in cls])
    return out["left"], out["right"], nl


def clean(dist, ref_half):
    """Flag junction/obstruction samples and fill them by circular interpolation."""
    n = len(dist)
    med = ndi.median_filter(np.nan_to_num(dist, nan=RAY_MAX), size=25, mode="wrap")
    cap = np.minimum(med, ref_half * 1.25) + 0.8
    bad = np.isnan(dist) | (dist > cap) | (dist < 0.5 * ref_half)
    bad = ndi.binary_dilation(bad, iterations=2)
    good = np.flatnonzero(~bad)
    filled = dist.copy()
    if len(good) and bad.any():
        xi = np.r_[good - n, good, good + n]
        filled[bad] = np.interp(np.flatnonzero(bad), xi, np.tile(dist[good], 3))
    return filled, bad


def measure(R, P):
    """Edge offsets at each centreline sample: raw rays -> 7 m median (removes grid boxes and
    other short paint marks) -> junction cleanup -> ~1 m Gaussian (no pixel steps)."""
    dl, dr, nl = find_edges(R, P)
    ref = np.nanmedian(np.r_[dl, dr])
    out = []
    for d in (dl, dr):
        dm = ndi.median_filter(np.nan_to_num(d, nan=RAY_MAX), size=7, mode="wrap")
        dm[np.isnan(d) & (ndi.uniform_filter1d(np.isnan(d).astype(float), 7, mode="wrap") > 0.5)] = np.nan
        f, bad = clean(dm, ref)
        out += [ndi.gaussian_filter1d(f, 1.0, mode="wrap"), bad]
    dl_f, bad_l, dr_f, bad_r = out
    return dl_f, dr_f, bad_l, bad_r, nl


def recentre(R, P):
    """Replace the centreline by the exact midpoint of the measured edges, resampled at 1 m."""
    dl, dr, bad_l, bad_r, nl = measure(R, P)
    P = P + nl * ((dl - dr) / 2)[:, None]
    P = smooth_closed(P, 1.0)
    return resample_closed(P)


def trace(R, wps):
    P = route(R, wps)
    P, _ = resample_closed(P)
    P = smooth_closed(P, 3.0)
    for it in range(4):
        P, L = resample_closed(P)
        dl, dr, bad_l, bad_r, nl = measure(R, P)
        P = P + nl * ((dl - dr) / 2)[:, None]
        P = smooth_closed(P, 2.0)
    P, L = resample_closed(P)
    for it in range(2):
        P, L = recentre(R, P)
    dl, dr, bad_l, bad_r, nl = measure(R, P)
    return P, L, dl, dr, bad_l, bad_r, nl


def find_sf(R, P, dl, dr, nl, approx, search=10.0):
    """Station whose cross-section is whitest (painted S/F line) near the approximate point."""
    dist = np.hypot(P[:, 0] - approx[0], P[:, 1] - approx[1])
    i0 = int(np.argmin(dist))
    if dist[i0] > search:
        raise SystemExit(f"S/F approx point is {dist[i0]:.1f} m from the centreline")
    best, best_i, best_off = -1, i0, 0.0
    t, _ = normals(P)
    for di in range(-int(search), int(search) + 1):
        i = (i0 + di) % len(P)
        for off in np.arange(-0.6, 0.61, 0.1):        # sub-metre along-track search
            c = P[i] + t[i] * off
            u = np.linspace(-dr[i] + 0.3, dl[i] - 0.3, 60)
            xs, ys = c[0] + nl[i, 0] * u, c[1] + nl[i, 1] * u
            score = np.mean(R.sample(xs, ys) == 2)
            if score > best:
                best, best_i, best_off = score, i, off
    return best_i, best_off, best


def write_csv(path, header, rows, fmt):
    with open(path, "w") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(",".join(fmt % v for v in r) + "\n")


def main():
    R = Raster(BUILD / "classes.tif")
    stats, origin = {}, None
    results = {}
    for name in LAYOUTS:
        cfg = LAYOUTS[name]
        wps = np.loadtxt(TRACK / f"waypoints_{name}.csv", delimiter=",", skiprows=1)
        P, L, dl, dr, bad_l, bad_r, nl = trace(R, wps)
        if cfg["sf_approx"] is not None:
            i, off, score = find_sf(R, P, dl, dr, nl, cfg["sf_approx"])
            t, _ = normals(P)
            sf = P[i] + t[i] * off
            # restart the loop exactly at the S/F line
            P2 = np.vstack([sf, np.roll(P, -(i + 1), 0)])
            P, L = resample_closed(P2)
            dl, dr, bad_l, bad_r, nl = measure(R, P)
            if name == "senior":
                origin = dict(crs="EPSG:4083", x=round(float(sf[0]), 3), y=round(float(sf[1]), 3),
                              sf_whiteness=round(float(score), 3),
                              heading_deg=round(float(np.degrees(np.arctan2(*(P[1] - P[0])[::-1]))), 2),
                              note="local x = E - x, local y = N - y, z up; axes not rotated")
        results[name] = (P, L, dl, dr, bad_l, bad_r, nl)

    TRACK.mkdir(exist_ok=True)
    (TRACK / "origin.json").write_text(json.dumps(origin, indent=2) + "\n")
    ox, oy = origin["x"], origin["y"]
    for name, (P, L, dl, dr, bad_l, bad_r, nl) in results.items():
        left = P + nl * dl[:, None]
        right = P - nl * dr[:, None]
        w = dl + dr
        s = np.arange(len(P)) * (L / len(P))
        rows = np.c_[s, P, left, right, w, bad_l, bad_r]
        write_csv(TRACK / f"{name}_trace_4083.csv",
                  "s_m,cx,cy,lx,ly,rx,ry,width_m,left_interp,right_interp", rows,
                  "%.3f")
        loc = np.c_[P[:, 0] - ox, P[:, 1] - oy, np.zeros(len(P)), w]
        fn = "centerline.csv" if name == "senior" else f"centerline_{name}.csv"
        write_csv(TRACK / fn, "x,y,z,width", loc, "%.3f")
        meas = ~(bad_l | bad_r)
        ll = np.sum(np.hypot(*np.diff(np.vstack([left, left[:1]]), axis=0).T))
        rl = np.sum(np.hypot(*np.diff(np.vstack([right, right[:1]]), axis=0).T))
        stats[name] = dict(
            centreline_m=round(float(L), 1), nominal_m=LAYOUTS[name]["nominal"],
            diff_pct=round(float((L / LAYOUTS[name]["nominal"] - 1) * 100), 2),
            left_edge_m=round(float(ll), 1), right_edge_m=round(float(rl), 1),
            width_measured=dict(min=round(float(w[meas].min()), 2), mean=round(float(w[meas].mean()), 2),
                                p05=round(float(np.percentile(w[meas], 5)), 2),
                                p95=round(float(np.percentile(w[meas], 95)), 2),
                                max=round(float(w[meas].max()), 2)),
            width_all=dict(min=round(float(w.min()), 2), mean=round(float(w.mean()), 2),
                           max=round(float(w.max()), 2)),
            samples=len(P), interpolated_left=int(bad_l.sum()), interpolated_right=int(bad_r.sum()))
        print(name, json.dumps(stats[name]))
    (TRACK / "trace_stats.json").write_text(json.dumps(dict(origin=origin, layouts=stats), indent=2) + "\n")


if __name__ == "__main__":
    main()
