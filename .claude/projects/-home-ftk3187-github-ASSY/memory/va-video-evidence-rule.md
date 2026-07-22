---
name: va-video-evidence-rule
description: STANDING RULE for every V-A physics video (m21+) — markers, HUD DoF counter, full criterion window
metadata:
  type: feedback
---

Every V-A verification video MUST satisfy three requirements, or it is **not review evidence**:
(a) at least one **visually asymmetric feature per moving body** (a rotationally symmetric cylinder
looks static while spinning); (b) the **HUD primary-DoF counter** on screen; (c) coverage of the
**full criterion window including the pass moment** (a clip that ends before the gate is not evidence).

**Why:** videos are how a reviewer catches what the numbers hide (the m10 precedent). This rule exists
because the "invisible rotation" defect **recurred twice** — m19 (plain screw cylinder) and m20
(coupling: input shaft, hub, output shaft all symmetric). A green verdict JSON is not enough; the
reviewer must be able to SEE the motion.

**How to apply (the m20 fix, reuse it):**
- Add **visual-only marker geoms** — thin radial tabs, one contrasting colour per moving body,
  `contype=0`/`conaffinity=0` and **zero mass** (MuJoCo default `density=0` gives 0 mass). They add no
  inertia and no contact → physics identical. **Assert it**: run seed0 with vs without markers and check
  the verdict triple is byte-identical (m20 printed `[6.001,0.0,0.0006] == [6.001,0.0,0.0006]`).
- Use a **camera perpendicular to the motion axis** — a near-axial view hides rotation even with markers.
- Capture at a **high rate (e.g. 240 Hz) and emit at 60 fps** for legible slow-motion covering the whole
  drive; the HUD timestamps keep it honest.
- For declared-pair transmissions, also record a **discrimination clip** (break the coupling/equality):
  the input marker sweeps, the output marker stays dead still — the most legible evidence the element
  produces (pairs with the [[declared-pair-self-lock-physics]] discrimination-probe discipline).
