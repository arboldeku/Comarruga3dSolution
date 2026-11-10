"""Modo sombra: Jev decide a priori qué solución (S1–S4) reduce más el agua en cada
punto negro × lluvia; se registra y se contrasta con el solver. No actúa.

Uso:  python -m jev.run_shadow [--results-dir results] [--decisions-dir jev/decisions]
                               [--timeout 20] [--no-jev]

Salidas: jev/decisions/<run_id>.jsonl (contrato 4 + 6.2), results/jev_decisions.json
(lista, para el visor) y results/kpis_summary.json (vía jev.kpis).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import client, fallback, kpis

OPTIONS = list(fallback.OPTIONS)
FEATURES = ("elevation_m", "slope", "catchment_m2", "dist_to_channel_m", "urban_fraction", "depression_depth_m")
RAIN_DURATION_MIN = 60
MAX_CONSECUTIVE_FAILURES = 3  # tras esto se deja de llamar a Jev en la ejecución

# Descripciones del contrato 2 (supuestos del modelo, no proyectos reales).
BASE_CRITERIA = {
    "S1": "Ampliar la sección del cauce: se rebaja y ensancha el cauce para que lleve más caudal sin desbordar.",
    "S2": "Depósito de retención: un depósito almacena parte del agua y la vacía despacio.",
    "S3": "Pavimento permeable (SUDS): parte de la superficie urbana pasa a infiltrar el agua en el suelo.",
    "S4": "Elevar bordillos / desviar: barreras bajas que impiden que el agua entre en la zona y la desvían.",
}
INSTRUCTIONS = (
    "Eres un técnico de drenaje urbano. Dado un punto negro de inundación (rasgos del terreno) y una "
    "lluvia total en mm caída en 60 minutos, elige la única actuación que más reduce el agua acumulada "
    "(calado máximo) en ese punto. Unidades: slope en m/m, catchment_m2 = superficie que drena hacia el "
    "punto, dist_to_channel_m = distancia al cauce, urban_fraction entre 0 y 1, depression_depth_m = "
    "profundidad de la cubeta cerrada."
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build_criteria(index: dict | None) -> dict:
    """Opción -> descripción en lenguaje claro, con los parámetros de index.json si existen."""
    params = {}
    for s in (index or {}).get("solutions", []) or []:
        if isinstance(s, dict) and s.get("id") in BASE_CRITERIA and s.get("params"):
            params[s["id"]] = s["params"]
    out = {}
    for sid in OPTIONS:
        text = BASE_CRITERIA[sid]
        if sid in params:
            text += " Parámetros supuestos: " + json.dumps(params[sid], ensure_ascii=False, sort_keys=True) + "."
        out[sid] = text
    return out


def build_state(hotspot: dict, rain_mm: float) -> dict:
    """Estado para Jev: rasgos del punto negro + lluvia. Sin calados del solver."""
    state = {"hotspot_id": hotspot.get("id")}
    state.update({k: hotspot[k] for k in FEATURES if k in hotspot})
    state["rain_total_mm"] = rain_mm
    state["rain_duration_min"] = RAIN_DURATION_MIN
    return state


def _pairs(hot: dict, index: dict | None) -> list[tuple[dict, float, dict | None]]:
    by_id = {h["id"]: h for h in hot.get("hotspots", [])}
    best = hot.get("solver_best") or []
    if best:
        return [(by_id[b["hotspot_id"]], b["rain_mm"], b) for b in best if b.get("hotspot_id") in by_id]
    rains = (index or {}).get("rains_mm") or [30, 60, 100]
    return [(h, r, None) for h in by_id.values() for r in rains]


def run(results_dir: Path, decisions_dir: Path, timeout_s: float = 20.0, use_jev: bool = True,
        decide=None, write_kpis: bool = True) -> dict:
    decide = decide or client.decide_choice
    hot = _read_json(results_dir / "hotspots.json")
    if not hot or not hot.get("hotspots"):
        raise SystemExit(f"No existe o está vacío {results_dir / 'hotspots.json'} (lo genera engine).")
    index = _read_json(results_dir / "index.json")
    criteria = build_criteria(index)

    jev_ok, jev_note = client.env_status()
    if not use_jev:
        jev_ok, jev_note = False, "Jev desactivado con --no-jev"
    model_id = os.environ.get(client.ENV_MODEL, "").strip() or None
    run_id = datetime.now(timezone.utc).strftime("shadow_%Y%m%dT%H%M%SZ")
    failures = 0
    decisions = []

    for i, (h, rain, sb) in enumerate(_pairs(hot, index), start=1):
        state = build_state(h, rain)
        fb = fallback.decide(h, rain)
        jev_out = snapshot = latency = cost = tokens = None
        error = None if jev_ok else (f"missing_env: {jev_note}" if use_jev else jev_note)
        if jev_ok and failures < MAX_CONSECUTIVE_FAILURES:
            try:
                r = decide(state, INSTRUCTIONS, criteria, timeout_s=timeout_s)
                jev_out = {"choice": r["choice"], "probabilities": r.get("probabilities"),
                           "confidence": r.get("confidence")}
                snapshot, latency, cost = r.get("model"), r.get("latency_ms"), r.get("cost")
                tokens = r.get("input_tokens")
                failures = 0
            except client.JevError as exc:
                failures += 1
                error = str(exc)
        elif jev_ok:
            error = f"omitida: {MAX_CONSECUTIVE_FAILURES} fallos consecutivos de Jev"

        live = jev_out is not None
        effective = jev_out["choice"] if live else fb["choice"]
        best = sb.get("best") if sb else None
        depths = (sb or {}).get("depth_cm") or {}
        vals = sorted(depths[s] for s in OPTIONS if s in depths)
        margin = round(vals[1] - vals[0], 3) if len(vals) >= 2 else None
        decisions.append({
            "decision_id": f"d{i:03d}",
            "run_id": run_id,
            "hotspot_id": h.get("id"),
            "rain_mm": rain,
            "primitive": "choice",
            "input": {**{k: v for k, v in state.items() if k != "hotspot_id"}, "options": OPTIONS},
            "jev_output": jev_out,
            "jev_live": live,
            "jev_error": error,
            "fallback_output": fb,
            "fallback_used": not live,
            "effective_choice": effective,
            "solver_best": best,
            "solver_depth_cm": depths or None,
            "solver_margin_cm": margin,  # 2.º mejor − mejor; 0 = empate (gana el id menor)
            "agree": (effective == best) if best else None,
            "fallback_agree": (fb["choice"] == best) if best else None,
            "latency_ms": latency,   # null = no hubo llamada válida a Jev
            "cost_usd": cost,        # estimado: input_tokens × 0,042 USD / 1e6 (ver cost_note)
            "cost_note": client.COST_NOTE if cost is not None else None,
            "input_tokens": tokens,
            "mode": "shadow",
            "model_id": model_id,
            "model_snapshot": snapshot,
            "timestamp": _now(),
        })

    decisions_dir.mkdir(parents=True, exist_ok=True)
    jsonl = decisions_dir / f"{run_id}.jsonl"
    jsonl.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in decisions), encoding="utf-8")
    (results_dir / "jev_decisions.json").write_text(
        json.dumps(decisions, ensure_ascii=False, indent=1), encoding="utf-8")
    summary = kpis.write_summary(results_dir) if write_kpis else None
    return {"run_id": run_id, "jsonl": jsonl, "decisions": decisions, "kpis": summary,
            "jev_available": jev_ok, "jev_note": jev_note}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):  # consola de Windows: evita acentos rotos
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    root = client.ROOT
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results-dir", default=str(root / "results"))
    ap.add_argument("--decisions-dir", default=str(root / "jev" / "decisions"))
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--no-jev", action="store_true", help="solo respaldo determinista")
    a = ap.parse_args(argv)
    client.load_dotenv()
    out = run(Path(a.results_dir), Path(a.decisions_dir), a.timeout, use_jev=not a.no_jev)
    j = out["kpis"]["jev"]
    if not out["jev_available"]:
        print(f"AVISO: Jev NO se ejecutó ({out['jev_note']}). Solo respaldo determinista.")
    print(f"run_id={out['run_id']}  decisiones={j['n_decisions']}  vivas_jev={j['n_jev_live']}")
    print(f"acierto Jev vs solver: {j['accuracy_vs_solver_pct']} %  |  respaldo vs solver: "
          f"{j['baseline_accuracy_vs_solver_pct']} %  |  azar: {j['random_baseline_pct']} %")
    print(f"registro: {out['jsonl']}")
    print(f"visor:    {Path(a.results_dir) / 'jev_decisions.json'}  y  {Path(a.results_dir) / 'kpis_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
