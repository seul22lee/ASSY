#!/usr/bin/env python3
"""Regenerate every stage for every benchmark into one run directory.

A run is a snapshot of the whole pipeline at one revision, never a mix. Producing
stages independently lets a Stage 07 artifact sit beside a Stage 04 artifact that
a later change already invalidated, and nothing in the directory says so - the
files look equally current because they are equally present. So every stage is
written together or none is.

Usage:  python tools/run_benchmarks.py [run-name] [BM-001 ...]
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from assy.cadrender import render_cad  # noqa: E402
from assy.domain.engineering import CommitmentKind as CK  # noqa: E402
from assy.mechanismrender import render_mechanism, _views  # noqa: E402
from assy.stages import MechanicalArchitectureGenerator, ProductArchitecturePlanner  # noqa: E402
from assy.stages.s04_kinematic import KinematicBuilder  # noqa: E402
from assy.stages.s05_engineering import EngineeringIntegration  # noqa: E402
from assy.stages.s06_solver import ParametricSolver  # noqa: E402
from assy.stages.s07_cad import CADBuilder  # noqa: E402
from tests.fixtures import load_spec  # noqa: E402

BENCHMARKS = ("BM-001", "BM-002", "BM-101")


def run_one(bid: str, run: str) -> dict:
    spec = load_spec(bid)
    mech = MechanicalArchitectureGenerator().run(spec=spec)
    product = ProductArchitecturePlanner().run(spec=spec, mechanical=mech)
    km = KinematicBuilder(product, mech).build()
    definition = EngineeringIntegration().run(
        spec=spec, mechanical=mech, product=product, kinematic=km)
    solved = ParametricSolver().run(definition=definition)

    base = ROOT / "out" / bid / run
    states = [s.name for s in mech.selected.states]
    d02 = base / "stage_02_mechanical_architecture"
    d03 = base / "stage_03_product_architecture"
    d04 = base / "stage_04_concept_visualization"
    d05 = base / "stage_05_engineering_integration"
    d06 = base / "stage_06_parametric_solver"
    d07 = base / "stage_07_cad"
    for d in (d02, d03, d04, d05, d06, d07):
        d.mkdir(parents=True, exist_ok=True)

    (d02 / "output.json").write_text(mech.model_dump_json(indent=2))
    (d03 / "output.json").write_text(product.model_dump_json(indent=2))

    render_mechanism(km, states, d04 / "concept_layout.png",
                     subtitle=f"{bid} · {mech.selected_id} · kinematic concept model")
    (d04 / "kinematic_model.json").write_text(json.dumps({
        "selected": mech.selected_id, "views": _views(km), "states": states,
        "axes": km.axes, "free_choices": km.free_choices,
        "unplaced": km.unplaced, "contradictions": km.contradictions,
        "joints": {n: {"type": j.type.value, "axis": j.axis,
                       "parent": j.parent, "child": j.child}
                   for n, j in km.joints.items()},
        "coordinates": {f"{s}|{j}": round(q, 4) for (s, j), q in km.coordinates.items()},
    }, indent=2))

    ws = definition.working_state
    params = {c.subject for c in ws.active if c.kind is CK.PARAMETER}
    cons = [c for c in ws.active if c.kind is CK.CONSTRAINT]
    objs = [c for c in ws.active if c.kind is CK.OBJECTIVE]
    referenced: set[str] = set()
    for c in cons:
        referenced.update(re.findall(r"[A-Za-z_][A-Za-z_0-9.]*", c.expression or ""))
    feats: dict[str, list[str]] = {}
    for c in ws.active:
        if "feature" in c.roles and "." in c.subject:
            host, name = c.subject.split(".", 1)
            feats.setdefault(host, []).append(name)

    (d05 / "engineering_definition.json").write_text(definition.model_dump_json(indent=2))
    (d05 / "part_topology.json").write_text(
        json.dumps({k: sorted(v) for k, v in sorted(feats.items())}, indent=2))
    (d05 / "parameter_system.json").write_text(json.dumps({
        "parameters": sorted(params),
        "linked": sorted(params & referenced),
        "unlinked": sorted(params - referenced),
        "constraints": [{"subject": c.subject, "expression": c.expression,
                         "why": c.statement} for c in cons],
        "objectives": [{"subject": c.subject, "expression": c.expression} for c in objs],
    }, indent=2))

    (d06 / "output.json").write_text(solved.model_dump_json(indent=2))
    values = getattr(solved, "parameters", [])
    (d06 / "report.md").write_text("\n".join(
        [f"# {bid} Stage 06 parametric resolution", "",
         f"- parameters carried: {len(values)}",
         f"- diagnostics: {len(getattr(solved, 'diagnostics', []) or [])}", "",
         "## diagnostics"]
        + [f"- {x}" for x in (getattr(solved, "diagnostics", []) or [])] or ["- none"]))

    manifest = CADBuilder(out_dir=d07).run(
        definition=definition, solved=solved, kinematic=km,
        state_name=states[0] if states else None)
    (d07 / "manifest.json").write_text(manifest.model_dump_json(indent=2))
    render_cad(manifest, d07 / "cad_assembly.png",
               subtitle=f"{bid} · {mech.selected_id} · built geometry")

    summary = [
        f"{bid}   {mech.selected_id}", "",
        f"stage 05 ready: {definition.readiness.ready}",
        f"stage 07 status: {manifest.status.value}  ({len(manifest.parts)} parts, "
        f"{len(manifest.failures)} failures)", "",
        f"parameters {len(params)}, of which linked to a constraint: "
        f"{len(params & referenced)}",
        f"constraints {len(cons)}, objectives {len(objs)}",
        f"stage 04 contradictions: {len(km.contradictions)}, unplaced: {len(km.unplaced)}",
        "", "CONSTRAINTS",
    ]
    summary += [f"  {c.expression}\n      {c.statement[:110]}" for c in cons]
    summary += ["", "PART TOPOLOGY"]
    summary += [f"  {k}\n     " + ", ".join(sorted(v)) for k, v in sorted(feats.items())]
    summary += ["", "AXES"] + [f"  {k}: {v}" for k, v in sorted(km.axes.items())]
    summary += ["", "OPEN PROBLEMS"]
    summary += [f"  {k}: {v}" for k, v in
                sorted(Counter(p.phenomenon for p in ws.open_problems).items())]
    (base / "SUMMARY.txt").write_text("\n".join(summary))

    return {"benchmark": bid, "family": mech.selected_id,
            "parts": len(manifest.parts), "failures": len(manifest.failures),
            "params": len(params), "linked": len(params & referenced),
            "constraints": len(cons), "cad": manifest.status.value}


def main() -> int:
    args = [a for a in sys.argv[1:]]
    run = args[0] if args and not args[0].startswith("BM-") else \
        "run-" + datetime.now().strftime("%Y%m%d-%H%M")
    benches = [a for a in args if a.startswith("BM-")] or list(BENCHMARKS)

    rows = []
    for bid in benches:
        rows.append(run_one(bid, run))
        print(f"{bid}: {rows[-1]}")

    print(f"\nwritten to out/<BM>/{run}/")
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "tools" / "index_runs.py")], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
