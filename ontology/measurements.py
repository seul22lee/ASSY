"""Controlled measurement-name registry (D-ONT-6).

The gap this closes: a protocol's criteria/observables referenced measurement names as free
strings (`"theta_max_deg"`), with nothing tying them to what the verification harness actually
emits — a typo validates fine and breaks only at sim time. That is the D13 "checkable referent"
lesson one level up: a criterion is only checkable if its `observable` names something real.

So every measurement a protocol may reference lives here, once, with a unit and the phase/track
that produces it. V-13 rejects any criterion.observable or observable.measured not in this
registry. The registry migrates into the verify harness later (it is the harness's output
contract); it lives in ontology/ for now so the schema can be validated standalone.

Names here are the canonical ones the M0 physics runner (m0/vb.py, m0/p_hinge.py) actually
produced, plus the snap-fit formula outputs (§3.4). When the harness and this registry diverge,
that divergence is itself a bug to be caught — the registry is the single source of truth for
"what can be measured".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Measurement:
    name: str
    unit: str
    produced_by: str  # which verification surface emits it (audit trail)
    desc: str


_M = [
    # --- P-HINGE / V-B kinematics (m0/vb.py) ------------------------------------------
    Measurement("theta_max_deg", "deg", "P-HINGE", "peak lid opening angle (rel. to base)"),
    Measurement("theta_final_deg", "deg", "P-HINGE", "settled lid angle at end of run"),
    Measurement("overtravel_deg", "deg", "P-HINGE",
                "max angle in the deliberate overtravel probe (fold-flat detector)"),
    Measurement("bounce_open_deg", "deg", "P-HINGE", "max re-opening after first seating"),
    # --- pin retention ----------------------------------------------------------------
    Measurement("pin_radial_max_mm", "mm", "P-HINGE", "max pin drift radial to the bore axis"),
    Measurement("pin_axial_max_mm", "mm", "P-HINGE", "max pin drift along the bore axis"),
    # --- penetration, stratified by contact intent (D22) ------------------------------
    Measurement("pen_travel_mm", "mm", "P-HINGE", "non-intended contact during travel (defect)"),
    Measurement("pen_interface_mm", "mm", "P-HINGE", "pin/bore interface penetration"),
    Measurement("seat_impact_mm", "mm", "P-HINGE",
                "closing-seat impact depth (OBSERVABLE; preset-compliance artefact, D22)"),
    # --- free-body bookkeeping --------------------------------------------------------
    Measurement("box_slid_mm", "mm", "P-HINGE", "base COM translation (V-B free-body noise)"),
    # --- snap-fit formula recheck (Tier1, §3.4 / SNAPFIT §2.4) — snap_event surfaces --------
    Measurement("eps_pct", "%", "PR-T1", "cantilever peak strain (Bayer uniform/taper section)"),
    Measurement("W_out_over_W_in", "", "PR-T1", "separation/insertion force ratio (retention)"),
    Measurement("W_in_N", "N", "PR-T1-MATE", "per-hook mating (insertion) force"),
    Measurement("W_out_N", "N", "PR-T1-SEP", "per-hook separation force (= retention/hand-open)"),
    Measurement("mating_force_total_N", "N", "PR-T1-MATE",
                "total insertion force over all hooks (n_hooks * W_in); B1 <= 80 N ceiling"),
    Measurement("retention_force_N", "N", "PR-T1-SEP",
                "total separation force; B2 window: retention >= 15 N, hand-open <= 60 N"),
    # --- P-SLIDE / P-GEAR placeholders (declared now so M1/M3 protocols validate) -----
    Measurement("stroke_mm", "mm", "P-SLIDE", "drawer displacement along travel axis"),
    Measurement("offaxis_rot_deg", "deg", "P-SLIDE", "off-axis roll/pitch/yaw of the carriage"),
    Measurement("transmission_residual", "", "P-GEAR", "|s/(theta*r) - 1|, ratio consistency"),
    # --- P-HOLD (D-M13-2 lift): back-drive under load when the crank is released --------
    Measurement("backdrive_mm", "mm", "P-HOLD",
                "platform drop under gravity+load with the crank released (self-locking test)"),
]

MEASUREMENTS: dict[str, Measurement] = {m.name: m for m in _M}


def is_registered(name: str) -> bool:
    return name in MEASUREMENTS


def unit_of(name: str) -> str | None:
    m = MEASUREMENTS.get(name)
    return m.unit if m else None
