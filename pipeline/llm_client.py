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
    MECHSYNTH_LLM_BACKEND  ollama (default) | gemini | openai_compat
    MECHSYNTH_LLM_MODEL    default per backend
    MECHSYNTH_LLM_BASE_URL default http://localhost:11434 (ollama)
    GEMINI_API_KEY / GOOGLE_API_KEY   gemini, read from env or .env ONLY
    MECHSYNTH_LLM_API_KEY  openai_compat, read from env only

**Key handling.** Keys are read from the process env or a local `.env` (gitignored; `.env.example`
documents the names with no values). A key is sent as an HTTP header and NEVER interpolated into a
prompt — so it cannot reach `ir.stage_log`, which records prompts and responses verbatim.
`backend_info()` reports only whether a key was found, never its value.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.stage_failure import StageFailure

def _load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from a local .env into os.environ WITHOUT overriding a real env var.
    Values are never logged, echoed, or returned. The file is gitignored (see .env.example)."""
    f = Path(path)
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


_load_dotenv(str(Path(__file__).resolve().parents[1] / ".env"))

MAX_RETRIES = 3          # §4: pydantic parse retries ≤ 3
BACKEND = os.environ.get("MECHSYNTH_LLM_BACKEND", "gemini")  # D-E-8: gemini is the default; ollama/qwen is the cheap regression backend
_MODEL_DEFAULTS = {"ollama": "qwen3-coder:latest", "gemini": "", "openai_compat": ""}
DEFAULT_MODEL = os.environ.get("MECHSYNTH_LLM_MODEL") or _MODEL_DEFAULTS.get(BACKEND, "")
DEFAULT_BASE = os.environ.get("MECHSYNTH_LLM_BASE_URL", "http://localhost:11434")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT = int(os.environ.get("MECHSYNTH_LLM_TIMEOUT", "600"))


def _gemini_key() -> str:
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        raise LLMBackendError(
            "gemini backend selected but no GEMINI_API_KEY (or GOOGLE_API_KEY) is set. Put it in "
            "the gitignored .env — see .env.example. Never hardcode it.")
    return k


def _gemini_pick_model() -> str:
    """Pick the current PRO-TIER Gemini text model by ASKING the API, not by hardcoding a guess
    that silently rots. The exact resolved string is logged into stage_log for every call.

    Explicit over clever: a first attempt ranked on "contains 'pro'" and chose
    `deep-research-pro-preview` — a different PRODUCT that happens to share the word. So the rule is
    now a denylist of non-text/other-product families plus a version sort, and it is stated rather
    than inferred. Set MECHSYNTH_LLM_MODEL to override and skip resolution entirely.
    """
    global _GEMINI_RESOLVED
    if _GEMINI_RESOLVED:
        return _GEMINI_RESOLVED
    req = urllib.request.Request(f"{GEMINI_BASE}/models?key={_gemini_key()}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            models = json.load(r).get("models", [])
    except Exception as e:
        raise LLMBackendError(_redact(f"could not list Gemini models: {type(e).__name__}: {e}")) from e
    names = [m["name"].split("/", 1)[-1] for m in models
             if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    # not general text models / not the same product line
    DENY = ("image", "tts", "audio", "vision", "embedding", "aqa", "customtools",
            "deep-research", "lyria", "nano-banana", "robotics", "omni", "live")
    pro = [n for n in names
           if n.startswith("gemini-") and "-pro" in n and not any(d in n for d in DENY)]
    if not pro:
        raise LLMBackendError(f"no pro-tier Gemini text model exposes generateContent; saw {names[:15]}")

    def version(n: str) -> float:
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0.0

    # highest version wins; among equals prefer the shorter (plain) name over decorated variants.
    _GEMINI_RESOLVED = sorted(pro, key=lambda n: (version(n), -len(n)), reverse=True)[0]
    return _GEMINI_RESOLVED


_GEMINI_RESOLVED = ""


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
    prompt_tokens: int = 0        # D-E-9 / token-fix: input tokens the backend BILLED for this call
    eval_tokens: int = 0          # output tokens

    def as_log(self) -> dict:
        # every string that lands in the audit file passes through _redact — the log is committed,
        # so this is the last place a key could escape.
        return {"stage": self.stage, "attempt": self.attempt, "model": self.model,
                "prompt_sha256": self.prompt_sha256, "prompt": _redact(self.prompt),
                "response_raw": _redact(self.response_raw),
                "latency_s": round(self.latency_s, 2), "ok": self.ok,
                "validator_errors": [_redact(e) for e in self.errors],
                # tokens BOTH directions, per call — the meter D-E-9 mandated. `tokens` is the
                # canonical field; `eval_tokens` kept for back-compat with older summaries.
                "tokens": {"prompt": self.prompt_tokens, "output": self.eval_tokens,
                           "total": self.prompt_tokens + self.eval_tokens},
                "prompt_tokens": self.prompt_tokens, "eval_tokens": self.eval_tokens}


class LLMBackendError(RuntimeError):
    pass


def _redact(text: str) -> str:
    """Strip key material from anything that could be logged.

    This is not paranoia — it is a real hole I opened: `_post` puts the URL in its error message,
    and Gemini's URL carries `?key=...`. Those errors are recorded VERBATIM in `ir.stage_log`
    (validator_errors), so an HTTP 400 would have written the key into a committed audit file.
    Redact at the boundary where strings become loggable.
    """
    text = re.sub(r"([?&]key=)[^&\s\"']+", r"\1<REDACTED>", text)
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "MECHSYNTH_LLM_API_KEY"):
        v = os.environ.get(var)
        if v and len(v) > 8:
            text = text.replace(v, "<REDACTED>")
    return text


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
        raise LLMBackendError(_redact(f"HTTP {e.code} from {url}: {e.read()[:300]!r}")) from e
    except Exception as e:
        raise LLMBackendError(_redact(f"{type(e).__name__} calling {url}: {e}")) from e


def _strip_unsupported(schema):
    """Gemini's responseSchema is a strict OpenAPI subset: it rejects keys it does not know.
    Same schema semantics, different dialect — the STAGES must not have to care which backend they
    are talking to, so the translation lives here."""
    if isinstance(schema, dict):
        out = {}
        for k, v in schema.items():
            if k in ("additionalProperties", "$schema", "definitions", "default"):
                continue
            out[k] = _strip_unsupported(v)
        return out
    if isinstance(schema, list):
        return [_strip_unsupported(v) for v in schema]
    return schema


def _call_backend(prompt: str, schema: dict, model: str, temperature: float) -> tuple[str, int, int]:
    """One raw generation, schema-constrained. Returns (text, prompt_tokens, eval_tokens) — BOTH
    token directions from the backend's own usage report (never an estimate)."""
    if BACKEND == "gemini":
        # Same contract as every other backend: schema-constrained JSON out, no free prose.
        # The key rides in the URL/header, never in `prompt` — so it cannot reach stage_log.
        d = _post(f"{GEMINI_BASE}/models/{model}:generateContent?key={_gemini_key()}", {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature,
                                 "responseMimeType": "application/json",
                                 "responseSchema": _strip_unsupported(schema)},
        }, REQUEST_TIMEOUT)
        cands = d.get("candidates") or []
        if not cands:
            raise LLMBackendError(f"gemini returned no candidates: {str(d)[:200]}")
        parts = cands[0].get("content", {}).get("parts") or [{}]
        txt = "".join(p.get("text", "") for p in parts)
        um = d.get("usageMetadata", {}) or {}
        return txt, int(um.get("promptTokenCount", 0)), int(um.get("candidatesTokenCount", 0))
    if BACKEND == "ollama":
        d = _post(f"{DEFAULT_BASE}/api/chat", {
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "format": schema, "keep_alive": "30m",
            "options": {"temperature": temperature, "num_ctx": 16384},
        }, REQUEST_TIMEOUT)
        return (d["message"]["content"], int(d.get("prompt_eval_count", 0)),
                int(d.get("eval_count", 0)))
    if BACKEND == "openai_compat":
        d = _post(f"{DEFAULT_BASE}/v1/chat/completions", {
            "model": model, "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "stage_out", "schema": schema,
                                                "strict": True}},
        }, REQUEST_TIMEOUT)
        _u = d.get("usage", {}) or {}
        return (d["choices"][0]["message"]["content"], int(_u.get("prompt_tokens", 0)),
                int(_u.get("completion_tokens", 0)))
    raise LLMBackendError(f"unknown MECHSYNTH_LLM_BACKEND={BACKEND!r}")


def resolve_model() -> str:
    """The exact model string this run will use — resolved once, logged verbatim (never a guess)."""
    if DEFAULT_MODEL:
        return DEFAULT_MODEL
    if BACKEND == "gemini":
        return _gemini_pick_model()
    raise LLMBackendError(f"no model configured for backend {BACKEND!r}; set MECHSYNTH_LLM_MODEL.")


def backend_info() -> dict:
    """Never contains a key — only whether one was found."""
    try:
        model = resolve_model()
    except LLMBackendError as e:
        model = f"<unresolved: {e}>"
    has_key = bool(os.environ.get("MECHSYNTH_LLM_API_KEY")
                   or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return {"backend": BACKEND, "model": model,
            "base_url": GEMINI_BASE if BACKEND == "gemini" else DEFAULT_BASE,
            "api_key_from_env": has_key, "max_retries": MAX_RETRIES}


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
    model = model or resolve_model()
    convo = prompt
    last_errors: list[str] = []

    for attempt in range(MAX_RETRIES + 1):
        t0 = time.time()
        try:
            raw, ptok, etok = _call_backend(convo, schema, model, temperature)
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
                         prompt_tokens=ptok, eval_tokens=etok)
        ir.stage_log.append(rec.as_log())
        # INSTRUMENTATION SELF-CHECK (D-E-9 / token-fix): a real response whose backend reported ZERO
        # tokens both directions means the per-call meter has silently rotted — fail the run rather
        # than record an empty `tokens:{}` (the exact bug this fix closes).
        if raw and (ptok + etok) == 0:
            raise LLMBackendError(
                f"token instrumentation returned 0 prompt+output tokens for a non-empty {stage} "
                f"response (model={model}); the per-call meter is not recording — refusing to "
                f"proceed with an unmeasured run.")

        if not errors:
            return obj
        last_errors = errors
        if attempt == MAX_RETRIES:
            break
        # repair turn: the model is told, verbatim, which rule it broke. No paraphrase — a
        # paraphrase is a place for the error to drift. API economy: feed back only the FIRST 3
        # errors (fixing the first few usually clears the rest, and it caps prompt growth per retry).
        shown = errors[:3]
        more = f"  (+{len(errors) - 3} more, hidden to cap prompt growth)" if len(errors) > 3 else ""
        convo = (f"{prompt}\n\n"
                 f"# YOUR PREVIOUS ANSWER WAS REJECTED (attempt {attempt + 1}/{MAX_RETRIES})\n"
                 f"You produced:\n{raw}\n\n"
                 f"The validator rejected it with these errors (first 3 shown):\n"
                 + "\n".join(f"  - {e}" for e in shown) + more +
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
    """Per-stage call/retry/token counts — the headline of the audit trail. `_total` makes per-run
    cost visible at a glance (API economy: tokens are the meter)."""
    out: dict = {}
    tot_calls = tot_prompt = tot_output = 0
    for r in ir.stage_log:
        st = r.get("stage", "?")
        e = out.setdefault(st, {"calls": 0, "retries": 0, "ok": False,
                                "prompt_tokens": 0, "output_tokens": 0})
        tk = r.get("tokens") or {"prompt": r.get("prompt_tokens", 0), "output": r.get("eval_tokens", 0)}
        e["calls"] += 1
        e["retries"] = max(e["retries"], r.get("attempt", 0))
        e["ok"] = e["ok"] or r.get("ok", False)
        e["prompt_tokens"] += tk.get("prompt", 0); e["output_tokens"] += tk.get("output", 0)
        tot_calls += 1; tot_prompt += tk.get("prompt", 0); tot_output += tk.get("output", 0)
    out["_total"] = {"calls": tot_calls, "prompt_tokens": tot_prompt, "output_tokens": tot_output,
                     "total_tokens": tot_prompt + tot_output}
    return out
