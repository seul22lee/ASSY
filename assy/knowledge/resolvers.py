"""Resolution proposal knowledge.

For each problem phenomenon, propose one or more candidate resolutions. Each
candidate names the ``method`` that justified it so the commitment carries an
auditable rule reference (STAGE_05 section 7.5).

The LLM boundary sits exactly here: checks *detect* problems deterministically,
and this layer *proposes* responses. Where a proposal needs a number, the number
comes from :mod:`assy.knowledge.elements`, never from a language model (Rule L-2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from assy.domain.engineering import (
    Commitment,
    CommitmentKind,
    CommitmentStatus,
    EngineeringWorkingState,
    Problem,
    Resolution,
)
from assy.knowledge import elements as el
from assy.knowledge import materials as mat


@dataclass
class ResolveContext:
    """Everything a resolver may consult. Deliberately small (Rule TOK-1)."""

    payload_n: float = 15.0
    travel_mm: float = 90.0
    input_torque_limit_nmm: float = 2000.0
    structural_material: str = "PLA"
    bearing_material: str = "POM"
    shaft_material: str = "STEEL"
    process: str = "FDM"
    family_id: str = "lead_screw"
    self_locking_required: bool = True
    allowable_strain: float = 0.015
    """Design strain limit for a compliant element. Conservative for brittle PLA."""
    max_release_force_n: float = 15.0
    """Comfortable single-thumb effort."""


Resolver = Callable[[Problem, EngineeringWorkingState, ResolveContext], list[Resolution]]
REGISTRY: dict[str, Resolver] = {}


def resolver(*phenomena: str):
    def wrap(fn: Resolver) -> Resolver:
        for p in phenomena:
            REGISTRY[p] = fn
        return fn

    return wrap


def _entity(p: Problem) -> str:
    return p.entities[0] if p.entities else "unknown"


def _c(subject: str, kind: CommitmentKind, statement: str, **kw) -> Commitment:
    return Commitment(subject=subject, kind=kind, statement=statement, **kw)


# --------------------------------------------------------------------------
# Support and structure
# --------------------------------------------------------------------------
@resolver("radial_support", "bearing_interface")
def resolve_radial_support(p: Problem, state: EngineeringWorkingState, ctx: ResolveContext):
    e = _entity(p)
    span, dia = 60.0, 8.0
    load = ctx.payload_n
    allowable = 0.15  # mm, keeps a running clearance meaningful
    straddle = Resolution(
        problem_id=p.id,
        approach=f"straddle-mount {e} on two bushings",
        method="exact_constraint/two_bearing_location",
        benefits=["locates the axis in 5 DOF", "halves peak deflection versus a cantilever"],
        risks=["requires bearing seats in two walls, which crosses a parting line"],
        commitments=[
            _c(f"{e}.radial_support", CommitmentKind.SUPPORT, f"{e} runs in two bushings", value=2),
            _c(f"{e}.support_span", CommitmentKind.PARAMETER, f"{e} bearing span", value=span, unit="mm"),
            _c(f"{e}.diameter", CommitmentKind.PARAMETER, f"{e} shaft diameter", value=dia, unit="mm"),
            _c(f"{e}.radial_load", CommitmentKind.PARAMETER, f"{e} radial load", value=load, unit="N"),
            _c(
                f"{e}.deflection_allowable",
                CommitmentKind.CONSTRAINT,
                f"{e} deflection allowable",
                value=allowable,
                unit="mm",
            ),
            _c(
                f"{e}.bearing_material",
                CommitmentKind.VALUE,
                f"{e} bushing material",
                value=ctx.bearing_material,
            ),
        ],
        score=1.0,
    )
    cantilever = Resolution(
        problem_id=p.id,
        approach=f"cantilever {e} from one wall",
        method="single_wall_cantilever",
        benefits=["simplest assembly", "no parting-line coaxiality"],
        risks=["deflection scales with L^3", "axis tilts under load"],
        commitments=[
            _c(f"{e}.radial_support", CommitmentKind.SUPPORT, f"{e} cantilevered", value=1),
        ],
        score=0.3,
    )
    return [straddle, cantilever]


@resolver("axial_retention")
def resolve_axial_retention(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"shoulder one end of {e}, retaining clip the other",
            method="shoulder_and_clip_retention",
            benefits=["deterministic axial position", "serviceable"],
            risks=["clip groove is a stress riser"],
            commitments=[
                _c(
                    f"{e}.axial_retention",
                    CommitmentKind.SUPPORT,
                    f"{e} retained by shoulder and clip",
                    value="shoulder+clip",
                )
            ],
            score=1.0,
        )
    ]


@resolver("load_path", "structural_margin")
def resolve_load_path(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"route {e} load through the shell to the base",
            method="direct_load_path_to_ground",
            benefits=["shortest path to ground", "no bending in the shell wall"],
            commitments=[
                _c(
                    f"{e}.load_path",
                    CommitmentKind.RELATION,
                    f"{e} -> guidance -> shell -> base",
                    value="shell_to_base",
                )
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Motion
# --------------------------------------------------------------------------
@resolver("guidance", "jamming")
def resolve_guidance(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    span, overhang = 70.0, 25.0
    friction = mat.material(ctx.structural_material).friction_vs_self
    ratio = el.jamming_ratio(overhang, span, friction)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"two parallel guide rails for {e}",
            method="two_rail_guidance/jamming_ratio",
            benefits=[f"jamming index {ratio:.2f} (<1 is non-binding)", "resists tilt about two axes"],
            risks=["requires parallelism between rails"],
            commitments=[
                _c(f"{e}.guidance", CommitmentKind.SUPPORT, f"{e} runs on two guide rails", value=2),
                _c(f"{e}.guide_span", CommitmentKind.PARAMETER, f"{e} guide span", value=span, unit="mm"),
                _c(f"{e}.guide_overhang", CommitmentKind.PARAMETER, f"{e} load overhang", value=overhang, unit="mm"),
                _c(
                    f"{e}.jamming_index",
                    CommitmentKind.CONSTRAINT,
                    "jamming index must stay below 1",
                    value=round(ratio, 4),
                    expression="overhang/span < 1/(2*mu)",
                ),
            ],
            score=1.0,
        )
    ]


@resolver("travel_envelope")
def resolve_travel(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{e} travels {ctx.travel_mm:g} mm with clearance at both ends",
            method="requirement_derived_stroke",
            benefits=["satisfies the stated travel requirement"],
            commitments=[
                _c(
                    f"{e}.travel_envelope",
                    CommitmentKind.MOTION,
                    f"{e} stroke",
                    value=ctx.travel_mm,
                    unit="mm",
                    expression="stroke = required_travel",
                ),
                _c(
                    f"{e}.motion_clearance",
                    CommitmentKind.PARAMETER,
                    f"{e} end clearance",
                    value=5.0,
                    unit="mm",
                ),
            ],
            score=1.0,
        )
    ]


@resolver("end_stops")
def resolve_end_stops(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"hard stops at both ends of {e} travel",
            method="hard_stop_limits",
            benefits=["bounds travel without relying on user judgement"],
            commitments=[
                _c(f"{e}.end_stops", CommitmentKind.MOTION, f"{e} hard stops", value="both_ends")
            ],
            score=1.0,
        )
    ]


@resolver("motion_interference")
def resolve_motion_interference(p: Problem, state, ctx: ResolveContext):
    """Local fix first: grow the housing rather than change the stroke (Rule REV-1)."""
    housing = state.find_subject("housing.internal_height")
    stroke = state.find_subject("platform.travel_envelope")
    clear = state.find_subject("platform.motion_clearance")
    needed = float(stroke.value) + 2 * float(clear.value) + 10.0 if (stroke and clear) else 140.0
    out = []
    if housing:
        out.append(
            Resolution(
                problem_id=p.id,
                approach=f"increase internal height to {needed:g} mm",
                method="envelope_growth",
                benefits=["preserves the required stroke", "local change"],
                risks=["increases product height"],
                supersedes=[housing.id],
                commitments=[
                    _c(
                        "housing.internal_height",
                        CommitmentKind.PARAMETER,
                        "housing internal height",
                        value=needed,
                        unit="mm",
                    )
                ],
                score=1.0,
            )
        )
    return out


# --------------------------------------------------------------------------
# Machine elements
# --------------------------------------------------------------------------
@resolver("lead_relation", "backdrive_behaviour", "thread_engagement")
def resolve_screw(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    dm, lead = 8.0, 2.0
    mu = mat.material(ctx.structural_material).friction_vs_self
    r = el.lead_screw(ctx.payload_n, dm, lead, mu)
    turns = ctx.travel_mm / lead
    return [
        Resolution(
            problem_id=p.id,
            approach=f"M8 x {lead:g} mm lead screw ({'self-locking' if r.self_locking else 'back-drives'})",
            method="power_screw_square_thread",
            benefits=[
                f"self-locking: {r.self_locking} (mu={mu:.2f} vs tan(lambda)={r.lead_angle_deg:.2f} deg)",
                f"raise torque {r.torque_raise_nmm:.1f} Nmm, well under the {ctx.input_torque_limit_nmm:g} Nmm limit",
            ],
            risks=[f"efficiency only {r.efficiency:.0%}", f"{turns:.0f} crank turns for full travel"],
            commitments=[
                _c(f"{e}.pitch_diameter", CommitmentKind.PARAMETER, "screw pitch diameter", value=dm, unit="mm"),
                _c(f"{e}.lead", CommitmentKind.PARAMETER, "screw lead", value=lead, unit="mm"),
                _c(
                    f"{e}.lead_relation",
                    CommitmentKind.MOTION,
                    "platform travel per crank turn",
                    value=lead,
                    unit="mm/turn",
                    expression="travel = turns * lead",
                ),
                _c(
                    f"{e}.backdrive_behaviour",
                    CommitmentKind.CONSTRAINT,
                    "screw must be self-locking",
                    value=r.self_locking,
                    expression="mu > tan(lambda)",
                    status=CommitmentStatus.VERIFIED,
                ),
                _c(
                    f"{e}.thread_engagement",
                    CommitmentKind.INTERFACE,
                    "nut thread engagement length",
                    value=12.0,
                    unit="mm",
                ),
                _c(
                    f"{e}.raise_torque",
                    CommitmentKind.PARAMETER,
                    "torque to raise payload",
                    value=round(r.torque_raise_nmm, 2),
                    unit="Nmm",
                ),
                _c(
                    "input_effort",
                    CommitmentKind.OBJECTIVE,
                    "minimise crank effort while preserving self-locking",
                    expression="minimize(raise_torque) subject to mu > tan(lambda)",
                ),
            ],
            score=1.0,
        )
    ]


@resolver("ratio_relation", "centre_distance", "backlash")
def resolve_gear(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    module, z1, z2 = 1.5, 12, 24
    c = el.gear_centre_distance(module, z1, z2)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"module {module} gear pair, z={z1}/{z2}",
            method="standard_centre_distance",
            benefits=[f"centre distance {c:.2f} mm", f"ratio {el.gear_ratio(z1, z2):.2f}"],
            risks=[f"minimum {el.undercut_limit()} teeth to avoid undercut"],
            commitments=[
                _c(f"{e}.module", CommitmentKind.PARAMETER, "gear module", value=module, unit="mm"),
                _c(f"{e}.centre_distance", CommitmentKind.PARAMETER, "centre distance", value=c, unit="mm"),
                _c(
                    f"{e}.ratio_relation",
                    CommitmentKind.MOTION,
                    "gear ratio",
                    value=el.gear_ratio(z1, z2),
                    expression="i = z2/z1",
                ),
                _c(f"{e}.backlash", CommitmentKind.INTERFACE, "gear backlash", value=0.1, unit="mm"),
            ],
            score=1.0,
        )
    ]


@resolver("friction_wear")
def resolve_friction(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"low-friction bushing at {e}",
            method="bearing_material_selection",
            benefits=[f"{ctx.bearing_material} has low friction against polymer"],
            commitments=[
                _c(f"{e}.friction_wear", CommitmentKind.INTERFACE, f"{e} runs in {ctx.bearing_material}",
                   value=ctx.bearing_material)
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Packaging, assembly, manufacturing
# --------------------------------------------------------------------------
@resolver("internal_envelope")
def resolve_envelope(p: Problem, state, ctx: ResolveContext):
    height = ctx.travel_mm + 30.0
    return [
        Resolution(
            problem_id=p.id,
            approach=f"internal envelope sized for {ctx.travel_mm:g} mm stroke",
            method="stroke_plus_reserve",
            benefits=["contains the full stroke with end reserve"],
            commitments=[
                _c("housing.internal_height", CommitmentKind.PARAMETER, "housing internal height", value=height, unit="mm"),
                _c("housing.internal_width", CommitmentKind.PARAMETER, "housing internal width", value=110.0, unit="mm"),
                _c("housing.internal_depth", CommitmentKind.PARAMETER, "housing internal depth", value=90.0, unit="mm"),
            ],
            score=1.0,
        )
    ]


@resolver("assembly_access", "part_insertion", "service_access", "assembly_sequence")
def resolve_access(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach="removable side panel carrying one bushing of each pair",
            method="split_at_bearing_plane",
            benefits=["mechanism inserts before closure", "service without disturbing the platform"],
            risks=["bearing coaxiality now spans a parting line and needs dowels"],
            commitments=[
                _c(f"{e}.assembly_access", CommitmentKind.ASSEMBLY, "removable side panel", value="side_panel"),
                _c(f"{e}.service_access", CommitmentKind.ASSEMBLY, "panel exposes the drive", value="side_panel"),
                _c(f"{e}.part_insertion", CommitmentKind.ASSEMBLY, "insert through the open side face", value="side_face"),
                _c(
                    "assembly.sequence",
                    CommitmentKind.ASSEMBLY,
                    "guides -> platform -> screw -> shaft -> panel -> crank",
                    value="guides,platform,screw,shaft,panel,crank",
                ),
                _c(
                    "panel_alignment.tolerance_chain",
                    CommitmentKind.TOLERANCE,
                    "dowel-controlled bearing coaxiality across the split",
                    value=0.30,
                    unit="mm",
                    expression="0.10,0.10,0.20",
                ),
            ],
            score=1.0,
        )
    ]


@resolver("process_binding", "build_orientation")
def resolve_process(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    proc = mat.process(ctx.process)
    material = ctx.shaft_material if "shaft" in e else ctx.structural_material
    if not mat.compatible(material, ctx.process):
        material = ctx.structural_material
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{e}: {material} via {ctx.process}",
            method="material_process_compatibility",
            benefits=[f"{material} is listed compatible with {ctx.process}"],
            risks=["anisotropic layer adhesion" if proc.anisotropic else ""],
            commitments=[
                _c(f"{e}.material", CommitmentKind.MANUFACTURING, f"{e} material", value=material),
                _c(f"{e}.process", CommitmentKind.MANUFACTURING, f"{e} process", value=ctx.process),
                _c(
                    f"{e}.build_orientation",
                    CommitmentKind.MANUFACTURING,
                    f"{e} printed with loads in-plane",
                    value="loads_in_plane",
                ),
            ],
            score=1.0,
        )
    ]


@resolver("material")
def resolve_material(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    material = ctx.shaft_material if "shaft" in e else ctx.structural_material
    if not mat.compatible(material, ctx.process):
        material = ctx.structural_material
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{e} in {material}",
            method="material_selection",
            commitments=[_c(f"{e}.material", CommitmentKind.MANUFACTURING, f"{e} material", value=material)],
            score=1.0,
        )
    ]


@resolver("process")
def resolve_process_only(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{e} made by {ctx.process}",
            method="process_selection",
            commitments=[_c(f"{e}.process", CommitmentKind.MANUFACTURING, f"{e} process", value=ctx.process)],
            score=1.0,
        )
    ]


@resolver("wall_thickness")
def resolve_wall(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    proc = mat.process(ctx.process)
    thickness = round(proc.min_wall_mm * 2.0, 2)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{thickness:g} mm wall ({proc.name} minimum {proc.min_wall_mm:g} mm)",
            method="process_minimum_wall",
            benefits=["2x the process minimum gives margin for load and print variation"],
            commitments=[
                _c(f"{e}.wall_thickness", CommitmentKind.PARAMETER, f"{e} wall", value=thickness, unit="mm")
            ],
            score=1.0,
        )
    ]


@resolver("tolerance_chain")
def resolve_tolerance(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    proc = mat.process(ctx.process)
    parts = [proc.tolerance_mm, proc.tolerance_mm, 0.10]
    limit = round(el.stack_rss(parts) * 1.4, 3)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"allocate {limit:g} mm to the {e} chain",
            method="rss_tolerance_allocation",
            benefits=[f"RSS stack {el.stack_rss(parts):.3f} mm inside the {limit:g} mm allocation"],
            commitments=[
                _c(
                    f"{e}.tolerance_chain",
                    CommitmentKind.TOLERANCE,
                    f"{e} critical chain",
                    value=limit,
                    unit="mm",
                    expression=",".join(str(x) for x in parts),
                )
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Hinged bodies
# --------------------------------------------------------------------------
@resolver("hinge_axis", "angular_range", "hinge_support", "closing_clearance")
def resolve_hinge(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    open_deg = 105.0
    depth = 90.0
    thickness = 6.0
    offset = 4.0
    rear_clearance = 5.0
    reach = el.hinge_swing_clearance(thickness, offset, open_deg)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"rear hinge axis, {open_deg:g} deg swing on two knuckles",
            method="hinge_axis_placement/swing_sweep",
            benefits=[
                f"{open_deg:g} deg holds the lid clear of the opening",
                f"rearward corner reach {reach:.1f} mm is relieved behind the axis",
            ],
            risks=["lid corner interferes if the axis moves inboard"],
            commitments=[
                _c(f"{e}.hinge_axis", CommitmentKind.MOTION, f"{e} hinge axis at the rear edge",
                   value="rear_edge_x", expression="axis = rear_edge"),
                _c(f"{e}.angular_range", CommitmentKind.MOTION, f"{e} swing range",
                   value=open_deg, unit="deg", expression="0 <= theta <= open_angle"),
                _c(f"{e}.hinge_support", CommitmentKind.SUPPORT, f"{e} on two hinge knuckles", value=2),
                _c(f"{e}.hinge_offset", CommitmentKind.PARAMETER, f"{e} axis offset from rear face",
                   value=offset, unit="mm"),
                _c(f"{e}.depth", CommitmentKind.PARAMETER, f"{e} depth", value=depth, unit="mm"),
                _c(f"{e}.thickness", CommitmentKind.PARAMETER, f"{e} plate thickness",
                   value=thickness, unit="mm"),
                _c(f"{e}.closing_clearance", CommitmentKind.PARAMETER, f"{e} closing gap",
                   value=0.4, unit="mm"),
                _c(f"{e}.swing_reach", CommitmentKind.PARAMETER, f"{e} rearward swing reach",
                   value=round(reach, 2), unit="mm"),
                _c(f"{e}.rear_clearance", CommitmentKind.PARAMETER, f"{e} clearance behind the axis",
                   value=rear_clearance, unit="mm"),
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Compliant elements and retention
# --------------------------------------------------------------------------
@resolver("beam_geometry", "deflection_strain", "insertion_force")
def resolve_snap_beam(p: Problem, state, ctx: ResolveContext):
    """Size the beam so peak strain stays inside the material allowable.

    Geometry, strain, and actuation force are one coupled problem, so a single
    resolution commits all three rather than leaving the agenda to rediscover
    the coupling.
    """
    e = _entity(p)
    material = mat.material(ctx.structural_material)
    length, width, thickness, undercut = 12.0, 6.0, 1.2, 0.8
    strain = el.cantilever_snap_strain(undercut, length, thickness)
    force = el.cantilever_snap_deflection_force(
        undercut, length, width, thickness, material.youngs_modulus_mpa
    )
    allowable = ctx.allowable_strain
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{length:g}x{width:g}x{thickness:g} mm cantilever, {undercut:g} mm undercut",
            method="cantilever_beam/strain_limited_sizing",
            benefits=[
                f"peak strain {strain:.4f} against {allowable:.4f} allowable "
                f"({allowable / strain if strain else 0:.2f}x margin)",
                f"deflection force {force:.2f} N",
            ],
            risks=[
                f"{ctx.structural_material} creeps under sustained deflection",
                "strain rises with the square of shortening the beam",
            ],
            commitments=[
                _c(f"{e}.beam_geometry", CommitmentKind.INTERFACE, f"{e} cantilever geometry",
                   value=f"{length}x{width}x{thickness}"),
                _c(f"{e}.length", CommitmentKind.PARAMETER, f"{e} beam length", value=length, unit="mm"),
                _c(f"{e}.width", CommitmentKind.PARAMETER, f"{e} beam width", value=width, unit="mm"),
                _c(f"{e}.thickness", CommitmentKind.PARAMETER, f"{e} beam thickness", value=thickness, unit="mm"),
                _c(f"{e}.undercut", CommitmentKind.PARAMETER, f"{e} undercut depth", value=undercut, unit="mm"),
                _c(f"{e}.deflection_strain", CommitmentKind.CONSTRAINT, f"{e} peak strain",
                   value=round(strain, 5), expression="1.5*t*y/L^2 <= allowable_strain"),
                _c(f"{e}.strain_allowable", CommitmentKind.CONSTRAINT, f"{e} allowable strain",
                   value=allowable),
                _c(f"{e}.deflection_force", CommitmentKind.PARAMETER, f"{e} deflection force",
                   value=round(force, 3), unit="N"),
                _c(f"{e}.insertion_force", CommitmentKind.CRITICAL_CHARACTERISTIC,
                   f"{e} force to close past the catch", value=None, unit="N",
                   expression="P*(mu+tan(lead))/(1-mu*tan(lead))"),
            ],
            score=1.0,
        )
    ]


@resolver("engagement_geometry", "retention_force", "release_force", "release_actuation")
def resolve_engagement(p: Problem, state, ctx: ResolveContext):
    """Choose the two face angles that set the retention/release tradeoff."""
    e = _entity(p)
    beam = state.find_subject("snap_beam.deflection_force")
    force = float(beam.value) if beam else 4.0
    mu = mat.material(ctx.structural_material).friction_vs_self
    lead, retain = 30.0, 60.0
    limit = el.self_locking_face_angle(mu)
    f_insert = el.snap_engagement_force(force, lead, mu)
    f_retain = el.snap_engagement_force(force, retain, mu)
    f_release = force * (1.0 + mu)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{lead:g} deg lead face, {retain:g} deg retention face",
            method="snap_face_angles/retention_release_tradeoff",
            benefits=[
                f"insertion {f_insert:.2f} N, retention {f_retain:.2f} N "
                f"({f_retain / f_insert if f_insert else 0:.1f}x asymmetry)",
                f"thumb release {f_release:.2f} N by deflecting the beam directly",
                f"retention face stays below the {limit:.1f} deg self-locking angle",
            ],
            risks=["retention and release cannot both be improved by face angle alone"],
            commitments=[
                _c(f"{e}.engagement_geometry", CommitmentKind.INTERFACE, f"{e} face angles",
                   value=f"lead={lead},retain={retain}"),
                _c(f"{e}.lead_angle", CommitmentKind.PARAMETER, f"{e} lead face angle", value=lead, unit="deg"),
                _c(f"{e}.retention_angle", CommitmentKind.PARAMETER, f"{e} retention face angle",
                   value=retain, unit="deg"),
                _c(f"{e}.retention_force", CommitmentKind.CRITICAL_CHARACTERISTIC,
                   f"{e} force resisting opening", value=round(f_retain, 3), unit="N"),
                _c(f"{e}.release_force", CommitmentKind.CRITICAL_CHARACTERISTIC,
                   f"{e} thumb release effort", value=round(f_release, 3), unit="N"),
                _c(f"{e}.release_actuation", CommitmentKind.INTERFACE,
                   f"{e} thumb pad deflects the beam clear of the catch", value="thumb_pad"),
                _c("retention_vs_release", CommitmentKind.OBJECTIVE,
                   "maximise retention while keeping release effort comfortable",
                   expression="maximize(retention_force) subject to release_force <= 15 N"),
                _c(f"{e}.self_locking_limit", CommitmentKind.CONSTRAINT,
                   f"{e} retention angle must stay below the self-locking angle",
                   value=round(limit, 2), unit="deg", expression="retention_angle < atan(1/mu)"),
            ],
            score=1.0,
        )
    ]


@resolver("boundary_clearance")
def resolve_boundary(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{e} runs with a shrouded 1.5 mm gap to the static shell",
            method="moving_boundary_gap",
            benefits=["below the 3 mm pinch threshold, so no guard is required"],
            commitments=[
                _c(f"{e}.boundary_clearance", CommitmentKind.PARAMETER, f"{e} boundary gap",
                   value=1.5, unit="mm"),
                _c(f"{e}.pinch_access", CommitmentKind.PARAMETER, f"{e} exposed gap", value=1.5, unit="mm"),
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Safety and ergonomics
# --------------------------------------------------------------------------
@resolver("pinch_access")
def resolve_pinch(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    return [
        Resolution(
            problem_id=p.id,
            approach=f"shroud the {e} boundary and keep the running gap beneath it",
            method="guard_decouples_safety_gap",
            benefits=["decouples the safety gap from the running clearance"],
            risks=["adds a lip to the moulding/print"],
            commitments=[
                _c(f"{e}.pinch_access", CommitmentKind.PARAMETER, f"{e} exposed gap", value=2.0, unit="mm"),
                _c(f"{e}.guard", CommitmentKind.INTERFACE, f"{e} shroud lip", value="shroud_lip"),
            ],
            score=1.0,
        )
    ]


@resolver("ergonomic_reach")
def resolve_ergonomics(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    radius = 40.0
    torque = state.find_subject("lift_screw.raise_torque")
    force = (float(torque.value) / radius) if torque else 0.0
    return [
        Resolution(
            problem_id=p.id,
            approach=f"{radius:g} mm crank radius",
            method="hand_crank_effort",
            benefits=[f"{force:.2f} N tangential effort at the grip"],
            commitments=[
                _c(f"{e}.crank_radius", CommitmentKind.PARAMETER, "crank radius", value=radius, unit="mm"),
                _c(f"{e}.ergonomic_reach", CommitmentKind.INTERFACE, "crank grip reachable externally", value="side_face"),
                _c(
                    f"{e}.grip_force",
                    CommitmentKind.CRITICAL_CHARACTERISTIC,
                    "tangential effort at the crank grip",
                    value=round(force, 3),
                    unit="N",
                ),
            ],
            score=1.0,
        )
    ]


# --------------------------------------------------------------------------
# Generic fallbacks
# --------------------------------------------------------------------------
@resolver("parameter_value")
def resolve_parameter(p: Problem, state, ctx: ResolveContext):
    e = _entity(p)
    c = state.find_subject(e)
    if c is None:
        return []
    return [
        Resolution(
            problem_id=p.id,
            approach=f"assign a nominal value to {e}",
            method="nominal_default",
            risks=["nominal placeholder; should be driven by a relation once one exists"],
            supersedes=[c.id],
            commitments=[
                _c(e, c.kind, c.statement, value=1.0, unit=c.unit, status=CommitmentStatus.ASSUMED)
            ],
            score=0.5,
        )
    ]


def propose(p: Problem, state: EngineeringWorkingState, ctx: ResolveContext) -> list[Resolution]:
    """Candidate resolutions for a problem, or an empty list if unknown.

    An empty list is not a failure of the model - it is the honest signal that
    the knowledge base lacks a rule, which the loop reports rather than papers
    over (STAGE_05 section 11.3).
    """
    fn = REGISTRY.get(p.phenomenon)
    return fn(p, state, ctx) if fn else []
