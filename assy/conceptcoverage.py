"""Renderer coverage audit - two-way traceability between blueprint and picture.

The audit enforces two rules, in both directions:

  1. **Every glyph traces to a blueprint field.** A mark on the page that comes
     from nowhere is the picture asserting engineering the contracts never stated
     - the L1 failure mode in visual form. Each glyph declares the field it reads.

  2. **Every blueprint field is either drawn or explicitly excluded.** A field
     that is silently ignored looks, to a reviewer, exactly like a field the
     architecture does not carry. Exclusions must be stated and justified.

This module holds the registries only. It draws nothing, so the audit cannot
drift by being quietly bypassed: `conceptrender` builds its glyphs from
`GLYPH_SOURCES`, and the test suite checks both directions against a real
blueprint.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# 1. glyph -> the blueprint field it is derived from
# ---------------------------------------------------------------------------
GLYPH_SOURCES: dict[str, str] = {
    # structure and arrangement
    "piece_block": "placed_pieces[].zone",
    "region_block": "region_placements[].zone",
    "state_pose_extent": "state_poses[].extent",
    "joint_symbol": "kinematic_joints[].type",
    "coupling_arrow": "joint_couplings[].kind",
    "interaction_mark": "state_interactions[].kind",
    "predicate_badge": "state_predicates[].predicate",
    "transition_envelope_outline": "transition_envelopes[].extent",
    "validation_verdict": "state_validations[].feasible",
    "body_span_extent": "body_placements[].span",
    "containment_shading": "body_placements[].containment",
    "radial_offset": "body_placements[].radial",
    "unresolved_choice_note": "unresolved_layout_choices[].question",
    "layout_conflict_marker": "layout_conflicts[].between",
    "shell_envelope": "placed_pieces[].kind",
    "boundary_face_plate": "placed_pieces[].face",
    "face_role_label": "boundary_faces[].roles",
    "axis_line": "reference_frame.primary_axis",
    "station_position": "placed_pieces[].axis_station",
    # A/B - motion
    "swept_cylindrical": "swept_volumes[].shape",
    "swept_prismatic": "swept_volumes[].shape",
    "swept_helical": "swept_volumes[].shape",
    "swept_deformation": "swept_volumes[].shape",
    "swept_unknown_marker": "swept_volumes[].shape",
    "motion_arc_arrow": "placed_pieces[].motion_kind",
    "motion_linear_arrow": "placed_pieces[].motion_kind",
    "motion_helix_glyph": "placed_pieces[].motion_kind",
    "motion_deflection_outline": "placed_pieces[].motion_kind",
    "motion_unspecified_marker": "placed_pieces[].motion_kind",
    # P1/P2/P3 - kinematic class
    "joint_pivot_marker": "placed_pieces[].element_class",
    "joint_slider_marker": "placed_pieces[].permits_motion",
    "feature_marker": "placed_pieces[].element_class",
    "attachment_location": "placed_pieces[].attached_to",
    "motion_axis_from_joint": "placed_pieces[].permits_motion",
    "topology_edge": "placed_pieces[].anchor",
    "topology_axis": "placed_pieces[].anchor",
    "topology_corridor": "placed_pieces[].anchor",
    "topology_contact_surface": "placed_pieces[].anchor",
    "topology_boundary": "spatial_constraints[].anchor",
    "unresolved_anchor_dashing": "placed_pieces[].anchor",
    "derivation_basis_label": "placed_pieces[].anchor",
    "free_parameter_marker": "spatial_constraints[].anchor",
    "derived_extent_dashing": "placed_pieces[].element_class",
    "engagement_region": "spatial_constraints[].relation",
    # C/D - interface realization
    "interface_shared_axis": "spatial_constraints[].relation",
    "interface_coaxial_working_overlap": "spatial_constraints[].relation",
    "interface_common_travel_direction": "spatial_constraints[].relation",
    "interface_mating_adjacency": "spatial_constraints[].relation",
    "interface_axis_surrounded": "spatial_constraints[].relation",
    "interface_axial_reaction_station": "spatial_constraints[].relation",
    "interface_contact_at_extreme": "spatial_constraints[].relation",
    "interface_disjoint_swept": "spatial_constraints[].relation",
    "interface_exterior_reachable": "spatial_constraints[].relation",
    "interface_continuous_route": "spatial_constraints[].relation",
    "constraint_status_colour": "spatial_constraints[].status",
    # E/F - review overlay
    "annotation_callout": "annotations[].subject",
    "issue_marker": "issues[].regions",
    "issue_kind_colour": "issues[].kind",
    # caption
    "caption_provenance": "source_candidate_id",
    "caption_authority": "authoritative",
}


# ---------------------------------------------------------------------------
# 2. blueprint field -> how it is visualized, or why it is not
# ---------------------------------------------------------------------------
FIELD_GLYPHS: dict[str, tuple[str, ...]] = {
    "reference_frame": ("axis_line",),
    "boundary_faces": ("face_role_label", "boundary_face_plate"),
    "region_placements": ("region_block",),
    "state_poses": ("state_pose_extent",),
    "kinematic_joints": ("joint_symbol",),
    "joint_couplings": ("coupling_arrow",),
    "state_interactions": ("interaction_mark",),
    "state_predicates": ("predicate_badge",),
    "transition_envelopes": ("transition_envelope_outline",),
    "state_validations": ("validation_verdict",),
    "body_placements": ("body_span_extent", "containment_shading", "radial_offset"),
    "unresolved_layout_choices": ("unresolved_choice_note",),
    "layout_conflicts": ("layout_conflict_marker",),
    "placed_pieces": (
        "piece_block", "shell_envelope", "station_position",
        "motion_arc_arrow", "motion_linear_arrow", "motion_helix_glyph",
        "motion_deflection_outline", "motion_unspecified_marker",
        "joint_pivot_marker", "joint_slider_marker", "feature_marker",
        "attachment_location", "motion_axis_from_joint",
        "topology_edge", "topology_axis", "topology_corridor",
        "topology_contact_surface", "unresolved_anchor_dashing",
        "derivation_basis_label",
        "derived_extent_dashing",
    ),
    "swept_volumes": (
        "swept_cylindrical", "swept_prismatic", "swept_helical",
        "swept_deformation", "swept_unknown_marker",
    ),
    "spatial_constraints": (
        "interface_shared_axis", "interface_coaxial_working_overlap",
        "interface_common_travel_direction", "interface_mating_adjacency",
        "interface_axis_surrounded", "interface_axial_reaction_station",
        "interface_contact_at_extreme", "interface_disjoint_swept",
        "interface_exterior_reachable", "interface_continuous_route",
        "constraint_status_colour", "engagement_region", "topology_boundary",
        "free_parameter_marker",
    ),
    "annotations": ("annotation_callout",),
    "issues": ("issue_marker", "issue_kind_colour"),
    "source_candidate_id": ("caption_provenance",),
    "authoritative": ("caption_authority",),
}

FIELD_EXCLUSIONS: dict[str, str] = {
    "_access_paths": (
        "Stage 03 access paths, passed to the renderer alongside the blueprint "
        "rather than copied into it; ownership stays with Stage 03 and the "
        "blueprint does not restate them"
    ),
    "meta": (
        "object identity and provenance; carries no spatial content and is "
        "recorded in the run manifest instead"
    ),
    "image_refs": (
        "the renderer's own output; drawing it would be self-referential"
    ),
    "interference_candidates": (
        "every unaddressed candidate is already promoted to a typed issue and "
        "drawn as an issue marker; drawing both would double-report the same "
        "conflict and inflate apparent severity"
    ),
    "access_routes": (
        "obstruction is reported through issues (ACCESS_PATH_UNMET) and the "
        "reachable surfaces are drawn as face roles; the route objects "
        "themselves would restate both"
    ),
    "views": (
        "a specification of views worth producing, not spatial content. The "
        "renderer emits its own fixed panel set, so honouring this field would "
        "make the sheet vary per product and break visual comparability"
    ),
    "source_product_id": (
        "provenance of the consumed object; shown in the run manifest, not on "
        "the drawing"
    ),
    "product_advisories": (
        "upstream Stage 03 gaps passed through unchanged; they concern the "
        "architecture rather than its arrangement and are reviewed in "
        "output.json"
    ),
    "described_layout": (
        "a prose restatement of reference_frame, region_placements and "
        "swept_volumes, all of which are drawn; rendering it would duplicate "
        "content already visible"
    ),
    "spatial_hypotheses": (
        "a prose restatement of region_placements, which is drawn as region "
        "blocks"
    ),
    "review_concerns": (
        "a prose restatement of issues, which is drawn as issue markers"
    ),
}


def audit(blueprint: dict[str, Any]) -> dict[str, Any]:
    """Two-way coverage report for one blueprint.

    `unmapped_fields` non-empty means the blueprint grew a field nobody decided
    what to do with. `orphan_glyphs` non-empty means a glyph reads a field the
    blueprint does not carry.
    """
    present = sorted(blueprint)
    mapped = {k for k in FIELD_GLYPHS if k in blueprint}
    excluded = {k for k in FIELD_EXCLUSIONS if k in blueprint}

    orphan_glyphs = sorted(
        name for name, source in GLYPH_SOURCES.items()
        if source.split("[")[0].split(".")[0] not in blueprint
    )
    declared = {g for glyphs in FIELD_GLYPHS.values() for g in glyphs}

    return {
        "fields_present": present,
        "fields_visualized": sorted(mapped),
        "fields_excluded": {k: FIELD_EXCLUSIONS[k] for k in sorted(excluded)},
        "unmapped_fields": sorted(set(present) - mapped - excluded),
        "double_declared_fields": sorted(mapped & excluded),
        "orphan_glyphs": orphan_glyphs,
        "undeclared_glyphs": sorted(set(GLYPH_SOURCES) - declared),
        "glyph_count": len(GLYPH_SOURCES),
        "coverage": (
            f"{len(mapped)} visualized, {len(excluded)} explicitly excluded, "
            f"{len(set(present) - mapped - excluded)} unaccounted"
        ),
    }
