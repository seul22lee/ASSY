"""The D20 demonstration: the no-stop / stop V-B pair, side by side.

Same assembly, same seed, same preset — the ONLY difference is that the `stop` variant's IR carries
F1 (a stop_flange PassiveFeature) and the B3-class rotation LIMIT it imposes (bound="max", ceiling SOLVED from this box's
registered per V-08), which compiles to a real flange solid on the lid.

  baseline : no stop declared ⇒ no stop exists ⇒ the over-centre lid FOLDS RIGHT OVER (~272°).
             That is the finding (M0: "no stop: the lid is free to fold flat"), reported as the
             overtravel observable — never engineered away.
  stop     : the flange bottoms out on the box's own rear wall — the lid stops BY CONTACT (~124°,
             against a 120.05° declared ceiling: ~4° of contact compliance).

Run:  ./bin/py m8_pin_hinge_easy/build_stop_pair.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

T2 = Path("verify/t2_physics/out_easy")
OUT = Path(__file__).parent / "out"
def _b3_ceiling() -> float:
    """Read the declared ceiling FROM THE IR (B3, imposed by F1) — never hardcode it here; the
    number is F1's solved stop_angle and must travel with the plan."""
    from tasks.build_goldens import anchor_easy
    b3 = next(b for b in anchor_easy("stop").behaviors if b.id == "B3")
    return float(b3.motion.range_value)


B3_STOP_DEG = _b3_ceiling()


def series(tag, mode="V-B"):
    rows = list(csv.DictReader(open(T2 / f"t2_{tag}_{mode}.csv")))
    return ({k: np.array([float(r[k]) for r in rows]) for k in
             ("t", "theta_deg", "force_N", "pen_travel_mm")})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base, stop = series("easy_nostop"), series("easy")
    raw = {t: json.loads((T2 / f"t2_{t}_verdict.json").read_text()) for t in ("easy_nostop", "easy")}
    vb = {("easy" if t == "easy_nostop" else "easy_stop"): r["modes"]["V-B"]["p_hinge"]
          for t, r in raw.items()}   # local keys: "easy"=baseline/nostop demo, "easy_stop"=benchmark

    fig, axes = plt.subplots(2, 1, figsize=(9, 7.6), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1]})
    ax = axes[0]
    ax.plot(base["t"], base["theta_deg"], lw=2, color="#c53030",
            label=f"baseline — NO stop declared  (θmax {vb['easy']['per_seed'][0]['theta_max_deg']:.0f}°, "
                  f"{vb['easy']['seeds_passed']}/5)")
    ax.plot(stop["t"], stop["theta_deg"], lw=2, color="#2f855a",
            label=f"stop variant — F1 + B3  (θmax {vb['easy_stop']['per_seed'][0]['theta_max_deg']:.0f}°, "
                  f"{vb['easy_stop']['seeds_passed']}/5)")
    ax.axhline(B3_STOP_DEG, ls="--", c="#2f855a", lw=1.3)
    ax.text(base["t"][-1], B3_STOP_DEG + 4, f" B3 ceiling {B3_STOP_DEG}° (IR, bound=max)",
            color="#2f855a", ha="right", fontsize=8.5)
    ax.axhline(90, ls=":", c="#4a5568", lw=1)
    ax.text(base["t"][-1], 92, " over-centre (90°) — past here gravity OPENS the lid",
            color="#4a5568", ha="right", fontsize=8)
    ax.axhline(180, ls=":", c="#c53030", lw=1)
    ax.text(base["t"][-1], 182, " folded flat (180°)", color="#c53030", ha="right", fontsize=8)
    ax.axhspan(B3_STOP_DEG, max(stop["theta_deg"].max(), B3_STOP_DEG), color="#c6f6d5", alpha=.45)
    ax.set_ylabel("lid angle θ (deg)   —  V-B, contact-only")
    ax.set_title("D20 — stopping BY CONTACT.  Same assembly, same seed, same preset;\n"
                 "the only difference is that the IR declares a stop_flange (F1) and the rotation "
                 "limit it imposes (B3).", fontsize=10.5)
    ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=.25)

    ax = axes[1]
    ax.plot(base["t"], base["pen_travel_mm"], lw=1.5, color="#c53030", label="baseline travel (defect)")
    ax.plot(stop["t"], stop["pen_travel_mm"], lw=1.5, color="#2f855a", label="stop travel (defect)")
    ax.axhline(0.2, ls="--", c="#4a5568", lw=1)
    ax.text(base["t"][-1], 0.21, " 0.2 mm gate", color="#4a5568", ha="right", fontsize=8)
    ax.set_ylabel("travel pen (mm)"); ax.set_xlabel("t (s)")
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=.25)

    fig.tight_layout()
    fig.savefig(OUT / "stop_pair_theta.png", dpi=135); plt.close(fig)

    # the arrest, quantified — read from the trace, not asserted
    first = stop["t"][np.argmax(stop["theta_deg"] >= B3_STOP_DEG)] if (stop["theta_deg"] >= B3_STOP_DEG).any() else None
    rep = {
        "decision_row": "D-M8-2 (stop variant pair — D20 demonstration)",
        "B3_ceiling_deg": B3_STOP_DEG,
        "baseline": {"theta_max_deg": float(base["theta_deg"].max()),
                     "seeds_passed": vb["easy"]["seeds_passed"], "verdict": vb["easy"]["passed"],
                     "reading": "no stop declared ⇒ none exists ⇒ lid folds over (the finding)"},
        "stop": {"theta_max_deg": float(stop["theta_deg"].max()),
                 "seeds_passed": vb["easy_stop"]["seeds_passed"], "verdict": vb["easy_stop"]["passed"],
                 "first_reaches_ceiling_s": None if first is None else float(first),
                 "overshoot_deg": float(stop["theta_deg"].max() - B3_STOP_DEG),
                 "reading": "flange bottoms out on the box rear wall — arrest BY CONTACT"},
    }
    (OUT / "stop_pair.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2))
    print("wrote", OUT / "stop_pair_theta.png")


if __name__ == "__main__":
    main()
