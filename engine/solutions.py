"""Soluciones candidatas S0-S4 (contrato 2) y sus parámetros por defecto.

TODOS los parámetros son SUPUESTOS DEL MODELO para la demo, no proyectos reales
ni dimensionamientos de ingeniería. Etiqueta: estimación preliminar, modelo simplificado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from scipy.ndimage import binary_dilation, distance_transform_cdt, distance_transform_edt, minimum_filter

from .synthetic_terrain import REAL_ASC, URBAN_ROWS, Terrain

# Infiltración base (mm/h). Supuestos genéricos, sin calibrar.
INFILTRATION_MM_H = {"non_urban": 20.0, "urban": 3.0, "channel": 5.0}
REAL = REAL_ASC.exists()
S2_SOURCE = ("capacity_m3 = 3500: volumen ANUNCIADO por el Ayuntamiento de El Vendrell el 26/08/2026 "
             "para el depósito de Brisamar; es un anuncio, no un volumen hidráulico calibrado; la "
             "ubicación exacta es un supuesto (depresión urbana más honda del MDT)")
SOLUTION_SOURCES = {"S0": "supuesto del modelo", "S1": "supuesto del modelo",
                    "S2": S2_SOURCE if REAL else "supuesto del modelo",
                    "S3": "supuesto del modelo", "S4": "supuesto del modelo"}

SOLUTION_NAMES = {
    "S0": "Situación actual (línea base)",
    "S1": "Ampliar sección del cauce",
    "S2": "Depósito de retención",
    "S3": "Pavimento permeable (SUDS)",
    "S4": "Elevar bordillos / desviar",
}

DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "S0": {},
    # Rebaja el lecho `depth_m` y ensancha `width_cells` celdas a cada lado, en el tramo urbano.
    "S1": {"depth_m": 0.5, "width_cells": 1, "rows": [URBAN_ROWS[0] - 5, 200]},
    # Depósito en línea sobre el cauce, aguas arriba del tramo urbano: capta el agua que
    # supera `intake_depth_m` (hasta `max_inflow_m3s`) y la devuelve al cauce aguas abajo
    # de la toma a `max_outflow_m3s` como máximo (caudal máximo de vaciado).
    "S2": {"capacity_m3": 8000.0, "max_outflow_m3s": 0.3, "max_inflow_m3s": 6.0,
           "intake_depth_m": 0.35, "rows": [76, 82]},
    # Fracción de celdas urbanas (elegidas al azar con la semilla) con infiltración aumentada.
    "S3": {"area_fraction": 0.4, "infiltration_mm_h": 60.0},
    # Barreras continuas en ambas márgenes del cauce en el tramo urbano. El contrato habla de
    # aristas de celda; aquí se aproximan elevando celdas (2 celdas de ancho por margen para
    # que la barrera sea estanca en una malla de 4 vecinos).
    "S4": {"height_m": 0.5, "offset_cells": 3, "rows": [URBAN_ROWS[0], URBAN_ROWS[1] - 5]},
}


if REAL:
    # MDT real: el "cauce" es el eje de drenaje derivado del MDT (landuse 2), en todo el recorte.
    DEFAULT_PARAMS["S1"] = {"depth_m": 0.5, "width_cells": 1, "min_bed_m": 0.05}
    # Depósito: capta en un disco de `radius_cells` sobre la depresión urbana más honda y
    # devuelve a la celda del eje de drenaje más cercana. Umbral de toma bajo para que se use.
    DEFAULT_PARAMS["S2"] = {"capacity_m3": 3500.0, "max_outflow_m3s": 0.3, "max_inflow_m3s": 6.0,
                            "intake_depth_m": 0.10, "radius_cells": 3,
                            # vaciado solo tras la lluvia (supuesto de operación): si no, el
                            # caudal devuelto vuelve a la misma depresión y el depósito no se llena
                            "release_after_rain": True,
                            "location": "depresión urbana más honda (supuesto)"}
    # Barreras a `offset_cells` celdas (distancia de tablero) a ambos lados del eje, 2 de ancho.
    DEFAULT_PARAMS["S4"] = {"height_m": 0.5, "offset_cells": 3}


@dataclass
class Setup:
    """Entradas del solver ya modificadas por la solución."""
    z: np.ndarray                                # (ny, nx) float64
    infil_m_s: np.ndarray                        # (ny, nx)
    tank_cells: np.ndarray | None = None         # máscara bool de captación
    tank_release: np.ndarray | None = None       # máscara bool de devolución al cauce
    tank: dict[str, float] = field(default_factory=dict)
    sea: np.ndarray | None = None                # máscara bool de mar (contorno abierto a cota 0)


def resolve_params(solution_id: str, params: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_PARAMS[solution_id], **(params or {})}


def apply_solution(t: Terrain, solution_id: str, params: dict[str, Any] | None, seed: int) -> Setup:
    p = resolve_params(solution_id, params)
    z = t.dem.astype(np.float64).copy()
    lu = t.landuse
    ny, nx = z.shape
    infil = np.full(z.shape, INFILTRATION_MM_H["non_urban"])
    infil[lu == 1] = INFILTRATION_MM_H["urban"]
    infil[lu == 2] = INFILTRATION_MM_H["channel"]
    setup = Setup(z=z, infil_m_s=infil)
    chan = lu == 2
    sea = lu == 3
    if sea.any():
        setup.sea = sea
        infil[sea] = 0.0

    if sea.any() and solution_id == "S1":
        w = int(p["width_cells"])
        k = np.ones((2 * w + 1, 2 * w + 1), bool)
        dil = binary_dilation(chan, structure=k) & ~sea
        bed = minimum_filter(np.where(chan, z, np.inf), footprint=k)
        new = np.minimum(z, bed) - p["depth_m"]
        new = np.maximum(new, np.minimum(z, p["min_bed_m"]))   # no excavar por debajo del mar
        z[dil] = new[dil]
    elif sea.any() and solution_id == "S2":
        tx, ty = t.tank_xy
        yy, xx = np.ogrid[:ny, :nx]
        setup.tank_cells = ((yy - ty) ** 2 + (xx - tx) ** 2 <= int(p["radius_cells"]) ** 2) & ~sea
        _, (iy, ix) = distance_transform_edt(~chan, return_indices=True)
        setup.tank_release = np.zeros_like(chan)
        setup.tank_release[iy[ty, tx], ix[ty, tx]] = True
        setup.tank = {k_: float(p[k_]) for k_ in
                      ("capacity_m3", "max_outflow_m3s", "max_inflow_m3s", "intake_depth_m",
                       "release_after_rain")}
    elif sea.any() and solution_id == "S4":
        k = int(p["offset_cells"])
        d = distance_transform_cdt(~chan, metric="chessboard")
        z[((d == k) | (d == k + 1)) & ~sea] += p["height_m"]
    elif sea.any() or solution_id in ("S0", "S3"):
        pass                                       # S3 se aplica más abajo; S0 no cambia nada
    elif solution_id == "S1":
        r0, r1 = p["rows"]
        w = int(p["width_cells"])
        for r in range(max(r0, 0), min(r1, ny)):
            cols = np.flatnonzero(chan[r])
            if cols.size == 0:
                continue
            bed = z[r, cols].min()
            a, b = max(cols.min() - w, 0), min(cols.max() + w, nx - 1)
            z[r, a:b + 1] = np.minimum(z[r, a:b + 1], bed) - p["depth_m"]
    elif solution_id == "S2":
        r0, r1 = p["rows"]
        mask = np.zeros_like(chan)
        mask[r0:r1] = chan[r0:r1]
        setup.tank_cells = mask
        rr = r1 + 2
        setup.tank_release = np.zeros_like(chan)
        setup.tank_release[rr] = chan[rr]          # devolución repartida en la sección del cauce
        setup.tank = {k: float(p[k]) for k in
                      ("capacity_m3", "max_outflow_m3s", "max_inflow_m3s", "intake_depth_m")}
    if solution_id == "S3":
        rng = np.random.default_rng(seed)
        urban = np.flatnonzero(lu.ravel() == 1)
        pick = rng.choice(urban, size=int(round(p["area_fraction"] * urban.size)), replace=False)
        infil.ravel()[pick] = p["infiltration_mm_h"]
    elif solution_id == "S4" and not sea.any():
        r0, r1 = p["rows"]
        k = int(p["offset_cells"])
        for r in range(r0, r1):
            cols = np.flatnonzero(chan[r])
            if cols.size == 0:
                continue
            for cb in (cols.min() - k, cols.min() - k - 1, cols.max() + k, cols.max() + k + 1):
                if 0 <= cb < nx:
                    z[r, cb] += p["height_m"]
    setup.infil_m_s = infil / 1000.0 / 3600.0
    return setup
