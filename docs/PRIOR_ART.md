# Prior art y decisiones (no reinventar)

> **Aviso (2026-11-10, tarde):** las cifras de resultados de este documento corresponden a la primera ejecución con terreno sintético y están obsoletas. Los resultados vigentes, sobre el MDT de 5 m del ICGC, están en `README.md`, `docs/DECK.md` y `results/kpis_summary.json`. Las decisiones de librerías siguen siendo válidas.

Fecha de consulta de todo lo que sigue: 2026-11-10.

Todas las cifras de este documento son **estimación preliminar, modelo simplificado**, sobre **terreno sintético** (no es Comarruga real). Fuente de cifras: `results/kpis_summary.json`, 2026-11-10.

## Capa de decisión: Jev (TypeSafe AI) vía OpenRouter
- **Qué es:** modelo no generativo ("System One"): recibe estado + pregunta tipada y devuelve una respuesta tipada con probabilidades. Primitivas documentadas: Choice, Noul, Score y Box (Box solo en Jev 1.14).
  Fuente: https://openrouter.ai/blog/insights/what-is-jev/ (actualizado 2026-10-16).
- **Cómo se llama:** `POST https://openrouter.ai/api/v1/systemone`, con el formato de la API nativa de TypeSafe (referencia: docs.typesafe.ai/api). La versión anterior usaba `/api/alpha/decisions` y ya no está vigente.
- **Variables de entorno:** `JEV_API_KEY`, `JEV_BASE_URL`, `JEV_MODEL_ID`. Ver `.env.example`.
- **Modelo usado:** `typesafe/jev-1.14` (snapshot `typesafe/jev-1.14-20261014`, según `results/kpis_summary.json`, 2026-11-10). La documentación también cita `typesafe/jev-1.13` y el alias `~typesafe/jev-latest`; el tutorial de OpenRouter cita 1.13 y parece desactualizado. El modelo se lee de `JEV_MODEL_ID`.
- **Precio:** 0,042 USD/M tokens de entrada según docs.typesafe.ai/models.md (2026-11-10); precio efectivo en OpenRouter: sin dato; coste estimado (salida gratis; la API no devuelve coste). Límites de tasa: sin dato.
- **Decisión:** cliente HTTP propio mínimo con `requests` (un POST), con el formato de la API nativa de TypeSafe, enviado a OpenRouter.
- **Uso en este proyecto:** una pregunta Choice por punto negro y lluvia (opciones S1–S4), en modo sombra, con respaldo determinista siempre calculado y contraste con el solver.
- **Resultado en la ejecución de 2026-11-10** (`results/kpis_summary.json`, run `shadow_20261110T180551Z`):
  - 24 de 24 decisiones respondidas por Jev; respaldo usado en 0 % de los casos.
  - Acierto frente al solver: **16,7 %** con H2 (no fiable, artefacto H2); **9,5 %** excluyendo H2 (n = 21). Respaldo determinista: 33,3 % con H2 y 33,3 % excluyendo H2. Clase mayoritaria (S3, mejor solución del solver en 20 de 24 casos): 83,3 %. Azar: 25 %.
  - Distribución de elecciones de Jev: S2 en 21 de 24 casos, S3 en 3 (casi constante).
  - Acierto con margen ≥ 1 cm: Jev 25,0 % frente a respaldo 41,7 % (n = 12).
  - Acuerdo Jev–respaldo: 75,0 %.
  - Margen entre la mejor y la segunda solución < 1 cm en 12 de 24 casos: el acierto es ruidoso.
  - Los 24 casos son 8 puntos × 3 lluvias, no independientes: la diferencia con el respaldo no es concluyente.
  - Latencia medida: p50 346,4 ms; p95 548,5 ms; máx. 935,2 ms (rango más cercano, n = 24).
  - Coste estimado: 0,000034276 USD por decisión; 0,000822612 USD en total.
  - Probabilidad media asignada a la opción elegida: 37,9 % frente a acierto 16,7 % (sobreconfianza; n = 24, orientativo). Confianza media de la API: 0,171.
- **Conclusión:** Jev no demuestra valor en acierto (está por debajo del respaldo y del azar). Latencia y coste están medidos; el valor frente al respaldo no está demostrado (el respaldo es local, sin coste de API, y acierta más). Jev decide solo con rasgos del punto (pendiente, captación, distancia al cauce…), sin ejemplos ni resultados del solver.

## Solver: landlab OverlandFlow + envoltorio propio
- **Qué es:** componente `OverlandFlow` de landlab 2.11.0 (onda inercial local, de Almeida 2012) más un envoltorio propio, `comarruga-engine` 0.1.0, que añade lluvia, infiltración, depósito y balance de masa. Landlab también aporta `FlowAccumulator` y `SinkFillerBarnes`. No se escribió solver propio.
- **Malla y parámetros:** 200 × 200 celdas de 5 m (EPSG:25831). Manning 0,035. Infiltración: 20 mm/h en zona no urbana, 3 mm/h en urbana, 5 mm/h en cauce. Lluvia constante de 30, 60 o 100 mm en 60 min, más 30 min de drenaje. Umbral de inundación 0,05 m. Frontera: sur abierto (mar); norte, este y oeste cerrados. Numpy 1.26.4. Estos parámetros y los de S1–S4 son supuestos del modelo, sin calibrar.
- **Escenarios:** 15 = línea base S0 + soluciones S1–S4 para cada una de las tres lluvias. Todos válidos (`n_invalid` = 0). Error de volumen máximo: 1,513 %.
- **Tiempo de cómputo:** 15 escenarios en ~167 s con `OMP_NUM_THREADS=1` y 10 procesos: medición de la ejecución del 2026-11-10, no registrada en JSON. En `kpis_summary.json`: suma por escenario 1225,84 s; media 81,723 s; máximo 95,91 s.
- **Resultados por lluvia** (estimación preliminar, modelo simplificado · terreno sintético · `results/kpis_summary.json`, 2026-11-10). Reducción respecto a la línea base; valores negativos = aumento. Calado urbano = zona urbana; dominio completo = incluye cauce. Las filas de 30 mm provienen del punto H2: **no fiables (artefacto H2)**.

| Lluvia | Solución | Urbano: reducción calado máx. (cm) | Urbano: (%) | Dominio completo (incluye cauce): reducción (cm) | Dominio completo (%) | Reducción área inundada (%) |
|---|---|---|---|---|---|---|
| 30 mm (no fiable, H2) | S1 | 0,9 | 1,2 | 0,9 | 1,2 | −44,8 |
| 30 mm (no fiable, H2) | S2 | 0,0 | 0,0 | 0,0 | 0,0 | 0,0 |
| 30 mm (no fiable, H2) | S3 | 11,1 | 14,6 | 11,1 | 14,6 | 11,4 |
| 30 mm (no fiable, H2) | S4 | **−6,3 (empeora)** | −8,3 | −6,3 | −8,3 | −106,3 |
| 60 mm | S1 | 0,5 | 0,6 | 27,6 | 25,4 | 6,9 |
| 60 mm | S2 | 0,0 | 0,0 | 1,2 | 1,1 | 3,0 |
| 60 mm | S3 | **22,8** | **28,0** | 4,6 | 4,2 | 16,1 |
| 60 mm | S4 | **−7,9 (empeora)** | −9,7 | 19,2 | 17,7 | −54,6 |
| 100 mm | S1 | **−55,8 (empeora)** | −88,4 | 5,0 | 4,0 | 16,8 |
| 100 mm | S2 | 0,8 | 1,3 | 3,6 | 2,9 | 7,3 |
| 100 mm | S3 | 0,4 | 0,6 | 2,1 | 1,7 | 12,9 |
| 100 mm | S4 | **−33,3 (empeora)** | −52,8 | 19,8 | 16,0 | −21,0 |

- **Soluciones que empeoran el calado máximo urbano:** S4 con 30, 60 y 100 mm; S1 con 100 mm. Mayor reducción urbana: S3 con 60 mm (22,8 cm). La mayor reducción de dominio completo (S1 con 60 mm, 27,6 cm) no se traduce en la zona urbana (0,5 cm): no usarla como indicador de riesgo urbano.
- **Limitaciones conocidas:**
  - Artefacto numérico en el punto negro H2: el calado máximo no crece con la lluvia; cifras poco fiables (incluidas las de 30 mm).
  - S4 (barreras) nunca es la mejor y aumenta el área inundada, porque impide que la escorrentía urbana entre al cauce. S4 eleva celdas en vez de aristas.
  - S2 (depósito) está infrautilizado por el umbral de toma.
  - Varios puntos negros son someros (12–15 cm con 100 mm).
  - Rama de MDT real y perfil triangular sin probar.
- **Terreno:** sintético (`dem_source`: sintético). El MDT del ICGC no está disponible todavía.

## Visor: three.js 0.170.0
- **Qué es:** visor 3D en navegador con three.js 0.170.0 (licencia MIT), vendido en `web/vendor`. Sin build ni acceso a internet.
- **Parámetros de URL opcionales:** `?rain=60&sol=S2&mode=before|after|diff`.
- **Puesta en marcha:** `python -m http.server 8000` y abrir http://localhost:8000/web/.
- **Descartados:**
  - deck.gl: su `TerrainLayer` espera teselas RGB y es pesado sin bundler.
  - MapLibre: necesita teselas y un mapa base; un mapa base sugeriría que el terreno es real.
