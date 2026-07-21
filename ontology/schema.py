"""MechSynth ontology v0.1 — Pydantic v2 schema (MECHSYNTH_SPEC §2.4).

This is the single source of truth for the pipeline IR. The LLM only ever emits instances of
these classes (discrete decisions); it never emits coordinates or code (spec §2.1, D5/D7).

Beyond the spec's §2.4 (which is explicitly "abridged"), this module folds in:

  M-S extensions (per the session directive, since SNAPFIT_STARTER §1 is not in the repo):
    * MotionSpec.kind gains "snap_event", with event_force_window_N (the mate/separate force
      window of an engagement event).
    * Binding.offset_params recognises "undercut_dir" (the snap catch's undercut direction).

  M0 lessons, promoted from the physics track into the schema so the same mistakes cannot be
  made structurally:
    * Piece.is_base (D23) — V-B needs a designated base to weld; the schema must name it.
    * VerificationProtocol splits criteria (GATES) from observables (recorded, flagged, never
      silently promoted or demoted) — D19/D22. This is a typed class, not a bare dict.
    * A functional-clearance card MUST supply collision_hint() — enforced in
      knowledge/cards/base.py (D18/D21); the schema here only carries the reference.

Schema decisions that go beyond a literal reading of §2.4 are marked  # SCHEMA-DECISION  and
collected in the session summary as DRAFT decision rows.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Every model forbids unknown keys: a typo in an LLM-emitted IR must fail loudly at parse
# time, not slip through as silently-ignored data. (This is the schema-level analogue of the
# M0 lesson that a bare, unstructured blob has no nouns to check — D13.)
class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------------------
class PhaseE(str, Enum):
    use = "use"
    assembly = "assembly"
    static = "static"


class PortKind(str, Enum):
    axis = "axis"
    face = "face"
    edge = "edge"
    point = "point"


class MateE(str, Enum):
    coincident_axis = "coincident_axis"
    flush_face = "flush_face"
    offset_face = "offset_face"
    concentric = "concentric"
    on_face_uv = "on_face_uv"


class ResolvedBy(str, Enum):
    rule = "rule"
    formula = "formula"
    solver = "solver"
    user = "user"
    default = "default"


# kind of motion. "snap_event" is the M-S extension: an engagement/retention event rather
# than a continuous DoF (a snap latch is assembly + static, not a physics-engine trajectory —
# spec §3.4, D3).
MotionKind = Literal["rotation", "translation", "rot_to_trans", "fixed", "snap_event"]


# --------------------------------------------------------------------------------------
# Leaf value types
# --------------------------------------------------------------------------------------
class Citation(_Base):
    """Knowledge provenance (spec §2.2). Every non-obvious constant should trace to one."""
    doc: str
    section: Optional[str] = None


class MotionSpec(_Base):
    kind: MotionKind
    # M18 axis-1 (P&B §2.1.4): the NATURE of the working motion. "regular" = uniform/constant-ratio
    # (a hinge, a gear, a slide); "irregular" = a profiled, non-uniform law (a cam's rise-dwell-fall).
    # Default "regular" so every existing IR stays valid; only a cam-class element sets "irregular".
    nature: Literal["regular", "irregular"] = "regular"  # SCHEMA-DECISION (D-M18-2, P&B §2.1.4)
    axis_hint: Optional[str] = None  # semantic hint ("horizontal_rear") — NOT a coordinate
    range_value: Optional[float] = None  # deg or mm
    range_unit: Optional[Literal["deg", "mm"]] = None
    # What range_value MEANS (D-ONT-9): "min" = capability/range-of-motion floor (a use behaviour
    # that must reach the value, e.g. opens >= 90 deg); "max" = an imposed LIMIT the DoF must not
    # exceed (a stop, e.g. rotation limited to <= 109 deg); "exact" = a set point. Without this,
    # a rotation LIMIT constraint is indistinguishable from a rotation range-of-motion — the two
    # differ only in direction, and the ontology must keep them apart (found at m0 stop G-H).
    bound: Optional[Literal["min", "max", "exact"]] = None  # SCHEMA-DECISION (D-ONT-9)
    transmission: Optional[dict] = None  # e.g. {"mm_per_rev": 60.0}
    # M-S extension: for kind == "snap_event", the force window of the engagement, in newtons,
    # as (mating_force_max, separation_force_min). V-11 requires this when kind == snap_event.
    event_force_window_N: Optional[tuple[float, float]] = None  # SCHEMA-DECISION (M-S)


class Function(_Base):
    """User-level purpose (spec §2.2). §2.4 typed this as a bare dict; promoted to a model so
    the Functional-Basis verb is a checkable field, not free-form JSON."""  # SCHEMA-DECISION
    verb: str  # Functional Basis verb (vocabulary check deferred to stage 1 / M4)
    object: str
    qualifier: Optional[str] = None


class Behavior(_Base):
    id: str
    phase: PhaseE
    motion: MotionSpec
    # M18 axis-2 (P&B §2.1.4): relative arrangement of the input/output axes of a transmission.
    # "parallel" (coupling, spur), "intersecting" (bevel, universal joint), "crossed" (worm). Default
    # "parallel" so existing single-axis behaviours stay valid; a transmission sets it explicitly.
    axis_relationship: Literal["parallel", "intersecting", "crossed"] = "parallel"  # D-M18-2, §2.1.4
    # M18 axis-4 (P&B §7.4.3 self-help): does this behaviour HOLD its state against a back-driving
    # load without an added brake? A lead_screw with lead angle <= friction angle self-locks (True);
    # a plain rack_pinion does not (False → it needs a pawl_detent, D-M13-4). Default False (safe:
    # most behaviours do not self-lock). Resolves the DRAFT D-M13-3. (D-M18-3)
    self_locking: bool = False  # SCHEMA-DECISION (D-M18-3, P&B §7.4.3)
    load: Optional[dict] = None  # {"mass_kg": 0.5, "direction": "-z"}
    realized_by: Optional[str] = None  # element id
    imposed_by: Optional[str] = None  # constraint-imposing element id
    verified_by: Optional[str] = None  # protocol id
    # Provenance for imposed behaviours: which card imposed this (so V-08 can confirm the
    # card's imposed constraints are all registered). None for user-derived behaviours.
    imposed_by_card: Optional[str] = None  # SCHEMA-DECISION (D19/D22 audit trail)


class Port(_Base):
    """Named interface geometry of an element (spec §2.2)."""
    name: str
    kind: PortKind


class Anchor(_Base):
    """Named geometric feature of a host template (spec §2.2). Auto-assigned at template
    creation; carried in the IR so validation is self-contained (see HostTemplate)."""
    name: str
    kind: PortKind  # same geometric-kind vocabulary as ports


class HostTemplate(_Base):
    """Parametric skeleton of a piece, with its declared anchors (spec §2.2).

    SCHEMA-DECISION (D-ONT-1): §2.4's DesignPlan does not carry templates, but V-02 must check
    each Binding's anchor against "the anchors declared by the target Piece's HostTemplate".
    Without the template in the IR, that check needs an external registry the IR cannot be
    validated without. Carrying the used templates in the DesignPlan makes the IR
    self-describing and V-02 self-contained. Template *geometry* (params → solid) is still out
    of scope this session; only the anchor interface is declared here.
    """
    template_ref: str  # "box_shell" | "lid_panel" | "drawer_tray" | ...
    anchors: list[Anchor] = Field(default_factory=list)
    params: dict[str, float] = Field(default_factory=dict)


class Binding(_Base):
    element_id: str
    port: str
    piece_id: str
    anchor: str  # must be an anchor declared by the target Piece's HostTemplate (V-02)
    mate: MateE
    # offset_params carries mate-specific numbers. Recognised keys include:
    #   edge_margin_mm (float), u/v (floats in [0,1] for on_face_uv),
    #   undercut_dir (str, M-S: the snap catch undercut direction, e.g. "+y").
    offset_params: dict = Field(default_factory=dict)


class Parameter(_Base):
    name: str
    value: Optional[float] = None
    unit: str
    lo: float
    hi: float
    resolved_by: Optional[ResolvedBy] = None  # None until stage 5 resolves it (G5)
    # Provenance for a resolved value: the formula/table it came from. Every stage-5-resolved
    # Parameter must carry one (directed at m5). SCHEMA-DECISION (D-ONT-10).
    citation: Optional[Citation] = None


class Rule(_Base):
    """Parameter constraint, card-sourced (spec §2.2). Carried but not evaluated this session
    (stage-5 solving is out of scope); present so the golden IRs can express placement rules."""
    expr: str  # e.g. "engagement_len >= 0.35 * stroke"
    source_citation: Optional[Citation] = None


class Piece(_Base):
    id: str
    role: str
    # SCHEMA-DECISION (D-ONT-11): a piece is either FUNCTIONAL (host geometry chosen at ③, built
    # from a template) or HARDWARE (a body an ELEMENT needs — the pin hinge's pin — instantiated
    # at ④ into the plan, provenance-tagged and pointing back at its source element). Hardware
    # pieces have no template_ref (the card provides their geometry) and carry source_element.
    provenance: Literal["functional", "hardware"] = "functional"
    template_ref: Optional[str] = None  # required for functional; None for hardware (card-provided)
    source_element: Optional[str] = None  # set on hardware pieces → the element that provides them
    params: dict[str, float] = Field(default_factory=dict)
    # D23 (M0): V-B welds a designated base to world. The schema must name which piece is the
    # base, or the fixture rule has nothing to point at. role == "base" stays valid for spec
    # compatibility; is_base is the canonical, explicit flag.
    is_base: bool = False  # SCHEMA-DECISION (D23)

    @model_validator(mode="after")
    def _provenance_consistency(self):
        if self.provenance == "functional" and not self.template_ref:
            raise ValueError(f"functional piece '{self.id}' needs a template_ref")
        if self.provenance == "hardware" and not self.source_element:
            raise ValueError(f"hardware piece '{self.id}' needs source_element (D-ONT-11)")
        return self


class ElementInstance(_Base):
    """MechanicalElement instance (spec §2.4 / §2.2) — an element that *realizes* a behaviour
    (a hinge, a latch, a gear). Referenced by Behavior.realized_by."""
    id: str
    card_ref: str  # "pin_hinge", "snap_hook_cantilever", ...
    params: dict[str, float] = Field(default_factory=dict)
    host_pieces: list[str]  # pieces this element carves geometry into


class FeatureInstance(_Base):
    """PassiveFeature instance (D-ONT-4) — a feature that *constrains or supports* a behaviour
    rather than realizing one (a stop, a boss, a rib, a guide). Referenced by
    Behavior.imposed_by; it MUST NOT be referenced by Behavior.realized_by (a passive feature
    realizes nothing — enforced in V-08). Structurally identical to an ElementInstance; the
    distinction is which card class its card_ref resolves to (MechanicalElementCard vs
    PassiveFeatureCard), and that is what the ontology needs to keep straight."""
    id: str
    card_ref: str  # "stop_flange", ...
    params: dict[str, float] = Field(default_factory=dict)
    host_pieces: list[str]  # pieces this feature carves geometry into


# --------------------------------------------------------------------------------------
# AssemblyRule (D-ONT-12): constraints BETWEEN element instances / their bindings.
# --------------------------------------------------------------------------------------
class AssemblyRule(_Base):
    """A constraint BETWEEN element instances / their bindings — a FIRST-CLASS plan entity, the home
    element↔element constraints need (exactly as PassiveFeature needed one, D-ONT-4). NOT card-local
    (a card's `placement_rules` see one element) and NOT smuggled into either card. A DECLARATIVE
    predicate over NAMED IR referents — checkable by t0/⑤ without an LLM, and D13 applies (every
    referent it names must exist in the plan). Two typed kinds suffice for now (extensible later —
    deliberately NOT a general constraint language):

      exclusion  volume/sweep non-interference  — predicate {"excluded": <elem>, "sweep_of": <elem>}
                 ("the latch must lie outside the lid's swept volume"; the M0 B4 heritage)
      resource   a shared budget                 — predicate {"contributors": [<ref>,...],
                 "budget": <ref>, "op": "<="}  ("hook length + hinge edge_margin ≤ rim length")
      alignment  an instance↔instance POSE relation — predicate {"axes": [<elem.port>, <elem.port>],
                 "relation": "parallel", "level": true}  ("two drawer rails must be parallel and at
                 the same height"). D-E-10: a pose relation is neither a negative volume (exclusion)
                 nor a scalar budget (resource); it relates two elements' bound axis frames, checked
                 at t0 by comparing them. Falsifiable — a skewed pair fails.

    Provenance (D-ONT-12 c) records WHO imposed it — a card's `interaction_rules` knowledge, a
    template, or the task — so a rule never appears from thin air.
    """
    id: str
    kind: Literal["exclusion", "resource", "alignment"]
    provenance: str            # "card:<card_id>" | "template:<ref>" | "task"
    subjects: list[str]        # named IR referents: element/feature/piece ids, "E.port", "P.name"
    predicate: dict            # kind-typed payload (V-16 validates); its referents ⊆ subjects
    citation: Optional[str] = None


# --------------------------------------------------------------------------------------
# Verification: criteria (gates) vs observables (recorded, flagged, never gated) — D19/D22
# --------------------------------------------------------------------------------------
CompareOp = Literal["<=", ">=", "<", ">", "=="]


class Criterion(_Base):
    """A GATE: a functional outcome the geometry must answer (D22). Pass/fail."""
    name: str
    observable: str  # what is measured, e.g. "theta_max_deg"
    op: CompareOp
    threshold: float
    unit: str = ""


class Observable(_Base):
    """RECORDED, never gated (D19/D22). May carry a flag threshold that raises attention
    without failing the run. The canonical example is closing-seat impact magnitude: in a
    soft-constraint engine it measures the solver preset's compliance, not the geometry, so it
    is instrumented and flagged, never a criterion (M0 §4.4)."""
    name: str
    measured: str  # what is measured
    unit: str = ""
    flag_op: Optional[CompareOp] = None
    flag_threshold: Optional[float] = None
    note: str = ""


class VerificationProtocol(_Base):
    """actuate–observe–judge (spec §2.2), with the M0 criteria/observables split (D19/D22).

    SCHEMA-DECISION (D-ONT-2): §2.4 typed protocols as list[dict]. M0 proved the single most
    important property of a protocol is that its gates and its recorded-but-ungated quantities
    are *distinct and never confused*. Encoding that split in the type system — not in prose —
    is the whole point. Hence a typed class.
    """
    id: str
    verifies: str  # behavior id this protocol verifies (Behavior.verified_by points back)
    actuation: dict  # actuate spec, e.g. {"kind": "force_ramp", "F_max_N": 0.15, ...}
    criteria: list[Criterion]  # GATES
    observables: list[Observable] = Field(default_factory=list)  # recorded, flagged, not gated
    mode: Optional[Literal["V-A", "V-B"]] = None  # constraint-assisted / contact-only (§6.1)
    seeds: int = 5
    seed_pass: int = 4  # verdict = pass on >= seed_pass of seeds (§6.4)


class Material(_Base):
    """Material properties (spec §2.2/§3.1). v0.1: PETG only, but the class stays (D8)."""
    name: str
    E_MPa: float
    eps_allow_pct: float
    mu_friction: float
    density_kg_m3: float
    yield_MPa: Optional[float] = None
    print_min_wall_mm: Optional[float] = None
    print_clearance_mm: Optional[float] = None
    citations: list[Citation] = Field(default_factory=list)


# --------------------------------------------------------------------------------------
# Root
# --------------------------------------------------------------------------------------
class DesignPlan(_Base):
    """IR root; single source of truth for the pipeline (spec §2.4)."""
    task_id: str
    command: str  # raw user command
    functions: list[Function] = Field(default_factory=list)
    behaviors: list[Behavior] = Field(default_factory=list)
    pieces: list[Piece] = Field(default_factory=list)
    templates: list[HostTemplate] = Field(default_factory=list)  # SCHEMA-DECISION (D-ONT-1)
    elements: list[ElementInstance] = Field(default_factory=list)
    features: list[FeatureInstance] = Field(default_factory=list)  # PassiveFeatures (D-ONT-4)
    bindings: list[Binding] = Field(default_factory=list)
    assembly_rules: list[AssemblyRule] = Field(default_factory=list)  # SCHEMA-DECISION (D-ONT-12)
    parameters: list[Parameter] = Field(default_factory=list)
    protocols: list[VerificationProtocol] = Field(default_factory=list)  # D-ONT-2
    material: str = "PETG"
    variant: Optional[str] = None  # e.g. "nostop" / "stop" — the M0 hinge box has two
    stage_log: list[dict] = Field(default_factory=list)  # per-stage audit trail

    # --- convenience lookups (used by validators; not serialized) ----------------------
    def piece(self, pid: str) -> Optional[Piece]:
        return next((p for p in self.pieces if p.id == pid), None)

    def element(self, eid: str) -> Optional[ElementInstance]:
        return next((e for e in self.elements if e.id == eid), None)

    def feature(self, fid: str) -> Optional[FeatureInstance]:
        return next((f for f in self.features if f.id == fid), None)

    def instance(self, iid: str):
        """An element OR a feature by id — bindings and imposed_by may reference either."""
        return self.element(iid) or self.feature(iid)

    def template(self, template_ref: str) -> Optional[HostTemplate]:
        return next((t for t in self.templates if t.template_ref == template_ref), None)

    def protocol(self, pid: str) -> Optional[VerificationProtocol]:
        return next((p for p in self.protocols if p.id == pid), None)

    @model_validator(mode="after")
    def _ids_unique(self) -> "DesignPlan":
        """Structural integrity that must hold for *any* DesignPlan, independent of the V-rules
        (which are about design consistency). Duplicate ids make every downstream lookup
        ambiguous, so they are rejected at construction."""
        for label, items in (("behavior", self.behaviors), ("piece", self.pieces),
                             ("element", self.elements), ("feature", self.features),
                             ("protocol", self.protocols)):
            ids = [x.id for x in items]
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate {label} id(s): {sorted(dupes)}")
        # elements and features share the id namespace (bindings/imposed_by resolve across
        # both), so a collision between the two lists is also ambiguous.
        overlap = {e.id for e in self.elements} & {f.id for f in self.features}
        if overlap:
            raise ValueError(f"id(s) used by both an element and a feature: {sorted(overlap)}")
        return self


__all__ = [
    "PhaseE", "PortKind", "MateE", "ResolvedBy", "MotionKind", "CompareOp",
    "Citation", "MotionSpec", "Function", "Behavior", "Port", "Anchor", "HostTemplate",
    "Binding", "Parameter", "Rule", "Piece", "ElementInstance", "FeatureInstance",
    "Criterion", "Observable", "VerificationProtocol", "Material", "DesignPlan",
]
