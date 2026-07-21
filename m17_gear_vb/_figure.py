"""m17 FILE 3 — the one-look summary: peak contact force across the 5 probe conditions on a log-y
bar chart, RED = diverged, GREEN = survived. Reads the two verdict JSONs (FILE 1 + FILE 2).

  export MUJOCO_GL=disable ; ./bin/py m17_gear_vb/_figure.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path(__file__).parent / "out"


def main():
    f1 = json.loads((OUT / "sdf_probe_verdict.json").read_text())
    f2 = json.loads((OUT / "sdf_formulation_verdict.json").read_text())
    c1, c2 = f1["conditions"], f2["conditions"]

    # (label, peak_force, diverged, dt-note)
    bars = [
        ("wedge\nfrozen 5e-4", c1["wedge_frozen_5e-4"]["peak_force_N"], c1["wedge_frozen_5e-4"]["diverged"], "R2b baseline"),
        ("wedge\ndt/25 2e-5", c1["wedge_dt25_2e-5"]["peak_force_N"], c1["wedge_dt25_2e-5"]["diverged"], "clean roll"),
        ("SDF gear\nfrozen rigid", c2["sdf_frozen_rigid"]["peak_force_N"], c2["sdf_frozen_rigid"]["diverged"], "oracle"),
        ("SDF gear\nfrozen soft", c2["sdf_frozen_soft"]["peak_force_N"], c2["sdf_frozen_soft"]["diverged"], "oracle"),
        ("SDF gear\ndt/25 soft", c2["sdf_dt25_soft"]["peak_force_N"], c2["sdf_dt25_soft"]["diverged"], "seating transient"),
    ]
    labels = [b[0] for b in bars]
    vals = [max(b[1], 1e-2) for b in bars]
    colors = ["#c53030" if b[2] else "#2f855a" for b in bars]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = np.arange(len(bars))
    ax.bar(x, vals, color=colors, width=0.62, edgecolor="k", linewidth=0.4)
    ax.set_yscale("log"); ax.set_ylim(1e-2, 1e18)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("peak contact force (N, log)")
    for xi, b in zip(x, bars):
        tag = "DIVERGED" if b[2] else "survived"
        ax.text(xi, max(b[1], 1e-2) * 1.6, f"{b[1]:.1e}\n{tag}\n({b[3]})",
                ha="center", va="bottom", fontsize=7.5,
                color="#c53030" if b[2] else "#2f855a")
    ax.axhline(1e6, ls=":", c="#888", lw=0.8)
    ax.text(4.4, 1.3e6, "physical scale", fontsize=7, color="#888", ha="right")
    ax.set_title("R2b SDF probe — SDF removes facets but NOT the small-dt need\n"
                 "red = diverged (blows up at frozen dt) · green = survived (only at dt/25)",
                 fontsize=10)
    ax.grid(axis="y", alpha=0.25, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "r2b_sdf_probe_summary.png", dpi=140)
    plt.close(fig)
    print("wrote out/r2b_sdf_probe_summary.png")


if __name__ == "__main__":
    main()
