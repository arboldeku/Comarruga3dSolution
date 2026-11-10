# Contratos de datos

Todos los intercambios entre `engine`, `jev` y `web` usan JSON con estos campos. Si cambias uno, actualiza este archivo.

## 1. Escenario (`scenarios/<id>.json`)

```json
{
  "scenario_id": "rain60_S2",
  "zone_id": "comarruga_demo",
  "rain": { "total_mm": 60, "duration_min": 60, "profile": "constant" },
  "solution_id": "S2",
  "solution_params": {},
  "seed": 42
}
```

`rain.total_mm` equivale a l/m². Perfiles admitidos: `constant`, `triangular`.

## 2. Soluciones candidatas

| id | Nombre | Cómo se modela (simplificado) |
|---|---|---|
| S0 | Situación actual (línea base) | Terreno sin cambios |
| S1 | Ampliar sección del cauce | Rebajar celdas del cauce en `depth_m` y ensancharlas en `width_cells` |
| S2 | Depósito de retención | Sumidero con capacidad `capacity_m3` en celdas dadas, con caudal máximo de vaciado |
| S3 | Pavimento permeable (SUDS) | Aumentar infiltración en la fracción `area_fraction` de celdas urbanas |
| S4 | Elevar bordillos / desviar | Barreras en aristas de celda a altura `height_m` |

Parámetros por defecto en `engine/solutions.py`. Todos son supuestos del modelo, no proyectos reales.

## 3. Resultado del solver (`results/<scenario_id>.json`)

```json
{
  "scenario_id": "rain60_S2",
  "model": { "name": "<librería o solver>", "version": "<x.y.z>", "label": "estimación preliminar, modelo simplificado" },
  "data": { "dem_source": "<fuente o 'sintético'>", "dem_sha256": "<hash>", "resolution_m": 2.0 },
  "grid": { "nx": 0, "ny": 0, "cell_m": 2.0, "origin": [0, 0], "crs": "EPSG:25831" },
  "kpis": {
    "max_depth_cm": 0.0,
    "flooded_area_m2": 0.0,
    "flooded_area_pct": 0.0,
    "volume_m3_total": 0.0,
    "volume_error_pct": 0.0,
    "runtime_s": 0.0
  },
  "depth_file": "results/<scenario_id>_depth.npy",
  "hotspots": [ { "id": "H1", "x": 0, "y": 0, "max_depth_cm": 0.0 } ]
}
```

Invariante: `volume_error_pct` (balance de masa) debe ser < 5 %. Si no, el resultado se marca `invalid`.

## 4. Decisión de Jev (`jev/decisions/<run_id>.jsonl`, una línea por decisión)

```json
{
  "decision_id": "d001",
  "hotspot_id": "H1",
  "rain_mm": 60,
  "primitive": "choice",
  "input": { "slope": 0.0, "catchment_m2": 0, "options": ["S1", "S2", "S3", "S4"] },
  "jev_output": { "choice": "S2", "probabilities": { "S1": 0.0, "S2": 0.0, "S3": 0.0, "S4": 0.0 }, "confidence": 0.0 },
  "solver_best": "S2",
  "agree": true,
  "latency_ms": 0,
  "cost_usd": 0.0,
  "mode": "shadow",
  "fallback_used": false,
  "model_id": "<valor de JEV_MODEL_ID>",
  "timestamp": "2026-11-10T00:00:00Z"
}
```

Los nombres exactos de los campos de salida de Jev dependen de su API real. El agente debe leer la documentación vigente antes de fijar el mapeo y dejarlo documentado aquí.

## 5. KPIs del informe (`results/kpis_summary.json`)

- Por solución y lluvia: reducción de calado máximo (cm y %), reducción de área inundada (%).
- Jev: acierto frente al solver (%), latencia p50/p95 (ms), coste por decisión (USD), % de decisiones con respaldo determinista.
- Solver: tiempo por escenario (s), error de balance de masa (%).
- Contexto (con fuente): lluvia y episodios reales, solo si hay dato verificable.
