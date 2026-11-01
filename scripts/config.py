"""Shared constants for the Lanzarote karting build. Every script imports from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"      # raw downloads only - never modified after download
BUILD = ROOT / "build"    # regenerated intermediates (gitignored)
TRACK = ROOT / "track"    # derived track geometry (committed)

CRS = "EPSG:4083"         # REGCAN95 / UTM zone 28N (Canary Islands)

# GeoNames point for the club (28.94794 N, 13.62422 W) -> EPSG:4083
GEONAMES_XY = (634074.9, 3202997.0)

# 600 x 600 m working box around the complex, EPSG:4083 (xmin, ymin, xmax, ymax).
# Chosen from the 1 m/px overview: the complex spans ~633785-634290 E, 3202892-3203137 N.
BOX = (633740.0, 3202715.0, 634340.0, 3203315.0)

# PNOA orthophoto via IGN WMS (CC BY 4.0). Mosaic at the site: flight 2024-04, GSD 0.20 m.
ORTHO_WMS = "https://www.ign.es/wms-inspire/pnoa-ma"
ORTHO_LAYER = "OI.OrthoimageCoverage"
ORTHO_GSD = 0.20
ORTHO_FILE = DATA / "pnoa_ma_2024-04_0p20m_box600.tif"
