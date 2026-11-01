"""Step 4: check inputs are in EPSG:4083 and cover BOX, then write a surface-class raster.

Output: build/classes.tif (uint8, same grid as the orthophoto)
    0 = other (ground, gravel, grass, kerb red, buildings)
    1 = asphalt (dark blue-grey, low saturation)
    2 = white paint (bright, unsaturated: edge lines, kerb white blocks, marks)

The local origin (start/finish line) is set in step 5, where the S/F line is detected
on the traced centreline; it is written to track/origin.json.
LiDAR and MDT reprojection/clipping is added here once those files are in data/.
"""
import numpy as np
import rasterio
from scipy import ndimage as ndi

from config import BOX, BUILD, CRS, ORTHO_FILE


def classify(rgb):
    r, g, b = rgb.astype(np.float32)
    v = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (v - mn) / (v + 1e-3)
    asph = (b >= r + 2) & (b >= g + 1) & (v > 25) & (v < 125)
    asph = ndi.median_filter(asph.astype(np.uint8), size=3).astype(bool)
    white = (v >= 150) & (sat < 0.20)
    cls = np.zeros(asph.shape, np.uint8)
    cls[asph] = 1
    cls[white] = 2
    return cls


def main():
    with rasterio.open(ORTHO_FILE) as ds:
        if ds.crs.to_string() != CRS:
            raise SystemExit(f"{ORTHO_FILE.name}: CRS {ds.crs} != {CRS}")
        b = ds.bounds
        if (b.left, b.bottom, b.right, b.top) != BOX:
            raise SystemExit(f"{ORTHO_FILE.name}: bounds {b} != BOX {BOX}")
        cls = classify(ds.read())
        prof = ds.profile
    prof.update(count=1, dtype="uint8", compress="deflate", photometric=None)
    BUILD.mkdir(exist_ok=True)
    with rasterio.open(BUILD / "classes.tif", "w", **prof) as out:
        out.write(cls, 1)
    frac = np.bincount(cls.ravel(), minlength=3) / cls.size
    print(f"classes.tif: other {frac[0]:.1%}, asphalt {frac[1]:.1%}, white {frac[2]:.1%}")


if __name__ == "__main__":
    main()
