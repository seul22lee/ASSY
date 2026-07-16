"""M0 stretch: Mode V-B -- contact-only P-HINGE (spec 6.1).

No joints are declared. Box, lid and pin are three free 6-DoF bodies. The revolute DoF must
*emerge* from the pin sitting in the bore. This is the strict test of R1: V-A only proved
that a mechanism with a hand-declared hinge axis survives conversion; V-B asks whether the
converted **geometry itself** is a hinge. It is also the capability P-GEAR requires (spec
6.1: gears MUST use V-B, or meshing is assumed rather than demonstrated).

Pass criteria, fixed before the first run:
  1  pin retention   radial drift <= clearance + 0.1 mm; axial drift <= pin protrusion
  2  theta_max       >= 90 deg under follower force
  3  penetration     <= 0.2 mm away from the pin/bore interface;
                     at the interface, reported, and <= clearance is acceptable
  4  return          theta_final <= 5 deg on the reverse ramp
  5  multi-seed      5 seeds, >= 4 pass. Contact preset identical to M0 V-A (R5).

Collision strategy ladder (spec 6.2), recorded whether it works or not:
  (a) coacd  -- convex decomposition
  (b) sdf    -- UNAVAILABLE: MuJoCo's SDF plugin ships analytic shapes only
                (bolt/bowl/gear/nut/torus). There is no mesh-SDF, so a carved bore
                cannot be expressed. Recorded as a capability limit, not a failed attempt.
  (c) ring   -- primitive ring of convex wedges around the bore (collision_hint pathway)
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np

from p_hinge import (F_MAX, FPS, N_SEEDS, SEED_PASS, T_HOLD, T_RAMP, T_REV, THETA_TARGET,
                     g_conv)

T_COAST = 0.4  # s of zero drive after the lid is released at theta_target ("release" = coast)
T_END_VB = T_RAMP + T_COAST + T_REV + 1.0  # open, release/coast, close, settle

# Opening drive for V-B. F_MAX (0.15 N) was sized quasi-static for V-A's *damped* hinge joint;
# V-B's free bodies have no joint damping, so F_MAX accelerates the lid clean through
# theta_target and it coasts ~20 deg into its stop under its own momentum -- a dynamic impact,
# not the quasi-static press the protocol intends. Gravity's tip torque here is ~0.09 N, so
# F_OPEN just above it opens the lid slowly and it arrives at target near rest. This is a
# protocol (actuation) parameter, NOT the contact preset -- R5 is untouched, no M0 regression.
F_OPEN = 0.11  # N, quasi-static open
F_CLOSE = 0.15  # N, active close (= F_MAX)

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT


# --- bore patency: is the hole actually still there? ----------------------------------

def bore_patency(model, meta, manifest) -> tuple[bool, float, str]:
    """Sample the pin's own volume and ask MuJoCo how deep inside the box/lid collision
    geometry each sample lies. If the decomposition swallowed the bore, the pin's volume is
    solid plastic and this reports a large penetration.

    This is the check the overlay PNG cannot make: the bore is internal, so it is invisible
    from any camera angle. A swallowed bore looks *exactly* like a good one from outside.
    """
    ax = np.array(meta["hinge_axis_m"])
    half_len = manifest["derived"]["stack_w"] / 2 * 1e-3  # only where knuckles exist

    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    pin_body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "hinge_pin")

    # Cast rays outward from points *on the hinge axis* -- i.e. from inside the bore -- and
    # see how far they travel before striking collision geometry. That distance IS the bore
    # wall as the solver understands it. If the decomposition filled the hole, the rays hit
    # immediately and min_r collapses toward zero. Group 3 = collision geoms; the pin itself
    # is excluded so we measure the *hole*, not the thing sitting in it.
    geomgroup = np.array([0, 0, 0, 1, 0, 0], dtype=np.uint8)
    hit_r = []
    for x in np.linspace(-half_len * 0.9, half_len * 0.9, 25):
        for th in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            origin = np.array([ax[0] + x, ax[1], ax[2]])  # on the axis, inside the bore
            direction = np.array([0.0, np.cos(th), np.sin(th)])
            gid = np.zeros(1, dtype=np.int32)
            dist = mujoco.mj_ray(model, data, origin, direction, geomgroup, 1, pin_body, gid)
            if dist >= 0:
                hit_r.append(dist)
    if not hit_r:
        return False, 0.0, "no bore wall found by ray cast (geometry missing?)"

    min_r = float(np.min(hit_r)) * 1e3  # mm, from axis to nearest collision wall
    r_bore_mm = manifest["derived"]["bore_d"] / 2
    r_pin_mm = manifest["params"]["pin_d"] / 2
    nominal_cl = r_bore_mm - r_pin_mm  # the radial clearance the part was designed with
    effective_cl = min_r - r_pin_mm  # what the solver will actually let the pin use

    # "Does the pin fit" is too weak a bar. A bore whose clearance has been eaten away is a
    # seized hinge, and it would pass a naive patency test while being physically wrong. We
    # require the converted bore to preserve most of the designed clearance.
    open_bore = effective_cl >= 0.5 * nominal_cl
    note = (f"wall at {min_r:.3f} mm (bore {r_bore_mm:.3f}, pin {r_pin_mm:.3f}); "
            f"clearance {effective_cl:+.3f} of {nominal_cl:.3f} mm nominal "
            f"({100 * effective_cl / nominal_cl:.0f}% retained)")
    return open_bore, min_r, note


# --- observables ----------------------------------------------------------------------

def rel_angle_x(R_box: np.ndarray, R_lid: np.ndarray) -> float:
    """Lid rotation about the box's own hinge axis (+X), in rad. Measured relative to the
    box because in V-B the box is a free body and moves too."""
    R = R_box.T @ R_lid
    return float(np.arctan2(R[2, 1], R[1, 1]))


# Penetration is stratified by contact intent (D22). A single flat limit conflates a stray
# travel interference (a real defect) with the compliance of an intended load-bearing contact
# (the closed seat, the end stop). These are different physical events; they get different
# thresholds. Angle bands classify each lid<->box contact by the lid angle at that instant.
SEAT_BAND_DEG = 10.0   # |theta| <= this -> lid<->box contact is the closing seat
CLOSED_DEG = 3.0       # |theta| <= this -> lid is *fully* closed (for bounce detection)
STOP_BAND_DEG = 12.0   # within this of the design stop angle -> end-stop contact
SEAT_PEN_LIMIT = 0.3   # mm; intended closing-seat compliance (D22)
TRAVEL_PEN_LIMIT = 0.2  # mm; non-intended contact during travel = defect (D22)


@dataclass
class VbVerdict:
    theta_max_deg: float
    theta_final_deg: float
    pin_radial_max_mm: float
    pin_axial_max_mm: float
    pen_travel_mm: float       # (i) non-intended contact during travel -> defect
    pen_seat_mm: float         # (ii) intended closing-seat contact
    pen_interface_mm: float    # (ii) intended pin/bore interface
    bounce_open_deg: float     # max re-opening after first seating -> "settles closed"
    box_slid_mm: float
    diverged: bool

    def criteria(self, clearance, protrusion) -> dict:
        rad_lim = clearance + 0.1
        return {
            "1 pin retention: radial drift <= clearance+0.1": {
                "value": round(self.pin_radial_max_mm, 4), "threshold": round(rad_lim, 3),
                "pass": bool(self.pin_radial_max_mm <= rad_lim and not self.diverged)},
            "1 pin retention: axial drift <= protrusion": {
                "value": round(self.pin_axial_max_mm, 4), "threshold": round(protrusion, 3),
                "pass": bool(self.pin_axial_max_mm <= protrusion and not self.diverged)},
            "2 theta_max >= 90 deg": {
                "value": round(self.theta_max_deg, 2), "threshold": 90.0,
                "pass": bool(self.theta_max_deg >= 90.0 and not self.diverged)},
            "3 travel interference (non-intended) <= 0.2 mm": {
                "value": round(self.pen_travel_mm, 4), "threshold": TRAVEL_PEN_LIMIT,
                "pass": bool(self.pen_travel_mm <= TRAVEL_PEN_LIMIT and not self.diverged)},
            "3 pin/bore interface <= clearance": {
                "value": round(self.pen_interface_mm, 4), "threshold": round(clearance, 3),
                "pass": bool(self.pen_interface_mm <= clearance and not self.diverged)},
            # D22 (your ruling): "settles closed" is the hard criterion; closing-seat impact
            # *severity* is an observable, not a gate. A gravity-driven seat impact on an
            # over-centre lid is expected physics -- it is flagged, not failed, until a spec
            # declares an impact/durability requirement.
            "4 settles closed: theta_final <= 5 deg, no bounce-open": {
                "value": round(max(self.theta_final_deg, self.bounce_open_deg), 2),
                "threshold": 5.0,
                "pass": bool(self.theta_final_deg <= 5.0 and self.bounce_open_deg <= 5.0
                             and not self.diverged)},
        }

    def passed(self, clearance, protrusion) -> bool:
        return all(c["pass"] for c in self.criteria(clearance, protrusion).values())


# --- per-frame HUD (D15): burn the scored values into the video, so the motion on screen is
# provably the scored run. The numbers here are the SAME per-step locals the verdict is built
# from -- not a re-derivation. ------------------------------------------------------------
_LETTERS = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    " ": ["00000"] * 7,
}
_DIGITS = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00110", "00110"],
}
_FONT = {**_LETTERS, **_DIGITS}


def _hud(img, lines, colors=None):
    """Draw stacked text lines top-left. colors: per-line (r,g,b) or None -> white."""
    img = img.copy()
    s = 2  # pixel scale
    y = 6
    band_h = len(lines) * (7 * s + 3) + 6
    img[:band_h, :330] = (img[:band_h, :330] * 0.25).astype(img.dtype)
    for li, text in enumerate(lines):
        col = (colors[li] if colors else (255, 255, 255))
        x = 8
        for ch in text.upper():
            g = _FONT.get(ch, _FONT[" "])
            for ry, row in enumerate(g):
                for rx, on in enumerate(row):
                    if on == "1":
                        yy, xx = y + ry * s, x + rx * s
                        img[yy:yy + s, xx:xx + s] = col
            x += (len(g[0]) + 1) * s
        y += 7 * s + 3
    return img


def classify_lidbox(theta_deg: float, stop_angle_deg: float) -> str:
    """Which intended contact is the lid<->box pair, given the lid angle? (D22)"""
    if abs(theta_deg) <= SEAT_BAND_DEG:
        return "seat"
    if np.isfinite(stop_angle_deg) and abs(theta_deg - stop_angle_deg) <= STOP_BAND_DEG:
        return "stop"
    return "travel"


# --- overtravel/slam probe (OBSERVABLE, never a criterion) ----------------------------
# The principle (D19): verification answers the questions the behaviour spec asked. Everything
# else the simulation reveals is recorded as an observable -- never silently discarded, and
# never silently promoted to a pass/fail item. The Easy anchor's behaviour spec asks for
# "opens >= 90 deg and returns closed". It asks for neither an angular limit nor stop-impact
# survival. So the probe -- a deliberate continued push after opening -- is run as a SEPARATE
# pass, so it cannot corrupt the scored open/close dynamics (an earlier version inlined it,
# and for the no-stop lid the fold-to-220 wrecked the subsequent close phase). What the probe
# reveals (fold-flat overtravel; stop-impact depth and force) is measured, flagged, handed up.
T_PROBE = 0.6  # s of continued push
PROBE_SCALE = 0.5  # F_max/2
OVERTRAVEL_FLAG_DEG = 150.0


def probe_overtravel(model, meta, seed=0):
    """Separate observable pass: open the lid, then keep pushing. Returns the overtravel angle
    and, if the lid meets a hard stop, the impact depth and force. Never scored (D19)."""
    d = mujoco.MjData(model)
    rng = np.random.default_rng(seed)
    B = lambda n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)
    S = lambda n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n)
    box, lid = B("box_shell"), B("lid_panel")
    s_tip = S("lid_tip")
    mujoco.mj_forward(model, d)

    theta_prev, turns, t_open = 0.0, 0.0, None
    ot, contact, pen_max, force_max = -1e9, False, 0.0, 0.0
    while d.time < T_RAMP + T_HOLD + T_PROBE:
        if t_open is None:
            F = min(F_MAX, F_MAX * d.time / T_RAMP)
        else:
            F = F_MAX * PROBE_SCALE  # keep pushing past open -> overtravel / into the stop
        d.qfrc_applied[:] = 0.0
        mujoco.mj_applyFT(model, d, d.xmat[lid].reshape(3, 3) @ np.array([0., 0., F]),
                          np.zeros(3), d.site_xpos[s_tip], lid, d.qfrc_applied)
        mujoco.mj_step(model, d)
        if not np.all(np.isfinite(d.qpos)):
            break
        raw = rel_angle_x(d.xmat[box].reshape(3, 3), d.xmat[lid].reshape(3, 3))
        if raw - theta_prev > np.pi: turns -= 2 * np.pi
        elif raw - theta_prev < -np.pi: turns += 2 * np.pi
        theta_prev, theta = raw, raw + turns
        if t_open is None and theta >= THETA_TARGET:
            t_open = d.time
        if t_open is not None:
            ot = max(ot, theta)
            for i in range(d.ncon):
                c = d.contact[i]
                if {model.geom_bodyid[c.geom1], model.geom_bodyid[c.geom2]} == {box, lid}:
                    contact = True
                    pen_max = max(pen_max, max(0.0, -float(c.dist)) * 1e3)
                    f6 = np.zeros(6); mujoco.mj_contactForce(model, d, i, f6)
                    force_max = max(force_max, float(abs(f6[0])))
    ot_deg = float(np.rad2deg(ot)) if ot > -1e8 else None
    return {
        "theta_overtravel_max_deg": None if ot_deg is None else round(ot_deg, 2),
        "hard_stop_contact": bool(contact),
        "stop_impact_penetration_mm": round(pen_max, 4),
        "stop_impact_force_N": round(force_max, 3),
        "probe": f"open, then {PROBE_SCALE:g}*F_max sustained for {T_PROBE:g}s",
        "flag": ("no angular limit -- lid free to fold flat"
                 if ot_deg is not None and ot_deg > OVERTRAVEL_FLAG_DEG else None),
        "note": ("Design information for the intent layer, NOT a pass/fail item (D19): the "
                 "Easy anchor behaviour spec asks for >=90 deg opening + return to closed, and "
                 "requests neither an angular limit nor stop-impact survival. A future "
                 "behaviour spec may promote either to a criterion."),
    }


def run_vb(model, meta, seed=0, record=False, dt=None, stop_angle_deg=float("inf"),
           overlay=False):
    if dt is not None:
        model.opt.timestep = dt
    d = mujoco.MjData(model)
    rng = np.random.default_rng(seed)

    B = lambda n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n)
    S = lambda n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, n)
    box, lid, pin = B("box_shell"), B("lid_panel"), B("hinge_pin")
    s_tip, s_axis, s_pin = S("lid_tip"), S("box_axis"), S("pin_center")

    mujoco.mj_forward(model, d)
    # Seeds perturb the initial pose within the joint's own clearance -- probing robustness,
    # not re-tuning the model (R5).
    for b in (lid, pin):
        adr = model.jnt_qposadr[model.body_jntadr[b]]
        d.qpos[adr:adr + 3] += rng.uniform(-2e-5, 2e-5, 3)
    mujoco.mj_forward(model, d)

    box0 = d.xpos[box].copy()
    R_box0 = d.xmat[box].reshape(3, 3).copy()
    box_diag = float(model.stat.extent)  # MuJoCo's own model scale (m); the sanity-bound unit

    renderer = mujoco.Renderer(model, 480, 640) if record else None
    cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, "iso")

    ts, th, F_, pr, pa = [], [], [], [], []
    p_travel, p_seat, p_stop, p_iface = [], [], [], []  # stratified penetration (D22)
    frames, next_frame, diverged = [], 0.0, False
    t_open: float | None = None
    theta_prev, turns = 0.0, 0.0
    seated_after_open = False  # True once the lid, having opened, returns to the seat band
    bounce_open = 0.0          # max re-opening after that -> "settles closed, no bounce-open"

    while d.time < T_END_VB:
        # Scored protocol (D16 + D19 release amendment). Four phases:
        #   open    ramp 0 -> F_max until the lid is observed at theta_target
        #   coast   RELEASE the drive (F=0) -- the literal meaning of "release at theta_target".
        #           No force is held into a stop or into the over-centre fold. The lid coasts on
        #           its own momentum; whatever it does here it does un-driven.
        #   close   ramp 0 -> -F_max to actively pull it shut
        #   settle  release again (F=0) so the closed assembly is not shoved across the floor
        # The deliberate overtravel/slam probe is a SEPARATE pass (probe_overtravel); it is never
        # in this scored timeline, so it cannot corrupt the open/close dynamics.
        theta_now_deg = np.rad2deg(theta_prev + turns) if ts else 0.0
        if t_open is None:
            F = min(F_OPEN, F_OPEN * d.time / T_RAMP)
        elif d.time < t_open + T_COAST:
            F = 0.0
        elif d.time < t_open + T_COAST + T_REV and theta_now_deg > 90.0:
            # Pull the lid back up-and-over toward 90 deg. Release once it re-crosses the
            # over-centre point -- past 90 deg on the way down, gravity seats it on its own.
            # Driving through the seat (gravity + F_CLOSE) is what made the closing slam hard.
            F = -F_CLOSE * (d.time - t_open - T_COAST) / T_REV
        else:
            F = 0.0
        f_world = d.xmat[lid].reshape(3, 3) @ np.array([0.0, 0.0, F])
        d.qfrc_applied[:] = 0.0
        mujoco.mj_applyFT(model, d, f_world, np.zeros(3), d.site_xpos[s_tip], lid,
                          d.qfrc_applied)
        mujoco.mj_step(model, d)

        # A blow-up does not always produce NaN -- it can produce large finite garbage (a
        # seed once put the pin 405 metres from its bore, every value finite). Bound the state
        # explicitly, scaled to the model: the pin may not travel past 10x the model extent.
        if (not np.all(np.isfinite(d.qpos))
                or float(np.linalg.norm(d.xpos[pin] - d.xpos[box])) > 10 * box_diag
                or float(np.abs(d.qvel).max()) > 1e3):
            diverged = True
            break

        R_box = d.xmat[box].reshape(3, 3)
        # Unwrap. atan2 wraps at +-180 deg; the continuous angle is the only honest observable.
        raw = rel_angle_x(R_box, d.xmat[lid].reshape(3, 3))
        if raw - theta_prev > np.pi:
            turns -= 2 * np.pi
        elif raw - theta_prev < -np.pi:
            turns += 2 * np.pi
        theta_prev = raw
        theta = raw + turns

        if t_open is None and theta >= THETA_TARGET:
            t_open = d.time

        # Pin drift, expressed in the *box's* frame: the pin must stay in the box's bore,
        # and the box itself is free to move.
        delta = R_box.T @ (d.site_xpos[s_pin] - d.site_xpos[s_axis])
        radial = float(np.hypot(delta[1], delta[2])) * 1e3
        axial = float(abs(delta[0])) * 1e3

        # Penetration, stratified by contact intent (D22). A lid<->box contact is classified
        # by the lid angle at this instant: seating closed, at the end stop, or mid-travel.
        travel = seat = stop = iface = 0.0
        theta_deg = np.rad2deg(theta)
        for i in range(d.ncon):
            c = d.contact[i]
            bodies = {model.geom_bodyid[c.geom1], model.geom_bodyid[c.geom2]}
            pen = max(0.0, -float(c.dist))
            if pin in bodies:
                iface = max(iface, pen)            # (ii) pin/bore interface
            elif bodies == {box, lid}:
                kind = classify_lidbox(theta_deg, stop_angle_deg)
                if kind == "seat":
                    seat = max(seat, pen)          # (ii) intended closing seat
                elif kind == "stop":
                    stop = max(stop, pen)          # (ii) intended end stop (observable)
                else:
                    travel = max(travel, pen)      # (i) non-intended travel interference
            # box<->floor and lid<->floor are handled below as observables, not scored here

        # "Settles closed, no bounce-open": the lid starts closed, so we only start watching
        # for bounce once it has *opened* (t_open set) and then *returned to fully closed*
        # (<= CLOSED_DEG, tighter than the 10 deg contact band so entering the band is not
        # mistaken for a bounce). Any re-opening after that is a genuine bounce.
        if t_open is not None and theta_deg <= CLOSED_DEG:
            seated_after_open = True
        if seated_after_open:
            bounce_open = max(bounce_open, theta_deg)

        ts.append(d.time); th.append(theta); F_.append(F)
        pr.append(radial); pa.append(axial)
        p_travel.append(travel * 1e3); p_seat.append(seat * 1e3)
        p_stop.append(stop * 1e3); p_iface.append(iface * 1e3)

        if record and d.time >= next_frame:
            renderer.update_scene(d, camera=cam)
            frame = renderer.render()
            if overlay:
                # These are the exact per-step values feeding the verdict (D15). Pen shown is
                # the max over the three intent buckets at this instant; travel in red when
                # non-zero (a real defect), seat/bore otherwise.
                pen_now = max(travel, seat, iface) * 1e3
                frame = _hud(frame, [
                    f"T {d.time:4.2f}S",
                    f"ANGLE {theta_deg:5.0f}",
                    f"PIN R {radial:4.2f} A {axial:4.2f}",
                    f"PEN {pen_now:4.2f} TRAV {travel*1e3:4.2f}",
                ], colors=[(220, 220, 220), (120, 200, 255), (140, 255, 160),
                           (255, 150, 90) if travel > 1e-4 else (255, 200, 120)])
            frames.append(frame)
            next_frame += 1.0 / FPS

    if renderer:
        renderer.close()

    n_tail = max(1, int(0.1 / model.opt.timestep))
    theta = np.array(th)
    v = VbVerdict(
        theta_max_deg=float(np.rad2deg(theta.max())) if len(theta) else 0.0,
        theta_final_deg=float(np.rad2deg(np.abs(theta[-n_tail:]).mean())) if len(theta) else 180.0,
        pin_radial_max_mm=float(max(pr)) if pr else 999.0,
        pin_axial_max_mm=float(max(pa)) if pa else 999.0,
        pen_travel_mm=float(max(p_travel)) if p_travel else 0.0,
        pen_seat_mm=float(max(p_seat)) if p_seat else 0.0,
        pen_interface_mm=float(max(p_iface)) if p_iface else 0.0,
        bounce_open_deg=float(bounce_open),
        box_slid_mm=float(np.linalg.norm(d.xpos[box] - box0) * 1e3),
        diverged=diverged,
    )
    series = {"t": ts, "theta_deg": list(np.rad2deg(theta)), "force_N": F_,
              "pin_radial_mm": pr, "pin_axial_mm": pa,
              "pen_travel_mm": p_travel, "pen_seat_mm": p_seat,
              "pen_stop_mm": p_stop, "pen_interface_mm": p_iface}
    return v, series, frames


def plot(series, v: VbVerdict, meta, path: Path, title: str, ok: bool):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cl = meta["clearance_mm"]
    fig, ax = plt.subplots(4, 1, figsize=(8.5, 9.5), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1, 2, 1.6]})
    t = series["t"]

    ax[0].plot(t, series["theta_deg"], lw=2, color="#2b6cb0")
    ax[0].axhline(90, ls="--", c="#c53030", lw=1)
    ax[0].axhspan(-5, 5, color="#bee3f8", alpha=.6)
    ax[0].set_ylabel("lid angle theta (deg)\n(relative to box)")
    ax[0].set_title(f"{title}   [{'PASS' if ok else 'FAIL'}]   theta_max={v.theta_max_deg:.1f} deg, "
                    f"pin radial={v.pin_radial_max_mm:.3f} mm, axial={v.pin_axial_max_mm:.3f} mm",
                    color="#22543d" if ok else "#742a2a", fontsize=10)
    ax[0].grid(alpha=.25)

    ax[1].plot(t, series["force_N"], lw=1.5, color="#805ad5")
    ax[1].axhline(0, c="k", lw=.5); ax[1].set_ylabel("F (N)"); ax[1].grid(alpha=.25)

    ax[2].plot(t, series["pin_radial_mm"], lw=1.6, color="#2f855a", label="radial drift")
    ax[2].plot(t, series["pin_axial_mm"], lw=1.6, color="#b7791f", label="axial drift")
    ax[2].axhline(cl + 0.1, ls="--", c="#c53030", lw=1, label=f"radial limit {cl+0.1:.2f} mm")
    ax[2].axhline(meta["pin_protrusion_mm"], ls=":", c="#c53030", lw=1,
                  label=f"axial limit {meta['pin_protrusion_mm']:.1f} mm")
    ax[2].set_ylabel("pin drift from\nbore axis (mm)")
    ax[2].legend(fontsize=7, loc="upper left"); ax[2].grid(alpha=.25)

    # Penetration stratified by contact intent (D22).
    ax[3].plot(t, series["pen_travel_mm"], lw=1.5, color="#c53030", label="travel (defect)")
    ax[3].plot(t, series["pen_seat_mm"], lw=1.4, color="#dd6b20", label="closing seat")
    ax[3].plot(t, series["pen_interface_mm"], lw=1.4, color="#3182ce", label="pin/bore")
    ax[3].plot(t, series.get("pen_stop_mm", []), lw=1.0, color="#718096", ls=":",
               label="end stop (obs)")
    ax[3].axhline(0.2, ls="--", c="#c53030", lw=0.8, label="travel limit 0.2")
    ax[3].axhline(0.3, ls="--", c="#dd6b20", lw=0.8, label="seat/clearance 0.3")
    ax[3].set_ylabel("penetration (mm)\nby contact intent"); ax[3].set_xlabel("t (s)")
    ax[3].legend(fontsize=6.5, loc="upper right", ncol=2); ax[3].grid(alpha=.25)

    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main() -> None:
    strategy = sys.argv[1] if len(sys.argv) > 1 else "ring"
    tag = f"V-B_{strategy}"
    model = mujoco.MjModel.from_xml_path(str(OUT / f"hinge_{tag}.xml"))
    meta = json.loads((OUT / f"hinge_{tag}_meta.json").read_text())
    manifest = json.loads((OUT / "manifest.json").read_text())
    cl, protr = meta["clearance_mm"], meta["pin_protrusion_mm"]
    stop_angle = float(manifest["derived"].get("stop_angle_deg", float("inf")))

    print(f"\n=== M0 stretch  V-B  strategy={strategy} ===")
    print(f"    collision: " + ", ".join(f"{k}={v}" for k, v in meta["strategies"].items()))
    print(f"    end stop: " + ("none (lid free to fold flat)" if not np.isfinite(stop_angle)
                               else f"{stop_angle:.1f} deg"))

    open_bore, min_r, note = bore_patency(model, meta, manifest)
    print(f"\n  BORE PATENCY   {'OPEN' if open_bore else 'SWALLOWED'}   {note}")

    gok, _ = g_conv(model)

    report = {"mode": "V-B", "strategy": strategy,
              "contact_preset": meta["contact_preset"],
              "collision": meta["strategies"],
              "bore_patency": {"open": bool(open_bore), "min_wall_r_mm": min_r, "note": note},
              "g_conv": bool(gok)}

    # Patency is a *diagnostic*, not the gate: a bore with degraded clearance still tells us
    # something (does a seized-up hinge turn?), so we simulate anyway and let the criteria
    # speak. Only G-CONV can stop the run -- if the model explodes it cannot answer anything.
    if not gok:
        print(f"\n  --> {strategy}: G-CONV FAILED. Not simulating; the converted model is "
              f"broken, so any P-HINGE number it produced would be meaningless.")
        report["verdict"] = False
        report["failure"] = ("bore swallowed by the collision approximation -> pin starts "
                             "embedded in solid plastic" if not open_bore else "G-CONV failed")
        (OUT / f"t2_verdict_{tag}.json").write_text(json.dumps(report, indent=2))
        return
    if not open_bore:
        print("  (!) clearance badly degraded -- simulating anyway to record the failure mode")

    print(f"\n  P-HINGE (contact-only, follower force)  {N_SEEDS} seeds")
    verdicts = []
    for seed in range(N_SEEDS):
        rec = seed == 0
        v, series, frames = run_vb(model, meta, seed, record=rec, stop_angle_deg=stop_angle)
        if v.diverged:  # spec 6.4: one automatic retry at half the timestep
            print(f"    seed {seed}: diverged at dt=0.5 ms -> retry at 0.25 ms")
            v, series, frames = run_vb(model, meta, seed, record=rec, dt=0.00025,
                                       stop_angle_deg=stop_angle)
        ok = v.passed(cl, protr)
        verdicts.append((v, ok))
        if rec:
            plot(series, v, meta, OUT / f"t2_{tag}.png", f"P-HINGE / V-B / {strategy}", ok)
            if frames:
                imageio.mimsave(OUT / f"t2_{tag}.mp4", frames, fps=FPS)
            cols = ("t", "theta_deg", "force_N", "pin_radial_mm", "pin_axial_mm",
                    "pen_travel_mm", "pen_seat_mm", "pen_stop_mm", "pen_interface_mm")
            (OUT / f"t2_{tag}.csv").write_text(
                ",".join(cols) + "\n"
                + "\n".join(",".join(f"{series[k][i]:.6f}" for k in cols)
                            for i in range(len(series["t"]))))
        print(f"    seed {seed}: {'PASS' if ok else 'FAIL'}  theta_max {v.theta_max_deg:6.1f}  "
              f"theta_fin {v.theta_final_deg:5.1f}  bounce {v.bounce_open_deg:4.1f}  "
              f"pin_rad {v.pin_radial_max_mm:.3f}  pin_ax {v.pin_axial_max_mm:.3f}  "
              f"pen[trav/seat/bore] {v.pen_travel_mm:.3f}/{v.pen_seat_mm:.3f}/"
              f"{v.pen_interface_mm:.3f}  box {v.box_slid_mm:.1f}mm"
              + ("  DIVERGED" if v.diverged else ""))

    n_pass = sum(ok for _, ok in verdicts)
    verdict = n_pass >= SEED_PASS
    print(f"    -> {n_pass}/{N_SEEDS} seeds pass  =>  {'PASS' if verdict else 'FAIL'}")
    for name, c in verdicts[0][0].criteria(cl, protr).items():
        print(f"       {'ok  ' if c['pass'] else 'FAIL'} {name:<48s} {c['value']} "
              f"(limit {c['threshold']})")

    # Observables (D19): separate probe pass, never scored.
    ot = probe_overtravel(model, meta, seed=0)
    box_disp = round(sum(v.box_slid_mm for v, _ in verdicts) / len(verdicts), 2)
    seat_pen = round(max(v.pen_seat_mm for v, _ in verdicts), 4)
    # D22 (amended): seat-impact MAGNITUDE is an observable, flagged if > clearance scale.
    # In a soft-constraint engine this depth measures the frozen quasi-static preset's
    # compliance (D17), not the geometry -- so it is instrumented, flagged, never gated.
    seat = {
        "closing_seat_penetration_mm_max": seat_pen,
        "flag_threshold_mm": cl,
        "flag": (f"seat impact {seat_pen} mm > clearance {cl} mm -- dynamic gravity slam; "
                 "depth reflects the frozen quasi-static preset (D17), not the geometry. "
                 "If a spec declares an impact/durability requirement, instrument peak "
                 "contact force / impulse with an impact-validated preset, not depth."
                 if seat_pen > cl else None),
    }
    observables = {"overtravel_check": ot, "closing_seat_impact": seat,
                   "box_displacement_mm_mean": box_disp}
    print(f"\n  OBSERVABLES (recorded, not scored)")
    print(f"    overtravel: theta_max = {ot['theta_overtravel_max_deg']} deg, "
          f"stop_impact = {ot['stop_impact_penetration_mm']} mm / {ot['stop_impact_force_N']} N")
    print(f"    closing_seat_impact: {seat_pen} mm (flag > {cl} mm)")
    for f in (ot["flag"], seat["flag"]):
        if f:
            print(f"    FLAG: {f}")

    report.update({"seeds_passed": n_pass, "n_seeds": N_SEEDS, "verdict": verdict,
                   "criteria_seed0": verdicts[0][0].criteria(cl, protr),
                   "observables": observables,
                   "per_seed": [asdict(v) for v, _ in verdicts]})
    (OUT / f"t2_verdict_{tag}.json").write_text(json.dumps(report, indent=2))
    print(f"\nwrote t2_verdict_{tag}.json")


def relabel(strategy="ring", seed=0):
    """Regenerate a clearly-named, HUD-overlaid video for the current M0_VARIANT + seed, and
    print the 'fling' report (max angular-speed instant) straight from the scored series --
    so the video and the numbers are provably the same run (D15)."""
    tag = f"V-B_{strategy}"
    model = mujoco.MjModel.from_xml_path(str(OUT / f"hinge_{tag}.xml"))
    meta = json.loads((OUT / f"hinge_{tag}_meta.json").read_text())
    manifest = json.loads((OUT / "manifest.json").read_text())
    stop_angle = float(manifest["derived"].get("stop_angle_deg", float("inf")))
    cl, protr = meta["clearance_mm"], meta["pin_protrusion_mm"]

    v, series, frames = run_vb(model, meta, seed=seed, record=True, overlay=True,
                               stop_angle_deg=stop_angle)
    out_mp4 = OUT / f"t2_VB_{strategy}_{VARIANT}_seed{seed}.mp4"
    imageio.mimsave(out_mp4, frames, fps=FPS)

    # Fling = instant of peak angular speed, computed from the scored theta(t). Everything
    # reported here is read out of `series`, which is what the verdict was built from.
    t = np.array(series["t"]); th = np.array(series["theta_deg"])
    dt = np.diff(t); omega = np.abs(np.diff(th)) / np.where(dt > 0, dt, 1e9)  # deg/s
    k = int(np.argmax(omega))
    ok = v.passed(cl, protr)

    print(f"\n=== {VARIANT} / {strategy} / seed{seed}  ->  {out_mp4.name} ===")
    print(f"  scored verdict: {'PASS' if ok else 'FAIL'}   "
          f"(this is seed {seed}; the multi-seed verdict is in t2_verdict_{tag}.json)")
    print(f"  end stop: " + ("none -- lid free to fold flat" if not np.isfinite(stop_angle)
                             else f"{stop_angle:.1f} deg"))
    print(f"  FLING (peak angular speed {omega[k]:.0f} deg/s) at t={t[k]:.3f}s:")
    print(f"     theta          = {th[k]:7.1f} deg")
    print(f"     pin drift      = radial {series['pin_radial_mm'][k]:.3f} mm, "
          f"axial {series['pin_axial_mm'][k]:.3f} mm")
    print(f"     penetration    = travel {series['pen_travel_mm'][k]:.3f} | "
          f"seat {series['pen_seat_mm'][k]:.3f} | bore {series['pen_interface_mm'][k]:.3f} mm")
    print(f"  whole-run peaks (the scored maxima):")
    print(f"     theta_max      = {v.theta_max_deg:.1f} deg   theta_final = {v.theta_final_deg:.1f} deg")
    print(f"     pin radial max = {v.pin_radial_max_mm:.3f} mm   (limit {cl+0.1:.2f})")
    print(f"     travel pen max = {v.pen_travel_mm:.3f} mm   (limit 0.20, defect gate)")
    print(f"     seat pen max   = {v.pen_seat_mm:.3f} mm   (OBSERVABLE, flag>{cl})")
    interp = ("EXPECTED: no-stop lid folds flat past 180 deg -- the documented defect; pin "
              "retention is what fails it, not the fold itself."
              if not np.isfinite(stop_angle) else
              "EXPECTED: lid opens to the ~109 deg stop, no absurd excursion; box welded (D23).")
    print(f"  {interp}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "relabel":
        relabel(sys.argv[2] if len(sys.argv) > 2 else "ring",
                int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    else:
        main()
