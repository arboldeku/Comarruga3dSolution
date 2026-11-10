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
  - Lluvia de 100 mm con S3: mayor reducción del calado máximo urbano (61,0 cm, 27,3 %), con la salvedad del supuesto de usos del suelo.
  - Comparar antes y después con `mode=before|after|diff`. Con 60 mm, S1 empeora el máximo urbano (−29,0 cm): enseñarlo como contraejemplo.
  - Panel de decisiones de Jev: mostrar el acierto real (0 %, frente a 4,2 % del respaldo, 79,2 % de la clase mayoritaria S3 y 25 % del azar). Jev eligió S2 en los 24 casos; no venderlo como acierto.
- Terreno: MDT real del ICGC, sin calibrar.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*

---

# 4 · KPIs del solver y de las soluciones

- 15 de 15 escenarios válidos. Error de volumen máximo: 1,054 %.
- Tiempo por escenario: media 94,1 s, máximo 117,5 s (medido en el JSON). El tiempo de pared (~167 s con 10 procesos) no está registrado en el JSON.
- Calado máximo urbano (frente a S0):
  - Mayor reducción en cm: S3 con 100 mm, 61,0 cm (27,3 %).
  - Mayor reducción en %: S3 con 30 mm, 46,9 cm (46,2 %).
- Empeoran el máximo urbano: S1 con 30 mm (−5,6 cm) y 60 mm (−29,0 cm), y sube también el máximo global; S4 con 30 mm (−9,3 cm) y 100 mm (−4,0 cm). S2 no cambia el máximo urbano en ningún escenario.
- S2 no llega a usarse en el modelo: pico de 9,3 m³ con 100 mm; sus resultados son iguales a S0 porque la ubicación supuesta apenas recibe agua. Es una limitación de la ubicación supuesta, no una conclusión sobre el depósito real.
- S3 mejora el máximo urbano en los tres escenarios, pero su ventaja está inflada por el supuesto de usos del suelo (todo el terreno emergido tratado como urbano, con 40 % permeable).
- Área inundada (30 / 60 / 100 mm; negativo = aumenta): S1 +3,7 %, +14,9 %, +12,6 %; S3 +73,6 %, +32,0 %, +14,9 %; S4 −6,6 %, −1,9 %, +0,2 %; S2 0,0 %.
- Parámetros de solver y de S1–S4: supuestos del modelo, sin calibrar.

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json y results/index.json, 2026-11-10*

---

# 5 · KPIs de Jev (24 decisiones, modo sombra)

- Acierto frente al solver: **Jev 0 %** (0 de 24); respaldo determinista 4,2 % (1 de 24).
- Elegir siempre la clase mayoritaria (S3): 79,2 % (19 de 24). Azar: 25 %.
- Jev eligió la misma opción en todos los casos: **S2 en 24 de 24**. El mejor resultado del solver fue S3 en 19 y S1 en 5.
- Con margen ≥ 1 cm: Jev 0,0 % frente a respaldo 4,8 % (n = 21). Excluyendo empates: Jev 0,0 % frente a respaldo 4,3 %.
- Los 24 casos son 8 puntos × 3 lluvias, no independientes. Sin acierto demostrado.
- Latencia medida: p50 392,3 ms; p95 681,6 ms (rango más cercano, n = 24).
- Coste estimado: 0,000034 USD por decisión; 0,000828 USD en total (a partir de tokens; 0,042 USD por millón de tokens de entrada; la API no devuelve coste).
- Respaldo usado: 0 %.
- Valor demostrado: latencia y coste medidos. Valor frente al respaldo no demostrado (el respaldo es local, sin coste de API, y acierta más).

*Estimación preliminar, modelo simplificado · modelo sin calibrar · fuente: results/kpis_summary.json, 2026-11-10*

---

# 6 · Limitaciones honestas

- Modelo sin calibrar. Terreno real (MDT ICGC 5 m), pero con supuestos:
  - Usos del suelo: todo el terreno emergido tratado como urbano; eje de drenaje derivado del MDT.
  - Sin red de alcantarillado: los calados salen altos. Calados de 1 a 2,2 m: se dan en hoyos cerrados del propio MDT (aspecto de pasos inferiores); son cota superior, no calados esperables.
  - Nivel del mar fijo a 0 m, sin marea.
  - Lluvia de 60 min constante; sin hietograma real (Meteocat pendiente).
  - Ubicación del depósito supuesta.
- Lluvias: 100 mm de comunicado municipal; 60 mm de prensa, pendiente de contrastar; 30 mm de referencia.
- Volumen de S2 (3 500 m³): volumen anunciado, no calibrado.
- S2 sin efecto en el máximo urbano en ningún escenario. S1 empeora con 30 y 60 mm; S4 con 30 y 100 mm. La ventaja de S3 está inflada por el supuesto de usos del suelo.
- Jev está sobreconfiado: probabilidad media asignada a la opción elegida 53,1 % frente a acierto 0 % (n = 24, orientativo).
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
