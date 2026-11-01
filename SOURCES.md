# Sources and licences

Every file in `data/` is listed here. Files in `data/` are written once by a fetch script (or by hand where noted) and never modified; everything derived lives in `build/`, `track/`, `blender/`, `beamng/` or `krp/`.

## Attribution text (copy into any shipped readme)

```
Obra derivada de PNOA 2024 CC-BY 4.0 scne.es
```

Wording follows clause 4 of the IGN licence ("Obra derivada de <identificador del producto> <fecha> CC-BY 4.0 <atribución de productores>"); the licence's own PNOA example is "Obra derivada de PNOA 2010-2013 CC-BY scne.es". Clause 5 also asks for the same text in the metadata (abstract, lineage, access constraints) of any derived dataset, so it goes into the BeamNG `info.json` description and the KRP track info too. Lines for the LiDAR and MDT products will be added when those files arrive.

Licence document: https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf

## Files

| File | Product | Producer | Licence | How obtained | Notes |
|---|---|---|---|---|---|
| `data/pnoa_ma_2024-04_0p20m_box600.tif` | PNOA orthophoto (PNOA-MA mosaic), Lanzarote flight 2024-04, GSD 0.20 m | IGN / CNIG, Sistema Cartográfico Nacional (scne.es) | CC BY 4.0 | `scripts/fetch_ortho.py`: WMS GetMap from `https://www.ign.es/wms-inspire/pnoa-ma`, layer `OI.OrthoimageCoverage`, EPSG:4083, bbox 633740,3202715,634340,3203315, 3000×3000 px, GeoTIFF | Flight date and GSD read from the WMS `OI.MosaicElement` GetFeatureInfo at the circuit (FECHA 2024-04, RESOLUCION 0.20, not true-ortho). Redistributable with attribution. |

## Pending

| Needed for | Product | Status |
|---|---|---|
| Step 6, track elevation | PNOA-LiDAR ground-classified LAZ, newest coverage | CNIG download centre unreachable from the build container (connection reset); to be fetched by hand |
| Step 8, terrain | MDT02 (or MDT05) | CNIG download centre / IDEE WCS unreachable from the build container; to be fetched by hand |
| Step 2, first-guess outline | OpenStreetMap (`highway=raceway`, `sport=karting`), ODbL, "© OpenStreetMap contributors" | Overpass unreachable from the build container; optional |

## Not used / not shipped

- GRAFCAN / IDECanarias imagery: not downloaded. Cross-check only if ever needed; never shipped.
- Google Maps / Earth / Street View and other commercial imagery: not used.
