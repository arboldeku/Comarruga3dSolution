# Continuación del proyecto y qué modelo usar en cada tarea

Fecha: 10 de noviembre de 2026. Punto de partida: el estado del repo tras el hackathon (ver `docs/STAR.md`).

> La tabla de modelos caduca rápido. Lo que no caduca es el criterio de la sección 2: elige por tipo de tarea, no por nombre de modelo.

## 1. Dónde estamos

- Simulador sobre el relieve real de Brisamar (MDT ICGC 5 m), con ortofoto y edificios del Catastro, 15 escenarios válidos.
- Modelo **sin calibrar**, sin alcantarillado, con usos del suelo y duración de lluvia supuestos.
- Jev medido en modo sombra: 0 % de acierto en la tarea que se le dio. No es obligatorio seguir usándolo.

Objetivo de la continuación: pasar de demo a herramienta defendible ante un técnico y un ayuntamiento. El orden es datos → modelo físico → calibración → capa de decisión → producto → validación externa.

## 2. Criterio para elegir modelo y esfuerzo

| Modelo | Úsalo cuando… | No lo uses para… |
|---|---|---|
| **Fable 5.2** | Un error cuesta caro y no se ve a simple vista: decisiones de física, arquitectura, auditoría final, texto que firma alguien | Tareas mecánicas o con receta clara |
| **Opus 5.5** | Trabajo técnico difícil pero acotado: implementar el acoplamiento de modelos, depurar un solver, revisar un cambio grande | Redacción rutinaria, descargas |
| **Sonnet 5.5** | El grueso del código: ingesta de datos, visor, tests, scripts, refactorizaciones | Decidir qué es físicamente correcto |
| **Haiku** | Mecánico y verificable: reformatear, actualizar cifras desde un JSON, manifiestos, traducciones, clasificar en lote | Cualquier cosa donde haya que juzgar |

**Esfuerzo (High / Medium / Low):**
- **High:** cuando hay que razonar sobre algo que no se puede comprobar ejecutando (supuestos físicos, interpretación de resultados, diseño).
- **Medium:** por defecto para código que se valida con tests.
- **Low:** cuando la tarea es una receta y el resultado se comprueba solo (un script que pasa o no pasa).

**Tres reglas que salieron del hackathon:**
1. Si la tarea se puede verificar con un test o contra un JSON, baja de modelo. Si solo se puede verificar pensando, sube.
2. Un subagente barato con un encargo largo sale más caro que uno bueno con un encargo corto. El arreglo más caro del hackathon fue un Haiku con 13 puntos.
3. Quien escribe las cifras no las audita. La auditoría va siempre en un modelo distinto y más fuerte que el que redactó.

## 3. Tareas por fase

### Fase 1 · Datos (2–3 semanas)

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Descargar relieve de 1 m / 50 cm del ICGC y registrar en el manifiesto | Haiku | Low | Receta; se comprueba con el hash y las dimensiones |
| Ingesta de lluvia de Meteocat (cuando haya clave) e IDF | Sonnet 5.5 | Low | API documentada; se valida sumando los intervalos |
| Usos del suelo e impermeabilidad (ICGC, Copernicus) | Sonnet 5.5 | Medium | Reproyección y cruce de capas; errores de CRS son fáciles de cometer |
| Edificios como obstáculos en la malla | Sonnet 5.5 | Medium | Geometría con test visual y de masa |
| Revisar datum vertical al combinar relieve, mar y marea | Opus 5.5 | High | Un error de referencia altimétrica no se ve y lo estropea todo |
| Redactar las peticiones a Aigües del Vendrell y al Ayuntamiento | Sonnet 5.5 | Medium | Texto formal; lo revisas tú |
| Clasificar y geolocalizar fotos y avisos de vecinos | Haiku | Low | Lote grande y repetitivo; muestrea un 10 % a mano |

### Fase 2 · Modelo hidráulico (3–4 semanas)

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Elegir solver (Iber, HEC-RAS 2D, otro) y diseño del acoplamiento con SWMM | Fable 5.2 | High | Decisión de arquitectura difícil de deshacer |
| Implementar el acoplamiento superficie–red | Opus 5.5 | High | Técnicamente delicado: intercambio de caudales y conservación de masa |
| Construir el modelo SWMM a partir del inventario de la red | Sonnet 5.5 | Medium | Laborioso pero guiado por los datos |
| Definir las soluciones con ubicación y dimensiones realistas | Fable 5.2 | High | Juicio físico; aquí falló el depósito del hackathon. Validar con un técnico |
| Scripts de ejecución en lote y exportación de resultados | Sonnet 5.5 | Low | Fontanería |

### Fase 3 · Calibración y validación (2 semanas)

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Diseñar el protocolo: qué se ajusta, contra qué episodio, qué se reserva para validar | Fable 5.2 | High | Evita autoengañarse; define qué se podrá afirmar |
| Ejecutar la calibración y el análisis de sensibilidad | Sonnet 5.5 | Medium | Bucle de simulaciones con métricas claras |
| Interpretar por qué el modelo se desvía en un punto | Opus 5.5 | High | Diagnóstico físico, no receta |
| Tablas y gráficos del informe de calibración | Haiku | Low | Sale de los resultados |

### Fase 4 · Capa de decisión

No es obligatorio un modelo de lenguaje para decidir. La decisión real (qué combinación de obras, con qué presupuesto) se resuelve mejor con métodos clásicos.

| Tarea | Herramienta o modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Modelo sustituto del solver (predice calado en segundos) | Gradient boosting o proceso gaussiano, no un LLM | — | Auditable y entrenado con simulaciones propias |
| Programar el sustituto y su validación | Sonnet 5.5 | Medium | Aprendizaje automático estándar con test de error |
| Optimización multiobjetivo coste / reducción de daño | NSGA-II u otro algoritmo evolutivo, no un LLM | — | Devuelve la frontera de opciones |
| Plantear la función de daño y el análisis coste-beneficio | Fable 5.2 | High | Es donde se cuelan los supuestos que cambian la conclusión |
| Explicar los resultados en lenguaje llano | Sonnet 5.5 | Medium | Redacción a partir de una decisión ya tomada |
| Triaje de avisos vecinales (segunda oportunidad para Jev, opcional) | Jev o Haiku, comparados entre sí y contra una regla simple | Low | Tarea de criterio con ejemplos; solo se adopta si supera la regla |

### Fase 5 · Producto e ingeniería (en paralelo)

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Línea de tiempo, comparación lado a lado, panel "Datos y límites" | Sonnet 5.5 | Medium | Interfaz; se valida mirándola |
| Arreglos pequeños del visor (el cauce en rojo, estilos) | Haiku o Sonnet 5.5 | Low | Acotado |
| Tests automáticos de balance de masa y KPIs | Sonnet 5.5 | Low | Receta |
| Mantener README, deck y manifiestos al día | Haiku | Low | Copiar cifras desde el JSON; encargos cortos |
| Revisión de cada cambio grande antes de fusionar | Opus 5.5 | Medium | Segundo par de ojos |

### Fase 6 · Validación externa

| Tarea | Modelo | Esfuerzo | Por qué |
|---|---|---|---|
| Auditoría completa antes de enseñar cifras fuera | Fable 5.2 | High | Última barrera; debe intentar tumbar las conclusiones |
| Dossier para el ayuntamiento | Fable 5.2 | High | Texto con consecuencias; cuidar la hipótesis del Riuet |
| Revisión por ingeniero hidráulico y por letrado | Personas, no modelos | — | Ningún modelo sustituye una firma |

## 4. Qué hacer mañana

1. Enviar la solicitud a Meteocat y la petición del inventario de drenaje (redacción con Sonnet 5.5, Medium).
2. Recoger fotos con hora y lugar de los vecinos.
3. Bajar el relieve de 1 m y meter los edificios como obstáculos (Sonnet 5.5, Medium).
4. Pasar el auditor sobre el estado actual del repo (Fable 5.2, High): la segunda versión del hackathon quedó sin auditar.

## 5. Reparto orientativo del gasto

La mayor parte del volumen debería ir a Sonnet 5.5 y Haiku, y Fable 5.2 reservarse para unas pocas decisiones y las auditorías. Si Fable 5.2 se lleva más de una quinta parte del gasto, es señal de que se le están dando tareas con receta.
