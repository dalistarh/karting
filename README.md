# Lanzarote karting circuit – BeamNG.drive / Kart Racing Pro

Driveable recreation of the karting circuit on the LZ-2 (km 7, Tías, Lanzarote), built only from public data (IGN/CNIG, CC BY 4.0). Personal project.

- `data/` – raw source files, never modified (see `SOURCES.md`)
- `scripts/` – pipeline steps; `scripts/config.py` holds shared constants
- `track/` – derived geometry: `centerline.csv`, kerbs, surfaces, check images
- `blender/` – headless Blender build (`build_track.py`)
- `beamng/` – BeamNG level output
- `krp/` – Kart Racing Pro export
- `NOTES.md` – running log of decisions, measurements and open issues

Rebuild:

```bash
make setup
make all
```

Obra derivada de PNOA 2024 CC-BY 4.0 scne.es
