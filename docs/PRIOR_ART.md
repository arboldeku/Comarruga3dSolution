# Prior art y decisiones (no reinventar)

Fecha de consulta de todo lo que sigue: 2026-11-10.

Todas las cifras de este documento son **estimación preliminar, modelo simplificado**, sobre **terreno sintético** (no es Comarruga real). Fuente de cifras: `results/kpis_summary.json`, 2026-11-10.

## Capa de decisión: Jev (TypeSafe AI) vía OpenRouter
- **Qué es:** modelo no generativo ("System One"): recibe estado + pregunta tipada y devuelve una respuesta tipada con probabilidades. Primitivas documentadas: Choice, Noul, Score y Box (Box solo en Jev 1.14).
  Fuente: https://openrouter.ai/blog/insights/what-is-jev/ (actualizado 2026-10-16).
- **Cómo se llama:** `POST https://openrouter.ai/api/v1/systemone`, con el formato de la API nativa de TypeSafe (referencia: docs.typesafe.ai/api). La versión anterior usaba `/api/alpha/decisions` y ya no está vigente.
- **Variables de entorno:** `JEV_API_KEY`, `JEV_BASE_URL`, `JEV_MODEL_ID`. Ver `.env.example`.
- **Modelo usado:** `typesafe/jev-1.14` (snapshot `typesafe/jev-1.14-20261014`, según `results/kpis_summary.json`, 2026-11-10). La documentación también cita `typesafe/jev-1.13` y el alias `~typesafe/jev-latest`; el tutorial de OpenRouter cita 1.13 y parece desactualizado. El modelo se lee de `JEV_MODEL_ID`.
- **Precio:** 0,042 USD por millón de tokens de entrada, salida gratis (docs.typesafe.ai/models.md, consultado 2026-11-10). La API no devuelve coste: el coste del repo es una estimación a partir de tokens de entrada. Límites de tasa: sin dato.
- **Decisión:** cliente HTTP propio mínimo con `requests` (un POST), con el formato de la API nativa de TypeSafe, enviado a OpenRouter.
- **Uso en este proyecto:** una pregunta Choice por punto negro y lluvia (opciones S1–S4), en modo sombra, con respaldo determinista siempre calculado y contraste con el solver.
- **Resultado en la ejecución de 2026-11-10** (`results/kpis_summary.json`, run `shadow_20261110T180551Z`):
  - 24 de 24 decisiones respondidas por Jev; respaldo usado en 0 % de los casos.
  - Acierto frente al solver: **16,7 %**. Respaldo determinista: 33,3 %. Clase mayoritaria (S3, mejor solución del solver en 20 de 24 casos): 83,3 %. Azar: 25 %.
  - Acuerdo Jev–respaldo: 75,0 %.
  - Margen entre la mejor y la segunda solución < 1 cm en 12 de 24 casos: el acierto es ruidoso.
  - Latencia p50 346,4 ms; p95 548,5 ms.
  - Coste estimado: 0,000034276 USD por decisión; 0,000822612 USD en total.
  - Calibración: confianza media en la opción elegida 37,9 % frente a acierto 16,7 % (Jev sobreconfiado; n = 24, orientativo).
- **Conclusión:** Jev no demuestra valor en acierto (está por debajo del respaldo y del azar). Sí se demuestran latencia, coste por decisión, probabilidades y la tubería de contraste. Jev decide solo con rasgos del punto (pendiente, captación, distancia al cauce…), sin ejemplos ni resultados del solver.

## Solver: landlab OverlandFlow + envoltorio propio
- **Qué es:** componente `OverlandFlow` de landlab 2.11.0 (onda inercial local, de Almeida 2012) más un envoltorio propio, `comarruga-engine` 0.1.0, que añade lluvia, infiltración, depósito y balance de masa. Landlab también aporta `FlowAccumulator` y `SinkFillerBarnes`. No se escribió solver propio.
- **Malla y parámetros:** 200 × 200 celdas de 5 m (EPSG:25831). Manning 0,035. Infiltración: 20 mm/h en zona no urbana, 3 mm/h en urbana, 5 mm/h en cauce. Lluvia constante de 30, 60 o 100 mm en 60 min, más 30 min de drenaje. Umbral de inundación 0,05 m. Frontera: sur abierto (mar); norte, este y oeste cerrados. Numpy 1.26.4.
- **Escenarios:** 15 = línea base S0 + soluciones S1–S4 para cada una de las tres lluvias. Todos válidos (`n_invalid` = 0). Error de volumen máximo: 1,513 %.
- **Tiempo de cómputo:** 15 escenarios en ~167 s con `OMP_NUM_THREADS=1` y 10 procesos (dato del equipo, 2026-11-10). En `kpis_summary.json`: suma por escenario 1225,84 s; media 81,723 s; máximo 95,91 s.
- **Resultados por lluvia** (estimación preliminar, modelo simplificado · terreno sintético · `results/kpis_summary.json`, 2026-11-10). Reducción respecto a la línea base; valores negativos = aumento:

| Lluvia | Solución | Reducción calado máx. (cm) | Reducción calado máx. (%) | Reducción área inundada (%) |
|---|---|---|---|---|
| 30 mm | S1 | 0,9 | 1,2 | −44,8 |
| 30 mm | S2 | 0,0 | 0,0 | 0,0 |
| 30 mm | S3 | 11,1 | 14,6 | 11,4 |
| 30 mm | S4 | −6,3 | −8,3 | −106,3 |
| 60 mm | S1 | 27,6 | 25,4 | 6,9 |
| 60 mm | S2 | 1,2 | 1,1 | 3,0 |
| 60 mm | S3 | 4,6 | 4,2 | 16,1 |
| 60 mm | S4 | 19,2 | 17,7 | −54,6 |
| 100 mm | S1 | 5,0 | 4,0 | 16,8 |
| 100 mm | S2 | 3,6 | 2,9 | 7,3 |
| 100 mm | S3 | 2,1 | 1,7 | 12,9 |
| 100 mm | S4 | 19,8 | 16,0 | −21,0 |

- **Limitaciones conocidas:**
  - Artefacto numérico en el punto negro H2: el calado máximo no crece con la lluvia; cifras poco fiables.
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
