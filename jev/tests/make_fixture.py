"""Genera un fixture mínimo (contrato 6.1) en un directorio dado. Valores inventados
solo para pruebas; no son resultados del solver."""
from __future__ import annotations

import json
from pathlib import Path

HOTSPOTS = [
    {"id": "H1", "x": 10, "y": 12, "elevation_m": 3.2, "slope": 0.004, "catchment_m2": 52000,
     "dist_to_channel_m": 12.0, "urban_fraction": 0.7, "depression_depth_m": 0.1},
    {"id": "H2", "x": 40, "y": 30, "elevation_m": 5.0, "slope": 0.002, "catchment_m2": 30000,
     "dist_to_channel_m": 180.0, "urban_fraction": 0.5, "depression_depth_m": 0.6},
    {"id": "H3", "x": 70, "y": 55, "elevation_m": 9.1, "slope": 0.05, "catchment_m2": 6000,
     "dist_to_channel_m": 220.0, "urban_fraction": 0.9, "depression_depth_m": 0.05},
]
# depth_cm por lluvia: (S0, S1, S2, S3, S4)
DEPTHS = {
    "H1": {30: (10, 4, 8, 9, 9), 100: (60, 30, 50, 58, 55)},
    "H2": {30: (20, 20, 5, 15, 18), 100: (80, 78, 40, 75, 70)},
    "H3": {30: (6, 6, 5, 2, 3), 100: (30, 30, 30, 28, 12)},
}
# kpis por escenario: max_depth_cm, flooded_area_m2
SCEN = {
    (30, "S0"): (20.0, 1000.0), (30, "S1"): (20.0, 800.0), (30, "S2"): (10.0, 500.0),
    (30, "S3"): (15.0, 700.0), (30, "S4"): (18.0, 900.0),
    (100, "S0"): (80.0, 4000.0), (100, "S1"): (78.0, 3000.0), (100, "S2"): (50.0, 2000.0),
    (100, "S3"): (75.0, 3800.0), (100, "S4"): (70.0, 3600.0),
}


def write(results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    sols = ["S0", "S1", "S2", "S3", "S4"]
    best = []
    for hid, per in DEPTHS.items():
        for rain, vals in per.items():
            depth = dict(zip(sols, vals))
            b = min(sols[1:], key=lambda s: (depth[s], s))
            best.append({"hotspot_id": hid, "rain_mm": rain, "best": b, "depth_cm": depth})
    (results_dir / "hotspots.json").write_text(
        json.dumps({"hotspots": HOTSPOTS, "solver_best": best}), encoding="utf-8")
    scenarios = []
    for (rain, sol), (depth, area) in SCEN.items():
        sid = f"rain{rain}_{sol}"
        err = 6.0 if sid == "rain100_S4" else 0.5
        status = "invalid" if err >= 5 else "valid"
        (results_dir / f"{sid}.json").write_text(json.dumps({
            "scenario_id": sid, "rain_mm": rain, "solution_id": sol, "status": status,
            "model": {"name": "fixture", "version": "0", "label": "estimación preliminar, modelo simplificado"},
            "data": {"dem_source": "sintético"},
            "kpis": {"max_depth_cm": depth, "flooded_area_m2": area, "flooded_area_pct": 1.0,
                     "volume_m3_total": 1.0, "volume_error_pct": err, "runtime_s": 1.5},
        }), encoding="utf-8")
        scenarios.append({"scenario_id": sid, "rain_mm": rain, "solution_id": sol,
                          "result_file": f"results/{sid}.json", "status": status})
    (results_dir / "index.json").write_text(json.dumps({
        "label": "estimación preliminar, modelo simplificado", "dem_source": "sintético",
        "rains_mm": [30, 100],
        "solutions": [{"id": "S0", "name": "Situación actual", "params": {}},
                      {"id": "S1", "name": "Ampliar cauce", "params": {"depth_m": 0.5, "width_cells": 1}},
                      {"id": "S2", "name": "Depósito", "params": {"capacity_m3": 2000}},
                      {"id": "S3", "name": "SUDS", "params": {"area_fraction": 0.3}},
                      {"id": "S4", "name": "Bordillos", "params": {"height_m": 0.3}}],
        "scenarios": scenarios, "generated_at": "2026-11-10T00:00:00Z"}), encoding="utf-8")


if __name__ == "__main__":
    write(Path(__file__).resolve().parent / "fixtures" / "results")
