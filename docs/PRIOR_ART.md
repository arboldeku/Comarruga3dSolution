# Prior art y decisiones (no reinventar)

Fecha de consulta de todo lo que sigue: 2026-11-10.

## Capa de decisión: Jev (TypeSafe AI) vía OpenRouter
- **Qué es:** modelo no generativo ("System One"): recibe estado + pregunta tipada y devuelve una respuesta tipada con probabilidades. Primitivas documentadas: Choice, Noul, Score y Box (Box solo en Jev 1.14).
  Fuente: https://openrouter.ai/blog/insights/what-is-jev/ (actualizado 2026-10-16).
- **Cómo se llama:** `POST https://openrouter.ai/api/alpha/decisions`. Formato fijado en `docs/CONTRACTS.md` §6.2.
  Fuente: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request.md y https://openrouter.ai/docs/guides/community/jev-tutorial
- **IDs de modelo que aparecen en la documentación:** `typesafe/jev-1.14` (actual según blog y hub, publicado 2026-10-14), `typesafe/jev-1.13`, alias `~typesafe/jev-latest`. El tutorial todavía cita 1.13 (parece desactualizado). El repo **no fija ninguno**: se lee de `JEV_MODEL_ID`.
- **Precio:** 0,042 USD por millón de tokens de entrada, salida gratis (blog de OpenRouter, 2026-10-16). Página del modelo no consultada: verificar antes de citar en el deck. Límites de tasa: sin dato.
- **Decisión:** cliente HTTP propio mínimo con `requests` (un POST). Se descarta el SDK de TypeSafe (`/api/v1/systemone`) porque no está en la referencia de la API de OpenRouter y añade una dependencia sin necesidad.
- **Uso en este proyecto:** una pregunta Choice por punto negro y lluvia (opciones S1–S4), en modo sombra, con respaldo determinista y contraste con el solver.
