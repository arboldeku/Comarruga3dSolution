# Roadmap

## Fase 0 · Hackathon (este repo)
Una zona de 1 km² de Comarruga (MDT real del ICGC, 5 m), solver 2D simple, 4 soluciones, Jev eligiendo, KPIs de acierto/latencia/coste, visor 3D y deck corto.

## Fase 1 · MVP real (Comarruga)
- Cronología de eventos: lluvia medida (intensidad en 30 min, no solo total diario) frente a episodios de entrada de agua, con fotos geolocalizadas de vecinos.
- Modelo hidráulico 2D "antes vs. después" de las obras del Riuet, con MDT de distintas épocas (ICGC).
- Hipótesis alternativas a contrastar junto a la de las obras: drenaje o alcantarillado saturado; marea y nivel del mar (el modelo usa cota fija 0 m, sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min.
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

Estimación preliminar, modelo simplificado · modelo sin calibrar · terreno: MDT real del ICGC 5 m. Cifras en `results/kpis_summary.json` y `results/index.json`.

Limitaciones actuales:
- Modelo sin calibrar. Supuestos sin dato real: usos del suelo (todo el emergido tratado como urbano), ausencia de red de alcantarillado, nivel del mar fijo a 0 m sin marea, lluvia de 60 min sin hietograma, ubicación del depósito.
- Lluvias: 100 mm (comunicado del Ayuntamiento de El Vendrell, 22/08/2026); ~60 mm (prensa, 02/11/2026, pendiente de contrastar); 30 mm de referencia. El depósito S2 usa 3 500 m³, volumen anunciado (no calibrado).
- Jev acierta el 12,5 % frente al solver, por debajo del respaldo (16,7 %), de la clase mayoritaria (79,2 %) y del azar (25 %). Eligió S2 en los 24 casos. Sin ejemplos ni resultados del solver en el prompt.
- S2 y S3 no cambian el máximo urbano con 30 y 60 mm; S1 y S4 empeoran el máximo urbano en varios escenarios.

Pendientes:
- Meteocat: el portal apidocs.meteocat.gencat.cat devolvía 404 el 2026-11-10 y la API XEMA exige clave. Hietograma real pendiente; solicitud manual enviada o por enviar (confirmar).
- Red de drenaje real (Aigües del Vendrell).
- Edificios de Catastro.
- Usos del suelo reales.
- Marea.
- Calibración con calados observados.
- Jev: probar few-shot o Score; medir con márgenes > 1 cm.
