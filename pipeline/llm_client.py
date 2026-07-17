"""The single LLM wrapper (MECHSYNTH §4: "All LLM calls use structured output (JSON schema
enforced, pydantic parse retries ≤3)").

Three jobs, and nothing else:

  1. **Structured output.** Every call carries a JSON schema; the backend is asked to constrain
     generation to it. The LLM never emits free prose that we then parse hopefully — it emits an
     instance of a schema, which we then parse strictly. This is the mechanical half of "the LLM
     makes discrete ontology decisions only".
  2. **Validate → repair loop.** The parsed object is checked by the caller's validator. On failure
     the SAME call is re-issued with the FULL validator error text appended, up to `MAX_RETRIES`
     (3), then `StageFailure(stage, "G<n>", ...)`. The model is told exactly what rule it broke, in
     the validator's own words — no paraphrase, because a paraphrase is a place for the error to
     drift.
  3. **Audit.** Every call — including every retry — is logged verbatim into `ir.stage_log`:
     prompt hash + full prompt, raw response, retry index, validator errors, latency. **This is the
     point of the module.** A synthesis pipeline whose LLM calls are not reconstructable afterwards
     is not a research artifact, it is an anecdote.

Backend: pluggable, selected by env, NEVER a hardcoded key.
    MECHSYNTH_LLM_BACKEND  ollama (default) | openai_compat
    MECHSYNTH_LLM_MODEL    default qwen3-coder:latest
    MECHSYNTH_LLM_BASE_URL default http://localhost:11434
    MECHSYNTH_LLM_API_KEY  read from env only, only used by openai_compat
As of E-track-1 this environment has no frontier API key configured; the run uses local Ollama
(qwen3-coder 30.5B Q4). Backend choice is one env var, so re-running against a frontier model needs
no code change — see m9_llm_stages/REVIEW.md for why the model tier matters when reading scores.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from pipeline.stage_failure import StageFailure

MAX_RETRIES = 3          # §4: pydantic parse retries ≤ 3
DEFAULT_MODEL = os.environ.get("MECHSYNTH_LLM_MODEL", "qwen3-coder:latest")
DEFAULT_BASE = os.environ.get("MECHSYNTH_LLM_BASE_URL", "http://localhost:11434")
BACKEND = os.environ.get("MECHSYNTH_LLM_BACKEND", "ollama")
REQUEST_TIMEOUT = int(os.environ.get("MECHSYNTH_LLM_TIMEOUT", "600"))


@dataclass
class CallRecord:
    """One LLM call, verbatim. The unit of the audit trail."""
    stage: str
    attempt: int                 # 0 = first try, 1.. = repair retries
    model: str
    prompt_sha256: str
    prompt: str
    response_raw: str
    latency_s: float
    ok: bool
    errors: list[str] = field(default_factory=list)   # validator text that forced a retry
    eval_tokens: int = 0

    def as_log(self) -> dict:
        return {"stage": self.stage, "attempt": self.attempt, "model": self.model,
                "prompt_sha256": self.prompt_sha256, "prompt": self.prompt,
                "response_raw": self.response_raw, "latency_s": round(self.latency_s, 2),
                "ok": self.ok, "validator_errors": self.errors, "eval_tokens": self.eval_tokens}


class LLMBackendError(RuntimeError):
    pass


def _post(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    key = os.environ.get("MECHSYNTH_LLM_API_KEY")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise LLMBackendError(f"HTTP {e.code} from {url}: {e.read()[:300]!r}") from e
    except Exception as e:
        raise LLMBackendError(f"{type(e).__name__} calling {url}: {e}") from e


def _call_backend(prompt: str, schema: dict, model: str, temperature: float) -> tuple[str, int]:
    """One raw generation, schema-constrained. Returns (text, eval_tokens)."""
    if BACKEND == "ollama":
        d = _post(f"{DEFAULT_BASE}/api/chat", {
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "format": schema, "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": 16384},
        }, REQUEST_TIMEOUT)
        return d["message"]["content"], int(d.get("eval_count", 0))
    if BACKEND == "openai_compat":
        d = _post(f"{DEFAULT_BASE}/v1/chat/completions", {
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "stage_out", "schema": schema,
                                                "strict": True}},
        }, REQUEST_TIMEOUT)
        return d["choices"][0]["message"]["content"], int(d.get("usage", {}).get("completion_tokens", 0))
    raise LLMBackendError(f"unknown MECHSYNTH_LLM_BACKEND={BACKEND!r}")


def backend_info() -> dict:
    return {"backend": BACKEND, "model": DEFAULT_MODEL, "base_url": DEFAULT_BASE,
            "api_key_from_env": bool(os.environ.get("MECHSYNTH_LLM_API_KEY")),
            "max_retries": MAX_RETRIES}


def call_structured(*, ir, stage: str, gate: str, prompt: str, schema: dict, parse,
                    validate=None, model: str | None = None, temperature: float = 0.0):
    """Schema-constrained call with a validator-repair loop, fully audited.

    parse(dict) -> object      : may raise (pydantic ValidationError etc.)
    validate(object) -> [str]  : domain/IR validator errors ([] = clean); optional

    On any parse/validate failure the call is re-issued with the verbatim error text appended.
    After MAX_RETRIES the stage fails hard with StageFailure(stage, gate) — an LLM that cannot
    satisfy the schema after being told exactly what it broke is a RESULT, not something to paper
    over with a hand-written fallback (that would be the m8 fabrication lesson, one layer up).
    """
    model = model or DEFAULT_MODEL
    convo = prompt
    last_errors: list[str] = []

    for attempt in range(MAX_RETRIES + 1):
        t0 = time.time()
        try:
            raw, ntok = _call_backend(convo, schema, model, temperature)
        except LLMBackendError as e:
            rec = CallRecord(stage, attempt, model, _sha(convo), convo, "", time.time() - t0,
                             False, [str(e)])
            ir.stage_log.append(rec.as_log())
            raise StageFailure(stage, gate, f"LLM backend unreachable: {e}",
                               data={"attempt": attempt, "backend": backend_info()}) from e
        dt = time.time() - t0

        errors: list[str] = []
        obj = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            errors.append(f"response is not valid JSON despite the enforced schema: {e}")
            data = None
        if data is not None:
            try:
                obj = parse(data)
            except Exception as e:                       # pydantic ValidationError et al.
                errors.append(f"schema/pydantic parse failed: {e}")
        if obj is not None and validate is not None:
            errors = list(validate(obj))

        rec = CallRecord(stage, attempt, model, _sha(convo), convo, raw, dt, not errors, errors,
                         ntok)
        ir.stage_log.append(rec.as_log())

        if not errors:
            return obj
        last_errors = errors
        if attempt == MAX_RETRIES:
            break
        # repair turn: the model is told, verbatim, which rule it broke. No paraphrase — a
        # paraphrase is a place for the error to drift.
        convo = (f"{prompt}\n\n"
                 f"# YOUR PREVIOUS ANSWER WAS REJECTED (attempt {attempt + 1}/{MAX_RETRIES})\n"
                 f"You produced:\n{raw}\n\n"
                 f"The validator rejected it with these EXACT errors:\n"
                 + "\n".join(f"  - {e}" for e in errors) +
                 "\n\nFix ONLY what these errors name and answer again. Same JSON schema. "
                 "Do not restate the errors; return the corrected object.")

    raise StageFailure(stage, gate,
                       f"LLM could not satisfy {gate} after {MAX_RETRIES} repair retries; "
                       f"last errors: " + "; ".join(last_errors),
                       data={"attempts": MAX_RETRIES + 1, "last_errors": last_errors,
                             "backend": backend_info()})


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def stage_log_summary(ir) -> dict:
    """Per-stage call/retry counts — the headline of the audit trail."""
    out: dict = {}
    for r in ir.stage_log:
        st = r.get("stage", "?")
        e = out.setdefault(st, {"calls": 0, "retries": 0, "ok": False, "tokens": 0})
        e["calls"] += 1
        e["retries"] = max(e["retries"], r.get("attempt", 0))
        e["ok"] = e["ok"] or r.get("ok", False)
        e["tokens"] += r.get("eval_tokens", 0)
    return out
