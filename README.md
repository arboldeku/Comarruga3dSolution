# Comarruga Flood Lab

Simulador "¿y si...?" de acumulación de agua en zona urbana, con **Jev** como capa de decisión.

> Si lloviera X l/m² y la solución urbanística fuera Y, ¿cuántos cm de agua acumulada se ahorrarían en las zonas inundables?

Caso de estudio: Comarruga (Baix Penedès, Catalunya), cuenca del Riuet.

## Estado (2026-11-10)

MVP de hackathon, funcional con **terreno sintético**.

- **Terreno sintético:** no es el relieve real de Comarruga. El MDT del ICGC no está disponible todavía; ningún resultado describe la topografía real.
- **Solver:** landlab OverlandFlow con envoltorio propio. 15 escenarios válidos, precalculados en `results/`.
- **Visor 3D:** three.js, sin build ni internet.
- **Jev:** 24 de 24 decisiones respondidas en modo sombra. Su acierto frente al solver (16,7 %) está por debajo del respaldo determinista (33,3 %) y del azar (25 %). Jev muestra valor en latencia y coste por decisión; el valor en acierto no está demostrado.

## Por qué existe

Las entradas de agua en viviendas de Comarruga han pasado de 1 en 27 años a 2 solo en 2026 (testimonio del autor, pendiente de verificar con fuentes oficiales y vecinos). El objetivo a largo plazo es aportar evidencia cuantificable a los ayuntamientos. Este repo es el **MVP de hackathon**: una demostración, no un estudio de ingeniería.

## Aviso de rigor

Todos los resultados son **estimaciones preliminares** de un modelo simplificado, sobre **terreno sintético**. No sustituyen a un estudio hidráulico (Iber, HEC-RAS 2D) firmado por un técnico competente. Toda cifra lleva fuente y fecha, o dice `sin dato`.

- Que las obras del Riuet causaran inundaciones es una **hipótesis del autor**. Este repo no la demuestra ni atribuye causa a ninguna obra. Las soluciones S1–S4 son supuestos del modelo, no proyectos reales.
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
python -m engine.run_all          # recalcula los 15 escenarios (~167 s con OMP_NUM_THREADS=1 y 10 procesos); ya vienen precalculados en results/
python -m jev.run_shadow          # decisiones de Jev en modo sombra: llamadas reales a OpenRouter (coste medido 2026-11-10: 0,000822612 USD)
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
| Mayor reducción de calado máximo | S1 con 60 mm: 27,6 cm (25,4 %) |
| Acierto de Jev frente al solver | 16,7 % (24 decisiones) |
| Acierto del respaldo determinista | 33,3 % |
| Acierto de "elegir siempre la clase mayoritaria" (S3) | 83,3 % |
| Azar | 25 % |
| Latencia de Jev p50 / p95 | 346,4 ms / 548,5 ms |
| Coste estimado por decisión de Jev | 0,000034276 USD |
| Decisiones con respaldo | 0 % |

## Limitaciones

- **Terreno sintético.** El MDT real del ICGC no está disponible; la rama de MDT real y el perfil triangular no están probados.
- **Artefacto numérico en H2.** El calado máximo no crece con la lluvia; cifras poco fiables.
- **S4 (barreras)** nunca es la mejor y aumenta el área inundada, porque impide que la escorrentía urbana entre al cauce.
- **S2 (depósito)** está infrautilizado por el umbral de toma.
- **Puntos someros.** Varios puntos negros tienen 12–15 cm con 100 mm.
- **Jev sin acierto demostrado.** Acierta menos que el respaldo y que el azar. 12 de 24 casos tienen un margen < 1 cm entre soluciones. Jev decide sin ejemplos ni resultados del solver. Está sobreconfiado (confianza media 37,9 %, acierto 16,7 %; n = 24, orientativo).
- **Episodios reales:** sin dato verificable.

Detalle y tablas completas en `docs/PRIOR_ART.md`. Pendientes en `docs/ROADMAP.md`.

## Roadmap

Ver `docs/ROADMAP.md`.
