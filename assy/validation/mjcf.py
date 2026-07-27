"""MJCF model builders: rigid-body motion and contact.

Models are selected by the engineering roles present in the definition, not by
product identity. Two builders exist because two motion topologies exist:

    translating output -> slide-joint lift model
    hinged output      -> revolute lid model with a compliant retention feature

**Modelling limitation, stated explicitly.** MuJoCo is a rigid-body simulator and
cannot represent beam flexure. The snap beam is therefore modelled as a *lumped
torsional spring* whose stiffness is derived from the analytical cantilever
(k = 3EI/L). That is faithful enough for contact timing, engagement sequencing,
and gross retention, and it is *not* evidence about strain, stress, creep, or
fatigue - those come from the analytical backend. Neither backend alone is
sufficient for a compliant latch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from assy.domain.engineering import CADReadyEngineeringDefinition, CommitmentKind
from assy.knowledge import materials as mat

MM = 0.001


@dataclass
class ModelSpec:
    xml: str
    kind: str  # "lift" | "latch"
    limitations: list[str]
    joints: dict[str, str]  # semantic name -> mjcf joint name
    notes: dict[str, float]


def _v(definition: CADReadyEngineeringDefinition, subject: str, default: float) -> float:
    c = definition.working_state.find_subject(subject)
    if c is None or not isinstance(c.value, (int, float)) or isinstance(c.value, bool):
        return default
    return float(c.value)


def has_role(definition: CADReadyEngineeringDefinition, role: str) -> bool:
    return any(
        role in e.roles
        for e in definition.working_state.active_by_kind(CommitmentKind.ENTITY)
    )


# --------------------------------------------------------------------------
# Lift model (translating output)
# --------------------------------------------------------------------------
LIFT_XML = """<mujoco model="assy_lift">
  <compiler angle="degree"/>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <visual><global offwidth="960" offheight="720"/></visual>
  <default><geom rgba="0.72 0.74 0.78 1" friction="0.35 0.005 0.0001"/></default>
  <worldbody>
    <light pos="0.3 -0.3 {light_z}" dir="-0.4 0.4 -1" diffuse="0.9 0.9 0.9"/>
    <camera name="iso" pos="0.36 -0.36 {cam_z}" xyaxes="0.7 0.7 0 -0.4 0.4 0.8"/>
    <geom name="ground" type="plane" size="1 1 0.01" rgba="0.25 0.25 0.28 1"/>
    <body name="housing" pos="0 0 {wall}">
      <geom name="housing_base" type="box" size="{hw} {hd} {wall}"/>
      <geom name="housing_left" type="box" size="{wall} {hd} {hh}" pos="-{hw} 0 {hh}"/>
      <geom name="housing_right" type="box" size="{wall} {hd} {hh}" pos="{hw} 0 {hh}"/>
    </body>
    <body name="platform" pos="0 0 {platform_z}">
      <joint name="lift" type="slide" axis="0 0 1" range="0 {stroke}" damping="2.0"
             frictionloss="{frictionloss}"/>
      <geom name="platform_plate" type="box" size="{pw} {pd} 0.003" mass="0.08"/>
      <body name="payload" pos="0 0 0.021">
        <geom name="payload_mass" type="box" size="{pw2} {pd2} 0.015" mass="{payload}"
              rgba="0.85 0.45 0.2 1"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <position name="lift_drive" joint="lift" kp="{kp}" ctrlrange="0 {stroke}"
              forcerange="-{fmax} {fmax}"/>
  </actuator>
</mujoco>
"""


def build_lift(definition: CADReadyEngineeringDefinition, payload_kg: float) -> ModelSpec:
    stroke = _v(definition, "platform.travel_envelope", 90.0) * MM
    hw = _v(definition, "housing.internal_width", 110.0) * MM / 2
    hd = _v(definition, "housing.internal_depth", 90.0) * MM / 2
    hh = _v(definition, "housing.internal_height", 120.0) * MM / 2
    wall = _v(definition, "housing.wall_thickness", 2.4) * MM

    backdrive = definition.working_state.find_subject("lift_screw.backdrive_behaviour")
    self_locking = bool(backdrive.value) if backdrive is not None else False
    weight = (payload_kg + 0.08) * 9.81
    frictionloss = round(weight * 1.5, 3) if self_locking else 0.05
    kp = round(max(3000.0, frictionloss * 400.0), 1)

    xml = LIFT_XML.format(
        dt=0.002,
        light_z=hh * 5,
        cam_z=hh * 3,
        wall=wall,
        hw=hw,
        hd=hd,
        hh=hh,
        platform_z=wall * 2 + 0.01,
        stroke=stroke,
        pw=max(hw - 0.004, 0.01),
        pd=max(hd - 0.004, 0.01),
        pw2=max(hw / 2, 0.01),
        pd2=max(hd / 2, 0.01),
        payload=payload_kg,
        frictionloss=frictionloss,
        kp=kp,
        fmax=round(max(300.0, frictionloss * 20.0), 1),
    )
    return ModelSpec(
        xml=xml,
        kind="lift",
        limitations=[
            "the screw drive is lumped into joint friction and a position servo; "
            "thread contact, wear, and efficiency are not modelled",
        ],
        joints={"output": "lift"},
        notes={"frictionloss_n": frictionloss, "self_locking": float(self_locking)},
    )


# --------------------------------------------------------------------------
# Latch model (hinged output with compliant retention)
# --------------------------------------------------------------------------
def build_latch(definition: CADReadyEngineeringDefinition) -> ModelSpec:
    """Hinged lid with a compliant snap retention feature.

    Positions are computed rather than hand-placed so the assembled state has no
    initial penetration - an overlapping rest state injects a large contact
    impulse at t=0 and destroys the run before any physics happens.

    The beam is a rigid link on a torsional spring, k = 3EI/L from the analytical
    cantilever. Contact timing and gross retention are represented; strain is not.
    """
    open_deg = _v(definition, "lid.angular_range", 105.0)
    width = _v(definition, "housing.internal_width", 110.0) * MM
    depth = _v(definition, "lid.depth", 90.0) * MM
    height = _v(definition, "housing.internal_height", 60.0) * MM
    wall = _v(definition, "housing.wall_thickness", 2.4) * MM
    gap = _v(definition, "lid.closing_clearance", 0.4) * MM

    beam_l = _v(definition, "snap_beam.length", 12.0) * MM
    beam_w = _v(definition, "snap_beam.width", 6.0) * MM
    beam_t = _v(definition, "snap_beam.thickness", 1.2) * MM
    undercut = _v(definition, "snap_beam.undercut", 0.8) * MM
    lid_t = _v(definition, "lid.thickness", 6.0) * MM

    mat_c = definition.working_state.find_subject("snap_beam.material")
    material = mat.material(str(mat_c.value)) if mat_c else mat.material("PLA")
    e_mpa = material.youngs_modulus_mpa
    mu = material.friction_vs_self

    # Lumped torsional stiffness: k_theta = 3EI/L, converted N.mm/rad -> N.m/rad
    second_moment = (beam_w * 1000) * (beam_t * 1000) ** 3 / 12.0
    k_theta = (3.0 * e_mpa * second_moment / (beam_l * 1000)) * 1e-3

    # Rotor inertia so the stiff, light beam is integrable at a usable timestep.
    armature = 2.0e-6
    dt = 2.0e-4
    damping = round(2.0 * math.sqrt(k_theta * armature) * 1.6, 6)

    # The thumb actuator must actually be able to deflect the beam: a position
    # servo delivers kp * error, so kp must exceed the spring rate it works
    # against, with margin for the contact reaction it pushes through.
    release_travel = math.radians(30.0)
    release_kp = round(k_theta * 4.0, 3)
    release_fmax = round(k_theta * release_travel * 4.0, 3)

    hw, hd = width / 2, depth / 2
    wall_top = height + wall
    hz = height / 2 + wall

    # Beam: on the inner face of the front wall, pointing up.
    beam_y = hd - wall - beam_t / 2
    beam_root_z = wall * 2 + height * 0.45
    beam_tip_z = beam_root_z + beam_l
    hook_local_z = beam_l - 0.0012
    beam_inner_y = beam_y - beam_t / 2
    hook_half_y = undercut / 2
    hook_y_local = -(beam_t / 2 + hook_half_y)
    hook_inner_y = beam_inner_y - undercut  # innermost face of the hook
    hook_half_z = 0.0008
    hook_global_z = beam_root_z + hook_local_z

    # Lid rib hangs down just inboard of the hook; its lip protrudes outward to
    # sit *under* the hook when closed. Every face is placed with an explicit
    # clearance so the assembled rest state has no overlap anywhere.
    clear = 0.0001
    rib_half_t = 0.0006
    rib_outer_y = hook_inner_y - clear
    rib_y = rib_outer_y - rib_half_t
    rib_h = (wall_top - hook_global_z) / 2 + 0.004

    lip_inner_y = rib_outer_y
    lip_outer_y = beam_inner_y - clear  # reaches under the hook, clear of the beam
    lip_half_y = max((lip_outer_y - lip_inner_y) / 2, 0.0002)
    lip_y = (lip_inner_y + lip_outer_y) / 2
    lip_half_z = 0.0009
    lip_z_global = (hook_global_z - hook_half_z) - 2 * clear - lip_half_z

    # Lid pivots at the rear on top of the wall, clear of it by the closing gap.
    lid_z = wall_top + lid_t / 2 + gap
    rib_local_z = lip_z_global - lid_z
    lip_local_z = rib_local_z

    xml = f"""<mujoco model="assy_latch">
  <compiler angle="degree"/>
  <option timestep="{dt}" gravity="0 0 -9.81" integrator="implicitfast" cone="elliptic"/>
  <visual><global offwidth="960" offheight="720"/></visual>
  <default>
    <geom rgba="0.72 0.74 0.78 1" friction="{mu} 0.005 0.0001" solref="0.002 1"/>
  </default>
  <worldbody>
    <light pos="0.25 -0.35 0.35" dir="-0.3 0.5 -1" diffuse="0.95 0.95 0.95"/>
    <camera name="iso" pos="0.26 -0.26 0.20" xyaxes="0.7 0.7 0 -0.35 0.35 0.87"/>
    <camera name="latch_closeup" pos="0.035 -0.02 {hook_global_z + 0.012:.5f}"
            xyaxes="0 1 0 -0.5 0 0.87"/>
    <camera name="section" pos="0.30 0 {height * 0.7:.5f}" xyaxes="0 1 0 0 0 1"/>
    <geom name="ground" type="plane" size="1 1 0.01" rgba="0.22 0.22 0.25 1"/>

    <body name="box_body" pos="0 0 0">
      <geom name="floor" type="box" size="{hw:.5f} {hd:.5f} {wall:.5f}" pos="0 0 {wall:.5f}"
            contype="1" conaffinity="1"/>
      <geom name="wall_left" type="box" size="{wall:.5f} {hd:.5f} {height / 2:.5f}"
            pos="{-hw:.5f} 0 {hz:.5f}" contype="1" conaffinity="1"/>
      <geom name="wall_right" type="box" size="{wall:.5f} {hd:.5f} {height / 2:.5f}"
            pos="{hw:.5f} 0 {hz:.5f}" contype="1" conaffinity="1"/>
      <geom name="wall_rear" type="box" size="{hw:.5f} {wall:.5f} {height / 2:.5f}"
            pos="0 {-hd:.5f} {hz:.5f}" contype="1" conaffinity="1"/>
      <geom name="wall_front" type="box" size="{hw:.5f} {wall:.5f} {height / 2:.5f}"
            pos="0 {hd:.5f} {hz:.5f}" contype="1" conaffinity="1"/>

      <body name="snap_beam" pos="0 {beam_y:.5f} {beam_root_z:.5f}">
        <joint name="beam_flex" type="hinge" axis="1 0 0" range="-35 2"
               stiffness="{k_theta:.5f}" damping="{damping:.6f}" armature="{armature:.3e}"
               springref="0"/>
        <geom name="beam" type="box"
              size="{beam_w / 2:.5f} {beam_t / 2:.5f} {beam_l / 2:.5f}"
              pos="0 0 {beam_l / 2:.5f}" mass="0.0004" rgba="0.30 0.62 0.85 1"
              contype="4" conaffinity="4"/>
        <geom name="hook" type="box"
              size="{beam_w / 2:.5f} {hook_half_y:.5f} 0.0008"
              pos="0 {hook_y_local:.5f} {hook_local_z:.5f}" mass="0.0001"
              rgba="0.95 0.55 0.15 1" contype="4" conaffinity="4"/>
      </body>
    </body>

    <body name="lid" pos="0 {-hd:.5f} {lid_z:.5f}">
      <joint name="lid_hinge" type="hinge" axis="1 0 0" range="-1 {open_deg}" damping="0.0015"/>
      <geom name="lid_plate" type="box" size="{hw:.5f} {hd:.5f} {lid_t / 2:.5f}"
            pos="0 {hd:.5f} 0" mass="0.05" contype="2" conaffinity="2"/>
      <geom name="lid_rib" type="box"
            size="{beam_w / 2:.5f} {rib_half_t:.5f} {rib_h:.5f}"
            pos="0 {rib_y + hd:.5f} {rib_local_z + rib_h - 0.001:.5f}" mass="0.003"
            rgba="0.55 0.78 0.55 1" contype="4" conaffinity="4"/>
      <geom name="lid_lip" type="box"
            size="{beam_w / 2:.5f} {lip_half_y:.5f} {lip_half_z:.5f}"
            pos="0 {lip_y + hd:.5f} {lip_local_z:.5f}" mass="0.001"
            rgba="0.35 0.68 0.35 1" contype="4" conaffinity="4"/>
    </body>
  </worldbody>

  <actuator>
    <position name="lid_drive" joint="lid_hinge" kp="0.5" ctrlrange="-1 {open_deg}"
              forcerange="-2.5 2.5"/>
    <position name="beam_release" joint="beam_flex" kp="{release_kp:.3f}" ctrlrange="-35 0"
              forcerange="-{release_fmax:.3f} {release_fmax:.3f}"/>
  </actuator>
</mujoco>
"""

    return ModelSpec(
        xml=xml,
        kind="latch",
        limitations=[
            "MuJoCo is rigid-body: the snap beam is a lumped torsional spring "
            f"(k = 3EI/L = {k_theta:.4f} N.m/rad), not a flexing beam",
            "contact timing, engagement sequence, and gross retention are represented; "
            "strain, stress, creep, and fatigue are NOT, and come from the analytical backend",
            f"beam armature {armature:.1e} kg.m2 is added for numerical integrability and "
            "exceeds the physical beam inertia; beam natural frequency is therefore not physical",
            "the hook/lip pair is an idealised rigid engagement; real face friction and edge "
            "rounding will shift the measured contact forces",
            "the lid plate is on a separate contact group so it does not rest on the walls; "
            "lid/wall interference is not evaluated by this model",
        ],
        joints={"output": "lid_hinge", "compliant": "beam_flex"},
        notes={
            "k_theta_nm_per_rad": round(k_theta, 5),
            "armature_kgm2": armature,
            "beam_length_mm": beam_l * 1000,
            "undercut_mm": undercut * 1000,
            "open_deg": open_deg,
            "timestep_s": dt,
        },
    )


def build_for(
    definition: CADReadyEngineeringDefinition, payload_kg: float = 1.0
) -> ModelSpec | None:
    """Pick a model from the roles present. Returns None if nothing moves."""
    if has_role(definition, "translating"):
        return build_lift(definition, payload_kg)
    if has_role(definition, "hinged"):
        return build_latch(definition)
    return None
