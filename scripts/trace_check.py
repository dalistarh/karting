"""Step 5 check images and edge-accuracy numbers.

  track/trace_check.png          Senior + Junior over the orthophoto: edges, centreline, S/F,
                                 direction arrows, 100 m marks, interpolated spans in orange
  track/trace_check_senior_b.png the combined Senior candidate, same style
  track/edge_check_<layout>.png  20 evenly spaced 14 x 14 m chips at native 0.2 m/px, 3x zoom
  track/edge_check_<layout>.csv  per chip: offset from the traced edge to a colour change-point
                                 edge found from raw RGB only (independent of the class mask)
"""
import json

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

from config import ORTHO_FILE, TRACK

COL = {"senior": dict(l=(0, 255, 255), r=(255, 0, 255), c=(255, 255, 0)),
       "junior": dict(l=(80, 255, 80), r=(255, 140, 0), c=(255, 255, 255)),
       "senior_b": dict(l=(0, 255, 255), r=(255, 0, 255), c=(255, 255, 0))}
LABEL = {"senior": "Senior (West loop)", "junior": "Junior (East loop, clockwise assumed)",
         "senior_b": "Senior candidate B (West + East left snake via both crossings)"}


def load(name):
    a = np.loadtxt(TRACK / f"{name}_trace_4083.csv", delimiter=",", skiprows=1)
    return dict(s=a[:, 0], c=a[:, 1:3], l=a[:, 3:5], r=a[:, 5:7], w=a[:, 7],
                bl=a[:, 8] > 0, br=a[:, 9] > 0)


def font(sz):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def overview(rgb, T, layouts, stats, out, edge_legend):
    # crop to the complex, 0.2 m/px
    xa, xb, ya, yb = 633790.0, 634300.0, 3202880.0, 3203150.0
    c0, c1 = int((xa - T.c) / T.a), int((xb - T.c) / T.a)
    r0, r1 = int((T.f - yb) / -T.e), int((T.f - ya) / -T.e)
    im = Image.fromarray(rgb[r0:r1, c0:c1]).convert("RGB")
    im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.25)
    d = ImageDraw.Draw(im)

    def px(P):
        return [((x - T.c) / T.a - c0, (T.f - y) / -T.e - r0) for x, y in P]
    f = font(18)
    for name, t in layouts.items():
        k = COL[name]
        for key, flag, col in (("l", "bl", k["l"]), ("r", "br", k["r"])):
            pts = px(t[key])
            n = len(pts)
            for i in range(n):
                j = (i + 1) % n
                bad = t[flag][i] or t[flag][j]
                d.line([pts[i], pts[j]], fill=(255, 120, 0) if bad else col, width=3 if bad else 2)
        cp = px(t["c"])
        for i in range(0, len(cp), 2):
            d.line([cp[i], cp[(i + 1) % len(cp)]], fill=k["c"], width=1)
        # 100 m marks and direction arrows
        for s in range(0, int(t["s"][-1]) + 1, 50):
            i = int(np.argmin(abs(t["s"] - s)))
            p, q = np.array(cp[i]), np.array(cp[(i + 3) % len(cp)])
            v = (q - p) / (np.hypot(*(q - p)) + 1e-9)
            nrm = np.array([-v[1], v[0]])
            tip = p + v * 14
            d.polygon([tuple(tip), tuple(p + nrm * 7), tuple(p - nrm * 7)], fill=k["c"])
            if s % 100 == 0:
                d.text((p[0] + 8, p[1] - 22), f"{s}", fill=k["c"], font=f, stroke_width=2,
                       stroke_fill=(0, 0, 0))
    # S/F line
    sen = next(t for n, t in layouts.items() if n.startswith("senior"))
    a, b = px([sen["l"][0], sen["r"][0]])
    d.line([a, b], fill=(255, 255, 255), width=5)
    d.line([a, b], fill=(0, 0, 0), width=2)
    d.text((a[0] - 30, a[1] - 46), "S/F (origin)", fill=(255, 255, 255), font=f, stroke_width=2,
           stroke_fill=(0, 0, 0))
    # legend
    lines = []
    for name in layouts:
        st = stats[name]
        wm = st["width_measured"]
        lines.append(f"{LABEL[name]}: centreline {st['centreline_m']:.1f} m vs {st['nominal_m']:.0f} m "
                     f"({st['diff_pct']:+.1f}%), width min/mean/max {wm['min']:.1f}/{wm['mean']:.1f}/{wm['max']:.1f} m")
    lines.append(edge_legend)
    lines.append("Orthophoto: Obra derivada de PNOA 2024 CC-BY 4.0 scne.es  |  grid 0.2 m/px, north up")
    pad = 8
    h = len(lines) * 24 + pad * 2
    canvas = Image.new("RGB", (im.width, im.height + h), (20, 20, 20))
    canvas.paste(im, (0, 0))
    dc = ImageDraw.Draw(canvas)
    for i, s in enumerate(lines):
        dc.text((pad, im.height + pad + i * 24), s, fill=(235, 235, 235), font=font(17))
    # 50 m scale bar
    y = im.height - 30
    dc.rectangle([20, y, 20 + 250, y + 8], fill=(255, 255, 255))
    dc.text((20, y - 24), "50 m", fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
    canvas.save(TRACK / out, optimize=True)


def visible_edge(rgbf, T, c, e):
    """Independent edge estimate along the ray centre->traced edge, from raw colours only.

    Single change-point split of the RGB profile from 3 m inside to 1.5 m outside the traced
    edge: the split that minimises the summed within-segment colour variance. Asphalt is
    uniform, the outside (paint, kerb, grass, gravel) is not, so the split lands on the
    asphalt boundary. Returns the signed offset (m) from the traced edge (negative = inside).
    """
    v = e - c
    de = np.hypot(*v)
    u = v / de
    ts = np.arange(max(0.3, de - 3.0), de + 1.5, 0.05)
    xs, ys = c[0] + u[0] * ts, c[1] + u[1] * ts
    cc = (xs - T.c) / T.a - 0.5
    rr = (T.f - ys) / -T.e - 0.5
    prof = np.stack([ndi.map_coordinates(rgbf[..., k], [rr, cc], order=1) for k in range(3)], 1)
    n = len(ts)
    cs, cs2 = np.cumsum(prof, 0), np.cumsum(prof ** 2, 0)
    best, bj = np.inf, None
    for j in range(4, n - 4):                      # each segment at least 0.2 m
        a1, a2 = cs[j - 1], cs2[j - 1]
        b1, b2 = cs[-1] - a1, cs2[-1] - a2
        sse = (a2 - a1 ** 2 / j).sum() + (b2 - b1 ** 2 / (n - j)).sum()
        if sse < best:
            best, bj = sse, j
    return float(ts[bj] - de), np.array([xs[bj], ys[bj]])


def edge_chips(rgb, T, name, t, n=20, half=7.0, zoom=3):
    rgbf = rgb.astype(np.float32)
    N = len(t["s"])
    idx = [int(round(i * N / n)) % N for i in range(n)]
    tiles, rows = [], []
    f = font(15)
    for k, i in enumerate(idx):
        c = t["c"][i]
        cx, cy = (c[0] - T.c) / T.a, (T.f - c[1]) / -T.e
        h = int(half / T.a)
        x0, y0 = int(cx) - h, int(cy) - h
        chip = Image.fromarray(rgb[y0:y0 + 2 * h, x0:x0 + 2 * h]).resize((2 * h * zoom, 2 * h * zoom),
                                                                       Image.NEAREST)
        d = ImageDraw.Draw(chip)

        def p(P):
            return (((P[0] - T.c) / T.a - x0) * zoom, ((T.f - P[1]) / -T.e - y0) * zoom)
        rec = [k + 1, round(float(t["s"][i]), 1)]
        for key in ("l", "r"):
            e = t[key][i]
            v = e - c
            u = v / (np.hypot(*v) + 1e-9)
            off, vis = visible_edge(rgbf, T, c, e)
            rec.append(round(off, 2))
            # draw traced edge with a 0.5 m tolerance bar across it (along the normal)
            a, b = p(e - u * 0.5), p(e + u * 0.5)
            d.line([a, b], fill=(255, 255, 0), width=3)
            q = p(e)
            d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=(255, 0, 0), width=2)
            gpt = p(vis)
            d.ellipse([gpt[0] - 3, gpt[1] - 3, gpt[0] + 3, gpt[1] + 3], fill=(0, 255, 255))
        cp = p(c)
        d.line([p(t["l"][i]), p(t["r"][i])], fill=(255, 255, 255), width=1)
        d.ellipse([cp[0] - 3, cp[1] - 3, cp[0] + 3, cp[1] + 3], fill=(255, 255, 255))
        interp = bool(t["bl"][i] or t["br"][i])
        rec.append(int(interp))
        d.text((6, 4), f"#{k + 1}  s={t['s'][i]:.0f} m{'  (interp)' if interp else ''}",
               fill=(255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0))
        d.text((6, chip.height - 22), f"L {rec[2]:+.2f}  R {rec[3]:+.2f} m", fill=(255, 255, 255),
               font=f, stroke_width=2, stroke_fill=(0, 0, 0))
        tiles.append(chip)
        rows.append(rec)
    cols = 5
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * tw, ((n + cols - 1) // cols) * th + 40), (20, 20, 20))
    for k, tile in enumerate(tiles):
        sheet.paste(tile, ((k % cols) * tw, (k // cols) * th))
    ImageDraw.Draw(sheet).text(
        (8, sheet.height - 32),
        f"{name.title()}: red ring = traced edge, yellow bar = +-0.5 m, cyan dot = colour change-point edge "
        f"(independent of the class mask). Chips 14 x 14 m, 0.2 m/px.", fill=(235, 235, 235), font=font(16))
    sheet.save(TRACK / f"edge_check_{name}.png", optimize=True)
    with open(TRACK / f"edge_check_{name}.csv", "w") as fh:
        fh.write("point,s_m,left_offset_m,right_offset_m,interpolated\n")
        for r in rows:
            fh.write(",".join(str(v) for v in r) + "\n")
    offs = np.abs(np.array([r[2:4] for r in rows], float))
    return offs


def main():
    with rasterio.open(ORTHO_FILE) as ds:
        rgb = ds.read().transpose(1, 2, 0)
        T = ds.transform
    st = json.loads((TRACK / "trace_stats.json").read_text())
    layouts = {n: load(n) for n in st["layouts"]}
    overview(rgb, T, {n: layouts[n] for n in ("senior", "junior")}, st["layouts"], "trace_check.png",
             "Senior edges cyan (left) / magenta (right); Junior edges green (left) / orange (right); "
             "bright orange = interpolated across a junction")
    overview(rgb, T, {"senior_b": layouts["senior_b"]}, st["layouts"], "trace_check_senior_b.png",
             "Edges cyan (left) / magenta (right); bright orange = interpolated across a junction "
             "(incl. both tyre-barred crossings)")
    for name, t in layouts.items():
        offs = edge_chips(rgb, T, name, t)
        print(f"{name}: 20-point edge check, |offset| to colour change-point edge: "
              f"max {offs.max():.2f} m, mean {offs.mean():.2f} m, within 0.5 m: {(offs <= 0.5).sum()}/{offs.size}")


if __name__ == "__main__":
    main()
