"""Tier1 re-measurement (SNAPFIT §5.3, MECHSYNTH §4 stage 8).

The check the whole "compile from an IR" story lives or dies on: re-measure L/h/b/y from the
COMPILED STEP geometry (the tagged hook solid's extents along its own axes + the Tier0 undercut),
NOT from the IR, and compare. |IR − measured| > 0.05 mm ⇒ StageFailure(COMPILE_DRIFT). This is
what catches a compiler bug that the IR-trusting formula check cannot see (M0's lesson, one level
up): Tier1 inputs must come from geometry.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pipeline.stage_failure import StageFailure

DRIFT_TOL = 0.05  # mm


@dataclass
class Remeasurement:
    rows: list           # (name, ir, measured, drift, ok)
    ok: bool


def _extent(verts, direction) -> float:
    d = np.array(direction, float); d /= np.linalg.norm(d)
    proj = [float(np.dot(v, d)) for v in verts]
    return max(proj) - min(proj)


def remeasure_hook(hook_solid, dims, undercut_measured_mm: float) -> dict:
    """Measure L, h, b, y from the tagged hook solid along its own (growth, engage, width) axes."""
    verts = [(v.X, v.Y, v.Z) for v in hook_solid.vertices()]
    g = np.array(dims.growth_dir, float); g /= np.linalg.norm(g)
    e = np.array(dims.engage_dir, float); e /= np.linalg.norm(e)
    w = np.cross(g, e)
    # growth extent = beam length + root embed; engage extent = beam thickness + nose protrude
    L_meas = _extent(verts, g) - dims.embed
    h_meas = _extent(verts, e) - dims.protrude
    b_meas = _extent(verts, w)
    y_meas = undercut_measured_mm            # geometric undercut from Tier0 (§5.2b)
    return {"L": L_meas, "h": h_meas, "b": b_meas, "y": y_meas}


def remeasure_hinge(tags: dict, axis_dir=(1.0, 0.0, 0.0)) -> dict:
    """Measure pin_d, pin_len, bore_d, knuckle_od from the COMPILED hinge tags via each solid's
    bounding box (a cylinder BREP has only seam vertices, so a vertex-extent undercounts its
    diameter — the bbox is the honest cross measure). The hinge axis is world +X here, so the box's
    axial size is the length and the larger of the two cross sizes is the diameter."""
    ax = np.array(axis_dir, float); ax /= np.linalg.norm(ax)
    axis_i = int(np.argmax(np.abs(ax)))          # which world axis the hinge runs along (X here)
    cross = [i for i in range(3) if i != axis_i]

    def sizes(solid):
        bb = solid.bounding_box()
        return [bb.size.X, bb.size.Y, bb.size.Z]

    def diam(solid):
        s = sizes(solid); return max(s[cross[0]], s[cross[1]])

    m = {"pin_d": diam(tags["pin"]), "pin_len": sizes(tags["pin"])[axis_i],
         "bore_d": diam(tags["bore"])}
    kn = next(v for k, v in tags.items() if k.startswith("knuckle_"))
    m["knuckle_od"] = diam(kn)
    return m


def check_drift(dims, measured: dict, ir_params: dict | None = None) -> Remeasurement:
    """Compare the geometry-measured L/h/b/y against the IR. The IR reference is ⑤'s RESOLVED
    parameters (ir_params) — NOT the compiled HookDims. That distinction is the whole point: if the
    reference were the compiled dims, both sides would trace to ⑥ and a ⑤↔⑥ disagreement (e.g. ⑤
    resolves L=12 but ⑥ builds L=7) would be invisible — exactly the blind spot that let a 5 mm L
    drift through on the panel. Callers in the pipeline MUST pass ir_params from the resolved plan;
    the dims fallback exists only for direct unit tests with no resolve step."""
    ir = ir_params or {"L": dims.L, "h": dims.h_root, "b": dims.b, "y": dims.y}
    rows, ok_all = [], True
    for k in ir:
        drift = abs(ir[k] - measured[k])
        ok = drift <= DRIFT_TOL
        ok_all = ok_all and ok
        rows.append((k, round(ir[k], 4), round(measured[k], 4), round(drift, 4), ok))
    r = Remeasurement(rows=rows, ok=ok_all)
    if not ok_all:
        bad = [f"{k}: IR {i} vs measured {m} (drift {d})" for k, i, m, d, o in rows if not o]
        raise StageFailure("t1", "COMPILE_DRIFT",
                           "re-measured geometry disagrees with the IR: " + "; ".join(bad),
                           data={"rows": rows})
    return r
