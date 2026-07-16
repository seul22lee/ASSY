"""snap_hook_cantilever GEOMETRY — carve() + collision primitives (SNAPFIT §4-⑥, §5.2).

HOST-AGNOSTIC (D-GEN-1): the hook is built in a canonical LOCAL frame and placed by a transform
derived entirely from the bound anchors — root position + growth direction (the beam_root
anchor's normal) and engage direction (toward the catch_window anchor). There is NO reference to
any host's dimensions (no box_l/wall). The same carve()/collision_hint() therefore attach to
box_shell OR flat_panel_mount with zero card-code changes; only the bindings differ. If this file
ever branches on host type, that is the D-GEN-1 violation to flag.

  * HOOK: a design-2 tapered beam (root h → tip h/2) + a nose (α_in lead-in ramp, α_out undercut,
    protruding y past the mount face) — grown from the beam_root anchor along its normal.
  * CATCH WINDOW: a rectangular cutter (width = b + 2·clearance) through the receiving host at the
    catch_window anchor, along that anchor's normal.

carve() returns TAGGED sub-solids (hooks separable) for §5.2's three-way interference check, and
per-hook DIMENSION metadata (y/h/L/α) for the s6_hook_closeup overlay (§6).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from build123d import Box, Location, Plane, Polygon, Pos, extrude

from knowledge.materials import PETG
from pipeline.stage_failure import StageFailure

CLEARANCE = PETG.print_clearance_mm  # 0.30 mm
EMBED = 0.6  # root embed into the host so the beam↔host union merges (D14 coincident-face)
ENGAGE_MIN_VOL = 2.0  # mm³ — the window (at the beam tip) must remove at least this much receiver
#                       material, else the nose engages nothing: GEOM_INFEASIBLE (D-GEN-3/-4)

# Geometry defaults (used only if the instance carries no resolved params — flagged).
GEOM_DEFAULTS = {"L_hook": 12.0, "h_root": 2.5, "b": 8.0, "y_undercut": 1.5,
                 "tip_flat": 0.4, "alpha_in_deg": 30.0, "alpha_out_deg": 45.0,
                 "mount_gap": 2.0}  # face-to-catch gap the nose must span (host wall thickness-ish)


@dataclass
class HookDims:
    side_tag: str
    y: float
    h_root: float
    h_tip: float
    L: float
    b: float
    alpha_in: float
    alpha_out: float
    root_xyz: tuple
    nose_tip_xyz: tuple
    from_defaults: bool
    growth_dir: tuple = (0.0, 0.0, -1.0)   # beam axis in world (for Tier1 re-measurement)
    engage_dir: tuple = (1.0, 0.0, 0.0)    # nose protrusion axis in world
    protrude: float = 0.0                  # CLEARANCE + y (nose reach past the beam outer face)
    embed: float = 0.6


@dataclass
class CarveResult:
    parts: dict
    tags: dict
    dims: list
    meta: dict = field(default_factory=dict)


def _geom(inst) -> dict:
    g = dict(GEOM_DEFAULTS)
    used_default = True
    if inst is not None and getattr(inst, "params", None):
        for k in ("alpha_in_deg", "alpha_out_deg"):
            if k in inst.params:
                g[k] = float(inst.params[k])
        for k in ("L_hook", "h_root", "b", "y_undercut"):
            if k in inst.params:
                g[k] = float(inst.params[k]); used_default = False
    g["_from_defaults"] = used_default
    return g


# --- canonical hook (root at origin; beam grows +Z_local; nose protrudes +X_local) ----------
def _canonical_hook(g: dict, L: float, engage_off: float):
    """Build the hook in its own frame. Local +Z = beam growth (away from the mount), +X = engage
    (toward the catch), Y = width. `engage_off` places the beam OUTER face at the catch's lateral
    position (so the nose meets the catch); `L` is the growth-distance to the catch level — both
    derived from the anchors, so the hook adapts to any host spacing (D-GEN-1). The nose sits near
    the tip and protrudes CLEARANCE+y past the outer face into the catch window."""
    h_root, b, y = g["h_root"], g["b"], g["y_undercut"]
    h_tip = h_root / 2.0
    a_in, a_out = g["alpha_in_deg"], g["alpha_out_deg"]

    # The beam's OUTER face sits a print-clearance INSIDE the catch face (at engage_off), so the
    # beam does not rub the mount. The nose then protrudes CLEARANCE + y, putting its tip y PAST
    # the catch face — so the deflection needed to insert (nose overlap with the solid mount) is
    # exactly the undercut y (Bayer p.11: deflection = undercut). Tier0 (b) measures this.
    beam_outer = engage_off - CLEARANCE

    # Root embed: the first segment pokes EMBED below the root (local z<0) so the beam overlaps
    # the host it grows from and the boolean union merges cleanly (the D14 coincident-face lesson).
    n_seg = 6
    part = None
    segs = []
    for i in range(n_seg):
        z_a = (i * L / n_seg) - (EMBED if i == 0 else 0.0)
        z_b = (i + 1) * L / n_seg
        frac = i / n_seg                     # evaluate at the segment's ROOT edge so the thickest
        h = h_root + (h_tip - h_root) * frac  # segment is exactly h_root (Tier1 re-measures this)
        cx = beam_outer - h / 2.0            # beam spans x_local ∈ [beam_outer−h, beam_outer]
        seg = Pos(cx, 0, (z_a + z_b) / 2) * Box(h, b, (z_b - z_a))
        segs.append((cx, h, (z_a + z_b) / 2, (z_b - z_a)))
        part = seg if part is None else part + seg

    protrude = CLEARANCE + y                 # tip lands y past the catch face → deflection = y
    x0 = beam_outer                          # beam outer face
    x_tip = beam_outer + protrude            # = engage_off + y
    h_lead = min(protrude / max(math.tan(math.radians(a_in)), 0.20), L * 0.45)
    h_under = min(protrude / max(math.tan(math.radians(a_out)), 0.20), L * 0.25)
    tip_flat = g["tip_flat"]
    z_tip = L                                # local z=L is the beam TIP (the leading edge on insert)
    # Orientation: the LEAD-IN ramp is at the tip (local z=L, the first edge to meet the mount on
    # a −growth insertion), the UNDERCUT face is above it (smaller local z). Nose spans
    # z_local ∈ [z_tip − nose_h, z_tip].
    nose_h = h_lead + tip_flat + h_under
    pts = [(x0, z_tip),                                  # tip, on beam (lead-in start)
           (x_tip, z_tip - h_lead),                      # protruded (end of lead-in ramp)
           (x_tip, z_tip - h_lead - tip_flat),           # tip flat
           (x0, z_tip - nose_h)]                         # undercut face back to beam
    nose = extrude(Plane.XZ * Polygon(*pts, align=None), amount=b / 2, both=True)
    part = part + nose
    nose_desc = (x0, x_tip, z_tip, h_lead, tip_flat, h_under, protrude, nose_h)
    return part, segs, nose_desc


def _frame(root_pos, growth_dir, engage_dir) -> Location:
    """Location mapping local (+X→engage, +Z→growth) to world at root_pos. engage is
    orthogonalised against growth so the frame is clean regardless of anchor placement."""
    g = np.array(growth_dir, float); g /= np.linalg.norm(g)
    e = np.array(engage_dir, float)
    e = e - np.dot(e, g) * g
    if np.linalg.norm(e) < 1e-9:
        e = np.array([1.0, 0, 0]) - g[0] * g
    e /= np.linalg.norm(e)
    return Location(Plane(origin=tuple(root_pos), x_dir=tuple(e), z_dir=tuple(g)))


def _decompose(root_pos, growth_dir, catch_pos):
    """Split the root→catch vector into a growth component (along the anchor normal) and an engage
    component (lateral). This is everything the hook needs to bridge the two anchors — no host
    dimensions (D-GEN-1)."""
    g = np.array(growth_dir, float); g /= np.linalg.norm(g)
    vec = np.array(catch_pos, float) - np.array(root_pos, float)
    growth_dist = float(np.dot(vec, g))
    engage_vec = vec - growth_dist * g
    engage_dist = float(np.linalg.norm(engage_vec))
    engage_dir = tuple(engage_vec / engage_dist) if engage_dist > 1e-9 else (1.0, 0.0, 0.0)
    return tuple(g), growth_dist, engage_dist, engage_dir


def build_hook_at(root_pos, growth_dir, catch_pos, g: dict, tag: str):
    """A placed hook + dims + placement + its catch-window cutter. L comes from ⑤'s resolved
    parameter (D-GEN-3 — verified to fit the anchor span, else GEOM_INFEASIBLE); the lateral engage
    offset comes from the anchor spacing, so the hook still places host-agnostically (D-GEN-1). The
    window is built in the SAME local frame as the hook, sized to the nose + clearance, so it is
    exactly aligned and the assembled nose sits in it with no interference."""
    gdir, growth_dist, engage_off, engage_dir = _decompose(root_pos, growth_dir, catch_pos)
    # D-GEN-3: ⑤ owns L. L is a Bayer result (working strain ∝ 1/L²), so ⑥ — a compiler (D7) —
    # HONORS it and never re-derives it from the host span. For a WINDOW catch the window is cut at
    # the beam tip, so it tracks L (a longer beam simply catches lower on the wall — that is how
    # hold_retention's lengthened beam still fits a deep box). Whether the required beam actually
    # produces a working catch is judged GEOMETRICALLY, downstream in carve() (the window must
    # engage the receiver's material) — not by second-guessing L here. Absent a resolved L
    # (defaults), fall back to the host span.
    L = growth_dist if g["_from_defaults"] else g["L_hook"]
    canon, segs, nose = _canonical_hook(g, L, engage_off)
    loc = _frame(root_pos, gdir, engage_dir)
    hook = loc * canon
    x0, x_tip, z_tip, h_lead, tip_flat, h_under, protrude, nose_h = nose

    # window cutter, in the hook's frame: spans from just inside the beam outer face, out through
    # the nose tip + margin (the mount thickness), width = b + 2·clearance, over the nose z-band.
    cl = CLEARANCE
    win_w = g["b"] + 2 * cl
    x_lo, x_hi = engage_off - cl, x_tip + 4.0          # through the mount, past the nose tip
    z_lo, z_hi = z_tip - nose_h - cl, z_tip + cl
    cutter_local = Pos((x_lo + x_hi) / 2, 0, (z_lo + z_hi) / 2) * Box(x_hi - x_lo, win_w, z_hi - z_lo)
    window = loc * cutter_local

    root_w = (loc * Pos(engage_off - CLEARANCE - g["h_root"] / 2, 0, 0)).position
    nose_w = (loc * Pos(x_tip, 0, z_tip - h_lead)).position
    # world directions of the local beam (+Z) and engage (+X) axes, for Tier1 re-measurement
    gw = (loc * Pos(0, 0, 1)).position - loc.position
    ew = (loc * Pos(1, 0, 0)).position - loc.position
    d = HookDims(side_tag=tag, y=g["y_undercut"], h_root=g["h_root"], h_tip=g["h_root"] / 2,
                 L=L, b=g["b"], alpha_in=g["alpha_in_deg"], alpha_out=g["alpha_out_deg"],
                 root_xyz=(root_w.X, root_w.Y, root_w.Z), nose_tip_xyz=(nose_w.X, nose_w.Y, nose_w.Z),
                 from_defaults=g["_from_defaults"], growth_dir=(gw.X, gw.Y, gw.Z),
                 engage_dir=(ew.X, ew.Y, ew.Z), protrude=protrude, embed=EMBED)
    return hook, d, loc, window, win_w


def carve(pieces: dict, inst, bindings, immutable_pids=frozenset()) -> CarveResult:
    """Grow hooks (beam_root bindings) and cut windows (catch_window bindings), using ONLY anchor
    geometry — host-agnostic (D-GEN-1). `immutable_pids` are pieces the assembly may NOT modify
    (role='retained' — a foreign part such as a board/PCB); a window catch on such a receiver is
    GEOM_INFEASIBLE (it needs an edge-overhang catch instead — M-G-1 / D-GEN-4)."""
    hook_binds, catch_binds = [], []
    for bd in bindings:
        if bd.port == "beam_root":
            hook_binds.append(bd)
        elif bd.port == "catch_window":
            catch_binds.append(bd)
    if not hook_binds or not catch_binds:
        raise ValueError("snap_hook carve needs beam_root and catch_window bindings")

    g = _geom(inst)
    # pair hooks to catches by the left/right side token in the anchor name (a naming contract,
    # NOT a host-type branch): the IR pairs them; we honour that pairing.
    def side(anchor):  # "…left"/"…right" -> a pairing token; falls back to index
        return "left" if anchor.endswith("left") else ("right" if anchor.endswith("right") else anchor)
    catch_by_side = {side(b.anchor): b for b in catch_binds}

    parts = {pid: tr.part for pid, tr in pieces.items()}
    tags, dims = {}, []
    for hb in hook_binds:
        s = side(hb.anchor)
        cb = catch_by_side.get(s) or catch_binds[len(dims) % len(catch_binds)]
        # D-GEN-4: a window catch cuts the receiver. If the receiver is RETAINED (a foreign,
        # immutable part — the board clip's PCB), cutting it is illegal: that host needs an
        # edge-overhang catch (grab the edge, cut nothing), which is unimplemented (M-G-1). This is
        # the true, domain-honest reason the board clip is infeasible — independent of any L/nose
        # geometry coincidence, so it cannot false-pass.
        if cb.piece_id in immutable_pids:
            raise StageFailure(
                "compile", "GEOM_INFEASIBLE",
                f"a window catch would cut receiver '{cb.piece_id}', but that piece is RETAINED — a "
                f"foreign, immutable part (e.g. a board/PCB) the assembly may not modify. This host "
                f"needs an EDGE-OVERHANG catch that grabs the part's edge without cutting it "
                f"(M-G-1 / D-GEN-4). Roll back to ④.",
                data={"receiver": cb.piece_id, "tag": s})
        root_a = pieces[hb.piece_id].anchors[hb.anchor]
        catch_a = pieces[cb.piece_id].anchors[cb.anchor]
        hook, d, _loc, window, _w = build_hook_at(
            root_a.position, root_a.normal, catch_a.position, g, s)
        parts[hb.piece_id] = parts[hb.piece_id] + hook
        tags[f"hook_{s}"] = hook
        # D-GEN-3/-4: the catch is real only if the window (cut at the beam tip, so it tracks ⑤'s L)
        # actually removes receiver material. If the required beam overshoots the catch — as the
        # board clip's does: a window catch grown +Z past a board edge lands in open air — the nose
        # engages nothing. That is GEOM_INFEASIBLE at ⑥ (rollback to ④), NOT a silent bad geometry.
        recv = parts[cb.piece_id]
        engaged = window & recv
        vol = engaged.volume if engaged.solids() else 0.0
        if not g["_from_defaults"] and vol < ENGAGE_MIN_VOL:
            raise StageFailure(
                "compile", "GEOM_INFEASIBLE",
                f"required beam (L={d.L:.1f} mm) overshoots the catch: its window at the beam tip "
                f"removes {vol:.1f} mm³ from receiver '{cb.piece_id}' (need ≥ {ENGAGE_MIN_VOL}) — the "
                f"nose engages nothing. This host has an EDGE-OVERHANG catch, not a window "
                f"(M-G-1 / D-GEN-4). Roll back to ④.",
                data={"engaged_volume_mm3": vol, "L": d.L, "receiver": cb.piece_id, "tag": s})
        parts[cb.piece_id] = recv - window                 # window aligned to the nose (same frame)
        tags[f"window_cut_{s}"] = window
        dims.append(d)

    return CarveResult(parts=parts, tags=tags, dims=dims,
                       meta={"n_hooks": len(dims), "from_defaults": g["_from_defaults"]})


# --- collision primitives (D18/D21): canonical (frame-relative) so collision_hint stays host- ---
# agnostic. The compile step transforms them by the same anchor frame carve() used.
def collision_primitives(inst):
    """Convex approximation of ONE hook in its canonical frame (mm): the beam box stack + a nose
    box. No host dimensions — the compile step places these by the anchor frame. Format matches
    the M0 MJCF primitives (type/pos/size half-extents)."""
    g = _geom(inst)
    # canonical hook with a representative length (compile places by the anchor frame). engage_off
    # = 0 → the beam outer face is the local origin, matching how the frame is applied.
    _canon, segs, nose = _canonical_hook(g, g["L_hook"], 0.0)
    x0, x_tip, z_tip, h_lead, tip_flat, h_under, protrude, nose_h = nose
    prims = []
    for (cx, h, cz, dz) in segs:
        prims.append({"type": "box", "tag": "beam", "pos": (cx, 0.0, cz),
                      "size": (h / 2, g["b"] / 2, dz / 2)})
    prims.append({"type": "box", "tag": "nose", "pos": ((x0 + x_tip) / 2, 0.0, z_tip - nose_h / 2),
                  "size": (protrude / 2, g["b"] / 2, nose_h / 2)})
    return prims


def collision_selfcheck(inst) -> dict:
    """Clearance-retention self-check (D18): window width (b+2·clearance) − nose width (b) leaves
    the snap gap in the collision model. Host-agnostic (widths only)."""
    g = _geom(inst)
    b = g["b"]
    gap = ((b + 2 * CLEARANCE) - b) / 2
    return {"window_width_mm": b + 2 * CLEARANCE, "nose_width_mm": b,
            "clearance_each_side_mm": gap, "retained": abs(gap - CLEARANCE) < 1e-9 and gap > 0,
            "note": "window (b+2·clearance) preserves the snap gap around the nose (D18)"}
