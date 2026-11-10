# Roadmap

## Fase 0 · Hackathon (este repo)
Una zona de ~1 km² de Comarruga, solver 2D simple, 4 soluciones, Jev eligiendo, KPIs de acierto/latencia/coste, visor 3D y deck corto.

## Fase 1 · MVP real (Comarruga)
- Cronología de eventos: lluvia medida (intensidad en 30 min, no solo total diario) frente a episodios de entrada de agua, con fotos geolocalizadas de vecinos.
- Modelo hidráulico 2D "antes vs. después" de las obras del Riuet, con MDT de distintas épocas (ICGC).
- Hipótesis alternativas a contrastar junto a la de las obras: drenaje o alcantarillado saturado; marea y nivel del mar (el modelo tiene frontera sur abierta sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min.
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

## Recortes y pendientes del hackathon (2026-11-10)

Estimación preliminar, modelo simplificado · terreno sintético. Cifras en `docs/PRIOR_ART.md` y `results/kpis_summary.json`.

Limitaciones actuales:
- Terreno sintético. El MDT real del ICGC no está disponible.
- Jev acierta el 16,7 % frente al solver (con H2, no fiable), por debajo del respaldo (33,3 %) y del azar (25 %). Excluyendo H2: 9,5 % frente a 33,3 % (n = 21). Con margen ≥ 1 cm: 25,0 % frente a 41,7 % (n = 12). Elige S2 en 21 de 24 casos. Los 24 casos son 8 puntos × 3 lluvias, no independientes: la diferencia no es concluyente. Sin ejemplos ni resultados del solver en el prompt.
- Artefacto numérico en H2: el calado máximo no crece con la lluvia. Las cifras de 30 mm provienen de H2 (no fiables).
- Calado urbano: S4 empeora el máximo urbano con las tres lluvias y S1 con 100 mm.
- S2 (depósito) infrautilizado por el umbral de toma. S4 (barreras) aumenta el área inundada.
- S4 eleva celdas en vez de aristas. Rama de MDT real y perfil triangular sin probar.

Pendientes:
- Conseguir el MDT real del ICGC.
- Jev: probar few-shot o Score; medir con márgenes > 1 cm.
- Corregir H2.
- Recalibrar S2 y S4.
