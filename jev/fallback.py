"""Respaldo determinista (línea base) para elegir entre S1–S4.

Solo usa las características del punto negro y la lluvia. NO mira los resultados del
solver: es la referencia contra la que se mide a Jev, no un oráculo.

Regla (se aplica la primera condición que se cumple). Umbrales = supuestos del autor,
sin calibrar; "estimación preliminar, modelo simplificado":

  R1  dist_to_channel_m <= 30                      -> S1  junto al cauce: el agua viene del
                                                         desbordamiento, ampliar sección.
  R2  depression_depth_m >= 0.30                   -> S2  cubeta cerrada: el agua no tiene
                                                         salida, hace falta retener volumen.
  R3  urban_fraction >= 0.60 y rain_mm <= 40       -> S3  entorno muy urbano y lluvia
                                                         moderada: infiltrar en origen basta.
  R4  slope >= 0.03 y catchment_m2 < 20000         -> S4  ladera con cuenca pequeña: el agua
                                                         pasa de largo, desviar con bordillos.
  R5  en otro caso                                 -> S2  cuenca grande o caso dudoso: depósito.
"""
from __future__ import annotations

from typing import Mapping

OPTIONS = ("S1", "S2", "S3", "S4")

NEAR_CHANNEL_M = 30.0
DEPRESSION_M = 0.30
URBAN_FRACTION = 0.60
MODERATE_RAIN_MM = 40.0
STEEP_SLOPE = 0.03
SMALL_CATCHMENT_M2 = 20000.0


def _f(features: Mapping, name: str, default: float) -> float:
    try:
        return float(features.get(name, default))
    except (TypeError, ValueError):
        return default


def decide(features: Mapping, rain_mm: float) -> dict:
    """Devuelve {"choice": "Sx", "rule": "<regla aplicada>"}. Función pura."""
    dist = _f(features, "dist_to_channel_m", float("inf"))
    depr = _f(features, "depression_depth_m", 0.0)
    urban = _f(features, "urban_fraction", 0.0)
    slope = _f(features, "slope", 0.0)
    catch = _f(features, "catchment_m2", 0.0)
    rain = float(rain_mm)

    if dist <= NEAR_CHANNEL_M:
        return {"choice": "S1", "rule": f"R1: dist_to_channel_m <= {NEAR_CHANNEL_M:g} -> ampliar cauce"}
    if depr >= DEPRESSION_M:
        return {"choice": "S2", "rule": f"R2: depression_depth_m >= {DEPRESSION_M:g} -> depósito de retención"}
    if urban >= URBAN_FRACTION and rain <= MODERATE_RAIN_MM:
        return {"choice": "S3", "rule": f"R3: urban_fraction >= {URBAN_FRACTION:g} y lluvia <= {MODERATE_RAIN_MM:g} mm -> pavimento permeable"}
    if slope >= STEEP_SLOPE and catch < SMALL_CATCHMENT_M2:
        return {"choice": "S4", "rule": f"R4: slope >= {STEEP_SLOPE:g} y catchment_m2 < {SMALL_CATCHMENT_M2:g} -> bordillos / desvío"}
    return {"choice": "S2", "rule": "R5: caso por defecto -> depósito de retención"}
