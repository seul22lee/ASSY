"""Command-line entry point.

    ./mujoco_core/bin/py -m assy.cli --benchmark BM-002
    ./mujoco_core/bin/py -m assy.cli --request "Design a ..." --out out/custom
"""

from __future__ import annotations

import argparse
import sys

from assy.pipeline import Pipeline
from benchmarks import ALL, Tier


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="assy", description="Run the ASSY-Next pipeline")
    ap.add_argument("--benchmark", choices=sorted(ALL), help="run a benchmark fixture")
    ap.add_argument("--request", help="natural-language product request")
    ap.add_argument("--out", default="out", help="artifact directory")
    ap.add_argument("--verbose", action="store_true", help="print Stage 05 trace")
    args = ap.parse_args(argv)

    if args.benchmark:
        bm = ALL[args.benchmark]
        request, clarifications = bm.request, list(bm.clarifications)
        bid, tier = bm.id, bm.tier.value
        print(f"=== {bm.id}  {bm.name}  [{tier}] ===")
        if bm.tier is Tier.ADVANCED:
            print(
                "note: advanced benchmarks validate a mature pipeline and are outside\n"
                "      the initial implementation milestone; incomplete results are expected."
            )
    elif args.request:
        request, clarifications, bid, tier = args.request, [], "custom", "core"
        print("=== custom request ===")
    else:
        ap.error("one of --benchmark or --request is required")
        return 2

    pipeline = Pipeline(out_dir=args.out, benchmark_id=bid, tier=tier)
    result = pipeline.run(request, clarifications=clarifications)
    out = str(result.run_dir) if result.run_dir else args.out
    print()
    print(result.report())

    definition = result.get("CADReadyEngineeringDefinition")
    if definition is not None:
        r = definition.readiness
        print()
        print("CAD readiness")
        print(f"  ready ................... {r.ready}")
        print(f"  no blocking problems .... {r.no_blocking_problems}")
        print(f"  mandatory checks run .... {r.mandatory_checks_executed}")
        print(f"  mandatory checks pass ... {r.mandatory_checks_passing}")
        print(f"  all commitments set ..... {r.all_commitments_determined}")
        print(f"  structurally solvable ... {r.system_structurally_solvable}")
        if r.blocked_reason:
            print(f"  BLOCKED ................. {r.blocked_reason.value}")
        for label, items in (
            ("undetermined", r.undetermined),
            ("missing checks", r.missing_checks),
            ("failing checks", r.failing_checks),
        ):
            if items:
                print(f"  {label}: {', '.join(items[:6])}{' ...' if len(items) > 6 else ''}")
        if args.verbose:
            print("\nStage 05 trace")
            for line in definition.working_state.trace:
                print(f"  {line}")

    evaluation = result.get("EvaluationReport")
    if evaluation is not None:
        print(f"\nEvaluation: {evaluation.overall.value}")
        for o in evaluation.outcomes:
            observed = f" observed={o.observed}{o.unit or ''}" if o.observed is not None else ""
            print(f"  {o.requirement_id:>8}  {o.status.value:<22}{observed}  {o.note}")

    print(f"\nartifacts: {out}")
    return 0 if result.all_stages_ran else 1


if __name__ == "__main__":
    sys.exit(main())
