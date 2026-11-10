"""Tests sin red:  python -m unittest discover -s jev/tests -t ."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jev import client, fallback, kpis, run_shadow
from jev.tests import make_fixture

FAKE_KEY = "sk-or-TEST-clave-falsa-123456"
FAKE_MODEL = "modelo/de-prueba"  # solo para tests; no es un ID real
CRITERIA = {"S1": "a", "S2": "b", "S3": "c", "S4": "d"}
ENV = {client.ENV_KEY: FAKE_KEY, client.ENV_MODEL: FAKE_MODEL}


class Resp:
    def __init__(self, status=200, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def ok_payload(choice="S2", kind="choice"):
    return {"answers": {"q": {"type": kind, "choice": choice,
                              "probabilities": {"S1": 0.1, "S2": 0.7, "S3": 0.1, "S4": 0.1}, "confidence": 0.7}},
            "usage": {"input_tokens": 100, "output_tokens": 5, "cost": 0.0004}, "model": "snap-2026-11-01"}


def no_env():
    return mock.patch.dict(os.environ, {client.ENV_KEY: "", client.ENV_MODEL: ""})


class ClientTests(unittest.TestCase):
    def test_success_and_request_shape(self):
        calls = []

        def post(url, headers, json, timeout):
            calls.append((url, headers, json, timeout))
            return Resp(200, ok_payload())

        with mock.patch.dict(os.environ, ENV):
            r = client.decide_choice({"slope": 0.01}, "elige", CRITERIA, timeout_s=3, post=post)
        url, headers, body, timeout = calls[0]
        self.assertEqual(url, "https://openrouter.ai/api/alpha/decisions")
        self.assertEqual(headers["Authorization"], "Bearer " + FAKE_KEY)
        self.assertEqual(body, {"model": FAKE_MODEL, "state": {"slope": 0.01},
                                "questions": {"q": {"type": "choice", "instructions": "elige", "criteria": CRITERIA}}})
        self.assertEqual(timeout, 3)
        self.assertEqual((r["choice"], r["confidence"], r["cost"], r["model"]), ("S2", 0.7, 0.0004, "snap-2026-11-01"))
        self.assertEqual(r["probabilities"]["S2"], 0.7)
        self.assertGreaterEqual(r["latency_ms"], 0)
        self.assertNotIn(FAKE_KEY, json.dumps(r))

    def test_confidence_optional(self):
        p = ok_payload()
        del p["answers"]["q"]["confidence"]
        with mock.patch.dict(os.environ, ENV):
            r = client.decide_choice({}, "i", CRITERIA, post=lambda *a, **k: Resp(200, p))
        self.assertIsNone(r["confidence"])

    def _fails(self, post, reason, env=ENV):
        with mock.patch.dict(os.environ, env):
            with self.assertRaises(client.JevError) as cm:
                client.decide_choice({}, "i", CRITERIA, post=post, sleep=lambda s: None)
        self.assertEqual(cm.exception.reason, reason)
        self.assertNotIn(FAKE_KEY, str(cm.exception))
        self.assertNotIn(FAKE_KEY, repr(cm.exception))
        self.assertIsNone(cm.exception.__cause__)
        return cm.exception

    def test_refusal(self):
        self._fails(lambda *a, **k: Resp(200, ok_payload(kind="refusal")), "refusal")

    def test_choice_outside_options(self):
        self._fails(lambda *a, **k: Resp(200, ok_payload(choice="S9")), "invalid_choice")

    def test_timeout(self):
        def post(url, headers, json, timeout):
            raise TimeoutError(f"cabeceras {headers}")  # el mensaje original lleva la clave

        self._fails(post, "timeout")

    def test_http_error_scrubs_key(self):
        e = self._fails(lambda *a, **k: Resp(401, None, f"bad key {FAKE_KEY}"), "http_401")
        self.assertIn("***", e.detail)

    def test_bad_json(self):
        self._fails(lambda *a, **k: Resp(200, None, "<html>"), "bad_response")

    def test_missing_env_makes_no_call(self):
        def post(*a, **k):
            raise AssertionError("no debe llamar a la red")

        e = self._fails(post, "missing_env", env={client.ENV_KEY: "", client.ENV_MODEL: ""})
        self.assertIn("JEV_MODEL_ID", e.detail)
        self.assertIn("OPENROUTER_API_KEY", e.detail)

    def test_single_retry_on_5xx_and_429(self):
        for first in (503, 429):
            seq = [Resp(first, None, "x"), Resp(200, ok_payload())]
            n = []

            def post(*a, **k):
                n.append(1)
                return seq[len(n) - 1]

            with mock.patch.dict(os.environ, ENV):
                r = client.decide_choice({}, "i", CRITERIA, post=post, sleep=lambda s: None)
            self.assertEqual((r["choice"], len(n)), ("S2", 2))
        n = []

        def always500(*a, **k):
            n.append(1)
            return Resp(500, None, "x")

        self._fails(always500, "http_500")
        self.assertEqual(len(n), 2)

    def test_dotenv_does_not_override(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("# c\nJEV_MODEL_ID=del-env-file\nOPENROUTER_API_KEY='k2'\nVACIA=\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {client.ENV_MODEL: "ya-definido", client.ENV_KEY: ""}):
                client.load_dotenv(p)
                self.assertEqual(os.environ[client.ENV_MODEL], "ya-definido")
                self.assertEqual(os.environ[client.ENV_KEY], "k2")
                self.assertNotIn("VACIA", os.environ)


class FallbackTests(unittest.TestCase):
    def test_rules(self):
        base = {"slope": 0.001, "catchment_m2": 50000, "dist_to_channel_m": 500, "urban_fraction": 0.2,
                "depression_depth_m": 0.0}
        cases = [({"dist_to_channel_m": 10}, 60, "S1", "R1"),
                 ({"depression_depth_m": 0.5}, 60, "S2", "R2"),
                 ({"urban_fraction": 0.8}, 30, "S3", "R3"),
                 ({"urban_fraction": 0.8}, 100, "S2", "R5"),
                 ({"slope": 0.05, "catchment_m2": 5000}, 60, "S4", "R4"),
                 ({}, 60, "S2", "R5")]
        for patch, rain, choice, rule in cases:
            out = fallback.decide({**base, **patch}, rain)
            self.assertEqual(out["choice"], choice, patch)
            self.assertTrue(out["rule"].startswith(rule), out)
            self.assertEqual(out, fallback.decide({**base, **patch}, rain))  # determinista

    def test_ignores_solver_data_and_missing_fields(self):
        a = fallback.decide({"slope": 0.05, "catchment_m2": 100}, 60)
        b = fallback.decide({"slope": 0.05, "catchment_m2": 100, "depth_cm": {"S3": 0}, "best": "S3"}, 60)
        self.assertEqual(a, b)
        self.assertIn(fallback.decide({}, 60)["choice"], fallback.OPTIONS)


class ShadowAndKpiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.res = Path(self.tmp.name) / "results"
        self.dec = Path(self.tmp.name) / "decisions"
        make_fixture.write(self.res)

    def tearDown(self):
        self.tmp.cleanup()

    def _all_text(self):
        return "".join(p.read_text(encoding="utf-8") for p in Path(self.tmp.name).rglob("*") if p.is_file())

    def test_fallback_only_end_to_end(self):
        buf = io.StringIO()
        with no_env(), mock.patch.object(client, "load_dotenv"), contextlib.redirect_stdout(buf):
            rc = run_shadow.main(["--results-dir", str(self.res), "--decisions-dir", str(self.dec)])
        self.assertEqual(rc, 0)
        self.assertIn("Jev NO se ejecutó", buf.getvalue())
        lines = [json.loads(l) for l in next(self.dec.glob("*.jsonl")).read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines, json.loads((self.res / "jev_decisions.json").read_text(encoding="utf-8")))
        for d in lines:
            self.assertIsNone(d["jev_output"])
            self.assertTrue(d["fallback_used"])
            self.assertEqual(d["mode"], "shadow")
            self.assertIsNone(d["latency_ms"])
            self.assertIsNone(d["cost_usd"])
            self.assertIsNone(d["model_id"])
            self.assertEqual(d["agree"], d["fallback_output"]["choice"] == d["solver_best"])
            self.assertEqual(d["agree"], d["fallback_agree"])
            self.assertNotIn("depth_cm", d["input"])
            self.assertEqual(d["input"]["options"], ["S1", "S2", "S3", "S4"])
        s = json.loads((self.res / "kpis_summary.json").read_text(encoding="utf-8"))
        j = s["jev"]
        self.assertEqual((j["n_decisions"], j["n_jev_live"], j["fallback_pct"]), (6, 0, 100.0))
        self.assertIsNone(j["accuracy_vs_solver_pct"])
        self.assertIsNone(j["latency_p50_ms"])
        self.assertIsNone(j["calibration"])
        self.assertIn("no definidos", j["note"])
        # respaldo: H1->S1 (ok, ok); H2->S2 (ok, ok); H3 30mm->S3 (ok), 100mm->S4 (ok)
        self.assertEqual(j["baseline_accuracy_vs_solver_pct"], 100.0)
        self.assertEqual(s["label"], "estimación preliminar, modelo simplificado")
        self.assertEqual(s["dem_source"], "sintético")
        self.assertEqual(s["context"]["real_episodes"], "sin dato")

    def test_solution_and_solver_kpis(self):
        s = kpis.build_summary(self.res)
        row = next(r for r in s["solutions"] if r["rain_mm"] == 30 and r["solution_id"] == "S2")
        self.assertEqual((row["max_depth_reduction_cm"], row["max_depth_reduction_pct"],
                          row["flooded_area_reduction_pct"]), (10.0, 50.0, 50.0))
        self.assertEqual(len(s["solutions"]), 8)
        self.assertEqual(s["solver"]["n_scenarios"], 10)
        self.assertEqual(s["solver"]["n_invalid"], 1)
        self.assertEqual(s["solver"]["volume_error_pct_max"], 6.0)
        self.assertEqual(s["solver"]["runtime_s_mean"], 1.5)

    def test_live_jev_mixed_with_failures(self):
        seen = []

        def decide(state, instructions, criteria, timeout_s):
            seen.append((state, criteria))
            if state["hotspot_id"] == "H3":
                raise client.JevError("refusal", "x")
            return {"choice": "S2", "probabilities": {"S1": 0.1, "S2": 0.8, "S3": 0.05, "S4": 0.05},
                    "confidence": None, "cost": 0.001, "model": "snap-1", "latency_ms": 100.0 + len(seen)}

        with mock.patch.dict(os.environ, ENV):
            out = run_shadow.run(self.res, self.dec, decide=decide)
        for state, criteria in seen:
            self.assertFalse({"depth_cm", "best", "solver_best"} & set(state))
            self.assertNotIn("S0", criteria)
            self.assertIn("capacity_m3", criteria["S2"])
        j = out["kpis"]["jev"]
        self.assertEqual((j["n_decisions"], j["n_jev_live"]), (6, 4))
        self.assertEqual(j["accuracy_vs_solver_pct"], 50.0)   # H2 acierta, H1 falla
        self.assertEqual(j["baseline_accuracy_vs_solver_pct"], 100.0)
        self.assertEqual(j["jev_vs_baseline_agreement_pct"], 50.0)
        self.assertEqual(j["fallback_pct"], 33.3)
        self.assertEqual(j["cost_per_decision_usd"], 0.001)
        self.assertEqual(j["cost_total_usd"], 0.004)
        self.assertEqual(j["model_id"], FAKE_MODEL)
        self.assertEqual(j["model_snapshot"], "snap-1")
        self.assertEqual(j["jev_errors"], {"refusal": 2})
        self.assertEqual(j["calibration"]["mean_prob_chosen_pct"], 80.0)
        self.assertEqual(j["calibration"]["accuracy_pct"], 50.0)
        self.assertIsNotNone(j["latency_p95_ms"])
        h3 = [d for d in out["decisions"] if d["hotspot_id"] == "H3"]
        self.assertTrue(all(d["fallback_used"] and d["jev_output"] is None and d["agree"] for d in h3))
        self.assertNotIn(FAKE_KEY, self._all_text())

    def test_circuit_breaker_and_no_key_leak(self):
        n = []

        def post(url, headers, json, timeout):
            n.append(1)
            return Resp(401, None, f"invalid {FAKE_KEY}")

        buf = io.StringIO()
        with mock.patch.dict(os.environ, ENV), mock.patch.object(client, "_default_post", post), \
                mock.patch.object(client, "load_dotenv"), contextlib.redirect_stdout(buf), \
                contextlib.redirect_stderr(buf):
            run_shadow.main(["--results-dir", str(self.res), "--decisions-dir", str(self.dec)])
        self.assertEqual(len(n), run_shadow.MAX_CONSECUTIVE_FAILURES)
        self.assertNotIn(FAKE_KEY, buf.getvalue())
        self.assertNotIn(FAKE_KEY, self._all_text())
        j = json.loads((self.res / "kpis_summary.json").read_text(encoding="utf-8"))["jev"]
        self.assertEqual(j["n_jev_live"], 0)
        self.assertIn("http_401", j["note"])


if __name__ == "__main__":
    unittest.main()
