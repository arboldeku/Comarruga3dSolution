# Datos

## raw/
Descargas originales, **inmutables**. Cada archivo se registra en `raw/MANIFEST.json`:

```json
{ "file": "dem_comarruga.tif", "source": "ICGC (URL exacta)", "downloaded_at": "AAAA-MM-DD", "sha256": "...", "license": "..." }
```

Los archivos pesados (`.tif`, `.zip`) están en `.gitignore`; el manifiesto sí se versiona.

## processed/
Derivados reproducibles con un script a partir de `raw/`. Nada manual.

## Fuentes previstas
- ICGC: modelo de elevaciones (MDT) y LiDAR. Para la demo, el usuario descarga el MDT de ~1 km² de Comarruga y lo coloca en `raw/`.
- Si no hay MDT al empezar: terreno sintético (`engine/synthetic_terrain.py`), etiquetado `dem_source: "sintético"` en todos los resultados y en el visor.
- Meteocat, ACA, SNCZI/MITECO: fase 2.
