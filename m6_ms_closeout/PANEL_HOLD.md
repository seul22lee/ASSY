# D-GEN-1 HOLD — panel board-clip fails visual review

Status: **D-GEN-1 sign-off withdrawn.** The host-agnostic carve is proven for the *window-catch*
host (box) only. The board-clip (edge-overhang) host compiles to geometrically wrong hooks. Two
distinct defects, both flagged as DRAFT for a ruling — **not** fixed here.

Evidence (ground truth — actual solids sliced at y=0):
`out/panel_section.png` (board clip, wrong) · `out/box_section.png` (box, correct, for contrast).

## The data you asked for

**Panel golden bindings** (`snap_panel()`):
| port | piece | anchor |
|---|---|---|
| beam_root | M1 (flat_panel_mount) | rail_inner_left / rail_inner_right |
| catch_window | B1 (retained_board) | board_edge_left / board_edge_right |

**AnchorGeom (position mm, normal):**
| anchor | position | normal |
|---|---|---|
| rail_inner_left/right | (∓27, 0, 17) | (0, 0, 1) |
| board_edge_left/right | (∓25, 0, 24) | (±1, 0, 0) inward |

**Resolved (⑤) vs compiled (⑥):**
| | resolve ⑤ | geometry ⑥ | note |
|---|---:|---:|---|
| L | **12.0** | **7.0** | ⑥ discards ⑤'s L (Defect 1) |
| h_root | 2.093 | 2.093 | computed for L=12, applied to L=7 |
| b | 8.0 | 8.0 | fine — hook width never blew up |
| y | 1.5 | 1.5 | designed; **measured 0.0** at t0 (Defect 2) |
| α_out | 45° | 45° | SEPARABLE, W_sep = 31.84 N (in hand window) |

The "full-width vertical walls" in the render are the template **rails** (`Box(rt=3, W=40,
rh=22)`) — legitimate mount features, wall-scale by design. **b did not blow up** (b=8, a proper
finger). The hooks are small and live in the 2 mm gap between rail inner face (x=27) and board
edge (x=25); they are dwarfed by the rails, which is why the iso reads as "walls sandwiching a
board." The real problems are the two below, not hook scale.

## DRAFT decision 1 — who owns L? (resolve ⑤ vs anchor span ⑥)

`build_hook_at` sets `L = growth_dist = |catch − root along normal| = board_z(24) − rail_z(17) =
7`. It **ignores** ⑤'s resolved L=12. ⑤ sized h=2.093 to hit the target force *at L=12*; the
compiled L=7 beam is much stiffer, so the panel's true snap force ≠ the rationale sheet. The box
passed Tier1's L-check only because its anchors happen to give `growth_dist ≈ 12 = L` — a
load-bearing coincidence that broke on the second host.

**Options:**
- **(1a)** ⑥ builds the beam at ⑤'s resolved L; anchors set the root + engage, and the resolved L
  must be ≤ the host's available growth_dist (else INFEASIBLE-at-⑥, a real diagnosis).
- **(1b)** ⑤ reads the host's growth_dist as the L bound (or fixes L := growth_dist) before
  solving h — geometry-first, formula follows.
- **(1c)** keep as-is, accept the coincidence — *rejected: silently wrong on the panel.*

Recommend **(1a)**: ⑤ owns L (it's a formula output); ⑥ honors it; a host too short to fit the
beam is a legitimate infeasibility, not something to paper over by shrinking the beam.

## DRAFT decision 2 — nose topology: window vs edge-overhang

The canonical hook nose protrudes **laterally** (engage dir). Correct for a **window** catch: the
nose passes *through* a wall hole and the undercut catches the window's far edge (see
`box_section.png` — nose inside the window with y=1.5). A **board clip** catches the board's **top
edge**: the beam must grow *past* z=24 and the nose must curl *over* the top face so the undercut
sits above the board. The compiled panel nose reaches only z=20.9 (below the board top, z=24) at
x=23.5 (inside the edge, x=25) — it **does not overhang anything** (`panel_section.png`).

**On t0's three-way check:** it did **not** pass with a blind spot — it **FAILED**
(`UNDERCUT_MISMATCH`, measured undercut 0.000). The check did its job. My earlier
`catch_topology="overhang"` → N/A routing *masked that correct failure* — that was the quiet fix.
Withdrawn.

**Options:**
- **(2a)** Add an overhang-nose carve variant (grow past the edge, curl the undercut over the top
  face) + a matching overhang three-way check. The catch binding conveys topology
  (`undercut_dir`/a `catch_topology` field on the binding, not a runner kwarg). Then re-attempt
  D-GEN-1 as genuinely host-agnostic across *both* topologies.
- **(2b)** Scope D-GEN-1 to window-catch hosts for M-S; drop the panel from the close-out; make
  the board clip an explicit M-G (later milestone) item.
- **(2c)** keep the N/A masking — *rejected: it reports a broken host as a passing one.*

Recommend **(2b)** for the M-S close-out (don't hold the snap-only milestone on a second
topology), then **(2a)** as the first M-G task. Either way the panel is **removed** from the
"D-GEN-1 proven" claim until it compiles correctly.

## Panel intent (your last question)

α_out = 45° → **SEPARABLE** (service access). Self-lock for μ=0.3 is atan(1/0.3)=73.3°; 45° is
well below, so the joint releases. W_sep = 31.84 N sits inside the [15, 60] N hand window — a
board you can pull off by hand for service. This is the correct intent for a board clip and should
be **declared** in the golden (proposed: `intent: "separable"` on E1, asserted against W_sep ∈
hand-window). NOT the α′=90° permanent case (that's T-S1d).

## Impact on the M-S close-out

`ms_verdict.md` item 4 and the T-S1-panel report currently present the panel as a passing
D-GEN-1 host via N/A. That is now **false** and is on hold. T-S1a/T-S1b (box, both topologically
correct) are unaffected. Awaiting your ruling on decisions 1 and 2 before rebuilding.
