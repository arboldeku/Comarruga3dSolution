# Reglas del proyecto (Comarruga Flood Lab)

## Principios
1. **No reinventar.** Antes de implementar algo, busca si ya existe una librería o producto que lo haga (solver de flujo superficial, lectura de MDT, visualización 3D) y úsalo. Anota en `docs/PRIOR_ART.md` qué encontraste y por qué lo usas o descartas.
2. **Cada cifra lleva fuente y fecha.** Si no hay dato, escribe `sin dato`. Nunca inventes valores.
3. **Honestidad del modelo.** Todo resultado se etiqueta "estimación preliminar, modelo simplificado". No compares con estudios oficiales sin validarlo.
4. **Reparto de papeles.** El solver calcula; Jev decide; el LLM generativo explica. La aritmética y los invariantes (conservación de volumen, límites físicos) viven en código determinista.
5. **Jev siempre con respaldo.** Cada llamada a Jev tiene un camino determinista alternativo y se puede ejecutar en modo sombra (decide, se registra, no actúa).
6. **Datos crudos inmutables.** Todo lo descargado va a `data/raw/` con fuente, fecha de descarga y hash SHA-256 en `data/raw/MANIFEST.json`. No se edita nunca.
7. **Dato derivado reproducible.** Todo lo de `data/processed/` se regenera con un script a partir de `raw/`.
8. **Secretos fuera del repo.** Claves solo en variables de entorno (ver `.env.example`). Nunca en código, logs ni commits.
9. **Reproducibilidad.** Cada ejecución guarda versión de datos, parámetros y semilla en su JSON de resultados.

## Convenciones
- Python 3.11+, tipado, funciones puras para el solver.
- Contratos de datos en `docs/CONTRACTS.md`; no los cambies sin actualizarlos.
- Commits pequeños y frecuentes; la demo debe poder funcionar en cualquier commit de `main`.

## Respuestas en grafo o diagrama
Si el usuario pide "en grafo" o "en diagrama", o aporta una imagen de diagrama, aplica la skill `diagramas` (`.claude/skills/diagramas/SKILL.md`).

## Lo que NO se hace en el MVP
Supabase, Discord, Telegram, multi-zona, validación con Iber/HEC-RAS. Están en `docs/ROADMAP.md`.
