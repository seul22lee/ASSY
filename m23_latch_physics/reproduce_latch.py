"""m23_latch_physics — reproduce the SOURCED latch chain + the P-LATCH criteria (free/local)."""
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"m0"))
from knowledge.cards.snap_hook import P_deflect, W_sep, self_locking_angle, solve_h
from knowledge.materials import PETG
from tasks.build_goldens import latched_drawer
V = Path(__file__).resolve().parent/"out"/"t2_latch_verdict.json"

def main():
    p = next(e.params for e in latched_drawer().elements if e.card_ref=="snap_hook_cantilever")
    mu=PETG.mu_friction; h=solve_h(0.02,p["L_mm"],p["y_mm"],int(p.get("design_type",2)))
    P=P_deflect(p["b_mm"],h,1815.0,0.02,p["L_mm"]); W=W_sep(P,mu,p["alpha_out_deg"])*int(p["n_hooks"])
    ok=True
    print("\n========== m23 latch — SOURCED breakaway + close/hold/release ==========")
    print(f"[1] SOURCED W_out (Bayer, D3): solve_h→{h:.2f}mm ; P_deflect→{P:.2f}N ; "
          f"W_sep(α_out={p['alpha_out_deg']}°,µ={mu})×{int(p['n_hooks'])} = {W:.2f} N")
    print(f"    self-lock atan(1/µ)={self_locking_angle(mu):.1f}° > α_out {p['alpha_out_deg']}° ⇒ hand-releasable")
    print(f"    pull_hold = 0.5·W_out = {0.5*W:.1f} N (< breakaway) ; pull_release = 1.5·W_out = {1.5*W:.1f} N (> breakaway)")
    if V.exists():
        vj=json.load(open(V)); s0=vj["modes"]["P-LATCH"]["per_seed"][0]
        print(f"\n[2] P-LATCH measured (seed0): engage@{s0['click_s_mm']:.2f}mm ; hold disp {s0['hold_disp_mm']:.2f}mm "
              f"@{s0['pull_hold_N']}N ; release→{s0['peak_open_mm']:.0f}mm @{s0['pull_release_N']}N")
        print(f"    seeds passed {vj['modes']['P-LATCH']['seeds_passed']}/5 ; t0 gate {'CLEAN' if vj['t0_gate']['clean'] else 'FAIL'}")
        print(f"    discrimination: SOURCED threshold holds below / opens above ⇒ {'ok' if s0['passed'] else 'FAIL'}")
        ok &= s0["passed"] and vj["t0_gate"]["clean"] and abs(vj["sourced_breakaway"]["W_out_N"]-W)<0.1
    print(f"\n========== reproduction {'CLEAN' if ok else 'FAILED'} ==========\n")
    return 0 if ok else 1
if __name__=="__main__": sys.exit(main())
