"""M0: the collision-approximation overlay (spec 6.2, "mandatory").

Renders, side by side, what the *renderer* shows (full-fidelity tessellation) and what the
*solver* actually feels (the collision geoms). Any gap between these two is a lie the sim
can tell you with a straight face -- and this project's entire claim rests on the sim not
lying. It is the artifact that catches a swallowed bore, a filled-in cavity, or a visual
mesh in the wrong units.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import imageio.v2 as imageio
import mujoco
import numpy as np

VARIANT = os.environ.get("M0_VARIANT", "nostop")
OUT = Path(__file__).parent / "out" / VARIANT
W, H = 640, 480


def _shot(model, data, cam, group_visual: bool, group_collision: bool):
    r = mujoco.Renderer(model, H, W)
    opt = mujoco.MjvOption()
    mujoco.mjv_defaultOption(opt)
    opt.geomgroup[:] = 0
    if group_visual:
        opt.geomgroup[2] = 1
    if group_collision:
        opt.geomgroup[3] = 1
    if isinstance(cam, str):
        cam = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, cam)
    r.update_scene(data, camera=cam, scene_option=opt)
    img = r.render()
    r.close()
    return img


def bore_cam(meta) -> mujoco.MjvCamera:
    """Zoomed on the pin/bore interface -- the one place where a swallowed hole would hide
    (spec 6.2; the overlay is the only thing that makes such a swallow visible)."""
    c = mujoco.MjvCamera()
    c.azimuth, c.elevation, c.distance = 118.0, -12.0, 0.045
    c.lookat[:] = meta["hinge_axis_m"]
    return c


def label(img: np.ndarray, text: str) -> np.ndarray:
    """A 12 px block-letter caption, drawn by hand -- no font dependency."""
    F = {
        "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
        "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
        "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
        "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
        "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
        "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
        "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01111"],
        "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
        "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
        "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
        "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
        "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
        "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
        "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
        "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
        "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
        "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
        "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
        "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
        "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
        "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
        "(": ["00110", "01000", "10000", "10000", "10000", "01000", "00110"],
        ")": ["01100", "00010", "00001", "00001", "00001", "00010", "01100"],
        "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
        " ": ["00000"] * 7,
    }
    img = img.copy()
    img[:22] = (img[:22] * 0.25).astype(np.uint8)
    x, s = 8, 2
    for ch in text.upper():
        g = F.get(ch, F[" "])
        for ry, row in enumerate(g):
            for rx, on in enumerate(row):
                if on == "1":
                    y0, x0 = 4 + ry * s, x + rx * s
                    img[y0:y0 + s, x0:x0 + s] = 255
        x += (len(g[0]) + 1) * s
    return img


def main() -> None:
    import json

    mode = sys.argv[1] if len(sys.argv) > 1 else "V-A"
    model = mujoco.MjModel.from_xml_path(str(OUT / f"hinge_{mode}.xml"))
    meta = json.loads((OUT / f"hinge_{mode}_meta.json").read_text())
    data = mujoco.MjData(model)

    # Only V-A has a hinge joint at qpos[0]. In V-B qpos[0] is the box's *free joint* -- so
    # writing an angle there teleports the box out of frame instead of opening the lid.
    hinge = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "hinge")
    if hinge >= 0:
        data.qpos[model.jnt_qposadr[hinge]] = np.deg2rad(55)
    mujoco.mj_forward(model, data)

    panels = []
    for cam in ("iso", "hinge_closeup", bore_cam(meta)):
        vis = label(_shot(model, data, cam, True, False), "visual (true geometry)")
        col = label(_shot(model, data, cam, False, True), "collision (what solver feels)")
        panels.append(np.hstack([vis, np.full((H, 4, 3), 40, np.uint8), col]))

    sep = np.full((4, panels[0].shape[1], 3), 40, np.uint8)
    grid = np.vstack([panels[0], sep, panels[1], sep, panels[2]])
    out = OUT / f"t2_conv_overlay_{mode}.png"
    imageio.imwrite(out, grid)
    print(f"wrote {out}")

    # A quantitative companion to the picture: does the collision geometry conserve volume?
    # (A swallowed cavity shows up here as a big positive delta.)
    print("\n  collision-approximation volume check")
    for b in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, b)
        cols = [g for g in range(model.ngeom)
                if model.geom_bodyid[g] == b and model.geom_group[g] == 3]
        print(f"    {name:11s} {len(cols):2d} collision geom(s), "
              f"mass {model.body_mass[b]*1000:6.2f} g (from exact mesh, not from these)")


if __name__ == "__main__":
    main()
