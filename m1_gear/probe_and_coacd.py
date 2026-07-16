"""Regenerate the conjugate-action evidence (involute n4, forward roll at the out-of-bounds fine dt)
and run the CoACD-once record. Split from run_ladder so it can be re-run without redoing L1-L4."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import imageio.v2 as imageio
import mujoco

import coacd_record
import gear_mjcf
import p_gear
from run_ladder import plot_conjugate

OUT = Path(__file__).parent / "out"
FINE = 2e-5


def probe():
    xml, meta = gear_mjcf.build("involute", 4, tag="probe_inv_n4", op_cd=36.0)
    model = mujoco.MjModel.from_xml_path(str(xml))
    t0 = time.time()
    v, series, frames = p_gear.run_gear(model, meta, dt=FINE, omega=3.0, n_rev=1.0,
                                        record=True, forward_only=True)
    print(f"[probe] involute n4 fwd @ dt={FINE:.0e}: ratio={v.ratio:+.3f} err={v.ratio_err_pct:+.1f}% "
          f"TE={v.te_max_deg:.2f}° revs={v.revs_done} diverged={v.diverged}  [{time.time()-t0:.0f}s]")
    if series["t"]:
        plot_conjugate(series, meta, OUT / "conjugate_roll.png", "probe (n4, fwd)")
    if frames:
        imageio.mimsave(OUT / "t_gear_conjugate_roll.mp4", frames, fps=p_gear.FPS)
        print(f"  wrote conjugate_roll.png + t_gear_conjugate_roll.mp4 ({len(frames)} frames)")
    # update the probe record in ladder_verdict.json
    lv = json.loads((OUT / "ladder_verdict.json").read_text())
    lv["conjugate_probe"] = {"dt": FINE, "n_wedge": 4, "forward_only": True, "in_bounds": False,
                             "ratio": v.ratio, "ratio_err_pct": v.ratio_err_pct,
                             "te_max_deg": v.te_max_deg, "revs_done": v.revs_done,
                             "diverged": v.diverged, "backlash_design_mm": v.backlash_design_mm}
    (OUT / "ladder_verdict.json").write_text(json.dumps(lv, indent=2, default=float))
    return v


if __name__ == "__main__":
    probe()
    print()
    coacd_record.record()
