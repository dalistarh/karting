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

- Step 4 (`scripts/prepare.py`): orthophoto already EPSG:4083 and exactly BOX (checked in code). Writes `build/classes.tif`: asphalt = blue-grey, low saturation, V 25–125 (3×3 median); white paint = V ≥ 150, saturation < 0.2. The local origin is set in step 5 because it depends on the detected S/F line.
- Step 5 method (`scripts/trace.py`): a skeleton of the asphalt mask gave the network graph (probe, not in the pipeline); ordered waypoints every ~12 m were seeded from it and saved as `track/waypoints_*.csv` (EPSG:4083), and these are the hand-maintained input. Least-cost route through the waypoints (cost falls with distance to the asphalt edge), then 4 rounds of: rays every 1 m along both normals to the first non-asphalt run ≥ 0.5 m (thin edge line included, grid boxes/marks skipped), 7 m median on offsets, junction spans (offset > 1.25 × median half-width + 0.8 m, or no edge within 12 m) filled by interpolation and flagged, re-centre on the midpoint, smooth. Final centreline = midpoint of the final edges, resampled at 1 m.
- Step 5, S/F and direction: painted line across the main straight in front of the control building, 98% white across the section; centre = local origin, EPSG:4083 633996.941 E, 3203023.233 N (`track/origin.json`). Local axes are grid-aligned (not rotated). Direction ENE on the main straight (heading 10.4° from east), so turn 1 is a right-hander: grid boxes are painted behind (west of) the line and an arrow in the pit lane points east.
- Step 5, measured (centreline, `track/trace_stats.json`):
  - Senior = West loop (closed, kerbed loop with the grid): **1,101.2 m vs 1,281 m (−14.0%)**. Left edge 1,131.3 m, right edge 1,074.4 m. Width min/mean/max 7.11 / 8.22 / 10.06 m (5th–95th percentile 7.6–9.7 m); widest on the S/F straight (9.9 m at the line). The 10 m guide figure is the maximum, not typical.
  - Junior = East loop, assumed clockwise: **703.1 m vs 865 m (−18.7%)**. Width 6.90 / 7.78 / 9.39 m.
  - Candidate Senior B = West main straight → straight on past the small east pit shelter into the east track → east track's left snake (southwards) → mid service crossing → rest of the West loop: **1,309.2 m (+2.2%)**. Both crossings are barred by tyre stacks in the 2024-04 photo; the mid crossing is lighter paving (concrete?), ~10 m wide.
  - Every closed loop in the asphalt graph was enumerated: none other is near 1,281 m or 865 m. Combinations through the crossings give ~314, ~590, ~1,309 and ~1,576 m.
- Step 5, checks on the length gap: (a) scale: car-park bays repeat every 12.5 px = 2.5 m; (b) georeferencing: re-rendered the same area from the WMS in EPSG:4326 and projected the trace onto it, giving 98–100% asphalt 1 m inside the edges and 4–14% 1 m outside. A 14% scale error is ruled out. The skeleton's 1,175 m for the West loop was inflated ~6% by 8-connected pixel steps.
- Step 5, edge accuracy, 20 evenly spaced stations × 2 sides (`track/edge_check_*.png/.csv`). The independent edge is a colour change-point on raw RGB, not the class mask. Senior 34/40 within 0.5 m (mean |offset| 0.33 m, max 1.15 m); Junior 38/40 (mean 0.24 m, max 0.85 m); Senior B 35/40. Senior misses inspected visually: #1 (ray lies along the S/F paint), #7 (grey footpath beyond the edge line fools the check; the trace is on the line), #20 (pit-lane divider), #3 (−0.65 m at a kerb), #4 and #11 (interpolated junction spans at the hatched run-off, where the edge is genuinely ambiguous).
- Published lengths: lanzarote.com gives Senior 1,281 m and Junior 865 m; other guides give 2,346 m (Ocio Lanzarote), "about 2,500 m" (Barceló), "over 1,200 m" (Yumping) and 1.5 km (a rental listing). The venue hosted a 2004 World Championship (a guide's claim), which fits a combined layout. No public track map was found.

## Open issues

- **Owner decision (step 5 checkpoint):** which geometry is "Senior": the West loop as photographed (1,101 m, −14%) or candidate B through the two crossings (1,309 m, +2.2%)? And what is the 865 m Junior? No loop matches it; the East loop is 703 m.
- East-loop direction: clockwise assumed. If candidate B is right, the east track runs counter-clockwise (B uses its left snake southwards).
- LiDAR and MDT files must be downloaded by hand (see SOURCES.md "Pending").
- `centerline.csv` z column is 0 until step 6.
- The repo is public. That's fine for CC BY data with attribution, but the owner said personal use, so switch the repo to private if preferred.
