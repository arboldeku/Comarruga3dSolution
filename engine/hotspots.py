"""Puntos negros fijos (a partir de S0 con la lluvia mayor) y sus características."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter

RADIUS = 3            # celdas (contrato 6.1)
MIN_SEP = 14          # separación mínima entre puntos negros (celdas)
MIN_CHANNEL_DIST = 8  # celdas; evita que el radio de 3 pise el cauce o su ensanche (S1)
MIN_DEPTH_M = 0.10
MAX_HOTSPOTS = 8


def _disk(shape: tuple[int, int], x: int, y: int, radius: int = RADIUS) -> np.ndarray:
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (yy - y) ** 2 + (xx - x) ** 2 <= radius ** 2


def depth_at(depth: np.ndarray, x: int, y: int) -> float:
    """Calado máximo (cm) en un radio de 3 celdas."""
    return round(float(depth[_disk(depth.shape, x, y)].max()) * 100.0, 1)


def find_hotspots(depth_s0: np.ndarray, landuse: np.ndarray) -> list[tuple[int, int]]:
    """Máximos locales de calado en zona urbana, separados entre sí. Devuelve [(x, y)]."""
    dist_ch = distance_transform_edt(landuse != 2)
    ok = (landuse == 1) & (dist_ch >= MIN_CHANNEL_DIST) & (depth_s0 >= MIN_DEPTH_M)
    ok &= depth_s0 == maximum_filter(depth_s0, size=2 * RADIUS + 1)
    if (landuse == 3).any():      # MDT real: lejos del mar y del borde del recorte
        ok &= distance_transform_edt(landuse != 3) >= MIN_CHANNEL_DIST
        ok[:MIN_CHANNEL_DIST] = ok[-MIN_CHANNEL_DIST:] = False
        ok[:, :MIN_CHANNEL_DIST] = ok[:, -MIN_CHANNEL_DIST:] = False
    ys, xs = np.nonzero(ok)
    order = np.argsort(-depth_s0[ys, xs], kind="stable")
    chosen: list[tuple[int, int]] = []
    for i in order:
        x, y = int(xs[i]), int(ys[i])
        if all((x - cx) ** 2 + (y - cy) ** 2 >= MIN_SEP ** 2 for cx, cy in chosen):
            chosen.append((x, y))
        if len(chosen) == MAX_HOTSPOTS:
            break
    chosen.sort(key=lambda p: (p[1], p[0]))   # orden estable: de norte a sur
    return chosen


def _catchment_and_fill(dem: np.ndarray, cell_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Área drenante D8 (m²) y profundidad de depresión (m) con componentes de landlab."""
    from landlab import RasterModelGrid
    from landlab.components import FlowAccumulator, SinkFillerBarnes

    ny, nx = dem.shape
    g = RasterModelGrid((ny, nx), xy_spacing=cell_m)
    g.add_field("topographic__elevation", dem[::-1].astype(float).ravel().copy(), at="node")
    FlowAccumulator(g, flow_director="D8").run_one_step()
    area = g.at_node["drainage_area"].reshape(ny, nx)[::-1].copy()
    SinkFillerBarnes(g, method="D8", fill_flat=True).run_one_step()
    filled = g.at_node["topographic__elevation"].reshape(ny, nx)[::-1]
    return area, np.maximum(filled - dem, 0.0)


def hotspot_features(points: list[tuple[int, int]], dem: np.ndarray, landuse: np.ndarray,
                     cell_m: float) -> list[dict[str, Any]]:
    dist_ch = distance_transform_edt(landuse != 2) * cell_m
    gy, gx = np.gradient(dem.astype(float), cell_m)
    slope = np.hypot(gx, gy)
    try:
        area, dep = _catchment_and_fill(dem, cell_m)
    except Exception:  # respaldo: sin dato antes que inventar
        area = dep = None
    out = []
    for i, (x, y) in enumerate(points, start=1):
        m = _disk(dem.shape, x, y)
        out.append({
            "id": f"H{i}", "x": x, "y": y,
            "elevation_m": round(float(dem[y, x]), 2),
            "slope": round(float(slope[m].mean()), 4),
            "catchment_m2": int(area[m].max()) if area is not None else None,
            "dist_to_channel_m": round(float(dist_ch[y, x]), 1),
            "urban_fraction": round(float((landuse[_disk(dem.shape, x, y, 10)] == 1).mean()), 3),
            "depression_depth_m": round(float(dep[m].max()), 2) if dep is not None else None,
        })
    return out


def solver_best(hotspots: list[dict[str, Any]], depths: dict[tuple[int, str], np.ndarray],
                rains: list[int], solutions: list[str]) -> list[dict[str, Any]]:
    """`best` = solución S1-S4 con menor calado en el punto negro (empate: id menor)."""
    rows = []
    for hs in hotspots:
        for mm in rains:
            d = {s: depth_at(depths[(mm, s)], hs["x"], hs["y"]) for s in solutions}
            cands = [s for s in solutions if s != "S0"]
            best = min(cands, key=lambda s: (d[s], s))
            rows.append({"hotspot_id": hs["id"], "rain_mm": mm, "best": best, "depth_cm": d})
    return rows
