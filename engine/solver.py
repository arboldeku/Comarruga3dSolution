"""Solver 2D de flujo superficial: envoltorio sobre landlab.components.OverlandFlow
(de Almeida et al. 2012 / Bates et al. 2010, onda inercial local).

Landlab calcula el flujo; aquí se añaden por separación de operadores la lluvia,
la infiltración, el depósito (S2) y la contabilidad de masa:

    lluvia = almacenado + infiltrado + salido por el borde sur + retenido en depósito ± error

El caudal de salida se mide de forma independiente en los enlaces del borde sur
(no se obtiene como residuo), así que `volume_error_pct` es un control real.
Etiqueta: estimación preliminar, modelo simplificado.
"""
from __future__ import annotations

import time
from typing import Any

import numpy as np

from .solutions import Setup

MODEL_NAME = "landlab.OverlandFlow (de Almeida 2012) + envoltorio comarruga-engine 0.1.0"
H_INIT = 1e-5          # película mínima que exige landlab (m)
MANNING_N = 0.035      # supuesto único para toda la malla
DT_MAX_S = 5.0
DRAIN_MIN = 30.0       # drenaje simulado tras la lluvia (min)


def rain_rate_m_s(t: float, total_mm: float, duration_s: float, profile: str) -> float:
    if t >= duration_s:
        return 0.0
    mean = total_mm / 1000.0 / duration_s
    if profile == "triangular":
        return 2.0 * mean * (1.0 - abs(2.0 * t / duration_s - 1.0))
    return mean


def simulate(setup: Setup, cell_m: float, rain: dict[str, Any]) -> dict[str, Any]:
    """Devuelve calado máximo (ny, nx) y balance de masa. Fila 0 = norte."""
    import landlab
    from landlab import RasterModelGrid
    from landlab.components import OverlandFlow

    t0 = time.perf_counter()
    ny, nx = setup.z.shape
    # Malla con un anillo de nodos de contorno: N/E/O cerrados, S abierto (mar).
    zp = np.pad(setup.z, 1, mode="edge")
    sea = setup.sea
    if sea is None:
        zp[-1, :] = zp[-2, :] - 0.011 * cell_m      # el borde sur sigue la pendiente
    grid = RasterModelGrid((ny + 2, nx + 2), xy_spacing=cell_m)
    # landlab numera los nodos de sur a norte: se invierte el eje de filas
    grid.add_field("topographic__elevation", zp[::-1].ravel().copy(), at="node")
    h = grid.add_field("surface_water__depth", np.full(grid.number_of_nodes, H_INIT), at="node")
    inner = grid.nodes[1:-1, 1:-1].ravel()
    if sea is None:
        grid.set_closed_boundaries_at_grid_edges(True, True, True, False)
        land = np.ones(inner.size, bool)
    else:
        # MDT real: el mar es contorno abierto a cota fija 0 m (calado fijo H_INIT); los bordes
        # N/E/O del recorte quedan abiertos con salida libre (anillo a la cota de la celda vecina).
        land = ~sea[::-1].ravel()
        grid.status_at_node[inner[~land]] = grid.BC_NODE_IS_FIXED_VALUE
    of = OverlandFlow(grid, h_init=H_INIT, mannings_n=MANNING_N, steep_slopes=True)

    core = inner[land]
    assert np.array_equal(core, grid.core_nodes)
    pos = np.cumsum(land) - 1                       # índice en `core` de cada celda de tierra
    area = cell_m * cell_m

    def to_nodes(a: np.ndarray) -> np.ndarray:      # (ny, nx) fila 0 norte -> orden de nodos core
        return a[::-1].ravel()

    infil = to_nodes(setup.infil_m_s)[land]
    q = grid.at_link["surface_water__discharge"]
    # enlaces activos con un extremo en el contorno abierto; signo +1 si el flujo positivo sale
    tail, head = grid.node_at_link_tail, grid.node_at_link_head
    is_b = grid.status_at_node != grid.BC_NODE_IS_CORE
    al = grid.active_links
    out_links = al[is_b[tail[al]] | is_b[head[al]]]
    out_sign = np.where(is_b[head[out_links]], 1.0, -1.0)

    tank_idx = rel_idx = None
    tank = setup.tank
    if setup.tank_cells is not None:
        tank_idx = pos[np.flatnonzero(to_nodes(setup.tank_cells) & land)]
        rel_idx = pos[np.flatnonzero(to_nodes(setup.tank_release) & land)]

    duration = float(rain["duration_min"]) * 60.0
    t_end = duration + DRAIN_MIN * 60.0
    v_init = float(h[core].sum() * area)
    v_rain = v_infil = v_out = v_tank = 0.0
    tank_peak = 0.0
    hmax = np.zeros(core.size)
    h_end_rain = None
    t = 0.0
    steps = 0
    while t < t_end:
        dt = min(of.calc_time_step(), DT_MAX_S, t_end - t)
        # 1) lluvia (tasa a mitad de paso)
        r = rain_rate_m_s(t + 0.5 * dt, rain["total_mm"], duration, rain.get("profile", "constant"))
        hc = h[core]
        hc += r * dt
        v_rain += r * dt * area * core.size
        # 2) infiltración, limitada al agua disponible
        loss = np.minimum(np.maximum(hc - H_INIT, 0.0), infil * dt)
        hc -= loss
        v_infil += float(loss.sum()) * area
        # 3) depósito S2: capta por encima del umbral, devuelve aguas abajo con caudal limitado
        if tank_idx is not None:
            rel_v = min(tank["max_outflow_m3s"] * dt, v_tank)
            if tank.get("release_after_rain") and t < duration:
                rel_v = 0.0
            v_tank -= rel_v
            hc[rel_idx] += rel_v / area / rel_idx.size
            excess = np.maximum(hc[tank_idx] - tank["intake_depth_m"], 0.0)
            avail = float(excess.sum()) * area
            take = min(avail, tank["max_inflow_m3s"] * dt, tank["capacity_m3"] - v_tank)
            if take > 0.0:
                hc[tank_idx] -= excess * (take / avail)
                v_tank += take
                tank_peak = max(tank_peak, v_tank)
        h[core] = hc
        # 4) flujo superficial (landlab), un paso
        of.overland_flow(dt=dt)
        v_out += float((q[out_links] * out_sign).sum()) * cell_m * dt
        np.maximum(hmax, h[core], out=hmax)
        t += dt
        steps += 1
        if h_end_rain is None and t >= duration:
            h_end_rain = h[core].copy()

    v_stored = float(h[core].sum() * area) - v_init
    err = v_rain - (v_stored + v_infil + v_out + v_tank)
    def to_map(v: np.ndarray) -> np.ndarray:
        full = np.zeros(ny * nx)
        full[land] = v
        full = full.reshape(ny, nx)[::-1]
        return np.where(full < 1e-3, 0.0, full).astype(np.float32)

    depth_max = to_map(hmax)
    return {
        "depth_max": depth_max,
        "depth_end_rain": to_map(h_end_rain if h_end_rain is not None else hmax),
        "n_land_cells": int(core.size),
        "mass": {
            "rain_m3": v_rain, "stored_m3": v_stored, "infiltrated_m3": v_infil,
            "outflow_m3": v_out, "tank_stored_m3": v_tank, "tank_peak_m3": tank_peak,
            "error_m3": err,
            "error_pct": abs(err) / v_rain * 100.0 if v_rain > 0 else 0.0,
        },
        "steps": steps,
        "sim_time_s": t_end,
        "landlab_version": landlab.__version__,
        "numpy_version": np.__version__,
        "runtime_s": time.perf_counter() - t0,
    }
