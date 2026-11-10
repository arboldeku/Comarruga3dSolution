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

## 6. Ampliaciones fijadas en el hackathon (2026-11-10)

### 6.1 Archivos binarios y de índice (engine → web, jev)
- Todos los `.npy` son `float32`, orden C, forma `(ny, nx)`, fila 0 = norte. Unidades: metros.
- `results/<scenario_id>_depth.npy`: calado **máximo** por celda durante la simulación (m).
- `results/dem.npy`: elevación del terreno base S0 (m). Se referencia como `data.dem_file` en cada resultado.
- `results/landuse.npy` (opcional, `float32`): 0 = no urbano, 1 = urbano, 2 = cauce.
- `scenario_id` = `rain<mm>_<Sx>` (p. ej. `rain60_S2`). Lluvias de la demo: 30, 60, 100 mm en 60 min.
- Cada resultado añade `"status": "valid" | "invalid"` (inválido si `volume_error_pct` ≥ 5) y `"rain_mm"`, `"solution_id"`, `"solution_params"`, `"seed"`.
- `hotspots[].x`, `hotspots[].y` son índices de celda (columna, fila). Los mismos puntos negros (mismos `id` y posición) en todos los escenarios; `max_depth_cm` = calado máximo en un radio de 3 celdas.
- `results/index.json`:
  ```json
  { "label": "estimación preliminar, modelo simplificado",
    "dem_source": "sintético", "dem_file": "results/dem.npy", "landuse_file": "results/landuse.npy",
    "grid": { "nx": 0, "ny": 0, "cell_m": 0, "origin": [0,0], "crs": "EPSG:25831" },
    "rains_mm": [30, 60, 100], "solutions": [ { "id": "S0", "name": "...", "params": {} } ],
    "scenarios": [ { "scenario_id": "rain60_S2", "rain_mm": 60, "solution_id": "S2", "result_file": "results/rain60_S2.json", "status": "valid" } ],
    "generated_at": "ISO-8601" }
  ```
- `results/hotspots.json`: características por punto negro para la capa de decisión y mejor solución según el solver:
  ```json
  { "hotspots": [ { "id": "H1", "x": 0, "y": 0, "elevation_m": 0.0, "slope": 0.0, "catchment_m2": 0,
      "dist_to_channel_m": 0.0, "urban_fraction": 0.0, "depression_depth_m": 0.0 } ],
    "solver_best": [ { "hotspot_id": "H1", "rain_mm": 60, "best": "S2",
      "depth_cm": { "S0": 0.0, "S1": 0.0, "S2": 0.0, "S3": 0.0, "S4": 0.0 } } ] }
  ```
  `best` = solución S1–S4 con menor calado en el punto negro (empate: la de id menor).

### 6.2 Mapeo real de Jev (verificado en la documentación de OpenRouter el 2026-11-10)
Fuentes: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request.md ,
https://openrouter.ai/docs/guides/community/jev-tutorial , https://openrouter.ai/blog/insights/what-is-jev/
- `POST https://openrouter.ai/api/alpha/decisions`, cabeceras `Authorization: Bearer $OPENROUTER_API_KEY`, `Content-Type: application/json`.
- Petición: `model` (= `JEV_MODEL_ID`), `state` (cadena, objeto o lista), `questions` (mapa nombre → pregunta).
  Pregunta Choice: `{ "type": "choice", "instructions": <opcional>, "criteria": { "<opción>": "<descripción>" } }`.
  El nombre de la pregunta no se envía al modelo; el significado va en `instructions` y `criteria`.
- Respuesta: `answers.<pregunta>` con `type` (`choice` o `refusal`), `choice`, `probabilities` (mapa opción → número), `confidence` (opcional);
  `usage.input_tokens`, `usage.output_tokens`, `usage.cost`; `model` (instantánea fechada).
- Mapeo al contrato 4: `jev_output.choice` ← `answers.q.choice`; `jev_output.probabilities` ← `answers.q.probabilities`;
  `jev_output.confidence` ← `answers.q.confidence` (o `null`); `cost_usd` ← `usage.cost`
  (la referencia de la API dice "créditos" y el blog dice USD: discrepancia documentada, se registra el valor tal cual);
  `model_id` ← `JEV_MODEL_ID`; se añade `model_snapshot` ← `model` de la respuesta.
- Si `type` = `refusal`, hay error HTTP, timeout o faltan variables de entorno: `fallback_used: true` y `jev_output: null`;
  la decisión registrada es la del respaldo determinista (`fallback_output`).
- Cada línea añade siempre `fallback_output: { "choice": "Sx", "rule": "<regla aplicada>" }` y `fallback_agree` (línea base).
