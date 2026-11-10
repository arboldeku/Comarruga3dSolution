# Comarruga Flood Lab

Simulador "¿y si...?" de acumulación de agua en zona urbana, con **Jev** como capa de decisión.

> Si lloviera X l/m² y la solución urbanística fuera Y, ¿cuántos cm de agua acumulada se ahorrarían en las zonas inundables?

Caso de estudio: Comarruga (Baix Penedès, Catalunya), cuenca del Riuet.

## Estado (2026-11-10)

MVP de hackathon, funcional con **terreno sintético**.

- **Terreno sintético:** no es el relieve real de Comarruga. El MDT del ICGC no está disponible todavía; ningún resultado describe la topografía real.
- **Solver:** landlab OverlandFlow con envoltorio propio. 15 escenarios válidos, precalculados en `results/`.
- **Visor 3D:** three.js, sin build ni internet.
- **Jev:** 24 de 24 decisiones respondidas en modo sombra. Su acierto frente al solver (16,7 % con H2, no fiable; 9,5 % sin H2) está por debajo del respaldo determinista (33,3 %) y del azar (25 %). Latencia y coste medidos; valor frente al respaldo no demostrado (el respaldo es local, sin coste de API, y acierta más).
- **Calado urbano:** la mayor reducción es S3 con 60 mm (22,8 cm, 28,0 %). S4 empeora el máximo urbano con 30, 60 y 100 mm, y S1 con 100 mm.

## Por qué existe

Las entradas de agua en viviendas de Comarruga han pasado de 1 en 27 años a 2 solo en 2026 (testimonio del autor, pendiente de verificar con fuentes oficiales y vecinos). El objetivo a largo plazo es aportar evidencia cuantificable a los ayuntamientos. Este repo es el **MVP de hackathon**: una demostración, no un estudio de ingeniería.

## Aviso de rigor

Todos los resultados son **estimaciones preliminares** de un modelo simplificado, sobre **terreno sintético**. No sustituyen a un estudio hidráulico (Iber, HEC-RAS 2D) firmado por un técnico competente. Toda cifra lleva fuente y fecha, o dice `sin dato`.

- Que las obras del Riuet causaran inundaciones es una **hipótesis del autor**. Este repo no la demuestra ni atribuye causa a ninguna obra. Las soluciones S1–S4 son supuestos del modelo, no proyectos reales.
- Hipótesis alternativas a contrastar, no evaluadas aquí: drenaje o alcantarillado saturado; marea y nivel del mar (el modelo tiene frontera sur abierta sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min (el modelo usa lluvia constante durante 60 min).
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
python -m engine.run_all          # recalcula los 15 escenarios (~167 s con OMP_NUM_THREADS=1 y 10 procesos: medición de la ejecución del 2026-11-10, no registrada en JSON); ya vienen precalculados en results/
python -m jev.run_shadow          # decisiones de Jev en modo sombra: llamadas reales a OpenRouter (coste estimado a partir de tokens, 2026-11-10: 0,000822612 USD)
python -m http.server 8000        # después, abrir http://localhost:8000/web/
python -m unittest discover -s jev/tests -t .
```

- Visor, parámetros opcionales: `?rain=60&sol=S2&mode=before|after|diff`.
- Jev necesita `JEV_API_KEY`, `JEV_BASE_URL` y `JEV_MODEL_ID`. Ver `.env.example`.
- Instrucciones completas para el agente de código: `AGENT_PROMPT.md`.

## KPIs principales

Estimación preliminar, modelo simplificado · terreno sintético. Fuente: `results/kpis_summary.json`, 2026-11-10.

| KPI | Valor |
|---|---|
| Escenarios del solver válidos | 15 de 15 (`n_invalid` = 0) |
| Error de volumen máximo del solver | 1,513 % |
| Mayor reducción de calado máximo **urbano** (frente a S0) | S3 con 60 mm: 22,8 cm (28,0 %) |
| Soluciones que **empeoran** el calado máximo urbano | S4 con 30 mm (−6,3 cm), 60 mm (−7,9 cm) y 100 mm (−33,3 cm); S1 con 100 mm (−55,8 cm) |
| Mayor reducción de calado máximo, dominio completo (incluye cauce) | S1 con 60 mm: 27,6 cm (25,4 %) |
| Acierto de Jev frente al solver | 16,7 % (24 decisiones; con H2, no fiable) |
| Acierto de Jev excluyendo H2 | 9,5 % (n = 21) |
| Acierto del respaldo determinista | 33,3 % (24); 33,3 % excluyendo H2 (n = 21) |
| Acierto con margen ≥ 1 cm: Jev / respaldo | 25,0 % / 41,7 % (n = 12) |
| Distribución de elecciones de Jev (S2 / S3) | 21 / 3 de 24: casi constante |
| Acierto de "elegir siempre la clase mayoritaria" (S3) | 83,3 % |
| Azar | 25 % |
| Latencia de Jev p50 / p95 / máx. | 346,4 ms / 548,5 ms / 935,2 ms (rango más cercano, n = 24) |
| Coste estimado por decisión de Jev | 0,000034276 USD (estimado a partir de tokens) |
| Decisiones con respaldo | 0 % |

Las cifras de 30 mm provienen del punto H2: **no fiables (artefacto H2)**. Las de dominio completo incluyen el cauce.

## Limitaciones

- **Terreno sintético.** El MDT real del ICGC no está disponible; la rama de MDT real y el perfil triangular no están probados.
- **Artefacto numérico en H2.** El calado máximo no crece con la lluvia; cifras poco fiables.
- **S4 (barreras)** nunca es la mejor y aumenta el área inundada, porque impide que la escorrentía urbana entre al cauce.
- **S2 (depósito)** está infrautilizado por el umbral de toma.
- **Puntos someros.** Varios puntos negros tienen 12–15 cm con 100 mm.
- **Jev sin acierto demostrado.** Acierta menos que el respaldo y que el azar en el total (16,7 % frente a 33,3 % y 25 %). Casi constante: elige S2 en 21 de 24 casos. Con margen ≥ 1 cm, 25,0 % frente a 41,7 % del respaldo (n = 12). Los 24 casos son 8 puntos × 3 lluvias, no independientes: la diferencia no es concluyente. 12 de 24 casos tienen margen < 1 cm. Jev decide sin ejemplos ni resultados del solver. Probabilidad media asignada a la opción elegida 37,9 % frente a acierto 16,7 % (sobreconfianza; orientativo, n = 24); confianza media de la API 0,171.
- **Calado urbano:** S4 empeora el máximo urbano con las tres lluvias y S1 con 100 mm. Las cifras de dominio completo incluyen el cauce.
- **Episodios reales:** sin dato verificable.

Detalle y tablas completas en `docs/PRIOR_ART.md`. Pendientes en `docs/ROADMAP.md`.

## Roadmap

Ver `docs/ROADMAP.md`.
