"""Step 3: download the PNOA orthophoto for BOX from the IGN WMS as a GeoTIFF in EPSG:4083.

Skips the download if the file already exists (data/ is write-once).
"""
import sys
import urllib.parse
import urllib.request

import rasterio

from config import BOX, CRS, ORTHO_FILE, ORTHO_GSD, ORTHO_LAYER, ORTHO_WMS


def main():
    if ORTHO_FILE.exists():
        print(f"exists, not re-downloading: {ORTHO_FILE.name}")
        return
    xmin, ymin, xmax, ymax = BOX
    w = round((xmax - xmin) / ORTHO_GSD)
    h = round((ymax - ymin) / ORTHO_GSD)
    if max(w, h) > 4096:
        sys.exit(f"{w}x{h} exceeds the WMS 4096 px limit; tile the request")
    q = dict(SERVICE="WMS", VERSION="1.3.0", REQUEST="GetMap", LAYERS=ORTHO_LAYER,
             STYLES="", CRS=CRS, BBOX=f"{xmin},{ymin},{xmax},{ymax}",
             WIDTH=w, HEIGHT=h, FORMAT="image/tiff")
    url = ORTHO_WMS + "?" + urllib.parse.urlencode(q)
    ORTHO_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ORTHO_FILE.with_suffix(".part")
    with urllib.request.urlopen(url, timeout=300) as r, open(tmp, "wb") as f:
        ctype = r.headers.get("Content-Type", "")
        if "tiff" not in ctype:
            sys.exit(f"unexpected response {ctype}: {r.read(500)!r}")
        f.write(r.read())
    tmp.rename(ORTHO_FILE)
    with rasterio.open(ORTHO_FILE) as ds:
        print(ORTHO_FILE.name, ds.width, ds.height, ds.count, ds.crs, ds.res, ds.bounds)


if __name__ == "__main__":
    main()
