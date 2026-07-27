"""Run-artifact layer: benchmark -> run -> stage.

Persistence and visualization are **orthogonal** to the engineering stage
contracts. No stage knows this module exists; nothing here influences an
engineering decision. The authoritative output of a stage is always its
``output.json`` - reports, projections, and renders are derived views.

    out/<benchmark_id>/run-<run_id>/
        run_manifest.json
        run_summary.md
        assumptions.md
        stage_01_requirement_interpreter/
            input_refs.json      references, not copies
            output.json          authoritative
            report.md
        ...
        stage_05_engineering_integration/
            commitments.json  problems.json  resolutions.json
            checks.json  readiness_report.json  trace.md
        stage_07_cad_builder/
            cad/  visualizations/  part_legend.md
        stage_09_simulation_runner/
            raw/  visualizations/
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from assy import viz


class Authority(str):
    """How much weight a stage output carries."""

    AUTHORITATIVE = "authoritative"
    EVIDENCE_BACKED = "evidence-backed"
    PROVISIONAL = "provisional"
    PLACEHOLDER = "placeholder"


@dataclass(frozen=True)
class StageSlot:
    number: int
    name: str
    produces: str
    consumes: tuple[str, ...]
    baseline_authority: str
    question: str


# The wiring is explicit and mirrors Pipeline.run. Kept here rather than on the
# stages so the engineering contracts stay untouched by reporting concerns.
SLOTS: tuple[StageSlot, ...] = (
    StageSlot(1, "requirement_interpreter", "RequirementSpec", (), Authority.PLACEHOLDER,
              "What must the product accomplish?"),
    StageSlot(2, "mechanical_architecture", "MechanicalArchitecture", ("RequirementSpec",),
              Authority.PLACEHOLDER, "What mechanical principles can realise the functions?"),
    StageSlot(3, "product_architecture", "ProductArchitecture",
              ("RequirementSpec", "MechanicalArchitecture"), Authority.PLACEHOLDER,
              "How do the mechanisms become a coherent product?"),
    StageSlot(4, "concept_visualization", "ConceptVisualization",
              ("ProductArchitecture", "MechanicalArchitecture"), Authority.PLACEHOLDER,
              "How might the product architecture appear spatially?"),
    StageSlot(5, "engineering_integration", "CADReadyEngineeringDefinition",
              ("RequirementSpec", "MechanicalArchitecture", "ProductArchitecture",
               "ConceptVisualization"), Authority.AUTHORITATIVE,
              "How must this design be engineered to become CAD-ready?"),
    StageSlot(6, "parametric_solver", "SolvedDesign", ("CADReadyEngineeringDefinition",),
              Authority.AUTHORITATIVE, "What values satisfy the declared constraints?"),
    StageSlot(7, "cad_builder", "CADArtifactManifest",
              ("SolvedDesign", "CADReadyEngineeringDefinition"), Authority.AUTHORITATIVE,
              "Can the solved design be deterministically realised as CAD?"),
    StageSlot(8, "simulation_plan", "SimulationPlan",
              ("RequirementSpec", "SolvedDesign", "CADArtifactManifest",
               "CADReadyEngineeringDefinition"), Authority.AUTHORITATIVE,
              "How should the design be physically tested?"),
    StageSlot(9, "simulation_runner", "SimulationResult",
              ("SimulationPlan", "CADReadyEngineeringDefinition"), Authority.EVIDENCE_BACKED,
              "What did each validation backend produce?"),
    StageSlot(10, "metric_extraction", "MetricReport", ("SimulationPlan", "SimulationResult"),
              Authority.EVIDENCE_BACKED, "What quantities were observed?"),
    StageSlot(11, "requirement_evaluation", "EvaluationReport",
              ("RequirementSpec", "MetricReport", "CADReadyEngineeringDefinition",
               "SimulationPlan", "SimulationResult"), Authority.EVIDENCE_BACKED,
              "Which requirements passed, on what evidence?"),
    StageSlot(12, "revision_routing", "RevisionDirective",
              ("EvaluationReport", "CADReadyEngineeringDefinition"), Authority.AUTHORITATIVE,
              "What should change next, and where should execution restart?"),
)

SLOT_BY_PRODUCES = {s.produces: s for s in SLOTS}


@dataclass
class RunLayout:
    """Path computation. Created before the pipeline runs so stages can write in place."""

    root: Path
    benchmark_id: str
    run_id: str
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @classmethod
    def create(cls, out_root: Path | str, benchmark_id: str, run_id: str | None = None) -> RunLayout:
        rid = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        root = Path(out_root) / benchmark_id / f"run-{rid}"
        root.mkdir(parents=True, exist_ok=True)
        return cls(root=root, benchmark_id=benchmark_id, run_id=rid)

    def stage_dir(self, number: int) -> Path:
        slot = next(s for s in SLOTS if s.number == number)
        return self.root / f"stage_{slot.number:02d}_{slot.name}"

    def dir_for(self, produces: str) -> Path:
        return self.stage_dir(SLOT_BY_PRODUCES[produces].number)


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


def _obj(o: Any) -> dict[str, Any]:
    return o.model_dump(mode="json") if hasattr(o, "model_dump") else {}


class RunArtifactWriter:
    """Writes the run tree from a completed PipelineResult."""

    def __init__(self, layout: RunLayout, benchmark_id: str, tier: str, code_version: str):
        self.layout = layout
        self.benchmark_id = benchmark_id
        self.tier = tier
        self.code_version = code_version

    # -- authority classification ------------------------------------------
    def _authority(self, slot: StageSlot, obj: Any, ok: bool) -> str:
        if not ok or obj is None:
            return Authority.PROVISIONAL
        if slot.number == 5:
            return (
                Authority.AUTHORITATIVE
                if getattr(obj.readiness, "ready", False)
                else Authority.PROVISIONAL
            )
        if slot.number == 6:
            return (
                Authority.AUTHORITATIVE
                if getattr(obj.status, "value", "") == "solved"
                else Authority.PROVISIONAL
            )
        if slot.number == 7:
            return (
                Authority.AUTHORITATIVE
                if getattr(obj.status, "value", "") == "ok"
                else Authority.PROVISIONAL
            )
        if slot.number in (9, 10, 11):
            results = getattr(obj, "results", None)
            if results is not None and not results:
                return Authority.PROVISIONAL
            metrics = getattr(obj, "metrics", None)
            if metrics is not None and not metrics:
                return Authority.PROVISIONAL
            overall = getattr(getattr(obj, "overall", None), "value", None)
            if overall in ("insufficient_evidence", "invalid_test"):
                return Authority.PROVISIONAL
            return Authority.EVIDENCE_BACKED
        return slot.baseline_authority

    # -- per-stage reports --------------------------------------------------
    def _report(self, slot: StageSlot, obj: Any, record, authority: str) -> str:
        lines = [
            f"# Stage {slot.number:02d} - {slot.name.replace('_', ' ').title()}",
            "",
            f"> {slot.question}",
            "",
            f"- **status**: {'ok' if record and record.ok else 'FAILED'}",
            f"- **produces**: `{slot.produces}`",
            f"- **object id**: `{getattr(getattr(obj, 'meta', None), 'object_id', '-')}`",
            f"- **authority**: `{authority}`",
            "",
        ]
        if record and record.error:
            lines += ["## Failure", "", "```", record.error, "```", ""]
        if record and record.detail:
            lines += ["## Summary", "", record.detail, ""]

        if slot.number == 5 and obj is not None:
            r = obj.readiness
            lines += [
                "## CAD readiness",
                "",
                "| condition | value |",
                "|---|---|",
                f"| ready | {r.ready} |",
                f"| no blocking problems | {r.no_blocking_problems} |",
                f"| mandatory checks executed | {r.mandatory_checks_executed} |",
                f"| mandatory checks passing | {r.mandatory_checks_passing} |",
                f"| all commitments determined | {r.all_commitments_determined} |",
                f"| structurally solvable | {r.system_structurally_solvable} |",
                "",
                f"Iterations: {obj.iterations}. "
                f"Commitments: {len(obj.working_state.commitments)}. "
                f"Problems: {len(obj.working_state.problems)}. "
                f"Checks: {len(obj.working_state.checks)}.",
                "",
                "See `commitments.json`, `problems.json`, `resolutions.json`, `checks.json`, "
                "`readiness_report.json`, and `trace.md` for the design loop.",
                "",
            ]
            if obj.non_blocking_risks:
                lines += ["## Non-blocking risks", ""]
                lines += [f"- {x}" for x in obj.non_blocking_risks[:12]] + [""]

        if slot.number == 8 and obj is not None and obj.modelling_limitations:
            lines += ["## Modelling limitations", ""]
            lines += [f"- {x}" for x in obj.modelling_limitations] + [""]

        if slot.number == 9 and obj is not None:
            lines += ["## Backend results", "", "| test | backend | status | events |", "|---|---|---|---|"]
            for r in obj.results:
                lines.append(
                    f"| `{r.test_id}` | {r.backend.value} | {r.status.value} | {len(r.events)} |"
                )
            lines.append("")

        if slot.number == 11 and obj is not None:
            lines += ["## Requirement outcomes", "", "| requirement | status | observed | note |", "|---|---|---|---|"]
            for o in obj.outcomes:
                observed = f"{o.observed}{o.unit or ''}" if o.observed is not None else "-"
                lines.append(f"| {o.requirement_id} | {o.status.value} | {observed} | {o.note} |")
            lines.append("")
        return "\n".join(lines)

    # -- stage 05 projections ----------------------------------------------
    def _stage05_projections(self, obj, out: Path) -> None:
        ws = obj.working_state
        _dump(out / "commitments.json", [c.model_dump(mode="json") for c in ws.commitments.values()])
        _dump(out / "problems.json", [p.model_dump(mode="json") for p in ws.problems.values()])
        _dump(out / "resolutions.json", [r.model_dump(mode="json") for r in ws.resolutions.values()])
        _dump(out / "checks.json", [k.model_dump(mode="json") for k in ws.checks.values()])
        _dump(out / "readiness_report.json", obj.readiness.model_dump(mode="json"))

        open_problems = [p for p in ws.problems.values() if p.open]
        lines = [
            "# Stage 05 - Engineering Integration Trace",
            "",
            "The design loop, in order. Each line is one problem resolved.",
            "",
            f"- iterations: {obj.iterations}",
            f"- commitments: {len(ws.commitments)} ({len(ws.active)} active)",
            f"- problems: {len(ws.problems)} ({len(open_problems)} still open)",
            f"- resolutions: {len(ws.resolutions)}",
            f"- checks: {len(ws.checks)}",
            "",
            "## Loop",
            "",
            "```text",
        ]
        lines += ws.trace or ["(no trace recorded)"]
        lines += ["```", ""]

        superseded = [c for c in ws.commitments.values() if c.status.value == "superseded"]
        if superseded:
            lines += ["## Superseded commitments", "",
                      "Retraction is normal in design; nothing is deleted.", "",
                      "| commitment | subject | retired by |", "|---|---|---|"]
            for c in superseded:
                lines.append(f"| `{c.id}` | {c.subject} | `{c.superseded_by}` |")
            lines.append("")

        if open_problems:
            lines += ["## Open problems", "", "| id | severity | phenomenon | statement |", "|---|---|---|---|"]
            for p in sorted(open_problems, key=lambda x: x.severity.value)[:40]:
                lines.append(f"| `{p.id}` | {p.severity.value} | {p.phenomenon} | {p.statement} |")
            lines.append("")
        (out / "trace.md").write_text("\n".join(lines))

    # -- stage 07 legend and views -----------------------------------------
    def _stage07(self, obj, definition, out: Path) -> None:
        parts = [p.model_dump(mode="json") for p in obj.parts]
        state = definition.working_state if definition is not None else None
        roles = {}
        if state is not None:
            for p in obj.parts:
                c = state.find_subject(p.part_id)
                if c is not None:
                    roles[p.part_id] = list(c.roles)
        made = viz.render_cad_views(parts, out / "visualizations", roles)

        lines = [
            "# Part Legend",
            "",
            "Semantic identity is owned upstream; the mapping to files below is generated",
            "*by* the CAD builder and is never the authority for engineering identity.",
            "",
            "| part | role(s) | material | bbox (mm) | mass (g) | STEP |",
            "|---|---|---|---|---|---|",
        ]
        for p in obj.parts:
            part_roles = ", ".join(roles.get(p.part_id, [])) or "-"
            bbox = " x ".join(f"{v:g}" for v in p.bbox_mm) if p.bbox_mm else "-"
            step = Path(p.step_path).name if p.step_path else "-"
            lines.append(
                f"| `{p.part_id}` | {part_roles} | {p.material or '-'} | {bbox} | "
                f"{p.mass_g if p.mass_g is not None else '-'} | `{step}` |"
            )
        lines.append("")
        if obj.failures:
            lines += ["## Build failures", ""] + [f"- {f}" for f in obj.failures] + [""]
        if made:
            lines += ["## Views", ""] + [
                f"- {k}: `visualizations/{v.name}`" for k, v in made.items()
            ] + [""]
        (out / "part_legend.md").write_text("\n".join(lines))

    # -- stage 09/10 visuals ------------------------------------------------
    def _stage09(self, plan, result, out: Path) -> None:
        vis = out / "visualizations"
        raw = out / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        by_id = {t.id: t for t in plan.tests} if plan else {}

        for res in result.results:
            test = by_id.get(res.test_id)
            if test is None:
                continue
            if res.trajectory_path and Path(res.trajectory_path).exists():
                viz.plot_trajectory(Path(res.trajectory_path), vis, test.name)
            if res.backend.value == "analytical":
                viz.plot_analytical_summary(res.series_summary, vis)

        if plan and plan.model_path and Path(plan.model_path).exists():
            cameras = {"close_and_engage": "latch_closeup", "release_latch": "latch_closeup"}
            for test in plan.tests:
                if test.backend.value != "mujoco":
                    continue
                viz.animate(
                    Path(plan.model_path),
                    vis / f"{test.name}.mp4",
                    test.model_dump(mode="json"),
                    camera=cameras.get(test.name),
                )

    # -- run-level artifacts ------------------------------------------------
    def _assumptions(self, result) -> str:
        spec = result.get("RequirementSpec")
        definition = result.get("CADReadyEngineeringDefinition")
        plan = result.get("SimulationPlan")
        lines = [
            "# Assumptions",
            "",
            "Everything this run assumed rather than derived or measured.",
            "Stated explicitly so a reviewer can challenge the inputs, not just the outputs.",
            "",
        ]
        if spec is not None:
            lines += ["## Requirement interpretation", ""]
            lines += [f"- {a}" for a in spec.assumptions] or ["- (none recorded)"]
            lines += ["", "### Unknowns not resolved", ""]
            lines += [f"- {u}" for u in spec.unknowns] or ["- (none recorded)"]
            lines += ["", "### Inferred rather than stated", ""]
            inferred = [r for r in spec.requirements if r.origin.value != "user_stated"]
            lines += [f"- `{r.id}` {r.statement} ({r.origin.value})" for r in inferred] or [
                "- (none)"
            ]
            lines.append("")
        if definition is not None:
            assumed = [
                c for c in definition.working_state.active if c.status.value == "assumed"
            ]
            lines += ["## Engineering commitments held as assumptions", ""]
            lines += [f"- `{c.id}` {c.subject} = {c.value} ({c.statement})" for c in assumed] or [
                "- (none)"
            ]
            lines.append("")
        if plan is not None and plan.modelling_limitations:
            lines += ["## Modelling limitations", ""]
            lines += [f"- {x}" for x in plan.modelling_limitations]
            lines.append("")
        lines += [
            "## Implementation maturity",
            "",
            "Stages 01-04 are deterministic placeholders standing in for LLM reasoning.",
            "Their outputs are structurally valid but shallow, and are marked `placeholder`",
            "in `run_manifest.json`. They must not be read as engineering judgement.",
            "",
        ]
        return "\n".join(lines)

    def _summary(self, result, manifest: dict[str, Any]) -> str:
        lines = [
            f"# Run Summary - {self.benchmark_id} ({self.tier})",
            "",
            f"- run: `{self.layout.run_id}`",
            f"- created: {self.layout.created}",
            f"- commit: `{manifest['commit']}`",
            f"- code version: `{self.code_version}`",
            f"- session status: **{result.session.status.value}**",
            "",
            "## Stages",
            "",
            "| # | stage | status | main output | authority | evidence / checks | unresolved |",
            "|---|---|---|---|---|---|---|",
        ]
        for entry in manifest["stages"]:
            lines.append(
                f"| {entry['number']:02d} | {entry['name']} | {entry['status']} | "
                f"{entry['main_output']} | `{entry['authority']}` | {entry['evidence']} | "
                f"{entry['unresolved']} |"
            )
        lines += ["", "## Authority legend", "",
                  "| value | meaning |", "|---|---|",
                  "| `authoritative` | genuinely derived from upstream engineering data |",
                  "| `evidence-backed` | produced by a validation backend and valid |",
                  "| `provisional` | produced, but incomplete or under-evidenced |",
                  "| `placeholder` | temporary scaffolding, not engineering judgement |",
                  ""]

        definition = result.get("CADReadyEngineeringDefinition")
        if definition is not None:
            r = definition.readiness
            lines += [
                "## CAD readiness", "",
                f"**ready = {r.ready}**", "",
                f"- blocking problems cleared: {r.no_blocking_problems}",
                f"- mandatory checks executed: {r.mandatory_checks_executed}",
                f"- mandatory checks passing: {r.mandatory_checks_passing}",
                f"- all commitments determined: {r.all_commitments_determined}",
                f"- structurally solvable: {r.system_structurally_solvable}",
                "",
            ]
            if r.failing_checks:
                lines += [f"- failing: {', '.join(r.failing_checks)}", ""]

        evaluation = result.get("EvaluationReport")
        if evaluation is not None:
            lines += ["## Requirement evaluation", "",
                      f"**overall = {evaluation.overall.value}**", "",
                      "| requirement | status | observed | note |", "|---|---|---|---|"]
            for o in evaluation.outcomes:
                observed = f"{o.observed}{o.unit or ''}" if o.observed is not None else "-"
                lines.append(f"| {o.requirement_id} | {o.status.value} | {observed} | {o.note} |")
            lines.append("")

        lines += ["## Where to look", "",
                  "- design loop: `stage_05_engineering_integration/trace.md`",
                  "- geometry: `stage_07_cad_builder/part_legend.md`",
                  "- physical evidence: `stage_09_simulation_runner/report.md`",
                  "- assumptions: `assumptions.md`", ""]
        return "\n".join(lines)

    # -- entry point --------------------------------------------------------
    def write(self, result) -> Path:
        records = {r.produced: r for r in result.stages if r.produced}
        by_name = {r.name: r for r in result.stages}
        stages_manifest: list[dict[str, Any]] = []

        for slot in SLOTS:
            out = self.layout.stage_dir(slot.number)
            out.mkdir(parents=True, exist_ok=True)
            obj = result.get(slot.produces)
            record = records.get(slot.produces) or next(
                (r for n, r in by_name.items() if n.startswith(f"{slot.number:02d} ")), None
            )
            ok = bool(record and record.ok)
            authority = self._authority(slot, obj, ok)

            _dump(
                out / "input_refs.json",
                {
                    "stage": f"stage_{slot.number:02d}_{slot.name}",
                    "question": slot.question,
                    "consumes": [
                        {
                            "object": name,
                            "object_id": getattr(
                                getattr(result.get(name), "meta", None), "object_id", None
                            ),
                            "location": f"../stage_{SLOT_BY_PRODUCES[name].number:02d}"
                            f"_{SLOT_BY_PRODUCES[name].name}/output.json",
                        }
                        for name in slot.consumes
                        if name in SLOT_BY_PRODUCES
                    ],
                },
            )
            if obj is not None:
                _dump(out / "output.json", _obj(obj))
            (out / "report.md").write_text(self._report(slot, obj, record, authority))

            evidence, unresolved = "-", "-"
            if slot.number == 5 and obj is not None:
                ws = obj.working_state
                passing = sum(1 for k in ws.checks.values() if k.is_satisfied)
                evidence = f"{passing}/{len(ws.checks)} checks satisfied"
                unresolved = f"{len(obj.working_state.blocking_problems)} blocking"
                self._stage05_projections(obj, out)
            elif slot.number == 7 and obj is not None:
                evidence = f"{len(obj.parts)} parts built"
                unresolved = f"{len(obj.failures)} build failures"
                self._stage07(obj, result.get("CADReadyEngineeringDefinition"), out)
            elif slot.number == 9 and obj is not None:
                backends = {r.backend.value for r in obj.results}
                evidence = f"{len(obj.results)} runs via {', '.join(sorted(backends)) or 'none'}"
                bad = [r for r in obj.results if r.status.value != "completed"]
                unresolved = f"{len(bad)} not completed"
                self._stage09(result.get("SimulationPlan"), obj, out)
            elif slot.number == 10 and obj is not None:
                evidence = f"{len(obj.metrics)} metrics"
                unresolved = f"{sum(1 for m in obj.metrics if not m.valid)} invalid"
                viz.plot_metric_summary(
                    [m.model_dump(mode="json") for m in obj.metrics], out / "visualizations"
                )
            elif slot.number == 11 and obj is not None:
                evidence = f"overall={obj.overall.value}"
                unresolved = f"{len(obj.failed)} failed, {len(obj.insufficient)} under-evidenced"
            elif slot.number == 6 and obj is not None:
                evidence = f"{len(obj.parameters)} parameters"
                unresolved = f"{len(obj.violated)} violated constraints"

            stages_manifest.append(
                {
                    "number": slot.number,
                    "name": slot.name,
                    "status": "ok" if ok else "failed",
                    "main_output": slot.produces,
                    "object_id": getattr(getattr(obj, "meta", None), "object_id", None),
                    "authority": authority,
                    "evidence": evidence,
                    "unresolved": unresolved,
                    "directory": f"stage_{slot.number:02d}_{slot.name}",
                }
            )

        manifest = {
            "benchmark_id": self.benchmark_id,
            "tier": self.tier,
            "run_id": self.layout.run_id,
            "timestamp": self.layout.created,
            "commit": _git_commit(),
            "code_version": self.code_version,
            "session_status": result.session.status.value,
            "stages": stages_manifest,
            "artifacts": {
                "run_summary": "run_summary.md",
                "assumptions": "assumptions.md",
                "stage_directories": [s["directory"] for s in stages_manifest],
            },
        }
        _dump(self.layout.root / "run_manifest.json", manifest)
        (self.layout.root / "run_summary.md").write_text(self._summary(result, manifest))
        (self.layout.root / "assumptions.md").write_text(self._assumptions(result))
        return self.layout.root
