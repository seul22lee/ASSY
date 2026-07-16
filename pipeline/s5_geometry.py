"""Stage ⑤ — geometry parameter resolution for the snap task (SNAPFIT §2.4, MECHSYNTH §4 stage 5).

Runs the card's resolve chain on the golden-validated formulas: working strain → h (design-2
inversion) → P → W_in/W_out, then checks the FOUR force-window inequalities (from the B1/B2
snap_event windows in the IR). Infeasible ⇒ StageFailure(INFEASIBLE) listing the violated
inequalities and their margins (rollback to ④). Every resolved Parameter carries resolved_by +
citation. Stage-4 dimension choices (L, y, b) are not produced by an LLM this session, so feasible
design values stand in — flagged.

This module is stage logic; the physics stays in knowledge/cards/snap_hook_cantilever.py (formulas
only, approved at m3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from knowledge.cards.snap_hook_cantilever import (Es_secant, P_deflect, SHAPE_A_COEFF, W_mate,
                                                  W_sep, max_retract_angle, self_locking_angle,
                                                  solve_h, working_strain, y_perm)
from knowledge.materials import PETG
from ontology.schema import Citation, Parameter
from pipeline.stage_failure import StageFailure

BAYER = "Bayer Snap-Fit Joints for Plastics"

# Stage-4 dimension choices (placeholders until the LLM stage runs). Chosen feasible for T-S1a.
DESIGN_INPUTS = {"L": 12.0, "y": 1.5, "b": 8.0}
L_BOUNDS = (8.0, 25.0)  # SNAPFIT §2.2 L_mm bounds (the free variable for hold-retention)


@dataclass
class SnapResolution:
    strategy: str
    eps: float
    h: float
    L: float
    P: float
    W_in: float
    W_out: float           # separation force (N); +inf sentinel when permanent
    alpha_out_final: float
    self_lock_deg: float
    permanent: bool        # α_out ≥ self_lock ⇒ non-separable joint (T-S1d)
    checks: list  # (name, value, op, threshold, ok, margin)
    geom: dict     # resolved geometry params to inject for recompile
    feasible: bool = field(init=False)

    def __post_init__(self):
        self.feasible = all(c[4] for c in self.checks)

    @property
    def W_out_label(self) -> str:
        return "permanent (self-locking)" if self.permanent else f"{self.W_out:.2f} N"


def _cmp(v, op, thr):
    return (v <= thr) if op == "<=" else (v >= thr)


def _forces(*, L, y, b, alpha_in, alpha_out, design_type, E, mu, eps, permanent):
    h = solve_h(eps, L, y, design_type)
    Es = Es_secant(E, eps)
    P = P_deflect(b, h, Es, eps, L)
    W_in = W_mate(P, mu, alpha_in)
    W_out = float("inf") if permanent else W_sep(P, mu, alpha_out)  # ∞ = cannot be pulled open
    return h, P, W_in, W_out


def resolve_snap_hook(*, L, y, b, alpha_in, alpha_out, n_hooks, design_type,
                      E=PETG.E_MPa, mu=None, eps_perm=None, frequent=False,
                      window_mate=(0.0, 80.0), window_sep=(15.0, 60.0),
                      strategy="fixed_y") -> SnapResolution:
    """Resolve one hook. TWO strategies (D-GEN-2):

      "fixed_y"          — fix the undercut y, solve h from the strain ceiling, use the DESIGNED
                           α_out (NO escalation). Frequent-reopen thins h, and the thin beam fails
                           the retention floor honestly — the correct diagnosis, not a mask.
      "hold_retention"   — hold the retention W_out at its floor, free L within bounds, solve L
                           from the strain ceiling (ε ∝ 1/L²) then h. For frequent parts this
                           LENGTHENS the beam (longer, not thinner) — what a practising designer
                           does. This is Demo A's mechanism.

    A placement rule caps α_out at self_locking_angle(μ) − 10° in both strategies. Returns a
    SnapResolution; does not raise (the stage decides what infeasible means)."""
    from knowledge.cards.snap_hook_cantilever import EPS_PERM_PETG, MU_PETG
    mu = MU_PETG if mu is None else mu
    eps_perm = EPS_PERM_PETG if eps_perm is None else eps_perm
    a_out = float(alpha_out)
    eps = working_strain(eps_perm, frequent=frequent)   # ε_pm × (0.6 if frequent) × 0.5
    slock = self_locking_angle(mu)
    a_cap = max_retract_angle(mu)
    # A retract angle at/above the self-locking asymptote is an INTENTIONAL permanent joint
    # (T-S1d): W_sep diverges (cannot be pulled open). We classify it rather than compute a bogus
    # force, and waive the hand-open ceiling + the self-lock cap for it.
    permanent = a_out >= slock - 1e-6

    if strategy == "hold_retention" and not permanent:
        # target just above the retention floor with the designed α_out; back-solve L from P_needed
        P_need = (window_sep[0] * 1.03) / W_sep(1.0, mu, a_out)   # W_sep is linear in P
        C = SHAPE_A_COEFF[design_type]
        # P(L) = (b/6)·h²·Es·ε/L with h = C·ε·L²/y  ⇒  P = (b·Es·ε³·C²)/(6·y²) · L³
        Es = Es_secant(E, eps)
        k = (b * Es * eps**3 * C**2) / (6.0 * y**2)
        L = (P_need / k) ** (1.0 / 3.0) if k > 0 else float("inf")
        L = min(max(L, L_BOUNDS[0]), L_BOUNDS[1])
    # (fixed_y keeps the given L)

    h, P, W_in, W_out = _forces(L=L, y=y, b=b, alpha_in=alpha_in, alpha_out=a_out,
                                design_type=design_type, E=E, mu=mu, eps=eps, permanent=permanent)
    nWi = n_hooks * W_in
    checks = [
        ("n*W_in <= mate_hi", nWi, "<=", window_mate[1], _cmp(nWi, "<=", window_mate[1]),
         window_mate[1] - nWi),
        # retention floor: a permanent joint retains by definition (W_out = ∞ ≥ floor)
        ("W_out >= sep_lo (retention)", W_out, ">=", window_sep[0], _cmp(W_out, ">=", window_sep[0]),
         (W_out - window_sep[0]) if not permanent else float("inf")),
        ("h in bounds [1.2,4]", h, "<=", 4.0, 1.2 <= h <= 4.0, min(h - 1.2, 4.0 - h)),
        ("L in bounds [8,25]", L, "<=", 25.0, L_BOUNDS[0] <= L <= L_BOUNDS[1],
         min(L - L_BOUNDS[0], L_BOUNDS[1] - L)),
    ]
    if not permanent:
        # separable joints must be hand-openable AND stay clear of the self-locking cliff
        checks += [
            ("W_out <= sep_hi (hand-open)", W_out, "<=", window_sep[1],
             _cmp(W_out, "<=", window_sep[1]), window_sep[1] - W_out),
            ("alpha_out <= self_lock - 10deg", a_out, "<=", round(a_cap, 2),
             _cmp(a_out, "<=", a_cap), a_cap - a_out),
        ]
    geom = {"L_hook": L, "h_root": h, "b": b, "y_undercut": y,
            "alpha_in_deg": alpha_in, "alpha_out_deg": a_out}
    return SnapResolution(strategy=strategy, eps=eps, h=h, L=L, P=P, W_in=W_in, W_out=W_out,
                          alpha_out_final=a_out, self_lock_deg=slock, permanent=permanent,
                          checks=checks, geom=geom)


def resolve_plan(plan, *, design_inputs=None, frequent=False, strategy="fixed_y"):
    """Resolve every snap_hook element in the plan. Returns (resolutions, resolved_parameters).
    Raises StageFailure(INFEASIBLE) if any element cannot satisfy its force windows. Mutates
    each element's params in place with the resolved geometry so stage 6 recompiles for real.
    `strategy` (⑤ input): "fixed_y" (default) or "hold_retention" (D-GEN-2)."""
    di = {**DESIGN_INPUTS, **(design_inputs or {})}
    resolutions, params = {}, []
    for el in plan.elements:
        if el.card_ref != "snap_hook_cantilever":
            continue
        wm, ws = _force_windows(plan, el)
        r = resolve_snap_hook(
            L=di["L"], y=di["y"], b=di["b"],
            alpha_in=el.params.get("alpha_in_deg", 30.0),
            alpha_out=el.params.get("alpha_out_deg", 45.0),
            n_hooks=int(el.params.get("n_hooks", 2)),
            design_type=int(el.params.get("design_type", 2)),
            frequent=frequent, window_mate=wm, window_sep=ws, strategy=strategy)
        if not r.feasible:
            violated = [{"check": c[0], "value": round(c[1], 3), "op": c[2],
                         "threshold": c[3], "margin": round(c[5], 3)}
                        for c in r.checks if not c[4]]
            raise StageFailure("s5", "INFEASIBLE",
                               f"element '{el.id}' violates {len(violated)} force-window "
                               f"inequalit(y/ies): " + "; ".join(
                                   f"{v['check']} (val {v['value']} vs {v['threshold']}, "
                                   f"margin {v['margin']})" for v in violated),
                               data={"element": el.id, "violated": violated,
                                     "resolution": _summ(r)})
        el.params.update(r.geom)  # inject resolved geometry -> recompile is real (not defaults)
        resolutions[el.id] = r
        params += _resolved_parameters(el.id, r)
    plan.parameters.extend(params)
    return resolutions, params


def _force_windows(plan, el):
    """Read the mating window (B1 assembly snap_event) and separation window (B2 static
    snap_event) this element realizes, from the IR (not hard-coded)."""
    wm, ws = (0.0, 80.0), (15.0, 60.0)
    for b in plan.behaviors:
        if b.realized_by == el.id and b.motion.kind == "snap_event" and b.motion.event_force_window_N:
            if b.phase.value == "assembly":
                wm = tuple(b.motion.event_force_window_N)
            elif b.phase.value == "static":
                ws = tuple(b.motion.event_force_window_N)
    return wm, ws


def _resolved_parameters(eid, r: SnapResolution) -> list:
    cite_tbl1 = Citation(doc=BAYER, section="Table 1 p.9")
    cite_p16 = Citation(doc=BAYER, section="Calc Example I p.16")
    cite_p14 = Citation(doc=BAYER, section="p.14 mating/separation force")
    return [
        Parameter(name=f"{eid}.eps", value=round(r.eps, 5), unit="", lo=0.0, hi=0.1,
                  resolved_by="formula", citation=Citation(doc=BAYER, section="Table 2 p.12 + safety")),
        Parameter(name=f"{eid}.h_root", value=round(r.h, 4), unit="mm", lo=1.2, hi=4.0,
                  resolved_by="formula", citation=cite_p16),
        Parameter(name=f"{eid}.P", value=round(r.P, 3), unit="N", lo=0.0, hi=1e4,
                  resolved_by="formula", citation=cite_tbl1),
        Parameter(name=f"{eid}.W_in", value=round(r.W_in, 3), unit="N", lo=0.0, hi=1e4,
                  resolved_by="formula", citation=cite_p14),
        Parameter(name=f"{eid}.W_out", value=(None if r.permanent else round(r.W_out, 3)),
                  unit="N", lo=0.0, hi=1e4, resolved_by="formula",
                  citation=Citation(doc=BAYER, section="p.14 — permanent (α′≥self-lock)"
                                    if r.permanent else "p.14 separation force")),
        Parameter(name=f"{eid}.L_hook", value=round(r.L, 4), unit="mm", lo=8.0, hi=25.0,
                  resolved_by="solver" if r.strategy == "hold_retention" else "user",
                  citation=Citation(doc=BAYER, section="§2.2 bounds / hold-retention solve")),
        Parameter(name=f"{eid}.alpha_out_deg", value=round(r.alpha_out_final, 2), unit="deg",
                  lo=30.0, hi=90.0, resolved_by="user", citation=cite_p14),
    ]


def _summ(r: SnapResolution) -> dict:
    return {"strategy": r.strategy, "eps": round(r.eps, 5), "h": round(r.h, 4), "L": round(r.L, 3),
            "P": round(r.P, 3), "W_in": round(r.W_in, 3), "W_out": r.W_out_label,
            "alpha_out": round(r.alpha_out_final, 2), "self_lock": round(r.self_lock_deg, 1),
            "permanent": r.permanent}
