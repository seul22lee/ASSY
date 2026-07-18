"""m15 — NAIVE BASELINE ABLATION (D-M15-1). What does the scaffolding buy?

Naive condition: a ONE-SHOT prompt (task command + "write a complete build123d program" + the same
PETG/printable context). NO ontology, NO cards, NO staged gates, NO validator retries — the model
writes geometry code directly. We then grade the raw output in three tiers:

  a. EXECUTES  — does the generated code run and produce ≥1 solid? (MUSE-class)
  b. GEOMETRY  — every solid watertight AND parts don't interpenetrate at rest (t0-class, adapted)
  c. FUNCTION  — can the task's protocol even be MAPPED onto the output? (identifiable hinge axis /
                 rack / articulated parts). Where it cannot, we record UNMAPPABLE — that IS the
                 finding: naive output is not even gradeable for function. (Physics via the generic
                 MJCF path would use CoACD, whose known limit is that it SWALLOWS functional
                 clearances — D18 — so a naive blob that happens to run still can't be trusted
                 functionally; we label this rather than fake a green.)

The MechSynth column is REUSED from the m14 certification (the deterministic guarantee is exactly
what the scaffolding buys) — not re-run, to keep the pro budget at ~18 calls (D-E-9).

Run:  ./bin/py m15_naive/naive.py [--pilot]
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = Path(__file__).parent / "out"
GEN = Path(__file__).parent / "gen"

# 6-task core subset — one per axis incl. one infeasible (drawn from the m14 ladder)
CORE = [
    dict(id="A1-snap-base", axis="base", mechanism="snap-lid",
         command="Design a snap-lid box I can push shut and pull open by hand. Plastic, for 3D printing."),
    dict(id="B1-hinge-latch", axis="base", mechanism="hinge+latch",
         command="A small hinged box whose lid latches shut at the front. Plastic, for 3D printing."),
    dict(id="C1-lift-base", axis="base", mechanism="crank-lift",
         command="Design a crank-operated platform that raises and lowers a load to different heights."),
    dict(id="A3-snap-force", axis="spec-tightening", mechanism="snap-lid",
         command="Design a push-on snap-lid box that closes with no more than 60 N by hand and needs at least 15 N of pull to open."),
    dict(id="C4-drawer", axis="constraint", mechanism="rack-drawer",
         command="Design a desktop cabinet whose drawer slides out horizontally when you turn a knob."),
    dict(id="C5-lift-nogear", axis="infeasible", mechanism="crank-lift-nogear",
         command="Design a crank lift that holds a 0.5 kg load, but without any gear or ratchet."),
]

SYSTEM = ("You are a mechanical designer. Given a design request, produce a COMPLETE parametric CAD "
          "program in Python using the build123d library that models the design as printable PETG "
          "parts (FDM, ~0.3 mm clearances, ~2 mm walls). The program must build the geometry and set "
          "a module-level variable `result` to a list of the finished build123d Part/Solid objects — "
          "ONE per separately-printed part (e.g. box and lid as two parts). Use only build123d. Do "
          "not print anything. Return ONLY the program in the `code` field.")

CODE_SCHEMA = {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}

# harness appended to the generated code: export each `result` part to STL, emit a JSON status
HARNESS = textwrap.dedent('''
    # --- m15 export harness (appended) ---
    import sys as _sys
    _sys.path[:] = [p for p in _sys.path if "m15_naive/gen" not in p]  # never shadow stdlib
    import json as _json
    from pathlib import Path as _P
    try:
        from build123d import export_stl as _export
        _parts = result if isinstance(result, (list, tuple)) else [result]
        _od = _P(_sys.argv[1]); _od.mkdir(parents=True, exist_ok=True)
        _n = 0
        for _i, _p in enumerate(_parts):
            _solid = getattr(_p, "part", _p)
            try:
                _export(_solid, str(_od / f"part_{_i}.stl"), tolerance=0.2, angular_tolerance=0.4)
                _n += 1
            except Exception as _e:
                pass
        print("M15_STATUS " + _json.dumps({"ok": True, "n_parts": len(_parts), "n_exported": _n}))
    except Exception as _e:
        print("M15_STATUS " + _json.dumps({"ok": False, "error": type(_e).__name__ + ": " + str(_e)[:200]}))
''')


def gen_code(command: str, model: str) -> tuple[str, int]:
    import os
    os.environ["MECHSYNTH_LLM_BACKEND"] = "gemini" if model.startswith("gemini") else "ollama"
    for m in [k for k in sys.modules if k.startswith("pipeline.llm_client")]:
        del sys.modules[m]                       # BACKEND is bound at import → force a fresh read
    from pipeline.llm_client import _call_backend
    prompt = SYSTEM + "\n\nDESIGN REQUEST:\n" + command
    txt, ptok, etok = _call_backend(prompt, CODE_SCHEMA, model, 0.4)
    return json.loads(txt).get("code", ""), ptok + etok


def execute(code: str, run_dir: Path) -> dict:
    """Run the generated program in a subprocess (timeout-guarded); capture exported STLs."""
    run_dir.mkdir(parents=True, exist_ok=True)
    src = run_dir / "gen.py"
    preamble = ("import sys as _s0\n_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]\n")
    src.write_text(preamble + code + "\n" + HARNESS)
    stl_dir = run_dir / "stl"
    import os as _os
    _to = int(_os.environ.get("M15_CAD_TIMEOUT", "90"))
    try:
        r = subprocess.run(["./bin/py", str(src), str(stl_dir)], cwd=str(ROOT),
                           capture_output=True, text=True, timeout=_to)
    except subprocess.TimeoutExpired:
        return {"executed": False, "reason": f"timeout (>{_to} s)"}
    status = None
    for line in r.stdout.splitlines():
        if line.startswith("M15_STATUS "):
            status = json.loads(line[len("M15_STATUS "):])
    stls = sorted(stl_dir.glob("*.stl")) if stl_dir.exists() else []
    if status is None:
        err = (r.stderr.strip().splitlines() or ["(no traceback)"])[-1][:160]
        return {"executed": False, "reason": f"crash: {err}"}
    if not status.get("ok"):
        return {"executed": False, "reason": status.get("error", "harness error")}
    return {"executed": True, "n_parts": status.get("n_parts", 0),
            "n_exported": status.get("n_exported", 0), "stls": [str(s) for s in stls]}


def grade_geometry(stls: list) -> dict:
    """b. watertight + no interpenetration at rest (t0-class, adapted to arbitrary output)."""
    import trimesh
    meshes = []
    for s in stls:
        try:
            m = trimesh.load(s, force="mesh")
            if len(m.faces):
                meshes.append(m)
        except Exception:
            pass
    if not meshes:
        return {"geometry_ok": False, "reason": "no loadable solids"}
    watertight = all(m.is_watertight for m in meshes)
    # interpenetration at rest: pairwise bounding-box overlap → sampled containment (cheap proxy)
    overlaps = 0
    for i in range(len(meshes)):
        for j in range(i + 1, len(meshes)):
            a, b = meshes[i], meshes[j]
            lo = np.maximum(a.bounds[0], b.bounds[0]); hi = np.minimum(a.bounds[1], b.bounds[1])
            if np.all(hi - lo > 0.5):                    # bbox overlap > 0.5 mm in every axis
                pts = a.sample(200)
                if b.contains(pts).sum() > 4:            # >2% of A's surface samples inside B
                    overlaps += 1
    return {"geometry_ok": bool(watertight and overlaps == 0), "watertight": bool(watertight),
            "interpenetrating_pairs": overlaps, "n_solids": len(meshes)}


def grade_function(task: dict, exe: dict) -> dict:
    """c. Can the task protocol even be MAPPED? Naive output has no declared axes/ports, so we probe
    for the mechanism's minimum structure; absent it → UNMAPPABLE (the finding). We do NOT run a
    physics green on a blob — CoACD would swallow any clearance (D18)."""
    need = {"snap-lid": 2, "hinge+latch": 2, "crank-lift": 3, "rack-drawer": 3,
            "crank-lift-nogear": 3}.get(task["mechanism"], 2)
    n = exe.get("n_exported", 0)
    if n < need:
        return {"function": "UNMAPPABLE",
                "reason": f"{n} printed solids < {need} the {task['mechanism']} mechanism needs "
                          f"(no articulable parts → no hinge axis / rack to map a protocol onto)"}
    # even with enough parts, naive output declares no axis/port/clearance → the protocol has no
    # referent (no hinge axis, no rack line). We record UNMAPPABLE with that reason (D18: a generic
    # CoACD conversion would swallow the very clearance the protocol tests).
    return {"function": "UNMAPPABLE",
            "reason": f"{n} solids present but NO declared mechanism referent (no hinge axis / rack / "
                      f"port); a generic MJCF conversion (CoACD) swallows functional clearances (D18) "
                      f"— the protocol cannot be mapped without the scaffolding's declared axes."}


import numpy as np  # noqa: E402


def run_cell(task: dict, model: str, seed: int) -> dict:
    tag = f"{task['id']}__{model.split('-')[0] if model.startswith('gemini') else 'qwen'}__s{seed}"
    run_dir = GEN / tag
    rec = {"task": task["id"], "axis": task["axis"], "model": model, "seed": seed, "tag": tag}
    try:
        code, ntok = gen_code(task["command"], model)
    except Exception as e:
        rec.update(gen_ok=False, error=f"gen: {type(e).__name__}: {str(e)[:120]}"); return rec
    rec["gen_ok"] = True; rec["gen_tokens"] = ntok; rec["code_chars"] = len(code)
    (run_dir).mkdir(parents=True, exist_ok=True)
    (run_dir / "source.txt").write_text(code)    # NOT .py — a code.py would shadow stdlib `code`
    exe = execute(code, run_dir)
    rec["executes"] = exe["executed"]
    rec["execute_detail"] = exe.get("reason") or f"{exe.get('n_exported')} solids exported"
    if not exe["executed"]:
        rec["geometry_ok"] = False; rec["function"] = "N/A (did not execute)"; return rec
    g = grade_geometry(exe["stls"])
    rec["geometry_ok"] = g["geometry_ok"]; rec["geometry_detail"] = g
    f = grade_function(task, exe)
    rec["function"] = f["function"]; rec["function_reason"] = f["reason"]
    rec["stls"] = exe["stls"]
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pilot = "--pilot" in sys.argv
    models = ["gemini-3.1-pro-preview", "qwen3-coder:latest"]
    tasks = CORE[:1] if pilot else CORE
    seeds = [0] if pilot else [0, 1, 2]
    rows = []
    for task in tasks:
        for model in models:
            for seed in seeds:
                r = run_cell(task, model, seed)
                rows.append(r)
                mk = ("exec✓" if r.get("executes") else "exec✗")
                gk = ("geom✓" if r.get("geometry_ok") else "geom✗")
                print(f"  {r['tag']:44s} {mk} {gk} func={r.get('function','—')}")
    (OUT / ("pilot.json" if pilot else "naive_results.json")).write_text(json.dumps(rows, indent=2))
    ex = sum(r.get("executes", False) for r in rows)
    gm = sum(r.get("geometry_ok", False) for r in rows)
    fn = sum(r.get("function", "") not in ("UNMAPPABLE", "N/A (did not execute)") for r in rows)
    print(f"\n=== naive: {len(rows)} runs — EXECUTES {ex}/{len(rows)}, GEOMETRY {gm}/{len(rows)}, "
          f"FUNCTION-mappable {fn}/{len(rows)} ===")
    print("wrote", OUT / ("pilot.json" if pilot else "naive_results.json"))


if __name__ == "__main__":
    main()
