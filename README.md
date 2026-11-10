# Comarruga Flood Lab

Simulador "¿y si...?" de acumulación de agua en zona urbana, con **Jev** como capa de decisión.

> Si lloviera X l/m² y la solución urbanística fuera Y, ¿cuántos cm de agua acumulada se ahorrarían en las zonas inundables?

Caso de estudio: Comarruga (Baix Penedès, Catalunya), cuenca del Riuet.

## Estado (2026-11-10)

MVP de hackathon sobre **terreno real** (MDT ICGC 5 m). Estimación preliminar, modelo simplificado, **modelo sin calibrar**.

- **Terreno:** MDT de 5 m del ICGC (servicio WCS `icc_mdt`, cobertura `icc:met5`), 1 km × 1 km en Brisamar / Coma-ruga (El Vendrell), EPSG:25831, descargado el 2026-11-10. Hash en `data/raw/MANIFEST.json`.
- **Supuestos sin dato real** (ver Limitaciones): usos del suelo (todo el terreno emergido tratado como urbano; eje de drenaje derivado del MDT), ausencia de red de alcantarillado, nivel del mar fijo a 0 m sin marea, duración de la lluvia (60 min, sin hietograma), ubicación del depósito.
- **Solver:** landlab OverlandFlow con envoltorio propio. 15 de 15 escenarios válidos, precalculados en `results/`.
- **Visor 3D:** three.js, sin build ni internet.
- **Jev:** 24 de 24 decisiones respondidas en modo sombra. Acierto frente al solver 0 % (0 de 24), por debajo del respaldo determinista (4,2 %), de elegir siempre la clase mayoritaria (S3, 79,2 %) y del azar (25 %). Jev eligió S2 en los 24 casos. Latencia y coste medidos; valor frente al respaldo no demostrado.
- **Calado urbano:** la mayor reducción es S3 con 100 mm (61,0 cm, 27,3 %), ventaja inflada por el supuesto de usos del suelo. S1 con 30 y 60 mm (también sube el máximo global) y S4 con 30 y 100 mm empeoran el máximo urbano. S2 no cambia el máximo urbano en ningún escenario.

## Por qué existe

Las entradas de agua en viviendas de Comarruga han pasado de 1 en 27 años a 2 solo en 2026 (testimonio del autor, pendiente de verificar con fuentes oficiales y vecinos). El objetivo a largo plazo es aportar evidencia cuantificable a los ayuntamientos. Este repo es el **MVP de hackathon**: una demostración, no un estudio de ingeniería.

## Aviso de rigor

Todos los resultados son **estimaciones preliminares** de un modelo simplificado, **sin calibrar**, sobre el MDT real del ICGC con supuestos de usos del suelo, drenaje, marea y lluvia. No sustituyen a un estudio hidráulico (Iber, HEC-RAS 2D) firmado por un técnico competente. Toda cifra lleva fuente y fecha, o dice `sin dato`.

- Que las obras del Riuet causaran inundaciones es una **hipótesis del autor**. Este repo no la demuestra ni atribuye causa a ninguna obra. Las soluciones S1–S4 son supuestos del modelo, no proyectos reales.
- Hipótesis alternativas a contrastar, no evaluadas aquí: drenaje o alcantarillado saturado; marea y nivel del mar (el modelo usa cota fija 0 m sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min (el modelo usa lluvia constante durante 60 min).
- Los episodios reales (1 entrada de agua en 27 años; 2 en 2026) son **testimonio del autor**, pendiente de verificar. Sin dato verificable en el repo.

## Arquitectura

```
MDT (ICGC) ──► engine (solver 2D) ──► results/*.json ──► web (visor 3D)
                    ▲                        │
                    │                        ▼
              scenarios/*.json         jev (decisión)  ──► KPIs ──► informe
```

| Carpeta | Qué contiene |
|---|---|
| `engine/` | Preparación del terreno y solver de flujo superficial |
| `jev/` | Cliente de Jev (vía OpenRouter), evaluación frente al solver |
| `web/` | Visor 3D en navegador con controles de lluvia y solución |
| `docs/` | Contratos de datos, roadmap, notas de datos, prior art y deck |
| `data/` | `raw/` (inmutable, con fuente y hash) y `processed/` |
| `.claude/` | Subagentes y skill de diagramas para Claude Code |

## Reparto de papeles

- **Solver (código):** calcula calados. Jev nunca calcula aritmética hidráulica.
- **Jev:** decide (elegir solución por punto negro y lluvia), con probabilidades.
- **LLM generativo:** redacta la explicación a partir de la decisión ya tomada.

## Puesta en marcha

```bash
pip install -r requirements.txt
python -m engine.run_all          # recalcula los 15 escenarios; ya vienen precalculados en results/ (tiempo de pared ~167 s con OMP_NUM_THREADS=1 y 10 procesos: medición de la ejecución del 2026-11-10, no registrada en JSON)
python -m jev.run_shadow          # decisiones de Jev en modo sombra: llamadas reales a OpenRouter (coste estimado a partir de tokens, 2026-11-10: 0,000828 USD)
python -m http.server 8000        # después, abrir http://localhost:8000/web/
python -m unittest discover -s jev/tests -t .
```

- Visor, parámetros opcionales: `?rain=60&sol=S2&mode=before|after|diff`.
- Jev necesita `JEV_API_KEY`, `JEV_BASE_URL` y `JEV_MODEL_ID`. Ver `.env.example`.
- Instrucciones completas para el agente de código: `AGENT_PROMPT.md`.

## Terreno y lluvias

| Dato | Valor | Fuente |
|---|---|---|
| Terreno | MDT 5 m, 200 × 200 celdas, 1 km × 1 km, EPSG:25831 | ICGC `icc:met5`, descargado 2026-11-10 (`data/raw/MANIFEST.json`) |
| Lluvia 100 mm | Total en Coma-ruga, 22/08/2026 | Comunicado del Ayuntamiento de El Vendrell (26/08/2026) |
| Lluvia 60 mm | Total del episodio del 02/11/2026 | Prensa (Diari de Tarragona, 03/11/2026), **pendiente de contrastar** |
| Lluvia 30 mm | Referencia | Supuesto |
| Duración de la lluvia | 60 min, constante | **Supuesto**; sin hietograma (Meteocat pendiente) |
| Volumen del depósito S2 | 3 500 m³ | **Volumen anunciado** por el Ayuntamiento para Brisamar (anuncio, no volumen hidráulico calibrado) |

## KPIs principales

Estimación preliminar, modelo simplificado · modelo sin calibrar · MDT real ICGC 5 m. Fuente: `results/kpis_summary.json` y `results/index.json`, 2026-11-10.

### Solver

| KPI | Valor |
|---|---|
| Escenarios válidos | 15 de 15 (`n_invalid` = 0) |
| Error de volumen máximo | 1,054 % |
| Tiempo de cálculo por escenario | media 94,1 s; máx. 117,5 s; total 1 411,8 s (suma de escenarios, no tiempo de pared; el de pared no está en el JSON) |

### Calado máximo urbano por solución (cm; base S0 entre paréntesis)

Valores negativos de reducción = el calado sube. El dominio completo y la zona urbana coinciden en todos los escenarios.

| Lluvia (base S0) | S1 Cauce | S2 Depósito | S3 Permeable | S4 Bordillos |
|---|---|---|---|---|
| 30 mm (101,5) | 107,1 (−5,6; −5,5 %) | 101,5 (0,0) | 54,6 (+46,9; +46,2 %) | 110,8 (−9,3; −9,2 %) |
| 60 mm (153,5) | 182,5 (−29,0; −18,9 %) | 153,5 (0,0) | 109,7 (+43,8; +28,5 %) | 146,3 (+7,2; +4,7 %) |
| 100 mm (223,8) | 215,8 (+8,0; +3,6 %) | 223,8 (0,0) | 162,8 (+61,0; +27,3 %) | 227,8 (−4,0; −1,8 %) |

- Mayor reducción del calado máximo urbano en cm: **S1 con 100 mm, 8,0 cm (3,6 %)**. Mayor en porcentaje: S4 con 60 mm, 7,2 cm (4,7 %).
- Empeoran el máximo urbano: S1 con 30 mm y 60 mm; S4 con 30 mm y 100 mm. S2 no cambia el máximo urbano en ningún escenario.
- S2 no llega a usarse en el modelo: pico del depósito de 9,3 m³ con 100 mm; sus resultados son iguales a S0 porque la ubicación supuesta apenas recibe agua. Es una limitación de la ubicación supuesta, no una conclusión sobre el depósito real.
- S3 mejora el máximo urbano en los tres escenarios, pero su ventaja está inflada por el supuesto de usos del suelo (todo el terreno emergido tratado como urbano, con 40 % permeable).
- Área inundada (% de reducción; negativo = aumenta): S1 +3,7 / +14,9 / +12,6; S3 +73,6 / +32,0 / +14,9; S4 −6,6 / −1,9 / +0,2; S2 0,0 (30 / 60 / 100 mm).

### Jev (24 decisiones, modo sombra)

| KPI | Valor |
|---|---|
| Decisiones respondidas | 24 de 24; respaldo usado 0 %; modelo `typesafe/jev-1.14` (snapshot 20261014) vía OpenRouter |
| Acierto de Jev frente al solver | **0 %** (0 de 24) |
| Acierto del respaldo determinista | 4,2 % (1 de 24) |
| Acierto de elegir siempre la clase mayoritaria (S3) | 79,2 % (19 de 24) |
| Azar | 25 % |
| Elección de Jev | **S2 en los 24 casos**: eligió la misma opción en todos |
| Distribución del mejor resultado del solver | S3 19, S1 5 |
| Acierto excluyendo empates (Jev / respaldo) | 0,0 % / 4,3 % (empates: 1) |
| Acierto con margen ≥ 1 cm (Jev / respaldo) | 0,0 % / 4,8 % (n = 21) |
| Probabilidad media asignada a la opción elegida | 53,1 % frente a acierto 0 % (sobreconfianza; n = 24, orientativo) |
| Coincidencia Jev / respaldo | 87,5 % |
| Latencia p50 / p95 / máx. | 392,3 ms / 681,6 ms / 683,6 ms (rango más cercano, n = 24) |
| Coste estimado | 0,000034 USD por decisión; 0,000828 USD en total (estimado a partir de tokens a 0,042 USD por millón de tokens de entrada; la API no devuelve coste) |

Notas de lectura:
- **Clase mayoritaria:** el 79,2 % corresponde a S3 como mejor resultado del solver en 19 de 24 casos.
- **Jev:** no supera al respaldo, ni a la clase mayoritaria, ni al azar. Con 24 casos no independientes (8 puntos × 3 lluvias) la diferencia con el respaldo no es concluyente, pero Jev no muestra acierto aquí.

## Limitaciones

- **Modelo sin calibrar.** Estimación preliminar, modelo simplificado.
- **Supuestos (no datos reales):**
  - Usos del suelo: todo el terreno emergido se trata como urbano; el eje de drenaje se deriva del MDT. La ventaja de S3 está inflada por este supuesto (40 % de área permeable).
  - Sin red de alcantarillado en el modelo: los calados salen altos (101,5 cm con 30 mm en S0) porque no hay drenaje subterráneo. Los calados de 1 a 2,2 m aparecen en hoyos cerrados del propio MDT (aspecto de pasos inferiores): son cota superior, no calados esperables.
  - Nivel del mar fijo a 0 m, sin marea.
  - Duración de la lluvia: 60 min constantes; sin hietograma real.
  - Ubicación del depósito S2: depresión urbana más honda del MDT.
- **Lluvias:** 100 mm comunicado municipal; 60 mm de prensa pendiente de contrastar; 30 mm de referencia.
- **Volumen de S2 (3 500 m³):** volumen anunciado por el Ayuntamiento, no calibrado.
- **S2** no cambia nada respecto a S0: pico de 9,3 m³ con 100 mm, porque la ubicación supuesta apenas recibe agua. Es una limitación de la ubicación, no una conclusión sobre el depósito real.
- **S1** empeora el máximo urbano con 30 y 60 mm, y **S4** con 30 y 100 mm. La ventaja de S3 está inflada por el supuesto de usos del suelo.
- **Jev sin acierto demostrado** frente al respaldo, la clase mayoritaria y el azar; elige siempre S2.
- **Episodios reales:** sin dato verificable.

Detalle y tablas completas en `docs/PRIOR_ART.md`. Pendientes en `docs/ROADMAP.md`.

## Roadmap

Ver `docs/ROADMAP.md`.
