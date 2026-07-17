"""Stage-⑥/t0 evaluation of D-ONT-12 AssemblyRules on the COMPILED geometry — their first live
firing. Two typed checks, one per kind:

  resource  — a numeric budget over named IR params: Σ contributors  <=/<  budget. Read straight
              from the plan (⑤ values), no geometry needed.
  exclusion — a geometric sweep non-interference: the `excluded` element's compiled geometry, swept
              through the `sweep_of` element's motion (the lid rotating about the hinge axis), must
              not interfere with the static host once disengaged. The M0 B4 lid-sweep check, now
              driven by a first-class rule instead of a hand-written one.
"""

from __future__ import annotations

import math

import numpy as np
from build123d import Axis, Pos, Rotation


def check_resource(plan, ar) -> tuple[bool, str]:
    """Σ contributors <=/< budget, from named IR referents (params)."""
    def val(ref):
        base, name = ref.split(".", 1)
        inst = plan.instance(base) or plan.piece(base)
        return float((inst.params or {})[name])
    p = ar.predicate
    total = sum(val(c) for c in p["contributors"])
    budget = val(p["budget"])
    ok = total <= budget if p["op"] == "<=" else total < budget
    detail = (f"Σ({'+'.join(p['contributors'])}) = {total:.1f} {p['op']} {p['budget']} = {budget:.1f}"
              f"  → {'ok' if ok else 'OVER by %.1f' % (total - budget)}")
    return ok, detail


def check_exclusion(ar, excluded_solid, static_solid, axis_pt, axis_dir,
                    sweep_deg=95.0, release_band_deg=20.0, steps=20) -> tuple[bool, str, float]:
    """Sweep `excluded_solid` (the latch, riding the lid) about the hinge axis 0→`sweep_deg`. Like
    the snap three-way (D22), the INITIAL band is intended: a rigid hook cannot deflect, so its
    undercut interferes with the window edge until it has lifted clear (in reality it flexes out).
    So the exclusion the rule forbids is interference in the FREE sweep — after the latch has
    RELEASED. Pass iff all interference is confined to the release band (≤ release_band_deg) and the
    free sweep beyond it is clean. Returns (ok, detail, free_peak_mm3)."""
    ax_pt = np.array(axis_pt, float)
    ax = np.array(axis_dir, float); ax /= np.linalg.norm(ax)
    angs = np.linspace(0.0, sweep_deg, steps + 1)
    pen = []
    for ang in angs:
        rot = Pos(*ax_pt) * Rotation(*(np.rad2deg(ax * math.radians(ang)))) * Pos(*(-ax_pt))
        try:
            inter = (rot * excluded_solid) & static_solid
            pen.append(inter.volume if inter.solids() else 0.0)
        except Exception:
            pen.append(0.0)
    nz = [i for i, p in enumerate(pen) if p >= 1.0]
    if not nz:
        return True, f"latch clears the box through the whole 0→{sweep_deg:.0f}° sweep (0 mm³)", 0.0
    last_ang = float(angs[nz[-1]])
    release_peak = max(pen[:nz[-1] + 1])
    # the free-sweep peak = any interference at an angle beyond the release band
    free_peak = max([pen[i] for i in range(len(pen)) if angs[i] > release_band_deg] + [0.0])
    ok = last_ang <= release_band_deg and free_peak < 1.0
    detail = (f"undercut releases by {last_ang:.0f}° (release-band peak {release_peak:.0f} mm³, "
              f"intended — D22); free sweep beyond {release_band_deg:.0f}° peak {free_peak:.2f} mm³ "
              f"→ {'CLEARS the box' if ok else 'FOULS the box'}")
    return ok, detail, free_peak



def check_alignment(plan, ar, tol_deg=1.0, tol_level_mm=0.5) -> tuple[bool, str]:
    """D-E-10: the two (or more) named travel axes must be PARALLEL (directions equal within
    tol_deg) and, if `level`, at the same height (mount-plane Z equal within tol_level_mm). Each axis
    referent is 'E.port' → resolved to that binding's anchor frame on the compiled geometry. This is
    the falsifiable t0 form of 'the drawer's two rails must line up': a skewed or stepped pair fails.

    Returns (ok, detail). No LLM, no physics — pure frame comparison, exactly what a first-class
    instance↔instance constraint should reduce to (the whole point of option A over a shared datum,
    which would make the relation unfalsifiable)."""
    import numpy as np
    from knowledge.templates import TEMPLATES
    p_ = ar.predicate or {}
    axes = p_.get("axes") or []
    frames = []
    for ref in axes:
        eid, port = ref.split(".", 1)
        b = next((x for x in plan.bindings if x.element_id == eid and x.port == port), None)
        if b is None:
            return False, f"alignment: axis referent {ref!r} has no matching binding"
        piece = plan.piece(b.piece_id)
        tr = TEMPLATES.get(piece.template_ref)
        # instantiate with the PIECE's params (skew/step live there) — not defaults, or a skewed
        # rail would read as aligned. The compiled anchor frame is what the requirement is about.
        kw = {k: v for k, v in (piece.params or {}).items() if isinstance(v, (int, float))}
        anc = tr(**kw).anchors.get(b.anchor) if tr else None
        if anc is None:
            return False, f"alignment: anchor {b.anchor!r} on {b.piece_id} not found"
        frames.append((np.array(anc.normal, float), np.array(anc.position, float)))
    d0 = frames[0][0] / (np.linalg.norm(frames[0][0]) or 1.0)
    worst_ang, worst_dz = 0.0, 0.0
    for (d, pos) in frames[1:]:
        dn = d / (np.linalg.norm(d) or 1.0)
        ang = np.degrees(np.arccos(min(1.0, abs(float(dn @ d0)))))   # unsigned angle between axes
        worst_ang = max(worst_ang, ang)
        worst_dz = max(worst_dz, abs(float(pos[2] - frames[0][1][2])))
    ok_par = worst_ang <= tol_deg
    ok_lvl = (worst_dz <= tol_level_mm) if p_.get("level") else True
    ok = ok_par and ok_lvl
    lvl = f", level Δz {worst_dz:.2f} mm (tol {tol_level_mm})" if p_.get("level") else ""
    detail = (f"{p_.get('relation')}: max axis angle {worst_ang:.2f}° (tol {tol_deg}°){lvl} → "
              f"{'ALIGNED' if ok else 'MISALIGNED'}")
    return ok, detail


def evaluate(plan, ar, compiled: dict, axis: dict) -> dict:
    """Dispatch one AssemblyRule to its typed checker. `compiled` = {element_id: {tag: Solid}} +
    {'parts': {pid: Solid}}; `axis` = {point, dir} (mm)."""
    if ar.kind == "resource":
        ok, detail = check_resource(plan, ar)
        return {"id": ar.id, "kind": ar.kind, "provenance": ar.provenance, "ok": ok, "detail": detail}
    if ar.kind == "alignment":
        ok, detail = check_alignment(plan, ar)
        return {"id": ar.id, "kind": ar.kind, "provenance": ar.provenance, "ok": ok, "detail": detail}
    # exclusion: the excluded element's compiled geometry vs the static base
    exc = ar.predicate["excluded"]
    parts = compiled["parts"]
    base_pid = next(p.id for p in plan.pieces if p.is_base)
    # the excluded element's own tagged geometry (its hooks), else its host non-base piece
    exc_solid = compiled.get(exc, {}).get("_latch") or parts[next(
        b.piece_id for b in plan.bindings if b.element_id == exc and b.port == "beam_root")]
    ok, detail, worst = check_exclusion(ar, exc_solid, parts[base_pid], axis["point"], axis["dir"])
    return {"id": ar.id, "kind": ar.kind, "provenance": ar.provenance, "ok": ok, "detail": detail,
            "peak_interference_mm3": round(worst, 3)}
