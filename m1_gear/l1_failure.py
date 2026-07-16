"""L1 failure evidence (paper material): the trapezoidal profile's contact-jump blow-up at the
FROZEN timestep. Runs L1 (trapezoid, 2 wedges/flank) at the frozen dt and plots the transmission
error and pinion angular velocity up to divergence — the constant-slope facets cannot roll
conjugately, so the contact point jumps between facet edges, spiking the force until the solver
diverges. This is "why naive tooth approximations fail, demonstrated in contact simulation."
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m0"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mujoco
import numpy as np

import gear_mjcf
import p_gear

OUT = Path(__file__).parent / "out"


def main():
    xml, meta = gear_mjcf.build("trapezoid", 2, tag="L1_fig", op_cd=36.9)
    model = mujoco.MjModel.from_xml_path(str(xml))
    v, series, _ = p_gear.run_gear(model, meta, dt=p_gear.FROZEN_DT, omega=3.0, n_rev=1.0,
                                   record=False)
    t = np.array(series["t"]); te = np.array(series["te_deg"]); wp = np.array(series["omega_pin"])
    ncon = np.array(series["ncon"])
    ratio_ideal = -meta["z1"] / meta["z2"]

    fig, ax = plt.subplots(3, 1, figsize=(8.5, 8), sharex=True)
    ax[0].plot(t, te, color="#c53030", lw=1.3)
    ax[0].axhline(360 / meta["z1"] / 2, ls=":", c="#888", lw=0.8, label="½ tooth pitch (slip bound)")
    ax[0].axhline(-360 / meta["z1"] / 2, ls=":", c="#888", lw=0.8)
    ax[0].set_ylabel("transmission\nerror (deg)")
    ax[0].set_title(f"L1 FAILURE — trapezoid (2 wedges/flank) @ frozen dt={p_gear.FROZEN_DT:.0e}: "
                    f"contact-jump divergence\n(the constant-slope facets cannot roll conjugately — "
                    f"the contact jumps facet→facet and spikes)", fontsize=9.5, color="#742a2a")
    ax[0].legend(fontsize=8); ax[0].grid(alpha=.25)

    ax[1].plot(t, wp, color="#2b6cb0", lw=1.3)
    ax[1].axhline(3.0, ls="--", c="#22543d", lw=0.8, label="drive target ω=3 rad/s")
    ax[1].set_ylabel("pinion angular\nvelocity (rad/s)")
    ax[1].legend(fontsize=8); ax[1].grid(alpha=.25)
    ax[1].text(t[-1], wp[-1], "  ← kicked backward\n     (contact blow-up)", fontsize=8,
               color="#742a2a", va="center")

    ax[2].plot(t, ncon, color="#805ad5", lw=1.0, drawstyle="steps-post")
    ax[2].set_ylabel("# contacts"); ax[2].set_xlabel("t (s)")
    ax[2].grid(alpha=.25)

    fig.tight_layout(); fig.savefig(OUT / "l1_contact_jump.png", dpi=140); plt.close(fig)
    print(f"L1 @ frozen dt: diverged={v.diverged}, TE peak {v.te_max_deg:.2f}°, "
          f"|ω_pin| max {np.abs(wp).max():.0f} rad/s (target 3). wrote l1_contact_jump.png "
          f"({len(t)} steps to blow-up)")


if __name__ == "__main__":
    main()
