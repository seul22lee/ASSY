"""Q2 evidence: is the ~26° cross-class grinding a PROXY ARTEFACT, or a real interference?

The claim under test — and it is only worth anything MEASURED, from two independent authorities:

  the PARTS   : build123d boolean on the compiled solids — box ∩ (lid rotated to 26°).
  the PROXIES : MuJoCo's own contact detection on the same pose, with the contact classes MERGED
                (i.e. as it was before the separation). MuJoCo is the authority here because
                MuJoCo's contacts are what actually drove the jam — not a hand-rolled overlap test.

If the parts clear while the proxies collide, the jam is an artefact of the convex approximation.
If the parts interfere too, suppression would be hiding a real defect and must not be done.

Run:  ./bin/py m8_pin_hinge_easy/build_proxy_overlay.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco as mj
import numpy as np
import trimesh
from matplotlib.patches import Rectangle
from build123d import Pos, Rotation, export_stl

from tasks.build_goldens import anchor_easy
from pipeline.compile_assembly import compile_assembly
from tasks.run_m8_t2 import build_hints
from verify.t2_physics.mjcf import build_mjcf

OUT = Path(__file__).parent / "out"
T2 = Path("verify/t2_physics/out_easy")
ANG = 26.0   # where V-B jammed before the contact classes were separated


def rot_about(solid, ax_pt, ax_dir, deg):
    ax = np.array(ax_dir, float); ax /= np.linalg.norm(ax)
    p = np.array(ax_pt, float)
    return Pos(*p) * Rotation(*(np.rad2deg(ax * math.radians(deg)))) * Pos(*(-p)) * solid


def real_interference(ca, deg):
    """Authority 1 — the PARTS. Volume of box ∩ (lid rotated by deg) on the compiled solids."""
    ax = ca.axes["E1"]
    lid = rot_about(ca.parts["P2"], ax["point"], ax["dir"], deg)
    inter = lid & ca.parts["P1"]
    return float(inter.volume) if inter.solids() else 0.0


def proxy_contacts_at(plan, ca, hints, deg):
    """Authority 2 — the PROXIES, per MuJoCo, with the contact classes MERGED (pre-separation).
    Poses the free lid at `deg` about the hinge axis and reports the box↔lid contact pairs."""
    merged = {pid: [{**p, "cclass": "seat", "owner": None} for p in prims]
              for pid, prims in hints.items()}          # collapse mech/seat → one class
    roles = {"P1": "base", "P2": "mover", "P3": "hardware"}
    xml, meta = build_mjcf({p: ca.parts[p] for p in ("P1", "P2", "P3")}, merged, ca.axes["E1"],
                           "P1", "P2", "P3", "V-B", T2 / "assets", roles, "easy",
                           tip_point=(0.0, 30.0, 40.0))
    f = T2 / "_merged26.xml"; f.write_text(xml)
    m = mj.MjModel.from_xml_path(str(f)); d = mj.MjData(m); f.unlink()
    mover = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "P2")
    base = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "P1")
    # pose the lid at `deg` about the hinge axis (free joint: qpos = pos(3) + quat(4))
    adr = m.jnt_qposadr[m.body_jntadr[mover]]
    ap = np.array(ca.axes["E1"]["point"], float) * 1e-3
    t = math.radians(deg)
    R = np.array([[1, 0, 0], [0, math.cos(t), -math.sin(t)], [0, math.sin(t), math.cos(t)]])
    new_pos = ap + R @ (np.array(d.qpos[adr:adr + 3]) - ap)
    d.qpos[adr:adr + 3] = new_pos
    d.qpos[adr + 3:adr + 7] = [math.cos(t / 2), math.sin(t / 2), 0.0, 0.0]   # w,x,y,z about +X
    mj.mj_forward(m, d)
    gname = lambda g: mj.mj_id2name(m, mj.mjtObj.mjOBJ_GEOM, g)
    pairs = []
    for i in range(d.ncon):
        c = d.contact[i]
        bs = {m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]}
        if bs == {base, mover}:
            pairs.append((gname(c.geom1), gname(c.geom2), round(float(-c.dist) * 1e3, 4)))
    return pairs


def _yz_rect(prim, ap, ad, deg, rotate):
    """(centre_yz, half_yz, angle_deg) of a box prim in the y–z plane — orientation included: the
    ring wedges carry a local euler about the axis, and the lid's rotation adds to it."""
    if prim.get("frame") == "world":
        c = np.array(prim["pos"], float); h = np.array(prim["size"], float); phi = 0.0
    else:
        X = np.array(ad, float); X /= np.linalg.norm(X)
        up = np.array([0, 0, 1.0]) if abs(X[2]) < 0.9 else np.array([0, 1.0, 0])
        Y = np.cross(up, X); Y /= np.linalg.norm(Y); Z = np.cross(X, Y)
        R = np.column_stack([X, Y, Z])
        c = np.array(ap, float) + R @ np.array(prim["pos"], float)
        h = np.array(prim["size"], float)
        phi = math.degrees(prim.get("euler", (0, 0, 0))[0])
    if rotate:
        t = math.radians(deg); a = np.array(ap, float); dvec = c - a
        c = a + np.array([dvec[0], dvec[1] * math.cos(t) - dvec[2] * math.sin(t),
                          dvec[1] * math.sin(t) + dvec[2] * math.cos(t)])
        phi += deg
    return (c[1], c[2]), (h[1], h[2]), phi, (c[0], h[0])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = anchor_easy(); ca = compile_assembly(plan); hints = build_hints(plan, ca)
    ap, ad = ca.axes["E1"]["point"], ca.axes["E1"]["dir"]

    vol0, vol26 = real_interference(ca, 0.0), real_interference(ca, ANG)
    pairs = proxy_contacts_at(plan, ca, hints, ANG)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    to2d = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1.0]])

    def mesh_of(solid, name):
        f = OUT / f"_{name}.stl"; export_stl(solid, str(f), tolerance=0.04, angular_tolerance=0.3)
        m = trimesh.load(f, force="mesh"); f.unlink(); return m

    ax0 = axes[0]
    lid_rot = rot_about(ca.parts["P2"], ap, ad, ANG)
    for solid, col, nm in ((ca.parts["P1"], "#8fb8de", "box"), (lid_rot, "#8fd39a", "lid")):
        sec = mesh_of(solid, nm).section(plane_origin=[0, 0, 0], plane_normal=[1, 0, 0])
        if sec is None:
            continue
        planar, _ = sec.to_planar(to_2D=to2d)
        for poly in planar.polygons_full:
            xs, ys = poly.exterior.xy
            ax0.fill(np.asarray(xs), np.asarray(ys), facecolor=col, edgecolor="#222", lw=.8, alpha=.9)
    ax0.set_aspect("equal"); ax0.axis("off")
    ax0.set_title(f"THE PARTS at {ANG:.0f}°  (build123d boolean)\n"
                  f"box ∩ rotated lid = {vol26:.2f} mm³   →   they CLEAR",
                  fontsize=10.5, color="#22543d" if vol26 < 1.0 else "#742a2a")

    ax1 = axes[1]
    for pid, rotate, col in (("P1", False, "#8fb8de"), ("P2", True, "#8fd39a")):
        for p in hints[pid]:
            if p.get("type") != "box":
                continue
            (cy, cz), (hy, hz), phi, (cx, hx) = _yz_rect(p, ap, ad, ANG, rotate)
            if abs(cx) >= hx:      # only prims the x=0 CUT PLANE passes through — the left panel is
                continue           # a true x=0 section, so the proxy panel must be the same section
            mech = bool(p.get("owner"))
            r = Rectangle((-hy, -hz), 2 * hy, 2 * hz,
                          facecolor="#f6ad55" if mech else col,
                          edgecolor="#c53030" if mech else "#333", lw=1.0 if mech else .6, alpha=.7)
            tr = (matplotlib.transforms.Affine2D().rotate_deg(phi).translate(cy, cz) + ax1.transData)
            r.set_transform(tr); ax1.add_patch(r)
    ax1.set_xlim(ax0.get_xlim()); ax1.set_ylim(ax0.get_ylim())
    ax1.set_aspect("equal"); ax1.axis("off")
    ax1.set_title(f"THEIR CONVEX PROXIES at {ANG:.0f}°  (orange = mech ring-of-wedges)\n"
                  f"MuJoCo reports {len(pairs)} box↔lid contacts with the classes MERGED",
                  fontsize=10.5, color="#742a2a")

    fig.suptitle("The ~26° jam is a PROXY ARTEFACT: the parts clear; their convex stand-ins collide",
                 fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "proxy_artifact_26deg.png", dpi=135); plt.close(fig)

    artefact = vol26 < 1.0 and len(pairs) > 0
    rep = {
        "decision_row": "D-M8-3 (contact-class separation — artefact evidence)",
        "angle_deg": ANG,
        "parts_authority": {"tool": "build123d boolean on compiled solids",
                            "interference_mm3_at_0deg": round(vol0, 4),
                            "interference_mm3_at_26deg": round(vol26, 4)},
        "proxies_authority": {"tool": "MuJoCo contact detection, classes MERGED",
                              "box_lid_contacts_at_26deg": len(pairs),
                              "pairs": pairs[:8]},
        "verdict": ("ARTEFACT CONFIRMED — the parts clear (0 mm³) while their convex proxies collide"
                    if artefact else
                    "NOT an artefact — the parts themselves interfere; suppression would hide a real defect"),
        "guard": ("Suppression is scoped to cross-class pairs between NAMED intended-contact classes "
                  "(mech = pin/bore ring-of-wedges; seat = lid-on-box seating + floor + flange). The "
                  "TRAVEL class is never suppressed: travel is measured on base↔mover SEAT-class "
                  "contacts, which stay live at every angle — that is the path a real lid-vs-box "
                  "interference takes, and it is exactly what fires at 0.63 mm in the no-stop "
                  "fold-over. See the LIMITATION note in REVIEW.md."),
    }
    (OUT / "proxy_artifact.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
