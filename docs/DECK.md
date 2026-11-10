# Comarruga Flood Lab: deck del hackathon

# 1 · Problema

- Testimonio del autor: 1 entrada de agua en viviendas de Comarruga en 27 años; 2 solo en 2026.
- Pendiente de verificar con fuentes oficiales y vecinos. Sin dato verificable en el repo.
- Hipótesis del autor, no demostrada: que las obras del Riuet hayan causado inundaciones.
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
  - Lluvia de 60 mm con S1: mayor reducción de calado máximo del conjunto (27,6 cm).
  - Comparar antes y después con `mode=before|after|diff`.
  - Panel de decisiones de Jev: mostrar el acierto real (16,7 %), no venderlo como acierto.
- No enseñar H2 como cifra fiable: hay un artefacto numérico conocido.

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 4 · KPIs del solver y de las soluciones

- 15 de 15 escenarios válidos. Error de volumen máximo: 1,513 %.
- Calculado en ~167 s con OMP_NUM_THREADS=1 y 10 procesos (dato del equipo, 2026-11-10).
- Mayor reducción de calado máximo: S1 con 60 mm, 27,6 cm (25,4 %).
- S3 reduce el calado máximo en 11,1 cm (14,6 %) con 30 mm, 4,6 cm con 60 mm y 2,1 cm con 100 mm.
- S4 aumenta el área inundada en los tres escenarios de lluvia (−106,3 %, −54,6 % y −21,0 %).

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 5 · KPIs de Jev (24 decisiones, modo sombra)

- Acierto frente al solver: **16,7 %**.
- Frente al respaldo determinista: 33,3 %. Frente a elegir siempre la clase mayoritaria (S3): 83,3 %. Frente al azar: 25 %.
- Por debajo del respaldo y del azar. 12 de 24 casos tienen margen < 1 cm: el acierto es ruidoso.
- Latencia: p50 346,4 ms; p95 548,5 ms.
- Coste estimado por decisión: 0,000034276 USD (total 0,000822612 USD). Estimado a partir de tokens.
- Respaldo usado: 0 %.
- Valor demostrado: latencia, coste y tubería de contraste. Valor no demostrado: acierto.

*Estimación preliminar, modelo simplificado · terreno SINTÉTICO · fuente: results/kpis_summary.json, 2026-11-10*

---

# 6 · Limitaciones honestas

- Terreno sintético. El MDT real del ICGC no está disponible.
- Artefacto numérico en H2: el calado máximo no crece con la lluvia.
- S4 nunca es la mejor y aumenta el área inundada. S2 está infrautilizado por el umbral de toma.
- Varios puntos negros son someros (12–15 cm con 100 mm).
- Jev está sobreconfiado (confianza media 37,9 % frente a acierto 16,7 %; n = 24, orientativo).
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
