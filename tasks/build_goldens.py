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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ontology.schema import (Anchor, Behavior, Binding, Criterion, DesignPlan, ElementInstance,
                             FeatureInstance, Function, HostTemplate, MotionSpec, Observable,
                             Parameter, Piece, VerificationProtocol)

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
def snap_starter() -> DesignPlan:
    functions = [
        Function(verb="secure", object="lid", qualifier="hold closed"),
        Function(verb="allow_access", object="contents", qualifier="repeated hand open/close"),
    ]

    # Templates + anchors (D-ONT-1). Anchor names are exactly those the §1.3 bindings reference.
    box_shell = HostTemplate(
        template_ref="box_shell",
        params={"box_l": 80.0, "box_w": 60.0, "box_h": 40.0, "wall": 2.0},
        anchors=[Anchor(name="side_wall_left", kind="face"),
                 Anchor(name="side_wall_right", kind="face")],
    )
    lid_panel = HostTemplate(
        template_ref="lid_panel",
        params={"lid_t": 3.0},
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
                        params={"n_hooks": 2, "design_type": 2,
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
                 motion=MotionSpec(kind="snap_event", event_force_window_N=(0.0, 80.0)),
                 realized_by="E1", verified_by="PR-T1-MATE"),
        Behavior(id="B2", phase="static",
                 motion=MotionSpec(kind="snap_event", event_force_window_N=(15.0, 60.0)),
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


def main() -> None:
    from ontology.validators import validate_all

    goldens = {
        "m0_hinge_box_nostop.json": m0_hinge_box("nostop"),
        "m0_hinge_box_stop.json": m0_hinge_box("stop"),
        "snap_panel.json": snap_panel(),
        "snap_starter.json": snap_starter(),
    }
    # snap_panel is the D-GEN-5 negative-test fixture: it deliberately binds a window catch to a
    # retained board, so V-14 must reject it at ④ (the earliest guard). Recorded as expected, not a
    # build failure. It is still written — the m6 close-out RUNS it (run_snap does not re-validate,
    # so it reaches ⑥/Tier0, demonstrating the downstream guards too — defense in depth).
    expected = {"snap_panel.json": "V-14"}
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
