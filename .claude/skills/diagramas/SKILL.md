---
name: diagramas
description: Responder en grafo o diagrama cuando el usuario lo pida, e interpretar diagramas que el usuario aporte. Úsala cuando el usuario diga "en grafo", "en diagrama", "dibújalo", "esquema", o adjunte una imagen de un diagrama.
---

# Skill: respuestas en grafo o diagrama

## Elegir formato
- Si el usuario dice "en grafo" o "en diagrama", responde con un diagrama.
- Si dice "en texto", responde en texto.
- Si no lo dice, usa texto, y ofrece el diagrama en una línea cuando la información tenga estructura (flujos, dependencias, arquitectura).
- Si el usuario pide ambos, diagrama primero y texto breve debajo.

## Generar
- Escribe el diagrama en **Mermaid** (`flowchart`, `sequenceDiagram`, `erDiagram` según el caso) y guárdalo en `docs/diagrams/<nombre>.md` dentro de un bloque ```mermaid.
- Máximo 10 nodos por diagrama; si hay más, divide en varios.
- Etiquetas cortas, en español, sin tildes problemáticas en los identificadores de nodo.
- Incluye en el mensaje el diagrama y la ruta del archivo.

## Interpretar
Cuando el usuario aporte una imagen de diagrama:
1. Transcribe nodos y relaciones a Mermaid para confirmar que lo has entendido.
2. Señala ambigüedades o flechas poco claras.
3. Responde a lo que pida, en el formato que indique (texto o diagrama).

## Reglas
- No inventes nodos que no estén en la información de partida.
- Mantén el etiquetado de rigor: si el diagrama muestra resultados del modelo, añade "estimación preliminar".
