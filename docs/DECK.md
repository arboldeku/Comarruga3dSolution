# Comarruga Flood Lab: deck del hackathon

# 1 · Problema

- Testimonio del autor: 1 entrada de agua en viviendas de Comarruga en 27 años; 2 solo en 2026.
- Pendiente de verificar con fuentes oficiales y vecinos. Sin dato verificable en el repo.
- Hipótesis del autor, no demostrada: que las obras del Riuet hayan causado inundaciones.
- Hipótesis alternativas a contrastar: drenaje o alcantarillado saturado; marea y nivel del mar (cota fija 0 m, sin marea); sedimentos o falta de mantenimiento del cauce; intensidad de lluvia en 30 min.
- Objetivo a largo plazo: aportar evidencia cuantificable a los ayuntamientos. Este repo es un MVP de hackathon.

*Testimonio del autor, pendiente de verificar · terreno: MDT real del ICGC 5 m (1 km², Brisamar / Coma-ruga)*

---

# 2 · Enfoque

- **Solver calcula:** calados con landlab OverlandFlow y un envoltorio propio. Jev nunca calcula aritmética hidráulica.
- **Jev decide:** elige la solución (S1–S4) por punto negro y lluvia, con probabilidades, en modo sombra. Respaldo determinista siempre calculado.
- **LLM explica:** redacta la explicación a partir de la decisión ya tomada (papel previsto; no evaluado en este MVP).

**Datos reales usados: MDT ICGC 5 m; totales de lluvia de comunicado municipal y prensa; volumen anunciado del depósito.**

*Estimación preliminar, modelo simplificado · modelo sin calibrar · supuestos: usos del suelo, sin alcantarillado, nivel del mar fijo, duración de lluvia 60 min*

---

# 3 · Demo

- Abrir: `python -m http.server 8000` y entrar en http://localhost:8000/web/
- Parámetros opcionales: `?rain=60&sol=S1&mode=before|after|diff`.
- Qué enseñar:
  - Lluvia de 100 mm con S1: mayor reducción del calado máximo urbano (8,0 cm, 3,6 %).
  - Comparar antes y después con `mode=before|after|diff`. Con 60 mm, S1 empeora el máximo urbano (−29,0 cm): enseñarlo como contraejemplo.
  - Panel de decisiones de Jev: mostrar el acierto real (12,5 %, frente a 16,7 % del respaldo, 79,2 % de la clase mayoritaria y 25 % del azar). Jev eligió S2 en los 24 casos; no venderlo como acierto.
- Terreno: MDT real del ICGC, sin calibrar.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*

---

# 4 · KPIs del solver y de las soluciones

- 15 de 15 escenarios válidos. Error de volumen máximo: 0,449 %.
- Tiempo por escenario: media 123,2 s, máximo 157,2 s (medido en el JSON). El tiempo de pared (~167 s con 10 procesos) no está registrado en el JSON.
- Calado máximo urbano (frente a S0):
  - Mayor reducción en cm: S1 con 100 mm, 8,0 cm (3,6 %).
  - Mayor reducción en %: S4 con 60 mm, 7,2 cm (4,7 %).
- Empeoran el máximo urbano: S1 con 30 mm (−5,6 cm) y 60 mm (−29,0 cm); S4 con 30 mm (−9,3 cm) y 100 mm (−4,0 cm); S2 con 100 mm (−0,1 cm).
- S2 y S3 no cambian el máximo urbano con 30 y 60 mm. Causa pendiente de revisar.
- Área inundada: S1 aumenta la reducción (+3,7 %, +14,9 %, +12,6 %); S4 la aumenta solo con 100 mm (+0,2 %) y la empeora con 30 mm (−6,6 %) y 60 mm (−1,9 %).
- Parámetros de solver y de S1–S4: supuestos del modelo, sin calibrar.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json y results/index.json, 2026-11-10*

---

# 5 · KPIs de Jev (24 decisiones, modo sombra)

- Acierto frente al solver: **Jev 12,5 %** (3 de 24); respaldo determinista 16,7 % (4 de 24).
- Elegir siempre la clase mayoritaria (S1): 79,2 % (19 de 24). Azar: 25 %.
- Jev eligió la misma opción en todos los casos: **S2 en 24 de 24**. El mejor resultado del solver fue S1 en 19, S2 en 3 y S4 en 2.
- Con margen ≥ 1 cm: Jev 0,0 % frente a respaldo 0,0 % (n = 16). Excluyendo empates: Jev 0,0 % frente a respaldo 5,9 %.
- La clase mayoritaria se beneficia de 7 empates que el convenio resuelve a favor de S1.
- Los 24 casos son 8 puntos × 3 lluvias, no independientes. Sin acierto demostrado.
- Latencia medida: p50 407,9 ms; p95 933,5 ms (rango más cercano, n = 24).
- Coste estimado: 0,000034 USD por decisión; 0,000819714 USD en total (a partir de tokens; 0,042 USD por millón de tokens de entrada; la API no devuelve coste).
- Respaldo usado: 0 %.
- Valor demostrado: latencia y coste medidos. Valor frente al respaldo no demostrado (el respaldo es local, sin coste de API, y acierta más).

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*

---

# 6 · Limitaciones honestas

- Modelo sin calibrar. Terreno real (MDT ICGC 5 m), pero con supuestos:
  - Usos del suelo: todo el terreno emergido tratado como urbano; eje de drenaje derivado del MDT.
  - Sin red de alcantarillado: los calados salen altos.
  - Nivel del mar fijo a 0 m, sin marea.
  - Lluvia de 60 min constante; sin hietograma real (Meteocat pendiente).
  - Ubicación del depósito supuesta.
- Lluvias: 100 mm de comunicado municipal; 60 mm de prensa, pendiente de contrastar; 30 mm de referencia.
- Volumen de S2 (3 500 m³): volumen anunciado, no calibrado.
- S2 y S3 sin efecto en el máximo urbano con 30 y 60 mm. S4 empeora el máximo con 30 y 100 mm.
- Jev está sobreconfiado: probabilidad media asignada a la opción elegida 47,0 % frente a acierto 12,5 % (n = 24, orientativo).
- Episodios reales: sin dato verificable. Las soluciones S1–S4 son supuestos del modelo, no proyectos reales.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*

---

# 7 · Siguientes pasos

- Red de drenaje real (Aigües del Vendrell) y edificios de Catastro.
- Hietograma real de Meteocat (portal sin respuesta el 2026-11-10; API XEMA con clave; solicitud manual pendiente de confirmar).
- Usos del suelo reales; marea.
- Calibrar con calados observados.
- Jev: probar few-shot o Score, y medir con márgenes > 1 cm.
- Verificar los episodios con fuentes oficiales y vecinos.
- Validación de un técnico hidráulico (Iber o HEC-RAS 2D) antes de presentar a un ayuntamiento.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*
