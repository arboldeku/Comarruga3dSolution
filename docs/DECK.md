# Comarruga Flood Lab: deck del hackathon

# 1 · Problema

- Testimonio del autor: 1 entrada de agua en viviendas de Comarruga en 27 años; 2 solo en 2026.
- Pendiente de verificar con fuentes oficiales y vecinos. Sin dato verificable en el repo.
- Hipótesis del autor, no demostrada: que las obras del Riuet hayan causado inundaciones.
- Hipótesis alternativas a contrastar: drenaje o alcantarillado saturado; marea y nivel del mar (frontera sur abierta, sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min.
- Objetivo a largo plazo: aportar evidencia cuantificable a los ayuntamientos. Este repo es un MVP de hackathon.

*Testimonio del autor, pendiente de verificar · terreno SINTÉTICO (no es Comarruga real)*

---

# 2 · Enfoque

- **Solver calcula:** calados con landlab OverlandFlow y un envoltorio propio. Jev nunca calcula aritmética hidráulica.
- **Jev decide:** elige la solución (S1–S4) por punto negro y lluvia, con probabilidades, en modo sombra. Respaldo determinista siempre calculado.
- **LLM explica:** redacta la explicación a partir de la decisión ya tomada (papel previsto; no evaluado en este MVP).

*Terreno SINTÉTICO (no es Comarruga real)*

---

# 3 · Demo

- Abrir: `python -m http.server 8000` y entrar en http://localhost:8000/web/
- Parámetros opcionales: `?rain=60&sol=S1&mode=before|after|diff`.
- Qué enseñar:
  - Lluvia de 60 mm con S3: mayor reducción de calado máximo urbano (22,8 cm, 28,0 %).
  - Comparar antes y después con `mode=before|after|diff`.
  - Panel de decisiones de Jev: mostrar el acierto real (16,7 % con H2; 9,5 % sin H2, n = 21), no venderlo como acierto.
- No enseñar H2 como cifra fiable: hay un artefacto numérico conocido. Las cifras de 30 mm provienen de H2: no fiables (artefacto H2).

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 4 · KPIs del solver y de las soluciones

- 15 de 15 escenarios válidos. Error de volumen máximo: 1,513 %.
- Calculado en ~167 s con OMP_NUM_THREADS=1 y 10 procesos: medición de la ejecución del 2026-11-10, no registrada en JSON.
- Calado máximo urbano (frente a S0): mayor reducción, S3 con 60 mm: 22,8 cm (28,0 %).
- Soluciones que **empeoran** el máximo urbano: S4 con 30 mm (−6,3 cm), 60 mm (−7,9 cm) y 100 mm (−33,3 cm); S1 con 100 mm (−55,8 cm).
- Dominio completo (incluye cauce): mayor reducción, S1 con 60 mm, 27,6 cm (25,4 %).
- S3 reduce el calado máximo urbano en 11,1 cm (14,6 %) con 30 mm, 0,4 cm con 100 mm y 22,8 cm con 60 mm. Las cifras de 30 mm son no fiables (artefacto H2).
- S4 aumenta el área inundada en los tres escenarios de lluvia (−106,3 % con 30 mm: no fiable, artefacto H2; −54,6 % con 60 mm; −21,0 % con 100 mm).
- Los parámetros del solver y de S1–S4 son supuestos del modelo, sin calibrar. El tiempo de ~167 s es una medición de la ejecución del 2026-11-10, no registrada en JSON.

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 5 · KPIs de Jev (24 decisiones, modo sombra)

- Acierto frente al solver: **16,7 %** con H2 (no fiable, artefacto H2); **9,5 %** excluyendo H2 (n = 21). Respaldo: 33,3 % con H2 y 33,3 % excluyendo H2.
- Frente a elegir siempre la clase mayoritaria (S3): 83,3 %. Frente al azar: 25 %.
- Acierto con margen ≥ 1 cm: Jev 25,0 % frente a respaldo 41,7 % (n = 12).
- Distribución de elecciones de Jev: S2 en 21 de 24, S3 en 3 (casi constante).
- Los 24 casos son 8 puntos × 3 lluvias, no independientes: la diferencia con el respaldo no es concluyente. 12 de 24 casos tienen margen < 1 cm: el acierto es ruidoso.
- Latencia medida: p50 346,4 ms; p95 548,5 ms (rango más cercano, n = 24).
- Precio: 0,042 USD/M tokens de entrada según docs.typesafe.ai/models.md (2026-11-10); precio efectivo en OpenRouter: sin dato. Coste estimado: 0,000034276 USD por decisión (total 0,000822612 USD).
- Respaldo usado: 0 %.
- Valor demostrado: latencia y coste medidos. Valor frente al respaldo no demostrado (el respaldo es local, sin coste de API, y acierta más).

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 6 · Limitaciones honestas

- Terreno sintético. El MDT real del ICGC no está disponible.
- Artefacto numérico en H2: el calado máximo no crece con la lluvia.
- S4 nunca es la mejor y aumenta el área inundada. S2 está infrautilizado por el umbral de toma.
- Varios puntos negros son someros (12–15 cm con 100 mm).
- Jev está sobreconfiado: probabilidad media asignada a la opción elegida 37,9 % frente a acierto 16,7 % (n = 24, orientativo). Confianza media de la API: 0,171.
- Episodios reales: sin dato verificable. Las soluciones S1–S4 son supuestos del modelo, no proyectos reales.

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 7 · Siguientes pasos

- Conseguir el MDT real del ICGC y repetir el cálculo sobre Comarruga.
- Corregir H2 y recalibrar S2 y S4.
- Jev: probar few-shot o Score, y medir con márgenes > 1 cm.
- Verificar los episodios con fuentes oficiales y vecinos.
- Validación de un técnico hidráulico (Iber o HEC-RAS 2D) antes de presentar a un ayuntamiento.

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*
