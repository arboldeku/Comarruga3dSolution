# Roadmap

## Fase 0 · Hackathon (este repo)
Una zona de ~1 km² de Comarruga, solver 2D simple, 4 soluciones, Jev eligiendo, KPIs de acierto/latencia/coste, visor 3D y deck corto.

## Fase 1 · MVP real (Comarruga)
- Cronología de eventos: lluvia medida (intensidad en 30 min, no solo total diario) frente a episodios de entrada de agua, con fotos geolocalizadas de vecinos.
- Modelo hidráulico 2D "antes vs. después" de las obras del Riuet, con MDT de distintas épocas (ICGC).
- Validación con un técnico hidráulico y un letrado antes de presentar a un ayuntamiento.

## Fase 2 · Datos a escala
- Recolección masiva: ICGC, Meteocat, ACA, SNCZI/MITECO.
- Pipeline propio: API → transformación → Supabase (PostgreSQL + PostGIS) solo con dato transformado y gobernado, sin duplicados.
- Crudos inmutables en almacenamiento de archivos con hash y fuente (archivo de pruebas). Rásteres pesados fuera de PostgreSQL.
- Históricos de lo que sea dato propio transformado.

## Fase 3 · Gabinete de agentes
Roles: jefe de gabinete, recolector de datos, hidrometeorólogo, modelador hidráulico, ingeniero civil/urbanista, jurídico-administrativo, auditor, comunicación y visualización.
- Subagentes en `.claude/agents/`, sesiones en la nube desde el móvil, GitHub como memoria, GitHub Actions para tareas automáticas.
- Coordinación entre agentes por tabla de tareas o subagentes; Discord como sala de observación y órdenes; Telegram solo para avisos personales.
- LLM por tarea (incluidos gratuitos), con capa unificadora existente en lugar de cliente propio. Modelo fuerte para todo lo que llegue al dossier.

## Reglas transversales
- Antes de construir algo, buscar si ya existe (ver `docs/PRIOR_ART.md`).
- Estimaciones preliminares siempre etiquetadas; revisión humana experta antes de uso oficial.
