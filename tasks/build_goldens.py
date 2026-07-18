"""Build the golden IRs by construction (so they are schema-valid by definition) and write
them to tasks/*.json. Run:  ./bin/py tasks/build_goldens.py

Two goldens:
  m0_hinge_box.json  — RETRO-EXPRESS the M0 hand-built hinged box, BOTH variants (nostop, stop)
                       as DesignPlans. This box already passed physics; if the schema cannot
                       express it, that is a schema bug found now instead of at M3.
  snap_starter.json  — T-S1, a snap-latch hinged box (inferred from §3.4, since SNAPFIT_STARTER
                       is not in the repo). Exercises the snap_event motion + force window.

Any expressiveness gap hit while building these is recorded as a DRAFT decision row in the
session summary, NOT patched over silently.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.schema import (Anchor, AssemblyRule, Behavior, Binding, Criterion, DesignPlan,
                             ElementInstance, FeatureInstance, Function, HostTemplate, MotionSpec,
                             Observable, Parameter, Piece, VerificationProtocol)

TASKS = Path(__file__).parent


# ======================================================================================
# Golden 1 — the M0 hinged box, retro-expressed. variant in {"nostop", "stop"}.
# ======================================================================================
def m0_hinge_box(variant: str) -> DesignPlan:
    assert variant in ("nostop", "stop")

    # --- Functions (the raw command's intent) -----------------------------------------
    functions = [
        Function(verb="allow_access", object="contents", qualifier="repeated open/close"),
    ]

    # --- Templates + their declared anchors (D-ONT-1: carried so V-02 is self-contained) ---
    # Anchor names are exactly those the M0 bindings need. In the real pipeline these are
    # auto-assigned at template creation (§2.2); here they are declared to match the geometry
    # m0/hinge_box.py actually built.
    box_shell = HostTemplate(
        template_ref="box_shell",
        params={"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0},
        anchors=[
            Anchor(name="rear_top_edge", kind="edge"),   # hinge axis line
            Anchor(name="rear_wall_outer", kind="face"),  # knuckle-lug mount
            Anchor(name="rim_top", kind="face"),          # the closing seat
        ],
    )
    lid_panel = HostTemplate(
        template_ref="lid_panel",
        params={"lid_t": 3.0},
        anchors=[
            Anchor(name="rear_edge_underside", kind="face"),  # lid knuckle mount
            Anchor(name="free_edge_mid", kind="point"),       # P-HINGE actuation point
        ]
        + ([Anchor(name="stop_flange_face", kind="face")] if variant == "stop" else []),
    )

    # --- Pieces. box/lid are FUNCTIONAL hosts (chosen at ③); the PIN is HARDWARE the hinge
    # provides (D-ONT-11) — instantiated at ④ from E1, provenance-tagged, params resolved at ⑤.
    pieces = [
        Piece(id="P1", role="base", template_ref="box_shell", is_base=True,
              params=dict(box_shell.params)),
        Piece(id="P2", role="lid", template_ref="lid_panel",
              params={**lid_panel.params,
                      **({"stop_flange_r": 8.0} if variant == "stop" else {})}),
        Piece(id="P3", role="pin", provenance="hardware", source_element="E1",
              params={"pin_d": 4.0, "pin_len": 30.6}),   # ⑤-resolved from the hinge (D-ONT-11)
    ]

    # --- Element: the pin hinge, carving into both pieces ---------------------------------
    elements = [
        ElementInstance(id="E1", card_ref="pin_hinge", host_pieces=["P1", "P2"],
                        params={"pin_d": 4.0, "knuckle_w": 8.0, "knuckle_n": 3,
                                "clearance": 0.30}),
    ]

    # --- PassiveFeature: the stop flange (stop variant only), D-ONT-4 ----------------------
    # The flange is a feature on the lid that bottoms out on the base rear wall, capping travel.
    # It CONSTRAINS the hinge's use-phase rotation; it realizes nothing.
    features = []
    if variant == "stop":
        features = [
            FeatureInstance(id="F1", card_ref="stop_flange", host_pieces=["P2"],
                            params={"stop_flange_r": 8.0, "stop_angle": 108.85}),
        ]

    # --- Bindings: port ↦ anchor (+ mate). These mirror the M0 geometry. ------------------
    bindings = [
        Binding(element_id="E1", port="axis", piece_id="P1", anchor="rear_top_edge",
                mate="coincident_axis", offset_params={"edge_margin_mm": 34.0}),
        Binding(element_id="E1", port="mount_A", piece_id="P1", anchor="rear_wall_outer",
                mate="flush_face"),
        Binding(element_id="E1", port="mount_B", piece_id="P2", anchor="rear_edge_underside",
                mate="flush_face"),
    ]
    if variant == "stop":
        # the flange contact face lands on the base rear wall
        bindings.append(
            Binding(element_id="F1", port="contact", piece_id="P2", anchor="stop_flange_face",
                    mate="flush_face"))

    # --- P-HINGE protocol: criteria (GATES) vs observables (recorded), the M0 split ---------
    # These are the exact V-B criteria/observables the physics session used (M0 §4.4). All
    # measurement names are drawn from the controlled registry (ontology/measurements.py, V-13).
    criteria = [
        Criterion(name="opens", observable="theta_max_deg", op=">=", threshold=90.0, unit="deg"),
        Criterion(name="pin_radial_retention", observable="pin_radial_max_mm", op="<=",
                  threshold=0.40, unit="mm"),
        Criterion(name="pin_axial_retention", observable="pin_axial_max_mm", op="<=",
                  threshold=3.0, unit="mm"),
        Criterion(name="no_travel_interference", observable="pen_travel_mm", op="<=",
                  threshold=0.20, unit="mm"),
        Criterion(name="pin_bore_interface", observable="pen_interface_mm", op="<=",
                  threshold=0.30, unit="mm"),
        Criterion(name="settles_closed", observable="theta_final_deg", op="<=",
                  threshold=5.0, unit="deg"),
        Criterion(name="no_bounce_open", observable="bounce_open_deg", op="<=",
                  threshold=5.0, unit="deg"),
    ]
    observables = [
        # D22 amended: seat-impact MAGNITUDE is an observable, flagged > clearance scale, never
        # a gate — in a soft-constraint engine it measures preset compliance (D17).
        Observable(name="closing_seat_impact", measured="seat_impact_mm", unit="mm",
                   flag_op=">", flag_threshold=0.30,
                   note="dynamic gravity slam; depth reflects the frozen quasi-static preset "
                        "(D17), not the geometry (D22 amended)"),
        Observable(name="box_displacement", measured="box_slid_mm", unit="mm"),
    ]
    # D-ONT-4: when the plan includes the stop_flange, the overtravel measurement is PROMOTED
    # from an observable to a CRITERION — the stop's verification contribution. Without the
    # stop it stays an observable (the no-stop lid is free to fold flat, the documented defect).
    if variant == "stop":
        criteria.append(
            Criterion(name="angle_limited", observable="overtravel_deg", op="<=",
                      threshold=150.0, unit="deg"))  # stop caps travel ~115 deg; fold-flat ~220
    else:
        observables.append(
            Observable(name="overtravel", measured="overtravel_deg", unit="deg",
                       flag_op=">", flag_threshold=150.0,
                       note="no angular limit -> lid free to fold flat (the no-stop defect)"))

    p_hinge = VerificationProtocol(
        id="P-HINGE", verifies="B1", mode="V-B", seeds=5, seed_pass=4,
        actuation={"kind": "follower_force_ramp", "F_open_N": 0.11, "F_close_N": 0.15,
                   "point": "free_edge_mid", "release_at_theta_deg": 95.0},
        criteria=criteria, observables=observables,
    )

    # --- Behaviors ------------------------------------------------------------------------
    behaviors = [
        # B1: the hinge REALIZES the opening rotation — a range-of-motion FLOOR (opens >= 90).
        Behavior(id="B1", phase="use",
                 motion=MotionSpec(kind="rotation", axis_hint="horizontal_rear",
                                   range_value=90.0, range_unit="deg", bound="min"),
                 realized_by="E1", verified_by="P-HINGE"),
        # B2: the pin-insertion path is a constraint the hinge IMPOSES (§3.3), not a DoF it
        # realizes — so imposed_by only (no realized_by). This is the fix for the illegible
        # double-edge at G-H: an imposed constraint gets exactly one (dashed) edge.
        Behavior(id="B2", phase="assembly",
                 motion=MotionSpec(kind="translation", axis_hint="along_hinge_axis"),
                 imposed_by="E1", imposed_by_card="pin_hinge"),
    ]
    if variant == "stop":
        # B3 — the rotation LIMIT imposed by the stop_flange (D-ONT-4/-9, V-08). bound="max"
        # marks it as a ceiling (<= 108.85 deg), NOT a range-of-motion like B1 — the semantic
        # the IR was previously missing. imposed_by F1, realized_by nothing (passive feature).
        behaviors.append(
            Behavior(id="B3", phase="use",
                     motion=MotionSpec(kind="rotation", axis_hint="horizontal_rear",
                                       range_value=108.85, range_unit="deg", bound="max"),
                     imposed_by="F1", imposed_by_card="stop_flange", verified_by="P-HINGE"))

    # --- Parameters (a few, resolved, to exercise V-04) -----------------------------------
    parameters = [
        Parameter(name="pin_d", value=4.0, unit="mm", lo=2.0, hi=6.0, resolved_by="user"),
        Parameter(name="clearance", value=0.30, unit="mm", lo=0.2, hi=0.4, resolved_by="rule"),
    ]

    return DesignPlan(
        task_id=f"m0_hinge_box_{variant}",
        command="Design a small box with a lid that opens and closes. Plastic, for 3D printing.",
        variant=variant,
        functions=functions,
        behaviors=behaviors,
        pieces=pieces,
        templates=[box_shell, lid_panel],
        elements=elements,
        features=features,  # D-ONT-4: the stop_flange PassiveFeature (stop variant only)
        bindings=bindings,
        parameters=parameters,
        protocols=[p_hinge],
        material="PETG",
    )


# ======================================================================================
# Golden 2 — T-S1 "snap-on lid box". AUTHORITATIVE transcription of SNAPFIT_STARTER §1.3
# (the doc wins; my earlier inference — a hinged box with a secondary latch — was wrong and is
# replaced). This is snap-fit ONLY: a lid pushed straight on and pulled off by hand, no hinge.
# D-ONT additions the doc's §1.3 note calls for: is_base on P1, the HostTemplate anchor
# interface (D-ONT-1/3), and PR-* protocols following the criteria/observables split (D-ONT-2).
# ======================================================================================
def snap_starter(box_l=80.0, box_w=60.0, box_h=40.0, n_hooks=2,
                 window_mate=(0.0, 80.0), window_sep=(15.0, 60.0)) -> DesignPlan:
    functions = [
        Function(verb="secure", object="lid", qualifier="hold closed"),
        Function(verb="allow_access", object="contents", qualifier="repeated hand open/close"),
    ]

    # Templates + anchors (D-ONT-1). Anchor names are exactly those the §1.3 bindings reference.
    box_shell = HostTemplate(
        template_ref="box_shell",
        params={"box_l": box_l, "box_w": box_w, "box_h": box_h, "wall": 2.0},
        anchors=[Anchor(name="side_wall_left", kind="face"),
                 Anchor(name="side_wall_right", kind="face")],
    )
    lid_panel = HostTemplate(
        template_ref="lid_panel",
        params={"lid_t": 3.0, "box_l": box_l, "box_w": box_w},
        anchors=[Anchor(name="rim_underside_left", kind="face"),
                 Anchor(name="rim_underside_right", kind="face")],
    )

    pieces = [
        Piece(id="P1", role="base", template_ref="box_shell", is_base=True,
              params=dict(box_shell.params)),
        Piece(id="P2", role="lid", template_ref="lid_panel", params=dict(lid_panel.params)),
    ]

    # One element: the snap hook (realizes B1 mate + B2 retention; imposes B3 sweep clearance).
    elements = [
        ElementInstance(id="E1", card_ref="snap_hook_cantilever", host_pieces=["P2", "P1"],
                        params={"n_hooks": int(n_hooks), "design_type": 2,
                                "alpha_in_deg": 30, "alpha_out_deg": 45}),
    ]

    # Four bindings (2 beam_root on the lid rim, 2 catch_window on the box side walls) — §1.3.
    bindings = [
        Binding(element_id="E1", port="beam_root", piece_id="P2", anchor="rim_underside_left",
                mate="on_face_uv", offset_params={"u": 0.5, "v": 1.0}),
        Binding(element_id="E1", port="beam_root", piece_id="P2", anchor="rim_underside_right",
                mate="on_face_uv", offset_params={"u": 0.5, "v": 1.0}),
        Binding(element_id="E1", port="catch_window", piece_id="P1", anchor="side_wall_left",
                mate="offset_face", offset_params={"undercut_dir": "insertion_axis_neg"}),
        Binding(element_id="E1", port="catch_window", piece_id="P1", anchor="side_wall_right",
                mate="offset_face", offset_params={"undercut_dir": "insertion_axis_neg"}),
    ]

    # Behaviors — §1.3. B1 mate (assembly), B2 retention (static), both snap_event; B3 the imposed
    # use-phase sweep-clearance constraint (fixed), attributed to the hook (V-08).
    behaviors = [
        Behavior(id="B1", phase="assembly",
                 motion=MotionSpec(kind="snap_event", event_force_window_N=tuple(window_mate)),
                 realized_by="E1", verified_by="PR-T1-MATE"),
        Behavior(id="B2", phase="static",
                 motion=MotionSpec(kind="snap_event", event_force_window_N=tuple(window_sep)),
                 realized_by="E1", verified_by="PR-T1-SEP"),
        Behavior(id="B3", phase="use", motion=MotionSpec(kind="fixed"),
                 imposed_by="E1", imposed_by_card="snap_hook_cantilever",
                 verified_by="PR-T0-SWEEP"),
        # B4 — the assembly insertion-path constraint the hook imposes (V-08): the hooks must
        # have room to deflect and travel to their catch windows. Assembly-phase, so no verified_by
        # is required (V-01 gates use-phase only); Tier0 checks it geometrically.
        Behavior(id="B4", phase="assembly",
                 motion=MotionSpec(kind="translation", axis_hint="insertion_axis"),
                 imposed_by="E1", imposed_by_card="snap_hook_cantilever"),
    ]

    # Protocols (criteria/observables split, D-ONT-2). Snap verification is Tier1 FORMULA
    # (§3.4, D3) + a Tier0 sweep — not a MuJoCo trajectory (mode=None for the formula ones).
    pr_mate = VerificationProtocol(
        id="PR-T1-MATE", verifies="B1", mode=None,
        actuation={"kind": "formula_recheck", "source": "Bayer p.16 mating force"},
        criteria=[Criterion(name="hand_closeable", observable="mating_force_total_N", op="<=",
                            threshold=80.0, unit="N")],  # A1: assumption, not from Bayer
        observables=[Observable(name="per_hook_mate", measured="W_in_N", unit="N")],
    )
    pr_sep = VerificationProtocol(
        id="PR-T1-SEP", verifies="B2", mode=None,
        actuation={"kind": "formula_recheck", "source": "Bayer p.16 separation force"},
        criteria=[
            Criterion(name="retention_floor", observable="retention_force_N", op=">=",
                      threshold=15.0, unit="N"),
            Criterion(name="hand_openable", observable="retention_force_N", op="<=",
                      threshold=60.0, unit="N"),
        ],
        observables=[Observable(name="per_hook_sep", measured="W_out_N", unit="N"),
                     Observable(name="peak_strain", measured="eps_pct", unit="%",
                                flag_op=">", flag_threshold=4.0,
                                note="Tier1 re-measured strain; gate lives with resolve_params")],
    )
    pr_sweep = VerificationProtocol(
        id="PR-T0-SWEEP", verifies="B3", mode=None,
        actuation={"kind": "tier0_sweep", "note": "insertion-path sweep, intentional-vs-defect"},
        # D22 contact-intent stratification (SNAPFIT §5.2): only NON-intended interference fails.
        criteria=[Criterion(name="no_defect_interference", observable="pen_travel_mm", op="<=",
                            threshold=0.20, unit="mm")],
    )

    # Params: a couple resolved, to exercise V-04 (formulas that fill the rest are next session).
    parameters = [
        Parameter(name="n_hooks", value=2.0, unit="count", lo=2.0, hi=4.0, resolved_by="user"),
        Parameter(name="alpha_in_deg", value=30.0, unit="deg", lo=25.0, hi=35.0, resolved_by="user"),
    ]

    return DesignPlan(
        task_id="T-S1",
        command=("Design a snap-lid box I can push shut and pull open by hand. "
                 "Plastic, for 3D printing."),
        functions=functions,
        behaviors=behaviors,
        pieces=pieces,
        templates=[box_shell, lid_panel],
        elements=elements,
        bindings=bindings,
        parameters=parameters,
        protocols=[pr_mate, pr_sep, pr_sweep],
        material="PETG",
    )


# ======================================================================================
# Golden 3 — the flat_panel_mount board clip (D-GEN-1: same snap_hook card, different host).
# ======================================================================================
def snap_panel() -> DesignPlan:
    # Intent: SEPARABLE (service access). α_out = 45° ≪ self-lock(μ=0.3)=73.3°, so the joint
    # releases; the resolved W_sep = 31.84 N sits inside B2's hand-open window (15–60 N). NOT the
    # α′=90° permanent case (that is T-S1d). The separability is declared functionally by B2's
    # snap_event window + PR-T1-SEP's retention_floor ≥ 15 N criterion.
    #
    # EXPECTED_FAIL (close-out harness): this is an EDGE-OVERHANG board clip, but the card only
    # implements the WINDOW catch — which cuts a hole in the receiver. Here the receiver B1 is
    # RETAINED (a foreign, immutable board/PCB), so cutting it is illegal and ⑥ correctly refuses:
    # GEOM_INFEASIBLE. The honest fix is an edge-overhang catch that grabs the board's edge without
    # modifying it — kept as a failing regression target for M-G-1 (D-GEN-4: edge_overhang nose
    # topology + matching overhang three-way check). Never route it to N/A; never delete it.
    functions = [
        Function(verb="secure", object="board", qualifier="retain a flat part"),
        Function(verb="allow_access", object="board", qualifier="removable by hand"),
    ]
    mount = HostTemplate(template_ref="flat_panel_mount", params={},
                         anchors=[Anchor(name="rail_inner_left", kind="face"),
                                  Anchor(name="rail_inner_right", kind="face")])
    board = HostTemplate(template_ref="retained_board", params={},
                         anchors=[Anchor(name="board_edge_left", kind="face"),
                                  Anchor(name="board_edge_right", kind="face")])
    pieces = [Piece(id="M1", role="base", template_ref="flat_panel_mount", is_base=True),
              Piece(id="B1", role="retained", template_ref="retained_board")]
    elements = [ElementInstance(id="E1", card_ref="snap_hook_cantilever", host_pieces=["M1", "B1"],
                                params={"n_hooks": 2, "design_type": 2, "alpha_in_deg": 30,
                                        "alpha_out_deg": 45})]
    bindings = [
        Binding(element_id="E1", port="beam_root", piece_id="M1", anchor="rail_inner_left",
                mate="on_face_uv", offset_params={"u": 0.5, "v": 0.5}),
        Binding(element_id="E1", port="beam_root", piece_id="M1", anchor="rail_inner_right",
                mate="on_face_uv", offset_params={"u": 0.5, "v": 0.5}),
        Binding(element_id="E1", port="catch_window", piece_id="B1", anchor="board_edge_left",
                mate="offset_face", offset_params={"undercut_dir": "inward"}),
        Binding(element_id="E1", port="catch_window", piece_id="B1", anchor="board_edge_right",
                mate="offset_face", offset_params={"undercut_dir": "inward"}),
    ]
    pr_mate = VerificationProtocol(id="PR-T1-MATE", verifies="B1", mode=None,
        actuation={"kind": "formula_recheck"},
        criteria=[Criterion(name="hand_closeable", observable="mating_force_total_N", op="<=",
                            threshold=80.0, unit="N")])
    pr_sep = VerificationProtocol(id="PR-T1-SEP", verifies="B2", mode=None,
        actuation={"kind": "formula_recheck"},
        criteria=[Criterion(name="retention_floor", observable="retention_force_N", op=">=",
                            threshold=15.0, unit="N")])
    pr_sweep = VerificationProtocol(id="PR-T0-SWEEP", verifies="B3", mode=None,
        actuation={"kind": "tier0_sweep"},
        criteria=[Criterion(name="no_defect_interference", observable="pen_travel_mm", op="<=",
                            threshold=0.20, unit="mm")])
    behaviors = [
        Behavior(id="B1", phase="assembly",
                 motion=MotionSpec(kind="snap_event", event_force_window_N=(0.0, 80.0)),
                 realized_by="E1", verified_by="PR-T1-MATE"),
        Behavior(id="B2", phase="static",
                 motion=MotionSpec(kind="snap_event", event_force_window_N=(15.0, 60.0)),
                 realized_by="E1", verified_by="PR-T1-SEP"),
        Behavior(id="B3", phase="use", motion=MotionSpec(kind="fixed"),
                 imposed_by="E1", imposed_by_card="snap_hook_cantilever", verified_by="PR-T0-SWEEP"),
        Behavior(id="B4", phase="assembly",
                 motion=MotionSpec(kind="translation", axis_hint="insertion_axis"),
                 imposed_by="E1", imposed_by_card="snap_hook_cantilever"),
    ]
    return DesignPlan(
        task_id="T-S1-panel",
        command="Design a clip that retains a flat board and can be removed by hand. Plastic, 3D printing.",
        functions=functions, behaviors=behaviors, pieces=pieces, templates=[mount, board],
        elements=elements, bindings=bindings,
        parameters=[Parameter(name="n_hooks", value=2.0, unit="count", lo=2.0, hi=4.0,
                              resolved_by="user")],
        protocols=[pr_mate, pr_sep, pr_sweep], material="PETG")


def anchor_easy(variant: str = "stop", box_l=80.0, box_w=60.0, box_h=40.0,
                open_min: float = 90.0) -> DesignPlan:
    """The EASY ANCHOR (MECHSYNTH §8.1) — the pipeline's first MULTI-ELEMENT assembly: a box + lid
    with a pin_hinge (E1, rear) AND a snap_hook latch (E2, front). Carries the D-ONT-11 hardware pin
    (P3) and both D-ONT-12 AssemblyRules (snap_hook's latch-vs-lid-sweep EXCLUSION + the
    hook/edge_margin RESOURCE budget on the shared rim). This is what a post-④ plan looks like.

    variant="stop" (DEFAULT — the benchmark golden, tasks/anchor_easy.json): carries F1 (a
    stop_flange PassiveFeature on the lid) + B3 (the use-phase rotation LIMIT it imposes,
    bound="max", ceiling DERIVED from this box's own axis by the card's formula, registered per
    V-08) + its binding. Per D-ONT-4 the overtravel observable is PROMOTED to a criterion.

    **Why the stop is in the benchmark (D-M8-5):** honest V-B proved the §8.1 spec — "opens ≥90°
    AND returns closed" — is PHYSICALLY UNSATISFIABLE for this over-centre lid without a stop. Past
    90° gravity pulls the lid further open, so it folds flat; there is no actuation that satisfies
    both clauses on a stop-less design. The stop is therefore not a convenience: it is a design
    REQUIREMENT the system DISCOVERED from its own physics, and the benchmark must carry it.

    variant="nostop" (tasks/anchor_easy_nostop.json — the D20 demonstration golden): the same plan
    with F1/B3 removed and NOTHING else changed. Its V-B verdict is an honest, EXPECTED FAIL —
    "fold-over, no angular limit" — kept as a live regression target (the snap_panel EXPECTED_FAIL
    pattern). It is what proves V-A cannot tell the two designs apart while V-B can (D20)."""
    assert variant in ("stop", "nostop"), variant
    box_shell = HostTemplate(template_ref="box_shell",
        params={"box_l": box_l, "box_w": box_w, "box_h": box_h, "wall": 2.0},
        anchors=[Anchor(name="rear_top_edge", kind="edge"), Anchor(name="rear_wall_outer", kind="face"),
                 Anchor(name="front_wall_inner", kind="face"), Anchor(name="rim_top", kind="face")])
    lid_panel = HostTemplate(template_ref="lid_panel",
        params={"lid_t": 3.0, "box_l": box_l, "box_w": box_w,
                **({"stop_flange_r": 8.0} if variant == "stop" else {})},
        anchors=[Anchor(name="rear_edge_underside", kind="face"),
                 Anchor(name="front_edge_underside", kind="face"),
                 Anchor(name="free_edge_mid", kind="point")]
        + ([Anchor(name="stop_flange_face", kind="face")] if variant == "stop" else []))

    pieces = [
        Piece(id="P1", role="base", template_ref="box_shell", is_base=True, params=dict(box_shell.params)),
        Piece(id="P2", role="lid", template_ref="lid_panel", params={**lid_panel.params, "rim_length": 80.0}),
        Piece(id="P3", role="pin", provenance="hardware", source_element="E1",
              params={"pin_d": 4.0, "pin_len": 30.6}),   # D-ONT-11 hardware pin
    ]
    elements = [
        ElementInstance(id="E1", card_ref="pin_hinge", host_pieces=["P1", "P2"],
                        params={"pin_d": 4.0, "knuckle_w": 8.0, "knuckle_n": 3, "clearance": 0.30,
                                "edge_margin": 27.7}),   # edge_margin ⑤-resolved (named for AR2)
        ElementInstance(id="E2", card_ref="snap_hook_cantilever", host_pieces=["P2", "P1"],
                        params={"L_mm": 12.0, "b_mm": 8.0, "y_mm": 1.5, "n_hooks": 1,
                                "design_type": 2, "alpha_in_deg": 30.0, "alpha_out_deg": 45.0}),
    ]
    bindings = [
        Binding(element_id="E1", port="axis", piece_id="P1", anchor="rear_top_edge",
                mate="coincident_axis", offset_params={"face_len": 80.0}),
        Binding(element_id="E1", port="mount_A", piece_id="P1", anchor="rear_wall_outer", mate="flush_face"),
        Binding(element_id="E1", port="mount_B", piece_id="P2", anchor="rear_edge_underside", mate="flush_face"),
        # the latch: beam on the lid FRONT edge, catch window in the box FRONT wall
        Binding(element_id="E2", port="beam_root", piece_id="P2", anchor="front_edge_underside",
                mate="on_face_uv", offset_params={"u": 0.5, "v": 0.5}),
        Binding(element_id="E2", port="catch_window", piece_id="P1", anchor="front_wall_inner",
                mate="offset_face", offset_params={"undercut_dir": "inward"}),
    ]
    # D-ONT-12 AssemblyRules — first-class, provenance-tagged, referents named in the IR (D13)
    assembly_rules = [
        AssemblyRule(id="AR1", kind="exclusion", provenance="card:snap_hook_cantilever",
                     subjects=["E2", "E1"], predicate={"excluded": "E2", "sweep_of": "E1"},
                     citation="MECHSYNTH §5.2 / M0 B4 (latch ∉ lid sweep)"),
        AssemblyRule(id="AR2", kind="resource", provenance="task",
                     subjects=["E2.L_mm", "E1.edge_margin", "P2.rim_length"],
                     predicate={"contributors": ["E2.L_mm", "E1.edge_margin"],
                                "budget": "P2.rim_length", "op": "<="},
                     citation="shared front-rim budget: hook length + hinge edge_margin ≤ rim"),
    ]
    # protocols: P-HINGE (V-A + V-B) for the hinge; PR-LATCH (formula) for the snap
    crit = [Criterion(name="opens", observable="theta_max_deg", op=">=", threshold=open_min, unit="deg"),
            Criterion(name="pin_radial_retention", observable="pin_radial_max_mm", op="<=", threshold=0.40, unit="mm"),
            Criterion(name="settles_closed", observable="theta_final_deg", op="<=", threshold=5.0, unit="deg"),
            Criterion(name="no_travel_interference", observable="pen_travel_mm", op="<=", threshold=0.20, unit="mm")]
    p_hinge_va = VerificationProtocol(id="P-HINGE-VA", verifies="B1", mode="V-A", seeds=5, seed_pass=4,
        actuation={"kind": "follower_force_ramp", "F_open_N": 0.15, "point": "free_edge_mid"}, criteria=crit)
    p_hinge_vb = VerificationProtocol(id="P-HINGE-VB", verifies="B1", mode="V-B", seeds=5, seed_pass=4,
        actuation={"kind": "follower_force_ramp", "F_open_N": 0.11, "point": "free_edge_mid",
                   "release_at_theta_deg": 95.0}, criteria=crit)
    pr_latch = VerificationProtocol(id="PR-LATCH", verifies="B4", mode=None, actuation={"kind": "formula_recheck"},
        criteria=[Criterion(name="hand_closeable", observable="mating_force_total_N", op="<=", threshold=80.0, unit="N"),
                  Criterion(name="retention_floor", observable="retention_force_N", op=">=", threshold=15.0, unit="N")])
    pr_sweep = VerificationProtocol(id="PR-SWEEP", verifies="B5", mode=None, actuation={"kind": "tier0_sweep"},
        criteria=[Criterion(name="no_defect_interference", observable="pen_travel_mm", op="<=", threshold=0.20, unit="mm")])
    behaviors = [
        Behavior(id="B1", phase="use", motion=MotionSpec(kind="rotation", axis_hint="horizontal_rear",
                 range_value=90.0, range_unit="deg", bound="min"), realized_by="E1", verified_by="P-HINGE-VB"),
        Behavior(id="B2", phase="assembly", motion=MotionSpec(kind="translation", axis_hint="along_hinge_axis"),
                 imposed_by="E1", imposed_by_card="pin_hinge"),   # hinge pin-insertion path
        Behavior(id="B4", phase="static", motion=MotionSpec(kind="snap_event", event_force_window_N=(15.0, 60.0)),
                 realized_by="E2", verified_by="PR-LATCH"),
        Behavior(id="B5", phase="use", motion=MotionSpec(kind="fixed"),
                 imposed_by="E2", imposed_by_card="snap_hook_cantilever", verified_by="PR-SWEEP"),  # sweep clearance (AR1's face)
        Behavior(id="B6", phase="assembly", motion=MotionSpec(kind="translation"),
                 imposed_by="E2", imposed_by_card="snap_hook_cantilever"),   # hook insertion path
    ]
    features = []
    if variant == "stop":
        # F1 — the stop_flange PassiveFeature (D-ONT-4). It CONSTRAINS; it realizes nothing.
        # stop_angle is SOLVED from THIS box's geometry by the card's own formula (the hinge axis
        # sits at the box's rear top edge, z=box_h) — not typed, and not copied from M0, whose axis
        # is at the lid mid-plane and whose answer (108.85°) is therefore a different box's number.
        from knowledge.cards.stop_flange_geometry import stop_angle_deg as _stop_ang
        _bw, _bh = box_shell.params["box_w"], box_shell.params["box_h"]
        _stop = _stop_ang(axis_y=-_bw / 2 - 4.0, axis_z=_bh, box_w=_bw, box_h=_bh,
                          stop_flange_r=8.0)
        features.append(FeatureInstance(id="F1", card_ref="stop_flange", host_pieces=["P2"],
                                        params={"stop_flange_r": 8.0, "flange_w": 8.0,
                                                "stop_angle": _stop}))
        bindings.append(Binding(element_id="F1", port="contact", piece_id="P2",
                                anchor="stop_flange_face", mate="offset_face",
                                offset_params={"rearward_of_axis": True}))
        # B3 — the rotation LIMIT F1 imposes (bound="max": a CEILING, not a range-of-motion like
        # B1's floor). V-08 requires this: a constraint a feature imposes must be registered in the
        # IR, so a stop can never exist only in geometry — let alone only in a collision model.
        # range_value is F1's SOLVED stop_angle, so the declared ceiling and the compiled flange are
        # the same number by construction (the carve re-solves and refuses on disagreement).
        behaviors.append(
            Behavior(id="B3", phase="use",
                     motion=MotionSpec(kind="rotation", axis_hint="horizontal_rear",
                                       range_value=_stop, range_unit="deg", bound="max"),
                     imposed_by="F1", imposed_by_card="stop_flange", verified_by="P-HINGE-VB"))
    parameters = [Parameter(name="pin_d", value=4.0, unit="mm", lo=2.0, hi=6.0, resolved_by="user"),
                  Parameter(name="clearance", value=0.30, unit="mm", lo=0.2, hi=0.4, resolved_by="rule")]
    return DesignPlan(task_id="anchor_easy",
        command="A small hinged box whose lid latches shut at the front. Plastic, 3D printing.",
        functions=[Function(verb="allow_access", object="contents", qualifier="repeated open/close"),
                   Function(verb="secure", object="lid", qualifier="latch shut, hand-releasable")],
        behaviors=behaviors, pieces=pieces, templates=[box_shell, lid_panel], elements=elements,
        features=features, variant=variant,
        bindings=bindings, assembly_rules=assembly_rules, parameters=parameters,
        protocols=[p_hinge_va, p_hinge_vb, pr_latch, pr_sweep], material="PETG")




def slide_fixture() -> DesignPlan:
    """Minimal two-piece slide_rail fixture (D-track / §3.5): a base with a T-rail + a carriage that
    captures it. Reproduces the §3.5 constraint chain numerically (engagement ≥ 0.35·stroke, the
    drawer-width equality) on the smallest geometry that exercises P-SLIDE. One element (E1
    slide_rail), two functional pieces (P1 base[base], P2 carriage[mover])."""
    slide_base = HostTemplate(template_ref="slide_base",
        params={"base_l": 120.0, "base_w": 40.0, "base_t": 3.0},
        anchors=[Anchor(name="rail_face", kind="face"), Anchor(name="travel_edge", kind="axis")])
    slide_carriage = HostTemplate(template_ref="slide_carriage",
        params={"car_l": 24.0, "car_w": 30.0, "car_t": 3.0, "car_z": 3.0},
        anchors=[Anchor(name="groove_face", kind="face")])
    pieces = [
        Piece(id="P1", role="base", template_ref="slide_base", is_base=True,
              params=dict(slide_base.params)),
        Piece(id="P2", role="carriage", template_ref="slide_carriage",
              params=dict(slide_carriage.params)),
    ]
    elements = [ElementInstance(id="E1", card_ref="slide_rail", host_pieces=["P1", "P2"],
                                params={"rail_w": 8.0, "rail_h": 8.0, "clearance": 0.35,
                                        "stroke": 60.0})]
    bindings = [
        Binding(element_id="E1", port="rail_mount", piece_id="P1", anchor="rail_face",
                mate="flush_face"),
        Binding(element_id="E1", port="carriage_mount", piece_id="P2", anchor="groove_face",
                mate="flush_face"),
        Binding(element_id="E1", port="travel_axis", piece_id="P1", anchor="travel_edge",
                mate="coincident_axis"),
    ]
    # B1: the slide REALIZES the extraction travel (use-phase translation, stroke floor)
    behaviors = [
        Behavior(id="B1", phase="use", motion=MotionSpec(kind="translation", axis_hint="horizontal",
                 range_value=60.0, range_unit="mm", bound="min"), realized_by="E1",
                 verified_by="P-SLIDE-VB-E1"),
    ]
    parameters = [Parameter(name="stroke", value=60.0, unit="mm", lo=10.0, hi=400.0,
                            resolved_by="user"),
                  Parameter(name="clearance", value=0.35, unit="mm", lo=0.25, hi=0.45,
                            resolved_by="rule")]
    # card-sourced (D5): the slide's imposed behaviours (B2 assembly-insertion, B3 travel-keepout)
    # and its P-SLIDE protocols, exactly as ④ would attach them — kept here so the golden is
    # self-consistent (V-08/V-01 clean) without hand-authoring card knowledge.
    from knowledge.cards.base import CARD_REGISTRY as _C
    card = _C["slide_rail"]
    n = len(behaviors)
    for tmpl in card.imposes:
        n += 1
        behaviors.append(Behavior(id=f"B{n}", phase=getattr(tmpl.phase, "value", tmpl.phase),
                                  motion=MotionSpec(kind=getattr(tmpl.motion.kind, "value",
                                                                 tmpl.motion.kind)),
                                  imposed_by="E1", imposed_by_card="slide_rail"))
    plan = DesignPlan(task_id="slide_fixture",
        command="A drawer that slides out on a rail and stays on it. Plastic, 3D printing.",
        functions=[Function(verb="guide", object="drawer", qualifier="slide out 60 mm and back"),
                   Function(verb="allow_access", object="contents", qualifier="pull-out drawer")],
        behaviors=behaviors, pieces=pieces, templates=[slide_base, slide_carriage],
        elements=elements, bindings=bindings, parameters=parameters)
    for pr in card.verification(plan, elements[0]):
        plan.protocols.append(pr)
        b = next((x for x in plan.behaviors if x.id == pr.verifies), None)
        if b is not None and not b.verified_by:
            b.verified_by = pr.id
    return plan


def rack_pinion_fixture() -> DesignPlan:
    """Minimal rack&pinion fixture (§3.6 amended / D-track 2): a bearing-post carrier holding an
    INVOLUTE pinion (M1's profile — the trapezoid is dead, D-M1-1) that drives a straight rack. One
    element (E1 rack_pinion), two functional pieces (P1 pinion_carrier[base], P2 rack_carrier[mover]).

    Realizes ONE use-phase rot_to_trans behaviour (B1): the pinion turns, the rack translates
    `stroke` mm. The card's §3.6 formulas set the geometry; P-GEAR verifies the transmission V-A ONLY
    (the standing R2b-open flag — bidirectional contact meshing is DEFERRED, D-M1-5/-7)."""
    m, z, stroke = 5.0, 12, 120.0
    axis_h = 45.0
    pinion_carrier = HostTemplate(template_ref="pinion_carrier",
        params={"base_l": 70.0, "base_w": 44.0, "base_t": 4.0, "axis_h": axis_h, "post_w": 14.0},
        anchors=[Anchor(name="pinion_axis", kind="axis"), Anchor(name="mesh_line", kind="edge")])
    rack_carrier = HostTemplate(template_ref="rack_carrier",
        params={"module": m, "z_pinion": z, "axis_h": axis_h, "rail_l": 200.0,
                "carrier_t": 5.0, "face_w": 8.0},
        anchors=[Anchor(name="rack_mount", kind="face")])
    pieces = [
        Piece(id="P1", role="base", template_ref="pinion_carrier", is_base=True,
              params=dict(pinion_carrier.params)),
        Piece(id="P2", role="rack", template_ref="rack_carrier", params=dict(rack_carrier.params)),
    ]
    elements = [ElementInstance(id="E1", card_ref="rack_pinion", host_pieces=["P1", "P2"],
                                params={"module": m, "z_pinion": z, "pressure_angle_deg": 20.0,
                                        "face_w": 8.0, "backlash": 0.20, "stroke": stroke})]
    bindings = [
        Binding(element_id="E1", port="pinion_axis", piece_id="P1", anchor="pinion_axis",
                mate="coincident_axis"),
        Binding(element_id="E1", port="rack_mount", piece_id="P2", anchor="rack_mount",
                mate="flush_face"),
        Binding(element_id="E1", port="mesh_line", piece_id="P1", anchor="mesh_line",
                mate="coincident_axis"),
    ]
    # travel_per_rev = π·m·z (§3.6 pitch circumference) — the transmission ratio the rot_to_trans
    # behaviour carries (V-06). π·5·12 = 188.496 mm/rev; the pinion pitch radius rp = m·z/2 = 30 mm.
    travel_per_rev = math.pi * m * z
    behaviors = [
        Behavior(id="B1", phase="use",
                 motion=MotionSpec(kind="rot_to_trans", axis_hint="horizontal",
                                   range_value=stroke, range_unit="mm", bound="min",
                                   transmission={"mm_per_rev": round(travel_per_rev, 3),
                                                 "pitch_radius_mm": m * z / 2.0,
                                                 "kind": "rack_pinion"}),
                 realized_by="E1"),
    ]
    parameters = [Parameter(name="module", value=m, unit="mm", lo=5.0, hi=6.0, resolved_by="rule"),
                  Parameter(name="stroke", value=stroke, unit="mm", lo=20.0, hi=400.0,
                            resolved_by="user")]
    # card-sourced (D5): the imposed assembly behaviour, attached BEFORE construction (pydantic copies
    # the list at build time) — so the mesh-insertion constraint the card imposes is registered (V-08).
    from knowledge.cards.base import CARD_REGISTRY as _C
    card = _C["rack_pinion"]
    n = len(behaviors)
    for tmpl in card.imposes:
        n += 1
        behaviors.append(Behavior(id=f"B{n}", phase=getattr(tmpl.phase, "value", tmpl.phase),
                                  motion=MotionSpec(kind=getattr(tmpl.motion.kind, "value",
                                                                 tmpl.motion.kind)),
                                  imposed_by="E1", imposed_by_card="rack_pinion"))
    plan = DesignPlan(task_id="rack_pinion_fixture",
        command="A knob that drives a rack straight out and back. Plastic, 3D printing.",
        functions=[Function(verb="convert", object="motion", qualifier="rotation to translation"),
                   Function(verb="drive", object="rack", qualifier="linear travel from a knob")],
        behaviors=behaviors, pieces=pieces, templates=[pinion_carrier, rack_carrier],
        elements=elements, bindings=bindings, parameters=parameters)
    # the P-GEAR V-A protocol, exactly as ④ would attach it. The V-B reversal gap rides along NAMED
    # in the protocol's actuation (D-M1-7) so no design silently claims contact-level meshing.
    for pr in card.verification(plan, elements[0]):
        plan.protocols.append(pr)
        b = next((x for x in plan.behaviors if x.id == pr.verifies), None)
        if b is not None and not b.verified_by:
            b.verified_by = pr.id
    return plan


def anchor_hard(variant: str = "drawer", stroke: float = 120.0,
                load_kg: float = 0.5) -> DesignPlan:
    """THE HARD ANCHOR (MECHSYNTH §8.2, RETARGETED at D-M13-2) — one mechanism, two products.

    variant="lift" (the PRIMARY benchmark): a **crank-operated lift platform**. Same two `slide_rail`
    + `rack_pinion` mechanism, rotated so **travel is VERTICAL (+Z)** and **gravity acts along the
    travel axis**. Here the gear is FUNCTIONALLY NECESSARY (a drawer's rack-pinion is over-engineered;
    a good model would omit it — but a vertical lift needs it to hold and raise a load against
    gravity). Adds a 0.5 kg load and a **static/hold** behaviour (must not back-drive when the crank
    is released). The geometry rotation reuses the m10/m11 carves + hints + verification VERBATIM
    (the physics layer applies the −90° tilt about Y); only what does NOT carry over is named.

    variant="drawer" (the labeled ALTERNATE, tasks/anchor_hard.json): the original horizontal
    rack-pinion drawer cabinet — kept as a schema/geometry stress test.

    Both are the pipeline's first MULTI-CARD MECHANISM: two `slide_rail` instances (the two rails)
    + one `rack_pinion` (the crank→platform transmission), with the **alignment** AssemblyRule firing
    for the first time on real geometry (the two rails must be parallel + level).

    Frame (m13 correction — see m13_hard_anchor/REVIEW.md): +X = FRONT (pull-out). Two FLOOR rails
    run +X at ±rail_gap/2 (matched height = the alignment subjects); a vertical +Z knob's pinion
    meshes an +X rack under the drawer. This reuses the PROVEN m10/m11 carves verbatim.

    Composition note (D-D-1 replace-semantics): `slide_rail.carve` REPLACES its mover piece, so it
    cannot also BE the drawer. Each rail therefore owns its own carriage piece (P2/P3, slide_carriage);
    the drawer_tray (P4) is a plain tray welded to both carriages at physics time. `rack_pinion.carve`
    UNIONS the pinion into the knob (P5) and the rack into the rack_bar (P6).

    §8.2 constraint chain (⑤ resolves; each number derived, see the s5 table in the runner):
      drawer_w   = cab_inner_w − 2(rail_w+cl) = 132 − 2·8.35 = 115.30 mm
      L_rack    ≥ stroke + πmz/4            = 120 + 47.12    = 167.12 mm
      axis_off   = rack_pitchline + d/2       (= rp = 30 mm; the mesh offset)
      engagement ≥ 0.35·stroke              = 42 mm
    Stroke is SCALED from the §8.2 nominal 300 mm to **120 mm**: the m12 desktop cabinet is 200 mm
    deep, so a 300 mm extension would pull the drawer clean out; 120 mm keeps ≥45 mm engaged."""
    m, z = 5.0, 12
    rail_w, rail_h, cl, wall, cab_w = 8.0, 8.0, 0.35, 4.0, 140.0
    rp = m * z / 2.0
    tpr = math.pi * m * z
    cab_inner_w = cab_w - 2 * wall
    drawer_w = cab_inner_w - 2 * (rail_w + cl)                 # §8.2 → 115.30
    L_rack = stroke + tpr / 4.0                                # §8.2 → 167.12
    rail_gap, seat_x, seat_y, seat_z = 80.0, 76.0, 60.0, 30.0
    rack_cy = seat_y - rp                                      # rack pitch line, rp inboard of pinion

    cabinet = HostTemplate(template_ref="cabinet_shell",
        params={"cab_d": 200.0, "cab_w": cab_w, "cab_h": 90.0, "wall": wall,
                "rail_gap": rail_gap, "knob_y": seat_y},
        anchors=[Anchor(name=n, kind=k) for n, k in
                 [("rail_mount_L", "face"), ("rail_mount_R", "face"), ("rail_axis_L", "axis"),
                  ("rail_axis_R", "axis"), ("knob_mount", "axis"), ("pawl_mount", "face"),
                  ("floor", "face")]])
    carr = {pid: HostTemplate(template_ref="slide_carriage",
                              params={"car_l": 24.0, "car_w": 30.0, "car_t": 3.0, "car_z": 3.0},
                              anchors=[Anchor(name="groove_face", kind="face")]) for pid in ("P2", "P3")}
    tray = HostTemplate(template_ref="drawer_tray",
        params={"tray_d": 150.0, "tray_w": round(drawer_w, 2), "tray_h": 42.0, "floor_z": 16.0},
        anchors=[Anchor(name="rack_mount", kind="face"), Anchor(name="rack_line", kind="edge"),
                 Anchor(name="front_pull", kind="face"), Anchor(name="carriage_seat_L", kind="face"),
                 Anchor(name="carriage_seat_R", kind="face")])
    knob = HostTemplate(template_ref="knob_shaft",
        params={"seat_x": seat_x, "seat_y": seat_y, "seat_z": seat_z, "top_z": 90.0},
        anchors=[Anchor(name=n, kind="axis") for n in ("shaft_seat", "mount_axis", "grip_face")])

    pieces = [
        Piece(id="P1", role="base", template_ref="cabinet_shell", is_base=True, params=dict(cabinet.params)),
        Piece(id="P2", role="carriage_L", template_ref="slide_carriage", params=dict(carr["P2"].params)),
        Piece(id="P3", role="carriage_R", template_ref="slide_carriage", params=dict(carr["P3"].params)),
        Piece(id="P4", role="drawer", template_ref="drawer_tray", params=dict(tray.params)),
        Piece(id="P5", role="knob", template_ref="knob_shaft", params=dict(knob.params)),
    ]
    elements = [
        ElementInstance(id="E1", card_ref="slide_rail", host_pieces=["P1", "P2"],
                        params={"rail_w": rail_w, "rail_h": rail_h, "clearance": cl, "stroke": stroke}),
        ElementInstance(id="E2", card_ref="slide_rail", host_pieces=["P1", "P3"],
                        params={"rail_w": rail_w, "rail_h": rail_h, "clearance": cl, "stroke": stroke}),
        # E3 rack_pinion — §8.2 "rack integrated into the drawer" branch (both golden): the rack
        # carves into the drawer underside (P4), not a separate rack_bar. Knob (P5) carries the pinion.
        ElementInstance(id="E3", card_ref="rack_pinion", host_pieces=["P5", "P4"],
                        params={"module": m, "z_pinion": z, "pressure_angle_deg": 20.0,
                                "face_w": 8.0, "backlash": 0.20, "stroke": stroke}),
    ]
    if variant == "lift":
        # E4 pawl_detent — the physics-discovered HOLD element (D-M13-4). Mounts on the tower (P1),
        # catches the rack on the platform (P4). Asymmetric Bayer angles: shallow drive, steep lock.
        elements.append(ElementInstance(id="E4", card_ref="pawl_detent", host_pieces=["P1", "P4"],
                        params={"L_mm": 14.0, "b_mm": 5.0, "h_mm": 1.0, "alpha_drive_deg": 30.0,
                                "alpha_lock_deg": 80.0, "detent_pitch_mm": 3.0, "detent_depth_mm": 1.0}))
    bindings = [
        Binding(element_id="E1", port="rail_mount", piece_id="P1", anchor="rail_mount_L", mate="flush_face"),
        Binding(element_id="E1", port="carriage_mount", piece_id="P2", anchor="groove_face", mate="flush_face"),
        Binding(element_id="E1", port="travel_axis", piece_id="P1", anchor="rail_axis_L", mate="coincident_axis"),
        Binding(element_id="E2", port="rail_mount", piece_id="P1", anchor="rail_mount_R", mate="flush_face"),
        Binding(element_id="E2", port="carriage_mount", piece_id="P3", anchor="groove_face", mate="flush_face"),
        Binding(element_id="E2", port="travel_axis", piece_id="P1", anchor="rail_axis_R", mate="coincident_axis"),
        Binding(element_id="E3", port="pinion_axis", piece_id="P5", anchor="shaft_seat", mate="coincident_axis"),
        Binding(element_id="E3", port="rack_mount", piece_id="P4", anchor="rack_mount", mate="flush_face"),
        Binding(element_id="E3", port="mesh_line", piece_id="P4", anchor="rack_line", mate="coincident_axis"),
    ]
    if variant == "lift":
        bindings.append(Binding(element_id="E4", port="pawl_mount", piece_id="P1",
                                anchor="pawl_mount", mate="flush_face"))
        bindings.append(Binding(element_id="E4", port="ratchet_line", piece_id="P4",
                                anchor="rack_line", mate="coincident_axis"))
    # AR1 alignment (D-E-10) — its FIRST real firing: the two rail travel axes parallel + level.
    assembly_rules = [
        AssemblyRule(id="AR1", kind="alignment", provenance="task",
                     subjects=["E1.travel_axis", "E2.travel_axis"],
                     predicate={"axes": ["E1.travel_axis", "E2.travel_axis"],
                                "relation": "parallel", "level": True},
                     citation="§8.2: the drawer's two rails must be parallel and level"),
    ]
    lift = variant == "lift"
    hint = "vertical" if lift else "horizontal"
    load = {"mass_kg": load_kg, "direction": "-z"} if lift else None
    # realized use behaviours: each rail carries the platform/drawer travel; the rack_pinion the
    # transmission. In the lift the translation is VERTICAL and carries the 0.5 kg load.
    behaviors = [
        Behavior(id="B1", phase="use", motion=MotionSpec(kind="translation", axis_hint=hint,
                 range_value=stroke, range_unit="mm", bound="min"), realized_by="E1", load=load),
        Behavior(id="B2", phase="use", motion=MotionSpec(kind="translation", axis_hint=hint,
                 range_value=stroke, range_unit="mm", bound="min"), realized_by="E2", load=load),
        Behavior(id="B3", phase="use", motion=MotionSpec(kind="rot_to_trans", axis_hint=hint,
                 range_value=stroke, range_unit="mm", bound="min",
                 transmission={"mm_per_rev": round(tpr, 3), "pitch_radius_mm": rp, "kind": "rack_pinion"}),
                 realized_by="E3", load=load),
    ]
    # static/HOLD (lift only) — the platform must NOT back-drive under load when the crank is released.
    # Expressed WITHOUT new schema (D-M13-3 DRAFT): phase=static + motion=fixed + Behavior.load, with
    # the "resists back-drive" requirement carried as a P-HOLD criterion. realized_by E3 (the gear is
    # what would hold it) — and the physics tests whether a plain rack-pinion actually can.
    if lift:
        behaviors.append(Behavior(id="B_HOLD", phase="static",
                 motion=MotionSpec(kind="fixed", axis_hint="vertical"),
                 load={"mass_kg": load_kg, "direction": "-z"}, realized_by="E4"))
    # card-sourced imposed behaviours (V-08), per instance, BEFORE construction (pydantic copies list)
    from knowledge.cards.base import CARD_REGISTRY as _C
    n = len(behaviors)
    for e in elements:
        for tmpl in _C[e.card_ref].imposes:
            n += 1
            behaviors.append(Behavior(id=f"B{n}", phase=getattr(tmpl.phase, "value", tmpl.phase),
                                      motion=MotionSpec(kind=getattr(tmpl.motion.kind, "value", tmpl.motion.kind)),
                                      imposed_by=e.id, imposed_by_card=e.card_ref))
    parameters = [
        Parameter(name="stroke", value=stroke, unit="mm", lo=20.0, hi=400.0, resolved_by="user"),
        Parameter(name="drawer_w", value=round(drawer_w, 2), unit="mm", lo=0.0, hi=cab_inner_w,
                  resolved_by="rule"),
        Parameter(name="L_rack", value=round(L_rack, 2), unit="mm", lo=0.0, hi=400.0, resolved_by="rule"),
        Parameter(name="module", value=m, unit="mm", lo=5.0, hi=6.0, resolved_by="rule"),
    ]
    if lift:
        task_id, cmd = "anchor_lift", (
            "Design a crank-operated platform that raises and lowers a load to different heights.")
        functions = [Function(verb="position", object="load", qualifier="raise/lower to height"),
                     Function(verb="convert", object="motion", qualifier="crank rotation to lift"),
                     Function(verb="guide", object="platform", qualifier="two parallel vertical rails")]
    else:
        task_id, cmd = "anchor_hard", (
            "Design a desktop cabinet whose drawer slides out when you turn the knob. "
            "The drawer should extend about 300 mm.")
        functions = [Function(verb="allow_access", object="contents", qualifier="pull-out drawer"),
                     Function(verb="convert", object="motion", qualifier="knob rotation to drawer travel"),
                     Function(verb="guide", object="drawer", qualifier="two parallel rails")]
    plan = DesignPlan(task_id=task_id, command=cmd, variant=variant,
        functions=functions, behaviors=behaviors, pieces=pieces,
        templates=[cabinet, carr["P2"], carr["P3"], tray, knob],
        elements=elements, bindings=bindings, assembly_rules=assembly_rules, parameters=parameters)
    # attach card verification protocols exactly as ④ would (P-SLIDE per rail, P-GEAR for the pinion)
    for e in elements:
        for pr in _C[e.card_ref].verification(plan, e):
            plan.protocols.append(pr)
            b = next((x for x in plan.behaviors if x.id == pr.verifies), None)
            if b is not None and not b.verified_by:
                b.verified_by = pr.id
    return plan


def anchor_lift() -> DesignPlan:
    """The retargeted PRIMARY Hard anchor (D-M13-2) — the crank-operated lift platform."""
    return anchor_hard(variant="lift")


def main() -> None:
    from ontology.validators import validate_all

    goldens = {
        "m0_hinge_box_nostop.json": m0_hinge_box("nostop"),
        "m0_hinge_box_stop.json": m0_hinge_box("stop"),
        "snap_panel.json": snap_panel(),
        "snap_starter.json": snap_starter(),
        # D-M8-5 GOLDEN SWAP: the BENCHMARK anchor carries the stop. Honest V-B proved the §8.1
        # spec ("opens ≥90° AND returns closed") is physically UNSATISFIABLE for this over-centre
        # lid without one — a design requirement the system discovered from its own physics.
        "anchor_easy.json": anchor_easy("stop"),
        # the D20 demonstration golden: same plan, F1/B3 removed, nothing else. Validator-CLEAN (a
        # stop-less design is a legal IR); its *verdict* is an expected FAIL — see `expected_verdict_fail`.
        "anchor_easy_nostop.json": anchor_easy("nostop"),
        "slide_fixture.json": slide_fixture(),
        "rack_pinion_fixture.json": rack_pinion_fixture(),
        "anchor_lift.json": anchor_lift(),          # D-M13-2 PRIMARY: crank lift platform
        "anchor_hard.json": anchor_hard(),          # labeled ALTERNATE: horizontal drawer
    }
    # EXPECTED_FAIL at the VERDICT level (distinct from `expected` below, which is validator-level):
    # these goldens are legal IRs whose physics verdict must FAIL, and are kept as live regression
    # targets rather than deleted (the snap_panel pattern, applied one tier down).
    expected_verdict_fail = {
        "anchor_easy_nostop.json": "expected: fold-over, no angular limit — V-B 0/5 (D20 demo)",
    }
    # snap_panel is the D-GEN-5 negative-test fixture: it deliberately binds a window catch to a
    # retained board, so V-14 must reject it at ④ (the earliest guard). Recorded as expected, not a
    # build failure. It is still written — the m6 close-out RUNS it (run_snap does not re-validate,
    # so it reaches ⑥/Tier0, demonstrating the downstream guards too — defense in depth).
    expected = {"snap_panel.json": "V-14"}
    for fname, why in expected_verdict_fail.items():
        print(f"  note: {fname} is an EXPECTED_FAIL regression target — {why}")
    for fname, plan in goldens.items():
        viols = validate_all(plan)
        exp = expected.get(fname)
        if exp and viols and all(v.rule == exp for v in viols):
            status = f"{exp} REJECT ×{len(viols)} (expected — D-GEN-5 ④ negative test) ✓"
        else:
            status = "CLEAN" if not viols else f"{len(viols)} VIOLATION(S)"
        print(f"{fname:28s} {plan.task_id:24s} {status}")
        for v in viols:
            print(f"    {v.rule}: {v.detail}")
        (TASKS / fname).write_text(plan.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
