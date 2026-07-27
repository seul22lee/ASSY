# BM-001 Golden Stage Outputs

## Benchmark

**BM-001 — Latching Storage Box**

This document defines the expected information depth and responsibility boundary for each stage of the ASSY pipeline.

It is not a single hidden correct design. Different mechanically coherent solutions are acceptable.

The representative path used here is:

> Separate pin hinge + reusable elastic cantilever release latch + body-side catch + low-cost two-piece enclosure

The purpose of the representative path is to make downstream outputs concrete enough to evaluate.

---

# 01 Requirement Interpreter

## Responsibility

Translate the user request into a structured engineering contract.

Do not select a latch mechanism, hinge mechanism, material, process, layout, or detailed geometry.

## Expected product intent

Create a compact reusable storage product that provides an enclosed storage volume, allows repeated intentional access, and remains securely closed during normal handling and transport.

## Expected user-intent summary

A compact desktop storage box with a reusable latch that is easy to operate, resists accidental opening, remains secure during transport, and can be manufactured and assembled economically.

## Expected requirements

- Provide an enclosed storage volume.
- Permit intentional access to the storage volume.
- Open repeatedly.
- Close repeatedly.
- Maintain the closed state until intentional release.
- Resist accidental opening during normal handling.
- Remain securely closed during transport.
- Permit intentional release by the user.
- Be practical and easy to operate.
- Prefer one-handed operation, but do not require it.
- Fit a practical desktop scale.
- Support low-cost manufacturing.
- Support practical assembly.
- Remain mechanically plausible under repeated use.

## Expected behavioural decomposition

### Repeated opening

- Actor: user
- Action: open
- Object: access closure
- Condition: intentional access
- Input: displacement or force
- Output: open state
- Character: repeated/cyclic

### Repeated closing

- Actor: user
- Action: close
- Object: access closure
- Condition: after use
- Input: displacement
- Output: closed state
- Character: repeated/cyclic

### Closed-state retention

- Actor: product
- Action: maintain
- Object: closed state
- Condition: absent intentional release
- Input: unspecified disturbance or external handling load
- Output: maintained state
- Character: held

### Intentional release

- Actor: user
- Action: release
- Object: retention state
- Condition: intentional operation
- Input: force or displacement
- Output: released state
- Character: single event within a repeated cycle

## Expected operating scenarios

### Repeated normal access

The user opens the product, accesses the storage volume, and closes it again repeatedly.

### Closed normal handling

The closed product is lifted, repositioned, or handled without accidental opening.

### Transport

The closed product experiences ordinary movement, vibration, and orientation changes while remaining secured.

## Expected design freedoms

- Latch mechanism
- Hinge mechanism
- Material
- Manufacturing process
- Wall construction
- Fastening strategy
- Internal organization
- Overall appearance
- Opening angle
- Separate metal fastener permitted
- Multiple engineering solutions acceptable

## Forbidden Stage 01 outputs

- Cantilever snap latch selected
- Living hinge selected
- Magnet selected
- Screw closure selected
- Injection molding selected
- Additive manufacturing selected
- Fixed wall thickness
- Fixed hinge-pin diameter
- Fixed latch location

---

# 02 Mechanical Architecture

## Responsibility

Generate mechanically distinct architecture candidates and select or retain suitable candidates using structured Stage 01 information.

Do not generate detailed feature geometry or exact dimensions.

## Expected functional chain

- Provide an enclosure opening.
- Move a closure between open and closed states.
- Retain the closure in the closed state.
- Resist accidental release.
- Receive intentional user input.
- Release retention.
- Permit repeated cycling.
- Limit opening travel.
- Transfer retention loads into the enclosure structure.

## Expected candidate set

### Candidate A — Elastic cantilever retention

**Principle**

An elastic member deflects during engagement and release, then recovers to retain a rigid catch.

**Conceptual roles**

- Enclosure body
- Lid or closure
- Rotational opening interface
- Elastic retention member
- Mating catch
- User release interface
- Opening stop

**Advantages**

- Low part count
- Compact
- Potentially one-handed
- Fast operation
- Easy integration into molded or printed parts

**Risks**

- Root fatigue
- Creep
- Excessive insertion or release force
- Tolerance sensitivity
- Material dependence

### Candidate B — Sliding bolt latch

**Principle**

A guided translational member enters or leaves a receiver to block or permit closure motion.

**Conceptual roles**

- Closure
- Guided slider
- Receiver
- User actuation surface
- Slider retention feature

**Advantages**

- Clear locked/unlocked state
- Low elastic-strain dependence
- Broad material compatibility

**Risks**

- Added parts
- Jamming
- Debris sensitivity
- Accidental slider movement
- Assembly complexity

### Candidate C — Over-centre lever latch

**Principle**

A lever passes over centre and maintains clamping force in the locked state.

**Advantages**

- Strong retention
- Clear state
- Good transport security

**Risks**

- Protruding hardware
- More parts
- Larger envelope
- Higher manufacturing and assembly cost

## Representative selection

**Elastic cantilever retention**

## Expected selected architecture content

- Physical principle
- Functional chain
- Conceptual element roles
- Retention and release relations
- Opening relation
- Conceptual load-transfer path
- Support obligations
- Spatial implications
- Risks
- Requirement traceability
- Unresolved product-level decisions

## Expected obligations for Stage 03+

- Retention member requires a structurally supported root.
- Catch must resist opening load.
- Release surface must remain accessible.
- Accidental gripping force should not align with release direction.
- Opening motion requires a defined rotational or translational interface.
- Opening travel requires a stop.
- Retention and release geometry must not obstruct storage volume.

---

# 03 Product Architecture

## Responsibility

Organize the selected mechanical architecture into a complete product.

## Expected major product pieces

- Main body
- Lid
- Separate hinge pin
- Optional pin retainer or integrated retention feature

The representative design integrates the elastic latch into the lid and the catch into the body.

## Expected product regions

- Enclosed storage volume
- Rear hinge region
- Front retention region
- Front user-release access region
- Lid rotational envelope
- Base support region
- Lid/body overlap region
- Assembly access region

## Expected spatial organization

- Storage volume occupies the body interior.
- Hinge axis lies along the rear upper edge.
- Latch sits opposite the hinge.
- Release surface is externally reachable.
- Catch sits on the body front wall.
- Latch deflection space does not obstruct stored contents.
- Lid opening envelope clears the body.
- Hinge-pin insertion path remains available.

## Expected load paths

### Retention load

Lid → latch hook → body catch → reinforced front wall → body walls/base

### Hinge load

Lid → lid knuckles → pin → body knuckles → rear wall

## Expected assembly strategy

1. Manufacture body and lid.
2. Align hinge knuckles.
3. Insert hinge pin.
4. Apply positive axial retention.
5. Close lid and verify engagement.

## Expected unresolved decisions

- Hinge knuckle count
- Pin retention method
- Latch-arm orientation
- Release direction
- Lid overlap depth
- Storage dimensions
- Material
- Process

---

# 04 Spatial Concept Analysis

## Responsibility

Create a non-authoritative visual-spatial blueprint and identify placement contradictions.

## Expected views

- Closed isometric
- Open isometric
- Front section through latch
- Rear section through hinge
- Exploded assembly
- Side motion-envelope view

## Expected annotations

- Hinge axis
- Latch location
- Release direction
- Latch deflection direction
- Catch engagement
- Storage volume
- Lid opening envelope
- Hinge-pin insertion direction

## Expected visual-spatial review

Potential issues should include:

- Latch root too thin
- Catch wall insufficiently reinforced
- Release pad exposed to accidental gripping
- Lid rear-edge interference
- Missing pin retention
- Deflection volume intruding into storage
- Inaccessible assembly direction

The image is not engineering truth. The output is a structured issue list for Stage 05.

---

# 05 Engineering Integration

## Responsibility

Use LLM reasoning to synthesize the actual parametric part topology, interfaces, feature sequence, and engineering commitments.

## Expected part topology

### Body

- Rounded rectangular enclosure shell
- Internal storage cavity
- Rear hinge knuckles
- Front catch ledge
- Local catch reinforcement
- Lid-overlap receiving rim
- Stable base
- Optional local ribs

### Lid

- Shallow shell
- Rear hinge knuckles
- Integrated cantilever latch arm
- Hook head
- External release pad
- Root fillet
- Overlap skirt
- Opening stops

### Hinge pin

- Cylindrical pin
- Insertion lead-in
- Positive axial retention feature

## Expected parametric feature program

The program should include symbolic parameters for:

- Body length, width, height
- Wall thickness
- Lid overlap
- Latch length, width, root thickness, tip thickness
- Hook depth
- Lead-in and retention angles
- Root radius
- Release travel
- Hinge diameter and clearances
- Opening-stop angle

Expected feature sequence:

- Build outer shells
- Hollow body and lid
- Add overlap features
- Generate hinge knuckles
- Generate latch relief slots
- Generate tapered cantilever
- Generate hook and release pad
- Add root fillet
- Add catch and reinforcement
- Add opening stops
- Add pin-retention geometry

## Expected engineering commitments

- Separate pin hinge
- Integral lid latch
- Body-side catch
- Intentional release deflects latch away from catch
- Accidental gripping does not align with release
- Reinforced latch root and catch
- Positive hinge-pin retention
- Dedicated opening stop
- Defined storage-clearance envelope

## Expected engineering problems

- Latch strain
- Insertion force
- Release force
- Retention force
- Creep and fatigue
- Hook/catch tolerance
- Hinge interference
- Storage-volume interference
- Pin insertion
- Catch-wall strength
- Process compatibility

## Stage 05 exit condition

- Part identities fixed
- Topology fixed
- Symbolic parameters declared
- Interfaces declared
- Motion envelope declared
- Assembly sequence declared
- Critical checks linked
- Stage 06 only needs numerical closure

---

# 06 Parametric Solver

## Responsibility

Solve dimensions and coupled constraints without changing topology.

## Representative solved output

### Product envelope

- Body length: 120 mm
- Body width: 80 mm
- Body height: 45 mm

### Walls

- Nominal wall: 2.2 mm
- Catch wall: 3.0 mm
- Hinge wall: 3.0 mm
- Lid overlap clearance: 0.35 mm

### Hinge

- Pin diameter: 3.0 mm
- Pin clearance: 0.20 mm
- Knuckle outer diameter: 6.2 mm
- Axial clearance: 0.25 mm
- Opening angle: 105 degrees

### Latch

- Arm length: 24 mm
- Root thickness: 1.8 mm
- Tip thickness: 1.25 mm
- Width: 12 mm
- Hook depth: 1.8 mm
- Root radius: 1.5 mm
- Release travel: 2.2 mm
- Engagement overlap: 1.2 mm
- Catch clearance: 0.30 mm

## Expected solver checks

- Hinge axes align.
- Lid clears body during rotation.
- Release travel exceeds engagement overlap with margin.
- Latch stays outside storage volume.
- Wall and fillet minima are satisfied.
- Catch engagement remains feasible across tolerance.
- Crank or mechanism assumptions are not introduced.

---

# 07 CAD Builder

## Responsibility

Execute the Stage 05 feature program using Stage 06 values.

Do not redesign the product.

## Expected artifacts

- body.step
- lid.step
- hinge_pin.step
- assembly.step
- native source models
- body.stl
- lid.stl
- hinge_pin.stl
- rendered views

## Expected semantic references

- lid.latch.root
- lid.latch.arm
- lid.latch.hook
- body.catch.engagement_face
- body.hinge.axis
- lid.hinge.axis
- lid.stop.contact_face
- storage.volume

## Build acceptance

- Valid solids
- No non-manifold geometry
- Latch arm physically separated by relief
- Hinge bores coaxial
- No gross assembly interference
- Semantic references remain stable
- Opening path exists

---

# 08 Validation Planning

## Responsibility

Define evidence needed for each requirement.

## Expected validation set

- Lid opening/closing kinematics
- Latch insertion force
- Latch release force
- Peak latch strain
- Closed-state retention
- Transport disturbance resistance
- Hinge swept-envelope collision
- Opening-stop contact
- Assembly insertion path
- Selected-process manufacturability
- Storage-volume measurement
- One-handed accessibility assessment

Each test must include:

- Linked requirement
- Claim
- Backend
- Inputs
- Assumptions
- Observable
- Pass criterion
- Validity domain

---

# 09 Validation Execution

## Expected representative evidence

- Lid reaches 105 degrees.
- No unintended collision.
- Latch clears catch after intentional release.
- Insertion force measured.
- Release force measured.
- Peak strain measured.
- Retention load measured.
- Transport disturbance retains closure.
- Hinge-pin insertion path exists.
- Manufacturing checks complete.

---

# 10 Metric Extraction

## Expected metrics

- Lid opening angle
- Simulated cycle count
- Latch insertion force
- Latch release force
- Peak latch strain
- Retention opening load
- Usable storage volume
- Collision count
- Engagement success
- Release success
- Transport retention result
- Assembly-path result

Do not evaluate requirements in this stage.

---

# 11 Requirement Evaluation

## Responsibility

Compare valid evidence with each requirement.

Expected statuses include:

- PASS
- FAIL
- INVALID_TEST
- INSUFFICIENT_EVIDENCE
- NOT_SCORED for preferences where appropriate

Expected evaluation topics:

- Enclosed storage
- Intentional access
- Repeated opening
- Repeated closing
- Closed-state retention
- Accidental-opening resistance
- Transport security
- Intentional release
- Ease of operation
- One-handed preference
- Desktop scale
- Low-cost manufacturing
- Assembly practicality
- Mechanical plausibility

Do not claim PASS for vague requirements without an explicit evidence criterion.

---

# 12 Revision Routing

## Responsibility

Route failure to the earliest incorrect design decision.

## Expected routing examples

### Excessive release force

Return to Engineering Integration or Parametric Solver.

Targets:

- Latch length
- Thickness
- Root transition
- Release leverage

Preserve:

- Product architecture
- Hinge
- Storage volume

### Excessive latch strain

Return to Engineering Integration.

Targets:

- Latch topology
- Root geometry
- Material assumption

Escalate to Mechanical Architecture only if the elastic-latch principle is unsuitable.

### Transport retention failure

Return to Engineering Integration or Mechanical Architecture depending on whether local geometry or the retention principle is responsible.

### Invalid test

Return to Validation Planning, not to design.

---

# Golden success criterion

BM-001 succeeds when the pipeline can transform abstract closure requirements into a complete product in which:

- Access is repeatable.
- Closed-state retention is physically implemented.
- Accidental opening is resisted.
- Intentional release is usable.
- Hinge, latch, catch, enclosure, and stops are geometrically integrated.
- The parametric geometry is generated by the LLM rather than selected from a fixed geometry card.
- Deterministic checks and evidence validate the result.
