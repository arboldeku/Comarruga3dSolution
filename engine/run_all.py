"""Genera terreno, escenarios y resultados de la demo.

Uso (desde la raíz del repo):  python -m engine.run_all
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# landlab usa OpenMP: un hilo por proceso para no sobresuscribir la CPU al paralelizar escenarios
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

from . import hotspots as hs_mod
from .solutions import (DEFAULT_PARAMS, INFILTRATION_MM_H, SOLUTION_NAMES, SOLUTION_SOURCES,
                        apply_solution, resolve_params)
from .solver import DRAIN_MIN, MANNING_N, MODEL_NAME, simulate
from .synthetic_terrain import load_terrain

LABEL = "estimación preliminar, modelo simplificado"
RAINS_MM = [30, 60, 100]
SOLUTIONS = ["S0", "S1", "S2", "S3", "S4"]
SEED = 42
ZONE_ID = "comarruga_demo"
FLOOD_THRESHOLD_M = 0.05     # una celda cuenta como inundada a partir de 5 cm (supuesto)
SCEN_DIR, RES_DIR = Path("scenarios"), Path("results")
RAIN_SOURCES = {
    "30": "lluvia de referencia, supuesto",
    "60": "~60 mm citados por prensa para el episodio del 02/11/2026 (Diari de Tarragona, 03/11/2026), "
          "pendiente de contrastar",
    "100": "100 mm comunicados por el Ayuntamiento de El Vendrell para Coma-ruga el 22/08/2026",
    "duracion": "sin dato de hietograma; 60 min es un supuesto",
}


def _dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_scenarios() -> list[dict[str, Any]]:
    SCEN_DIR.mkdir(exist_ok=True)
    out = []
    for mm in RAINS_MM:
        for sid in SOLUTIONS:
            sc = {
                "scenario_id": f"rain{mm}_{sid}", "zone_id": ZONE_ID,
                "rain": {"total_mm": mm, "duration_min": 60, "profile": "constant"},
                "solution_id": sid, "solution_params": DEFAULT_PARAMS[sid], "seed": SEED,
            }
            _dump(SCEN_DIR / f"{sc['scenario_id']}.json", sc)
            out.append(sc)
    return out


def run_scenario(sc: dict[str, Any]) -> dict[str, Any]:
    terrain = load_terrain(sc["seed"])
    setup = apply_solution(terrain, sc["solution_id"], sc["solution_params"], sc["seed"])
    res = simulate(setup, terrain.cell_m, sc["rain"])
    res["scenario"] = sc
    return res


def main() -> None:
    t0 = time.perf_counter()
    RES_DIR.mkdir(exist_ok=True)
    terrain = load_terrain(SEED)
    ny, nx = terrain.dem.shape
    np.save(RES_DIR / "dem.npy", terrain.dem.astype(np.float32))
    np.save(RES_DIR / "landuse.npy", terrain.landuse.astype(np.float32))
    scenarios = write_scenarios()
    sea = terrain.landuse == 3
    land = ~sea
    has_sea = bool(sea.any())
    boundary = ("mar (celdas -8888 del MDT) abierto a cota fija 0 m, supuesto sin marea; bordes N/E/O "
                "del recorte abiertos con salida libre; sin aportes desde fuera del recorte"
                if has_sea else "sur abierto (mar); norte, este y oeste cerrados")

    workers = max(1, min(len(scenarios), (os.cpu_count() or 2) - 2))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(run_scenario, scenarios))

    depths = {(r["scenario"]["rain"]["total_mm"], r["scenario"]["solution_id"]): r["depth_max"]
              for r in results}
    points = hs_mod.find_hotspots(depths[(max(RAINS_MM), "S0")], terrain.landuse)
    feats = hs_mod.hotspot_features(points, terrain.dem, terrain.landuse, terrain.cell_m)
    best = hs_mod.solver_best(feats, depths, RAINS_MM, SOLUTIONS)
    _dump(RES_DIR / "hotspots.json", {
        "label": LABEL, "dem_source": terrain.dem_source,
        "landuse_source": terrain.landuse_source, "radius_cells": hs_mod.RADIUS,
        "depth_metric": "calado máximo temporal en un radio de 3 celdas",
        "source_scenario": f"rain{max(RAINS_MM)}_S0",
        "hotspots": feats, "solver_best": best,
    })

    # Control del artefacto de montículo transitorio: el calado S0 debe crecer con la lluvia.
    for hs in feats:
        ds = [hs_mod.depth_at(depths[(mm, "S0")], hs["x"], hs["y"]) for mm in RAINS_MM]
        if any(b < a for a, b in zip(ds, ds[1:])):
            print(f"AVISO {hs['id']}: calado S0 no monótono con la lluvia {ds}")

    grid = {"nx": nx, "ny": ny, "cell_m": terrain.cell_m, "origin": list(terrain.origin),
            "crs": "EPSG:25831"}
    cell_area = terrain.cell_m ** 2
    index_rows = []
    for r in results:
        sc = r["scenario"]
        sid = sc["scenario_id"]
        d = r["depth_max"]
        np.save(RES_DIR / f"{sid}_depth.npy", d.astype(np.float32))
        flooded = (d >= FLOOD_THRESHOLD_M) & land      # el mar no cuenta
        m = r["mass"]
        status = "valid" if m["error_pct"] < 5.0 else "invalid"
        out = {
            "scenario_id": sid,
            "status": status,
            "rain_mm": sc["rain"]["total_mm"],
            "solution_id": sc["solution_id"],
            "solution_params": resolve_params(sc["solution_id"], sc["solution_params"]),
            "seed": sc["seed"],
            "model": {
                "name": MODEL_NAME, "version": r["landlab_version"], "label": LABEL,
                "numpy_version": r["numpy_version"],
                "params": {
                    "mannings_n": MANNING_N, "infiltration_mm_h": INFILTRATION_MM_H,
                    "rain": sc["rain"], "drain_min": DRAIN_MIN, "sim_time_s": r["sim_time_s"],
                    "steps": r["steps"], "flood_threshold_m": FLOOD_THRESHOLD_M,
                    "boundary": boundary,
                },
            },
            "data": {"dem_source": terrain.dem_source, "dem_sha256": terrain.dem_sha256,
                     "resolution_m": terrain.cell_m, "dem_file": "results/dem.npy",
                     "landuse_file": "results/landuse.npy",
                     "landuse_source": terrain.landuse_source,
                     "landuse_values": "0 no urbano, 1 urbano, 2 cauce/eje de drenaje, 3 mar"},
            "grid": grid,
            "kpis": {
                "max_depth_cm": round(float(d[land].max()) * 100.0, 1),
                "max_depth_urban_cm": round(float(d[terrain.landuse == 1].max()) * 100.0, 1),
                "flooded_area_m2": round(float(flooded.sum()) * cell_area, 1),
                "flooded_area_pct": round(float(flooded.sum()) / float(land.sum()) * 100.0, 2),
                "stored_volume_m3": round(float(d[land].sum()) * cell_area, 1),
                "volume_m3_total": round(m["rain_m3"], 1),
                "volume_error_pct": round(m["error_pct"], 3),
                "runtime_s": round(r["runtime_s"], 2),
            },
            "mass_balance_m3": {k: round(v, 1) for k, v in m.items() if k.endswith("_m3")},
            "depth_file": f"results/{sid}_depth.npy",
            "hotspots": [{"id": h["id"], "x": h["x"], "y": h["y"],
                          "max_depth_cm": hs_mod.depth_at(d, h["x"], h["y"])} for h in feats],
        }
        _dump(RES_DIR / f"{sid}.json", out)
        index_rows.append({"scenario_id": sid, "rain_mm": out["rain_mm"],
                           "solution_id": out["solution_id"],
                           "result_file": f"results/{sid}.json", "status": status})
        k = out["kpis"]
        if sc["solution_id"] == "S2":
            print(f"  depósito S2: pico {m['tank_peak_m3']:.0f} m3")
        print(f"{sid:12s} {status:7s} max={k['max_depth_cm']:6.1f} cm  urb={k['max_depth_urban_cm']:6.1f} cm  "
              f"inund={k['flooded_area_pct']:5.2f} %  err={k['volume_error_pct']:6.3f} %  t={k['runtime_s']:5.1f} s")

    _dump(RES_DIR / "index.json", {
        "label": LABEL, "dem_source": terrain.dem_source, "dem_sha256": terrain.dem_sha256,
        "dem_file": "results/dem.npy", "landuse_file": "results/landuse.npy",
        "landuse_source": terrain.landuse_source,
        "landuse_values": "0 no urbano, 1 urbano, 2 cauce/eje de drenaje, 3 mar",
        "sea_level": "cota fija 0 m, supuesto sin marea" if has_sea else None,
        "grid": grid, "rains_mm": RAINS_MM, "rain_sources": RAIN_SOURCES,
        "solutions": [{"id": s, "name": SOLUTION_NAMES[s], "params": DEFAULT_PARAMS[s],
                       "source": SOLUTION_SOURCES[s],
                       **({"tank_xy": list(terrain.tank_xy)} if s == "S2" and terrain.tank_xy else {})}
                      for s in SOLUTIONS],
        "scenarios": index_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    print("\nsolver_best:")
    for b in best:
        print(f"  {b['hotspot_id']} rain{b['rain_mm']:<3d} best={b['best']}  {b['depth_cm']}")
    print(f"\nTotal: {time.perf_counter() - t0:.1f} s, {workers} procesos")


if __name__ == "__main__":
    main()
