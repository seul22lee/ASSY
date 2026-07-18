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


def _gemini_list_text_models() -> list[str]:
    """Names of Gemini models that expose generateContent — a metadata call (NOT a generation, so it
    consumes no token quota and is safe as a free-tier reachability probe)."""
    req = urllib.request.Request(f"{GEMINI_BASE}/models?key={_gemini_key()}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            models = json.load(r).get("models", [])
    except Exception as e:
        raise LLMBackendError(_redact(f"could not list Gemini models: {type(e).__name__}: {e}")) from e
    return [m["name"].split("/", 1)[-1] for m in models
            if "generateContent" in (m.get("supportedGenerationMethods") or [])]


def _gemini_pick_model(tier: str = "") -> str:
    """Pick the current Gemini text model of a TIER (pro | flash) by ASKING the API, not by hardcoding
    a guess that silently rots. The exact resolved string is logged into stage_log for every call.

    Tier is MECHSYNTH_LLM_TIER (default pro, D-E-8). Flash is the FREE-TIER workhorse (D-M16-5):
    generous free quota, so the m15 bulk cells can run on it if it holds the bindings.

    Explicit over clever: a first attempt ranked on "contains 'pro'" and chose
    `deep-research-pro-preview` — a different PRODUCT that happens to share the word. So the rule is
    now a denylist of non-text/other-product families plus a version sort, and it is stated rather
    than inferred. Set MECHSYNTH_LLM_MODEL to override and skip resolution entirely.
    """
    tier = (tier or os.environ.get("MECHSYNTH_LLM_TIER", "pro")).lower()
    if tier not in ("pro", "flash"):
        raise LLMBackendError(f"MECHSYNTH_LLM_TIER must be 'pro' or 'flash', got {tier!r}")
    if _GEMINI_RESOLVED.get(tier):
        return _GEMINI_RESOLVED[tier]
    names = _gemini_list_text_models()
    # not general text models / not the same product line
    DENY = ("image", "tts", "audio", "vision", "embedding", "aqa", "customtools",
            "deep-research", "lyria", "nano-banana", "robotics", "omni", "live")
    want = f"-{tier}"
    cands = [n for n in names
             if n.startswith("gemini-") and want in n and not any(d in n for d in DENY)]
    if not cands:
        raise LLMBackendError(f"no {tier}-tier Gemini text model exposes generateContent; saw {names[:15]}")

    def version(n: str) -> float:
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0.0

    # highest version wins; among equals prefer the shorter (plain) name over decorated variants.
    _GEMINI_RESOLVED[tier] = sorted(cands, key=lambda n: (version(n), -len(n)), reverse=True)[0]
    return _GEMINI_RESOLVED[tier]


_GEMINI_RESOLVED: dict[str, str] = {}


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


# Free-tier reality (D-M16-5): a free Gemini/OpenAI key is RATE-LIMITED, not paid — the server
# answers 429 (quota) or 503 (overloaded) instead of billing. So the ONLY thing standing between
# "free tier" and "works" is backoff. These transient statuses are retried with exponential backoff,
# honouring a Retry-After header when the server sends one; everything else fails fast (a 400 is a
# bug, not a wait). Tunable via env so a latency-tolerant free-tier run can wait longer.
_BACKOFF_STATUSES = {429, 500, 503}
_BACKOFF_MAX = int(os.environ.get("MECHSYNTH_LLM_BACKOFF_RETRIES", "6"))
_BACKOFF_BASE = float(os.environ.get("MECHSYNTH_LLM_BACKOFF_BASE", "2.0"))   # seconds
_BACKOFF_CAP = float(os.environ.get("MECHSYNTH_LLM_BACKOFF_CAP", "90.0"))    # seconds


def _post(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode()
    key = os.environ.get("MECHSYNTH_LLM_API_KEY")
    for attempt in range(_BACKOFF_MAX + 1):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read()[:400]
            # a 429 is NOT always transient: a billing SPEND-CAP / RESOURCE_EXHAUSTED rejection is
            # permanent until the cap is raised — retrying it just wedges. Fail fast on those; only
            # back off on genuine rate-limit (per-minute quota) 429s.
            btxt = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else str(body)
            hard_429 = e.code == 429 and ("spend" in btxt.lower() or "spending cap" in btxt.lower()
                                          or "billing" in btxt.lower())
            if e.code in _BACKOFF_STATUSES and attempt < _BACKOFF_MAX and not hard_429:
                # prefer the server's own Retry-After; else exponential backoff, capped.
                ra = e.headers.get("Retry-After") if e.headers else None
                try:
                    wait = float(ra) if ra else min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** attempt))
                except ValueError:
                    wait = min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** attempt))
                time.sleep(wait)
                continue
            raise LLMBackendError(_redact(f"HTTP {e.code} from {url}: {body!r}")) from e
        except Exception as e:
            # network hiccups (timeout, reset) are transient too — back off and retry.
            if attempt < _BACKOFF_MAX:
                time.sleep(min(_BACKOFF_CAP, _BACKOFF_BASE * (2 ** attempt)))
                continue
            raise LLMBackendError(_redact(f"{type(e).__name__} calling {url}: {e}")) from e
    raise LLMBackendError(f"exhausted {_BACKOFF_MAX} backoff retries calling {url}")


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


def reachable_backends() -> dict:
    """Which backends this server can actually reach, probed with UNBILLED metadata calls only
    (ollama /api/tags, gemini model-list, openai_compat /v1/models) — NO generation, so this spends
    no token quota. Answers the review's 'report which free options are actually reachable'.
    Returns {backend: {"reachable": bool, "detail": str, "free": str}}."""
    out: dict = {}
    # ollama (local, always free)
    try:
        with urllib.request.urlopen(f"{DEFAULT_BASE}/api/tags", timeout=5) as r:
            tags = [m["name"] for m in json.load(r).get("models", [])]
        out["ollama"] = {"reachable": True, "free": "local (no key, no quota)",
                         "detail": f"{len(tags)} models: {tags[:6]}"}
    except Exception as e:
        out["ollama"] = {"reachable": False, "free": "local", "detail": f"{type(e).__name__}: {e}"}
    # gemini (free tier = flash; pro has a small free quota) — model list is unbilled
    try:
        names = _gemini_list_text_models()
        flash = [n for n in names if n.startswith("gemini-") and "-flash" in n][:4]
        pro = [n for n in names if n.startswith("gemini-") and "-pro" in n][:4]
        out["gemini"] = {"reachable": True,
                         "free": "flash: generous free tier; pro: small free tier then billed",
                         "detail": f"flash={flash} pro={pro}"}
    except Exception as e:
        out["gemini"] = {"reachable": False, "free": "flash free / pro billed",
                         "detail": _redact(f"{type(e).__name__}: {e}")}
    # openai_compat (generic: base_url + key from .env) — only meaningful if configured
    base = os.environ.get("MECHSYNTH_LLM_BASE_URL")
    if base and base != "http://localhost:11434":
        try:
            req = urllib.request.Request(f"{base}/v1/models")
            k = os.environ.get("MECHSYNTH_LLM_API_KEY")
            if k:
                req.add_header("Authorization", f"Bearer {k}")
            with urllib.request.urlopen(req, timeout=8) as r:
                mids = [m.get("id") for m in (json.load(r).get("data") or [])][:6]
            out["openai_compat"] = {"reachable": True, "free": "depends on provider",
                                    "detail": f"base={base} models={mids}"}
        except Exception as e:
            out["openai_compat"] = {"reachable": False, "free": "depends on provider",
                                    "detail": _redact(f"{type(e).__name__}: {e}")}
    else:
        out["openai_compat"] = {"reachable": None, "free": "depends on provider",
                                "detail": "not configured (set MECHSYNTH_LLM_BASE_URL + _API_KEY in .env)"}
    return out


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
                     "total_tokens": tot_prompt + tot_output,
                     # keep the per-stage shape (retries/ok) so callers can iterate .items() uniformly
                     "retries": max((v["retries"] for k, v in out.items() if k != "_total"), default=0),
                     "ok": all(v["ok"] for k, v in out.items() if k != "_total") if out else False}
    return out
