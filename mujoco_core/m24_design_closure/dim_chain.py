"""m24 Phase A (§14 T3b) — the latched_drawer DIMENSION CHAIN + fit schedule, the single source of truth.

Three FREE inputs (the storage requirement): W_i, D, H. Everything else DERIVES from a mate or a formula;
any number without a source is a T3b failure. The templates, the golden, and the T5 rig all import
`chain()` so a dimension is written once. The CLIP is dimensioned by INVERSE BAYER (snap_hook card
formulas): pick the beam L·b·undercut, get h_root/P/W_out/W_in, target W_out ≈ 30 N with W_in ≤ 20 N.

  ./bin/py m24_design_closure/dim_chain.py         # prints the chain + fit schedule
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "m0"))

from knowledge.cards.snap_hook import (P_deflect, W_mate, W_sep, fig18_factor,  # noqa: E402
                                       self_locking_angle, solve_h)

# --- constants (all sourced) ----------------------------------------------------------------
WALL = 2.4          # nominal print wall (m22/m24 slide fixtures)
SIDE_GAP = 1.0      # drawer-in-opening side clearance (drawer-fits-opening discipline)
CLR = 0.35          # A-PETG-1 print/slide clearance
RAIL_W = 8.0        # slide_rail rail width (M10)
RAIL_H = 6.0        # slide_rail rail height
PANEL_PROUD = 4.0   # front-panel oversize per side (covers the opening; lands on the face frame)
# CLIP (snap_hook card) inverse-Bayer inputs
MU = 0.30           # PETG.mu_friction (the m22/m23 sourced chain)
EPS, ES = 0.02, 1815.0   # Bayer working strain + secant modulus (PETG-class, Fig.16)
CLIP_L, CLIP_B, UNDERCUT = 12.0, 6.0, 1.35     # beam length, width, undercut (deflection) — design 2
ALPHA_IN, ALPHA_OUT = 30.0, 45.0
W_OUT_TARGET = 30.0


def chain(W_i: float = 60.0, D: float = 60.0, H: float = 25.0) -> dict:
    """Compute the full dimension chain. Returns {name: (value_mm, source)} + scalars used by geometry."""
    W_t = W_i + 2 * WALL                 # tray outer
    W_o = W_t + 2 * SIDE_GAP             # opening
    W_c = W_o + 2 * WALL                 # cabinet outer
    W_p = W_o + 2 * PANEL_PROUD          # front panel (proud each side)
    groove_w = RAIL_W + 2 * CLR          # under-tray groove rides the rail
    ride_clr = RAIL_H + CLR              # tray-floor-to-cabinet-floor gap
    # CLIP inverse Bayer
    h_root = solve_h(EPS, CLIP_L, UNDERCUT, 2)
    P = P_deflect(CLIP_B, h_root, ES, EPS, CLIP_L)
    W_out = W_sep(P, MU, ALPHA_OUT)
    W_in = W_mate(P, MU, ALPHA_IN)
    bump_h = UNDERCUT + CLR              # bump rises undercut above ride clearance → h overlap at closed
    stroke = D - 10.0                    # travel = D − margin
    rail_len = stroke + 5.0

    rows = {
        "W_i (free: inner width)": (W_i, "storage requirement (free input)"),
        "D (free: depth)": (D, "storage requirement (free input)"),
        "H (free: height)": (H, "storage requirement (free input)"),
        "tray outer W_t": (W_t, f"W_i + 2·wall({WALL})"),
        "opening W_o": (W_o, f"W_t + 2·side_gap({SIDE_GAP}) — drawer-fits-opening"),
        "cabinet outer W_c": (W_c, f"W_o + 2·wall({WALL})"),
        "front panel W_p": (W_p, f"W_o + 2·proud({PANEL_PROUD}) — covers the opening, lands on face frame"),
        "groove width": (groove_w, f"rail_w({RAIL_W}) + 2·clr({CLR}) A-PETG-1 (M10)"),
        "ride clearance": (ride_clr, f"rail_h({RAIL_H}) + clr({CLR})"),
        "CLIP beam L": (CLIP_L, "chosen; feeds inverse-Bayer"),
        "CLIP beam b": (CLIP_B, "chosen; feeds inverse-Bayer"),
        "CLIP undercut y": (UNDERCUT, "chosen deflection; feeds solve_h → W_out target"),
        "CLIP root h": (h_root, f"solve_h(eps={EPS},L={CLIP_L},y={UNDERCUT},d2)=C·eps·L²/y"),
        "CLIP P_deflect": (P, f"(b·h²/6)(Es·eps/L), Es={ES}"),
        "CLIP W_out (sep,45°)": (W_out, f"P·fig18(mu={MU},{ALPHA_OUT}°)={fig18_factor(MU,ALPHA_OUT):.3f} — target ≈{W_OUT_TARGET}"),
        "CLIP W_in (mate,30°)": (W_in, f"P·fig18(mu={MU},{ALPHA_IN}°)={fig18_factor(MU,ALPHA_IN):.3f} — ≤20 hand-insertable"),
        "self-lock angle": (self_locking_angle(MU), f"atan(1/mu={MU}) — >{ALPHA_OUT}° ⇒ releasable"),
        "bump height": (bump_h, f"undercut({UNDERCUT}) + clr({CLR}) — h overlap at closed, no ride contact"),
        "barb rest above floor": (CLR, f"clr({CLR}) — no contact while riding"),
        "front-panel-to-face gap": (0.0, "0 = the LANDING (closed hard stop, M1)"),
        "stroke": (stroke, f"D({D}) − margin(10)"),
        "rail length": (rail_len, "stroke + 5 overlap"),
    }
    geom = {"W_i": W_i, "D": D, "H": H, "W_t": W_t, "W_o": W_o, "W_c": W_c, "W_p": W_p,
            "wall": WALL, "side_gap": SIDE_GAP, "clr": CLR, "rail_w": RAIL_W, "rail_h": RAIL_H,
            "groove_w": groove_w, "ride_clr": ride_clr, "clip_L": CLIP_L, "clip_b": CLIP_B,
            "undercut": UNDERCUT, "h_root": h_root, "P": P, "W_out": W_out, "W_in": W_in,
            "bump_h": bump_h, "barb_rest": CLR, "stroke": stroke, "rail_len": rail_len,
            "panel_proud": PANEL_PROUD, "alpha_in": ALPHA_IN, "alpha_out": ALPHA_OUT, "mu": MU}
    return {"rows": rows, "geom": geom}


def print_schedule(c: dict) -> str:
    lines = ["=== latched_drawer DIMENSION CHAIN / FIT SCHEDULE (§14 T3b) — 3 free inputs, else derived ==="]
    lines.append(f"  {'quantity':<28s}{'value':>9s}   source")
    for name, (val, src) in c["rows"].items():
        lines.append(f"  {name:<28s}{val:>9.3f}   {src}")
    g = c["geom"]
    lines.append("")
    lines.append(f"  SOURCED latch forces: W_out={g['W_out']:.2f} N (designed), hold 0.5·W_out="
                 f"{0.5*g['W_out']:.2f} N, release 1.5·W_out={1.5*g['W_out']:.2f} N")
    lines.append(f"  (m23 old W_out=32.81 N → new DESIGNED W_out={g['W_out']:.2f} N — criteria scale accordingly)")
    return "\n".join(lines)


if __name__ == "__main__":
    c = chain()
    out = print_schedule(c)
    (ROOT / "m24_design_closure" / "out" / "latched_drawer_chain.txt").write_text(out + "\n")
    print(out)
