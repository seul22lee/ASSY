"""tools/render_ir.py — the REUSABLE IR-diagram renderer (spec §14 T1). Renders a task's golden IR as
a graph in the m2_ontology visual conventions: functions → behaviors → pieces(roles) → elements(card
ids) → bindings → protocols. Writes ir_<task>.mmd (mermaid) + ir_<task>.svg (self-contained).

An IR without its diagram fails T1. This wraps the existing viz/ir_graph.py (to_mermaid/to_svg) so
every Task D-track uses one renderer.

  ./bin/py tools/render_ir.py <task_fn> [out_dir]      # e.g. screw_lift, latched_drawer
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

import tasks.build_goldens as G  # noqa: E402
from viz.ir_graph import to_mermaid, to_svg  # noqa: E402


def render(task_fn: str, out_dir: Path) -> tuple[Path, Path]:
    plan = getattr(G, task_fn)()
    out_dir.mkdir(parents=True, exist_ok=True)
    mmd = out_dir / f"ir_{task_fn}.mmd"
    svg = out_dir / f"ir_{task_fn}.svg"
    mmd.write_text(to_mermaid(plan))
    svg.write_text(to_svg(plan, title=f"{task_fn}  —  functions → behaviors → pieces → elements → bindings → protocols"))
    return mmd, svg


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "screw_lift"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "m22_composition" / "out"
    m, s = render(task, out)
    print(f"wrote {m}\nwrote {s}")
