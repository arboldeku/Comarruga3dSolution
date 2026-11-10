"""KPIs del informe (contrato 5) -> results/kpis_summary.json.

Uso:  python -m jev.kpis [--results-dir results]
Lee results/index.json, results/<scenario_id>.json y results/jev_decisions.json.
Todo dato ausente se escribe como null o "sin dato"; no se inventa nada.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LABEL = "estimación preliminar, modelo simplificado"
SOLUTIONS = ("S1", "S2", "S3", "S4")
COST_NOTE = ("cost_usd registra usage.cost tal cual. La referencia de la API de OpenRouter lo describe como "
             "'créditos' y el blog como USD: discrepancia documentada (docs/CONTRACTS.md 6.2), sin resolver.")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _pct(num: float, den: float) -> float | None:
    return round(100.0 * num / den, 1) if den else None


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    v = sorted(values)
    return round(v[max(0, math.ceil(q * len(v)) - 1)], 1)  # nearest-rank


def _load_scenarios(results_dir: Path, index: dict | None) -> dict[str, dict]:
    out = {}
    if index and index.get("scenarios"):
        for s in index["scenarios"]:
            sid = s.get("scenario_id")
            r = _read_json(results_dir / f"{sid}.json")
            if r:
                out[sid] = r
    else:
        for p in sorted(results_dir.glob("rain*_S[0-4].json")):
            r = _read_json(p)
            if r:
                out[p.stem] = r
    return out


def _rain_sol(sid: str, r: dict) -> tuple[float | None, str | None]:
    rain, sol = r.get("rain_mm"), r.get("solution_id")
    if rain is None or sol is None:
        try:
            a, sol = sid.split("_", 1)
            rain = float(a.removeprefix("rain"))
        except ValueError:
            return None, None
    return rain, sol


def solutions_kpis(scen: dict[str, dict]) -> list[dict]:
    by = {}
    for sid, r in scen.items():
        rain, sol = _rain_sol(sid, r)
        if sol:
            by[(rain, sol)] = r
    rows = []
    for rain in sorted({k[0] for k in by}):
        base = by.get((rain, "S0"))
        bk = (base or {}).get("kpis", {})
        for sol in SOLUTIONS:
            r = by.get((rain, sol))
            if not r:
                continue
            k = r.get("kpis", {})
            row = {"rain_mm": rain, "solution_id": sol, "scenario_id": r.get("scenario_id"),
                   "status": r.get("status"), "max_depth_cm": k.get("max_depth_cm"),
                   "baseline_max_depth_cm": bk.get("max_depth_cm"),
                   "max_depth_reduction_cm": None, "max_depth_reduction_pct": None,
                   "flooded_area_reduction_pct": None}
            d0, d1 = bk.get("max_depth_cm"), k.get("max_depth_cm")
            if d0 is not None and d1 is not None:
                row["max_depth_reduction_cm"] = round(d0 - d1, 2)
                row["max_depth_reduction_pct"] = _pct(d0 - d1, d0)
            a0, a1 = bk.get("flooded_area_m2"), k.get("flooded_area_m2")
            if a0 is not None and a1 is not None:
                row["flooded_area_reduction_pct"] = _pct(a0 - a1, a0)
            rows.append(row)
    return rows


def solver_kpis(scen: dict[str, dict]) -> dict:
    per = []
    for sid, r in sorted(scen.items()):
        k = r.get("kpis", {})
        err = k.get("volume_error_pct")
        status = r.get("status") or ("invalid" if err is not None and abs(err) >= 5 else "valid")
        per.append({"scenario_id": sid, "runtime_s": k.get("runtime_s"), "volume_error_pct": err, "status": status})
    rts = [p["runtime_s"] for p in per if p["runtime_s"] is not None]
    errs = [abs(p["volume_error_pct"]) for p in per if p["volume_error_pct"] is not None]
    model = next((r.get("model") for r in scen.values() if r.get("model")), None)
    return {"model": model, "n_scenarios": len(per),
            "runtime_s_mean": round(sum(rts) / len(rts), 3) if rts else None,
            "runtime_s_max": max(rts) if rts else None,
            "runtime_s_total": round(sum(rts), 3) if rts else None,
            "volume_error_pct_max": max(errs) if errs else None,
            "n_invalid": sum(1 for p in per if p["status"] == "invalid"),
            "per_scenario": per}


def _calibration(live: list[dict]) -> dict | None:
    pts = []
    for d in live:
        probs = (d.get("jev_output") or {}).get("probabilities") or {}
        p = probs.get(d["jev_output"]["choice"])
        if isinstance(p, (int, float)) and d.get("solver_best"):
            pts.append((float(p), d["jev_output"]["choice"] == d["solver_best"]))
    if not pts:
        return None
    mean_p = sum(p for p, _ in pts) / len(pts)
    acc = sum(1 for _, ok in pts if ok) / len(pts)
    bins = []
    for lo, hi in ((0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        b = [(p, ok) for p, ok in pts if lo <= p < hi]
        if b:
            bins.append({"prob_range": [lo, min(hi, 1.0)], "n": len(b),
                         "mean_prob": round(sum(p for p, _ in b) / len(b), 3),
                         "accuracy_pct": _pct(sum(1 for _, ok in b if ok), len(b))})
    return {"n": len(pts), "mean_prob_chosen_pct": round(100 * mean_p, 1), "accuracy_pct": round(100 * acc, 1),
            "gap_pct": round(100 * (mean_p - acc), 1), "bins": bins,
            "note": "gap > 0 = Jev sobreconfiado; muestra pequeña, orientativo."}


def jev_kpis(decisions: list[dict] | None) -> dict:
    ds = decisions or []
    n = len(ds)
    live = [d for d in ds if d.get("jev_output")]
    scored = [d for d in ds if d.get("solver_best")]
    live_scored = [d for d in live if d.get("solver_best")]
    lat = [d["latency_ms"] for d in live if isinstance(d.get("latency_ms"), (int, float))]
    costs = [d["cost_usd"] for d in live if isinstance(d.get("cost_usd"), (int, float))]
    non_tie = [d for d in scored if d.get("solver_margin_cm") not in (None, 0, 0.0)]
    live_non_tie = [d for d in non_tie if d.get("jev_output")]
    errors = Counter((d.get("jev_error") or "").split(":")[0] for d in ds if d.get("jev_error"))
    if n == 0:
        note = "Sin decisiones registradas: ejecuta `python -m jev.run_shadow`."
    elif not live:
        why = next((d.get("jev_error") for d in ds if d.get("jev_error")), "motivo no registrado")
        note = (f"Jev NO se ejecutó en ninguna decisión ({why}). Todas las decisiones son del respaldo "
                "determinista; accuracy_vs_solver_pct es null a propósito.")
    elif len(live) < n:
        note = f"Jev respondió {len(live)} de {n} decisiones; el resto usó el respaldo determinista."
    else:
        note = "Jev respondió todas las decisiones."

    def hits(rows: list[dict]) -> int:
        return sum(1 for d in rows if d["jev_output"]["choice"] == d["solver_best"])

    return {
        "n_decisions": n,
        "n_jev_live": len(live),
        "accuracy_vs_solver_pct": _pct(hits(live_scored), len(live_scored)),
        "baseline_accuracy_vs_solver_pct": _pct(sum(1 for d in scored if d.get("fallback_agree")), len(scored)),
        "effective_accuracy_vs_solver_pct": _pct(sum(1 for d in scored if d.get("agree")), len(scored)),
        "jev_vs_baseline_agreement_pct": _pct(
            sum(1 for d in live if d["jev_output"]["choice"] == (d.get("fallback_output") or {}).get("choice")),
            len(live)),
        "random_baseline_pct": 25,
        # clase mayoritaria: acierto de elegir siempre la solución que más veces gana (se conoce a posteriori)
        "majority_class_baseline_pct": _pct(max(Counter(d["solver_best"] for d in scored).values()), len(scored)) if scored else None,
        "solver_best_distribution": dict(Counter(d["solver_best"] for d in scored)),
        "n_solver_margin_lt_1cm": sum(1 for d in scored if isinstance(d.get("solver_margin_cm"), (int, float)) and d["solver_margin_cm"] < 1),
        "n_solver_ties": len(scored) - len(non_tie),
        "accuracy_excl_ties_pct": _pct(hits(live_non_tie), len(live_non_tie)),
        "baseline_accuracy_excl_ties_pct": _pct(sum(1 for d in non_tie if d.get("fallback_agree")), len(non_tie)),
        "latency_p50_ms": _percentile(lat, 0.50),
        "latency_p95_ms": _percentile(lat, 0.95),
        "cost_per_decision_usd": round(sum(costs) / len(costs), 6) if costs else None,
        "cost_total_usd": round(sum(costs), 6) if costs else None,
        "fallback_pct": _pct(sum(1 for d in ds if d.get("fallback_used")), n),
        "jev_errors": dict(errors),
        "calibration": _calibration(live_scored),
        "model_id": next((d.get("model_id") for d in ds if d.get("model_id")), None),
        "model_snapshot": next((d.get("model_snapshot") for d in ds if d.get("model_snapshot")), None),
        "mode": "shadow",
        "run_id": ds[0].get("run_id") if ds else None,
        "note": note,
        "cost_unit_note": COST_NOTE,
        "ties_note": ("n_solver_ties = casos en que el solver da el mismo calado a las dos mejores soluciones "
                      "(gana la de id menor por convenio); ahí el 'acierto' es poco informativo."),
    }


def build_summary(results_dir: Path) -> dict:
    index = _read_json(results_dir / "index.json")
    scen = _load_scenarios(results_dir, index)
    dem = (index or {}).get("dem_source") or next(
        ((r.get("data") or {}).get("dem_source") for r in scen.values() if r.get("data")), None)
    return {
        "label": LABEL,
        "dem_source": dem or "sin dato",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "solutions": solutions_kpis(scen),
        "solver": solver_kpis(scen),
        "jev": jev_kpis(_read_json(results_dir / "jev_decisions.json")),
        "context": {
            "real_episodes": "sin dato",
            "real_rainfall": "sin dato",
            "note": ("Episodios reales: sin dato verificable (testimonio del autor pendiente de verificar). "
                     "No se atribuye causa a ninguna obra; las soluciones S1–S4 son supuestos del modelo, "
                     "no proyectos reales."),
        },
    }


def write_summary(results_dir: Path) -> dict:
    summary = build_summary(results_dir)
    (results_dir / "kpis_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # consola de Windows: evita acentos rotos
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-dir", default=str(Path(__file__).resolve().parent.parent / "results"))
    a = ap.parse_args(argv)
    s = write_summary(Path(a.results_dir))
    print(f"{Path(a.results_dir) / 'kpis_summary.json'}: {len(s['solutions'])} filas de soluciones, "
          f"{s['solver']['n_scenarios']} escenarios, {s['jev']['n_decisions']} decisiones")
    print(s["jev"]["note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
