# Comarruga Flood Lab: la sesión explicada con el método STAR

Fecha: 10 de noviembre de 2026. Todas las cifras son **estimaciones preliminares de un modelo simplificado y sin calibrar**. Fuente de las cifras: `results/kpis_summary.json` y `results/index.json` de ese día.

## S · Situación: de qué problema partíamos

En Coma-ruga (El Vendrell) el agua entra en las casas cada vez más a menudo. El autor cuenta que en 27 años le entró una vez y que en 2026 ya van dos (es su testimonio, pendiente de verificar). El 22 de agosto de 2026 cayeron 100 mm en Coma-ruga según el Ayuntamiento, y este anunció un depósito de 3.500 m³ en Brisamar.

Nadie puede responder hoy, con números y de forma sencilla, a la pregunta de un vecino: *si llueve tanto y se hace tal obra, ¿cuánta agua me ahorro en mi calle?*

Teníamos dos horas de hackathon, un repositorio vacío y una condición: usar **Jev**, un modelo de inteligencia artificial que no escribe texto sino que toma decisiones con una probabilidad, como pieza que decide.

## T · Tarea: qué había que conseguir

1. Un simulador "¿y si…?": elegir una lluvia y una solución urbanística y ver cuántos centímetros de agua se ahorran.
2. Que Jev eligiera la mejor solución para cada punto conflictivo, y medir si acierta comparándolo con el cálculo físico.
3. Un visor 3D que se abra en el navegador.
4. Honestidad total: cada cifra con su fuente, nada inventado, y sin afirmar que las obras del Riuet causaron las inundaciones (es una hipótesis).

## A · Acciones: qué se hizo

**Primera parte (terreno inventado, para tener algo funcionando)**
- Se montó un equipo de asistentes especializados: uno para el cálculo del agua, otro para el visor, otro para Jev y un auditor.
- No se reinventó nada: el cálculo usa Landlab (una librería científica de flujo de agua) y el visor usa three.js.
- Se definieron cuatro soluciones: S1 ampliar el cauce, S2 depósito de retención, S3 pavimento permeable, S4 elevar bordillos.
- Se conectó Jev de verdad (a través de OpenRouter), en "modo sombra": decide y se apunta lo que decide, pero no manda. Siempre hay una regla sencilla de respaldo por si falla.
- El auditor encontró dos errores graves de interpretación en las cifras y se corrigieron.

**Segunda parte (datos reales y públicos)**
- Se descargó el relieve real de Brisamar del Institut Cartogràfic (ICGC), con una medida cada 5 metros en 1 km².
- Se añadieron la foto aérea del ICGC y 2.013 edificios del Catastro, en 3D.
- Se usaron las lluvias documentadas: 100 mm (comunicado municipal, 22/08/2026) y unos 60 mm (prensa, 02/11/2026, por contrastar), y el volumen anunciado del depósito (3.500 m³).
- Se intentó conseguir la lluvia minuto a minuto de Meteocat: su portal de datos daba error ese día, así que queda pendiente.
- Se recalculó todo y se volvió a preguntar a Jev sobre el terreno real.

## R · Resultados: qué se obtuvo

**Lo que funciona**
- Una demo completa en el navegador, sobre el terreno real, con 15 simulaciones (3 lluvias × 5 situaciones), todas con las cuentas del agua cuadradas (error máximo del 1,05 %).
- Con 100 mm, el modelo estima un 23,3 % de la zona con agua y, en la mejor solución (pavimento permeable), el calado máximo urbano baja de 223,8 a 162,8 cm.
- Ampliar el cauce reduce un 12,6 % la superficie inundada con 100 mm.

**El papel de Jev, sin adornos**
- Respondió las 24 decisiones, en unos 0,4 segundos cada una y por 0,000034 USD cada una (coste estimado).
- **No acertó ninguna: 0 % de acierto.** Eligió el depósito en los 24 casos. Una regla simple acertó el 4,2 % y "decir siempre pavimento permeable" habría acertado el 79,2 %.
- Por qué: a Jev solo se le dieron unos pocos rasgos de cada punto, sin ejemplos, y el depósito del modelo estaba mal colocado y no hacía nada. Jev es rápido y barato, pero así, a ciegas, no sirve para esta decisión.
- Lo valioso es que **lo medimos**: la herramienta detectó que la IA se equivocaba antes de que nadie le hiciera caso.

**Lo que no se puede afirmar todavía**
- Los calados de 1 a 2 metros son un techo, no lo esperable: el modelo no incluye alcantarillado.
- El depósito no llegó a llenarse en el modelo (9 m³ de 3.500) porque su ubicación es un supuesto nuestro. No dice nada sobre el depósito real.
- La ventaja del pavimento permeable está exagerada: sin datos de usos del suelo, se aplicó a demasiada superficie.
- Falta la lluvia real minuto a minuto, la red de drenaje y calibrar con calados observados.

**En una frase:** en dos sesiones pasamos de un repositorio vacío a un simulador sobre el terreno real de Brisamar que compara soluciones con datos públicos, y que demostró con números que la IA de decisión, sin ejemplos, todavía no acierta.
