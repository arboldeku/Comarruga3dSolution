"""Cliente mínimo de Jev (contrato 6.2 de docs/CONTRACTS.md).

Formato: API System One de TypeSafe. Endpoint: POST {JEV_BASE_URL}/v1/systemone
(JEV_BASE_URL por defecto: https://api.typesafe.ai; sin cambiar el valor por defecto del código).
Ejecución del hackathon (modo sombra, 2026-11-10): JEV_BASE_URL=https://openrouter.ai/api con
JEV_MODEL_ID=typesafe/jev-1.14. Alternativa nativa, no probada con éxito: https://api.typesafe.ai con jev-1.14.0.
  { "model": $JEV_MODEL_ID, "state": ..., "questions": { "q": { "type": "choice",
    "instructions": "...", "criteria": { "<opción>": "<descripción>" } } } }

Seguridad: la clave solo se lee de la variable de entorno JEV_API_KEY (o de un
`.env` en la raíz, sin sobrescribir el entorno). Nunca se imprime, registra ni guarda:
los mensajes de error no incluyen cabeceras y cualquier texto externo se limpia.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Mapping

DEFAULT_BASE_URL = "https://api.typesafe.ai"
ENDPOINT_PATH = "/v1/systemone"
ENV_KEY = "JEV_API_KEY"
ENV_BASE = "JEV_BASE_URL"
# Precio: 0,042 USD por millón de tokens de entrada, salida gratis (docs.typesafe.ai/models.md, 2026-11-10).
USD_PER_INPUT_TOKEN = 0.042 / 1_000_000
COST_NOTE = "coste estimado a partir de tokens"
ENV_MODEL = "JEV_MODEL_ID"
QUESTION = "q"
ROOT = Path(__file__).resolve().parent.parent


class JevError(Exception):
    """Fallo de la llamada a Jev. `reason` es un código corto y estable."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}" if detail else reason)


def load_dotenv(path: Path | str | None = None) -> None:
    """Parser mínimo de `.env` (KEY=VALOR). No sobrescribe variables ya definidas."""
    p = Path(path) if path else ROOT / ".env"
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().removeprefix("export ").strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        if k and v and not os.environ.get(k):
            os.environ[k] = v


def env_status() -> tuple[bool, str]:
    """(disponible, nota). La nota nombra las variables ausentes, nunca sus valores."""
    missing = [n for n in (ENV_MODEL, ENV_KEY) if not os.environ.get(n, "").strip()]
    if missing:
        return False, " y ".join(missing) + " no definidos"
    return True, ""


def endpoint() -> str:
    base = os.environ.get(ENV_BASE, "").strip() or DEFAULT_BASE_URL
    return base.rstrip("/") + ENDPOINT_PATH


def _error_detail(resp: Any) -> str:
    """Campo `detail` del cuerpo JSON de error; si no hay JSON, el texto."""
    try:
        d = resp.json()["detail"]
        return d if isinstance(d, str) else repr(d)
    except Exception:
        return str(getattr(resp, "text", ""))


def _scrub(text: str, key: str) -> str:
    text = str(text)
    if key:
        text = text.replace(key, "***")
    return text[:300]


def _default_post(url: str, headers: dict, json: dict, timeout: float):  # pragma: no cover - red
    import requests

    return requests.post(url, headers=headers, json=json, timeout=timeout)


def decide_choice(
    state: Any,
    instructions: str,
    criteria: Mapping[str, str],
    timeout_s: float = 20.0,
    *,
    post: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Pregunta Choice a Jev. Devuelve
    {choice, probabilities, confidence|None, cost, cost_note, model, input_tokens, output_tokens, latency_ms}.
    `cost` (USD) se estima: input_tokens × 0,042 / 1e6 (la API no devuelve coste).

    Lanza JevError (reason) ante: `missing_env`, `timeout`, `network`, `http_<código>`,
    `bad_response`, `invalid_choice` (cualquier type != "choice" o choice fuera de las opciones; la forma
    de un rechazo no está documentada). Un reintento como máximo ante 429/529/5xx.
    """
    ok, note = env_status()
    if not ok:
        raise JevError("missing_env", note)
    key = os.environ[ENV_KEY].strip()
    model = os.environ[ENV_MODEL].strip()
    body = {
        "model": model,
        "state": state,
        "questions": {QUESTION: {"type": "choice", "instructions": instructions, "criteria": dict(criteria)}},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    send = post or _default_post
    url = endpoint()

    t0 = time.perf_counter()
    resp = None
    for attempt in (0, 1):
        try:
            resp = send(url, headers=headers, json=body, timeout=timeout_s)
        except Exception as exc:  # no se propaga el original: podría arrastrar la petición
            name = type(exc).__name__
            reason = "timeout" if "timeout" in name.lower() else "network"
            raise JevError(reason, name) from None
        status = getattr(resp, "status_code", None)
        if attempt == 0 and (status == 429 or (isinstance(status, int) and status >= 500)):
            sleep(1.0)
            continue
        break
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    status = getattr(resp, "status_code", None)
    if status != 200:
        raise JevError(f"http_{status}", _scrub(_error_detail(resp), key))
    try:
        data = resp.json()
        answer = data["answers"][QUESTION]
        kind = answer["type"]
    except Exception as exc:
        raise JevError("bad_response", type(exc).__name__) from None
    choice = answer.get("choice")
    if kind != "choice" or choice not in criteria:
        raise JevError("invalid_choice", _scrub(f"type={kind!r} choice={choice!r}", key))
    usage = data.get("usage") or {}
    tokens = usage.get("input_tokens")
    known = isinstance(tokens, (int, float)) and not isinstance(tokens, bool)
    return {
        "choice": choice,
        "probabilities": answer.get("probabilities"),
        "confidence": answer.get("confidence"),
        "cost": tokens * USD_PER_INPUT_TOKEN if known else None,
        "cost_note": COST_NOTE if known else None,
        "input_tokens": tokens,
        "output_tokens": usage.get("output_tokens"),
        "model": data.get("model"),
        "latency_ms": latency_ms,
    }
