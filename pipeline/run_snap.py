"""One-command snap-task runner: IR → ⑤ resolve → ⑥ compile → Tier0 → Tier1 → report.html.

Assembles a RunData dict (command, rationale sheet, IR graph, renders, gate results, verdict) and
hands it to viz.report.render_report. Tier2 is recorded as N/A — T-S1 has no use-phase motion
(SNAPFIT §0). Snap engagement/retention are formula-verified (Tier1), interference is Tier0.

  run_snap(plan, box_params, strategy, frequent, label) -> RunData

A host whose binding cannot seat the required beam L fails at ⑥ (GEOM_INFEASIBLE, D-GEN-3) — the
edge-overhang board clip is such a host and is deferred to M-G-1 (D-GEN-4).
"""

from __future__ import annotations

import base64
import io

import numpy as np

from knowledge.cards.snap_hook_geometry import CLEARANCE, carve
from knowledge.templates import TEMPLATES
from pipeline.s5_geometry import resolve_plan
from pipeline.stage_failure import StageFailure
from verify.t0_static import clearance_check, retention_check, three_way_check, watertight
from verify.t1_remeasure import check_drift, remeasure_hook
from viz.ir_graph import to_mermaid

BAYER = "Bayer Snap-Fit Joints for Plastics"


def _instantiate(plan) -> dict:
    """Instantiate each Piece's template, seeding params from the plan (so carve sees box_l etc.)."""
    pieces = {}
    for pc in plan.pieces:
        tmpl = TEMPLATES[pc.template_ref]
        pieces[pc.id] = tmpl(**{k: v for k, v in pc.params.items() if isinstance(v, (int, float))})
    return pieces


def _png_b64(fig) -> str:
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=115, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _render_iso(parts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import trimesh
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from build123d import export_stl
    from pathlib import Path
    tmp = Path("/tmp/_run_snap.stl")
    fig = plt.figure(figsize=(5, 4.5)); ax = fig.add_subplot(111, projection="3d")
    allv = []
    for i, (pid, part) in enumerate(sorted(parts.items())):
        export_stl(part, str(tmp), tolerance=0.05, angular_tolerance=0.3)
        m = trimesh.load(tmp, force="mesh"); tmp.unlink()
        col = ["#7fb2e5", "#f6c453", "#8fd694"][i % 3]
        ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolor=col,
                                             edgecolor="#33333322", linewidths=0.2, alpha=0.9))
        allv.append(m.vertices)
    allv = np.vstack(allv); c = allv.mean(0); r = (allv.max(0) - allv.min(0)).max() / 2 * 1.05
    ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
    ax.set_box_aspect((1, 1, 1)); ax.set_axis_off(); ax.view_init(elev=22, azim=-58)
    return _png_b64(fig)


def _rationale(res, dims) -> list:
    """The design-rationale sheet: every resolved dimension as [value | governing equation |
    citation]. This is the auditable heart of the report (SNAPFIT §9.1)."""
    C = {2: "1.09", 1: "0.67"}.get(2, "C")
    rows = [
        ("ε (working strain)", f"{res.eps:.3f}", "ε_pm × (0.6 if frequent) × 0.5",
         f"{BAYER} Table 2 p.12 + safety"),
        ("h (root thickness)", f"{res.h:.3f} mm", f"h = {C}·ε·L²/y  (design-2 inversion)",
         f"{BAYER} Table 1 p.9 / Calc Example I p.16"),
        ("L (beam length)", f"{res.L:.2f} mm", "given (fixed_y) / solved from ε-ceiling (hold_ret)",
         f"{BAYER} §2.2 bounds"),
        ("P (deflection force)", f"{res.P:.2f} N", "P = (b·h²/6)·(Es·ε/l)",
         f"{BAYER} Table 1 p.9"),
        ("W_in (mating, per hook)", f"{res.W_in:.2f} N", "W = P·(μ+tanα_in)/(1−μ·tanα_in)",
         f"{BAYER} p.14 / Fig.18"),
        ("W_out (separation)", res.W_out_label, "W = P·(μ+tanα_out)/(1−μ·tanα_out)"
         + ("  →  α_out ≥ self-lock ⇒ PERMANENT" if res.permanent else ""),
         f"{BAYER} p.14"),
        ("α_out (retract)", f"{res.alpha_out_final:.1f}°",
         f"≤ self_lock(μ)−10° = {res.self_lock_deg-10:.1f}°  (placement rule)",
         f"{BAYER} p.14/Fig.18 asymptote (D-GEN-2)"),
        ("y (undercut)", f"{dims.y:.2f} mm", "design input; = insertion deflection",
         f"{BAYER} p.11 (deflection = undercut)"),
    ]
    return [{"name": n, "value": v, "equation": e, "citation": c} for n, v, e, c in rows]


def run_snap(plan, *, box_params=None, strategy="fixed_y", frequent=False, label="T-S1") -> dict:
    command = plan.command
    stage_log = []

    # ⑤ resolve --------------------------------------------------------------------------
    infeasible = None
    try:
        res5, _ = resolve_plan(plan, frequent=frequent, strategy=strategy)
        r = res5[plan.elements[0].id]
        stage_log.append(("⑤ resolve", f"strategy={strategy}, frequent={frequent} → FEASIBLE"))
    except StageFailure as e:
        infeasible = e
        stage_log.append(("⑤ resolve", f"strategy={strategy} → {e.code}: {e.detail}"))
        return {"label": label, "command": command, "infeasible": True,
                "stage_log": stage_log, "failure": {"code": e.code, "detail": e.detail,
                "data": e.data}, "verdict": "FAIL (INFEASIBLE at ⑤)"}

    # ⑥ compile --------------------------------------------------------------------------
    pieces = _instantiate(plan)
    if box_params:
        for pid, bp in box_params.items():
            pieces[pid].params.update(bp)
    inst = plan.elements[0]
    binds = [b for b in plan.bindings if b.element_id == inst.id]
    # Retained pieces are foreign/immutable (a board/PCB) — a window catch may not cut them (D-GEN-4).
    immutable = frozenset(pc.id for pc in plan.pieces if pc.role == "retained")
    try:
        cr = carve(pieces, inst, binds, immutable_pids=immutable)
    except StageFailure as e:
        # ⑥ refused to compile — e.g. GEOM_INFEASIBLE (D-GEN-3): the required beam L does not fit
        # this host binding. An honest diagnosis, rolled back to ④, NOT a crash.
        stage_log.append(("⑥ compile", f"{e.code}: {e.detail}"))
        return {"label": label, "command": command, "infeasible": True, "stage_log": stage_log,
                "failure": {"code": e.code, "detail": e.detail, "data": e.data},
                "verdict": f"FAIL (INFEASIBLE at ⑥ — {e.code})"}
    stage_log.append(("⑥ compile", f"{len(cr.dims)} hook(s) + windows; tags {list(cr.tags)}; "
                      f"from_defaults={cr.meta['from_defaults']}"))
    d0 = cr.dims[0]
    # ⑤'s resolved parameters ARE the IR — this is what Tier1 re-measures against (not d0, which is
    # itself a ⑥ product; see t1_remeasure.check_drift). L/h from the resolve, b/y design inputs.
    ip = inst.params
    ir_params = {"L": float(ip["L_hook"]), "h": float(ip["h_root"]),
                 "b": float(ip["b"]), "y": float(ip["y_undercut"])}

    # Tier0 ------------------------------------------------------------------------------
    eng = {}
    for d in cr.dims:
        v = np.array(d.nose_tip_xyz) - np.array(d.root_xyz); v[2] = 0
        n = np.linalg.norm(v); eng["hook_" + d.side_tag] = tuple(v / n) if n > 1e-9 else (1, 0, 0)
    hooks = {k: v for k, v in cr.tags.items() if k.startswith("hook")}
    gates = []
    t0_ok = True
    # The insertion axis IS the hook growth direction: to disengage (undo the snap) the hook
    # retracts along −growth. This is host-agnostic — for the box the hooks grow −Z (lid down);
    # for the panel they grow +Z (board inserts the other way). Deriving it from the geometry
    # instead of hard-coding −Z is what makes the SAME Tier0 work on both hosts.
    catch_pid = next(b.piece_id for b in binds if b.port == "catch_window")
    hook_pid = next(b.piece_id for b in binds if b.port == "beam_root")
    undercut = 0.0
    for name, ok, det in watertight(cr.parts, strict=True) + \
            [clearance_check(d0.b + 2 * CLEARANCE, d0.b)]:
        gates.append(("Tier0", name, ok, det))
    # The §5.2 three-way check covers the WINDOW catch (nose passes through solid, interfering by y).
    # The edge-overhang catch (board clip) is a distinct topology deferred to M-G-1 (D-GEN-4); such
    # a host fails earlier — at ⑥ (GEOM_INFEASIBLE) — so it never reaches this check.
    try:
        t0 = three_way_check(receiver=cr.parts[catch_pid], mover=cr.parts[hook_pid],
                             hooks=hooks, y=d0.y, engage_dirs=eng, K=40,
                             insertion_dir=d0.growth_dir)
        for name, ok, det in t0.checks:
            gates.append(("Tier0 §5.2", name, ok, det))
        undercut = t0.undercut_measured_mm
    except StageFailure as e:
        t0_ok = False
        gates.append(("Tier0", f"three-way check ({e.code})", False, e.detail))

    # Tier0 (d) positive_retention — for a snap_event retention behavior (B2-class), the nose must
    # bear against the catch when the retained piece is pulled out. Pull-out = the assembly
    # separation axis = base-piece → retained-piece. "Held by gravity only" fails here.
    if any(b.motion.kind == "snap_event" and b.phase == "static" for b in plan.behaviors):
        base_pid = next((pc.id for pc in plan.pieces if pc.is_base), None)
        ret_pid = next((pc.id for pc in plan.pieces if not pc.is_base), catch_pid)
        bc, rc = cr.parts[base_pid].center(), cr.parts[ret_pid].center()
        pull = np.array([rc.X - bc.X, rc.Y - bc.Y, rc.Z - bc.Z])
        name, ok, det = retention_check(cr.tags["hook_" + d0.side_tag], cr.parts[catch_pid],
                                        pull, d0.y, d0.b)
        gates.append(("Tier0 §5.2", name, ok, det))

    # Tier1 ------------------------------------------------------------------------------
    # Re-measurement is topology-independent (it measures the compiled hook), so it runs even
    # when the window three-way check was N/A — as long as Tier0 didn't hard-fail.
    t1_ok = True
    if t0_ok is not False:
        try:
            rem = check_drift(d0, remeasure_hook(cr.tags["hook_" + d0.side_tag], d0, undercut),
                              ir_params=ir_params)
            for k, ir, m, dr, ok in rem.rows:
                gates.append(("Tier1 §5.3", f"{k}: |IR−measured| ≤ 0.05", ok,
                              f"IR {ir} vs measured {m} (drift {dr})"))
        except StageFailure as e:
            t1_ok = False
            gates.append(("Tier1", f"re-measurement ({e.code})", False, e.detail))

    # G-S2 (force windows) — from the resolve checks
    for name, val, op, thr, ok, margin in r.checks:
        gates.append(("G-S2 ⑤", name, ok, f"{val if isinstance(val,str) else round(val,2)} "
                      f"{op} {thr}"))

    scored = [g for g in gates if g[2] is not None]   # None = N/A, not counted
    all_ok = all(g[2] for g in scored)
    na = len(gates) - len(scored)
    verdict = ("PASS" if all_ok else "FAIL") + (f" ({na} N/A)" if na else "") \
        + "  ·  Tier2: N/A (no use-phase motion — SNAPFIT §0)"

    return {
        "label": label, "command": command, "infeasible": False, "strategy": strategy,
        "frequent": frequent, "permanent": r.permanent,
        "stage_log": stage_log,
        "rationale": _rationale(r, d0),
        "mermaid": to_mermaid(plan),
        "render_iso": _render_iso(cr.parts),
        "gates": gates,
        "verdict": verdict,
        "tier2": "N/A — T-S1 has no use-phase motion; engagement/retention are Tier1 formulas, "
                 "interference is Tier0 (SNAPFIT §0).",
        "summary": {"h": round(r.h, 3), "L": round(r.L, 2), "W_in": round(r.W_in, 2),
                    "W_out": r.W_out_label, "alpha_out": round(r.alpha_out_final, 1),
                    "undercut_measured": round(undercut, 3), "y_designed": round(d0.y, 3)},
    }
