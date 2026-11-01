# NOTES – running log

Newest entries at the bottom of each section. A new session should read this file first, then `SOURCES.md`.

## Decisions from the owner (2026-11-01)

- BeamNG.drive: latest Steam release. Kart mod: owner has none; chose **Backyard Kart** by nachtstiel (most downloaded kart on the official beamng.com repository, ~714k downloads at last check, has race configs). Realistic alternative if Backyard Kart's handling is too toy-like: **Autobello Formula Kart Classic**.
- Junior layout (865 m): yes, as a second layout after Senior.
- Use: personal, not a public release. Attribution still goes in the readme; no club name/logo in models.
- Brief otherwise as written; Claude has latitude on method.

## Environment

- Build runs in a Claude Code cloud container (Linux), not on the owner's Windows PC. Files are handed over; PiBoSo tools (Windows) are run by the owner or a local session.
- Repo: github.com/dalistarh/karting. The container is ephemeral, so every step is committed and pushed.
- Python 3.11 venv in `.venv` (`make setup`), Blender 4.5 LTS as the `bpy` 4.5.15 PyPI module (headless, no system install).
- Network policy (after owner allow-listed hosts): `www.ign.es`, `pnoa.ign.es`, `documentation.beamng.com`, PyPI and GitHub work. `overpass-api.de`, `centrodedescargas.cnig.es` and `servicios.idee.es` are allowed by policy but the connection is reset right after the TLS handshake starts (3/3 retries, 2026-11-01), so the remote side or the egress path refuses them. Workaround: orthophoto via IGN WMS on `www.ign.es`; LiDAR and MDT fetched by hand.

## Log

- Step 1: repo scaffold, `.venv` with numpy, scipy, laspy+lazrs, pyproj, shapely, rasterio, matplotlib, pillow, bpy 4.5.15.
- Step 2: Overpass unreachable; OSM outline skipped (optional per brief, first guess only). Located the circuit directly on the PNOA orthophoto instead.
- Step 2: GeoNames point (28.94794 N, 13.62422 W) = EPSG:4083 634074.9 E, 3202997.0 N falls inside the complex, ~35 m east of its centre. Confirmed the outline on a 1.5 km, 1 m/px PNOA overview; the "1 km away" link is the wrong one.
- Step 3: orthophoto at the site is PNOA flight 2024-04, GSD 0.20 m (WMS GetFeatureInfo on `OI.MosaicElement`). Downloaded the 600 × 600 m box (633740–634340 E, 3202715–3203315 N) as a 3000 × 3000 GeoTIFF in EPSG:4083 (CRS confirmed in the file's metadata).
- Site reading from the orthophoto: the complex is ~505 × 245 m, long axis roughly ENE. West half: track with red/white kerbs, painted grid boxes on the north straight next to grandstand and pit building → competition (Senior) track. East half: separate fenced track with red/white kerbs → probably Junior. North-east corner: small oval (kids) and a tight RC track. Infield is red gravel/ground with green artificial-grass strips along the edges. Hatched connector lanes inside the west track suggest alternative configurations.

## Open issues

- LiDAR and MDT files must be downloaded by hand (see SOURCES.md "Pending").
- Which configuration is the 1,281 m Senior layout must be settled by measuring candidates against 1,281 m and 865 m.
- Driving direction to be confirmed (grid boxes, kerb placement, pit entry/exit geometry).
