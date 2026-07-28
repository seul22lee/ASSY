#!/usr/bin/env python3
"""Write an index naming the newest run for each benchmark.

Runs accumulate because none may be deleted: a past run is evidence of what the
pipeline actually did on that date, and regenerating it would destroy the record.
So the fix for a crowded `out/` is navigation, not tidying: the only thing this
removes is a stale `latest` symlink, never a run.

Recency is taken from the directory name where it carries a date, and from the
modification time otherwise, so a hand-named run still sorts sensibly.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out"
DATED = re.compile(r"run-(\d{8})")

#: Files worth linking to directly from the index, in reading order.
HIGHLIGHTS = [
    ("SUMMARY.txt", "run summary — all stages"),
    ("stage_04_concept_visualization/concept_layout.png", "concept render"),
    ("stage_07_cad/cad_assembly.png", "CAD render"),
    ("stage_05_engineering_integration/part_topology.json", "part topology"),
    ("stage_05_engineering_integration/parameter_system.json", "parameter system"),
    ("stage_06_parametric_solver/report.md", "solver report"),
    ("stage_06_parametric_solver/output.json", "solver output"),
    ("stage_07_cad/assembly.step", "assembly STEP"),
]


def newest(bench: Path) -> Path | None:
    runs = [d for d in bench.glob("run-*") if d.is_dir()]
    if not runs:
        return None

    def key(d: Path):
        m = DATED.search(d.name)
        return (m.group(1) if m else "", d.stat().st_mtime)

    return sorted(runs, key=key)[-1]


def main() -> int:
    if not OUT.is_dir():
        print(f"no output directory at {OUT}", file=sys.stderr)
        return 1

    lines = ["# Latest results", "", "Regenerate with `python tools/index_runs.py`.", ""]
    for bench in sorted(p for p in OUT.iterdir() if p.is_dir() and p.name.startswith("BM-")):
        run = newest(bench)
        if run is None:
            continue
        # A `latest` symlink alongside a single run reads as a second copy of it.
        # The index carries the same information without adding a tree entry.
        stale = bench / "latest"
        if stale.is_symlink() or stale.exists():
            stale.unlink()

        total = len([d for d in bench.glob("run-*") if d.is_dir()])
        lines += [f"## {bench.name}", "",
                  f"`{run.relative_to(OUT.parent)}`  ({total} runs kept)", ""]
        for rel, label in HIGHLIGHTS:
            if (run / rel).exists():
                lines.append(f"- [{label}]({(run / rel).relative_to(OUT.parent)})")
        lines.append("")
        print(f"{bench.name}: {run.name}")

    (OUT / "LATEST.md").write_text("\n".join(lines))
    print(f"wrote {OUT / 'LATEST.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
