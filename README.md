# Comarruga Flood Lab

Simulador "¿y si...?" de acumulación de agua en zona urbana, con **Jev** como capa de decisión.

> Si lloviera X l/m² y la solución urbanística fuera Y, ¿cuántos cm de agua acumulada se ahorrarían en las zonas inundables?

Caso de estudio: Comarruga (Baix Penedès, Catalunya), cuenca del Riuet.

## Por qué existe

Las entradas de agua en viviendas de Comarruga han pasado de 1 en 27 años a 2 solo en 2026 (testimonio del autor, pendiente de verificar con fuentes oficiales y vecinos). El objetivo a largo plazo es aportar evidencia cuantificable a los ayuntamientos. Este repo es el **MVP de hackathon**: una demostración, no un estudio de ingeniería.

## Aviso de rigor

Todos los resultados son **estimaciones preliminares** de un modelo simplificado. No sustituyen a un estudio hidráulico (Iber, HEC-RAS 2D) firmado por un técnico competente. Toda cifra debe llevar fuente y fecha, o decir `sin dato`.

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
| `docs/` | Contratos de datos, roadmap, notas de datos |
| `data/` | `raw/` (inmutable, con fuente y hash) y `processed/` |
| `.claude/` | Subagentes y skill de diagramas para Claude Code |

## Reparto de papeles

- **Solver (código):** calcula calados. Jev nunca calcula aritmética hidráulica.
- **Jev:** decide (elegir solución, puntuar riesgo, clasificar reportes), con probabilidades.
- **LLM generativo:** redacta la explicación a partir de la decisión ya tomada.

## Puesta en marcha

Ver `AGENT_PROMPT.md` (instrucciones completas para el agente de código) y `.env.example` (variables necesarias).

## Roadmap

Ver `docs/ROADMAP.md`.
