# BM-002 Golden Stage Outputs

## Benchmark

**BM-002 — Enclosed Hand-Cranked Platform Lift**

This document defines the expected information depth and responsibility boundary for each stage of the ASSY pipeline.

It is not a single hidden correct design. Different mechanically coherent solutions are acceptable.

The representative path used here is:

> External hand crank → supported horizontal input shaft → bevel gear pair → vertical lead screw → travelling nut → guided internal platform

The purpose of the representative path is to make downstream outputs concrete enough to evaluate.

---

# 01 Requirement Interpreter

## Responsibility

Translate the user request into a structured engineering contract.

Do not select a transmission, shaft layout, guide arrangement, support strategy, material, process, or detailed geometry.

## Expected product intent

Create a compact manually operated desktop device that uses external rotational user input to repeatedly raise and lower an internal load-supporting platform through a specified vertical travel while keeping the mechanism enclosed and operating safely and stably.

## Expected user-intent summary

A compact enclosed platform-lifting product operated by an external hand crank. The internal platform must move upward and downward approximately 80–100 mm, support about 1 kg, avoid obvious jamming or unstable operation, and remain practical to assemble and manufacture.

## Expected requirements

- Provide an external hand-crank input.
- Raise an internal platform.
- Lower the internal platform.
- Provide approximately 80–100 mm of travel.
- Support approximately 1 kg.
- Permit repeated lifting cycles.
- Keep platform motion adequately guided.
- Avoid obvious jamming.
- Avoid unstable operation.
- Enclose the mechanism within the housing.
- Use manual operation only.
- Fit a practical desktop scale.
- Be safe to use.
- Be mechanically plausible.
- Support practical assembly.
- Support practical manufacturing.

## Expected behavioural decomposition

### Crank input

- Actor: user
- Action: rotate
- Object: external hand crank
- Input: manual rotation
- Output: transmitted rotation
- Character: repeated/cyclic
- Directionality: bidirectional or unspecified according to the user statement

### Platform raising

- Actor: product
- Action: raise
- Object: internal platform
- Input: rotation
- Output: upward translation
- Character: continuous or intermittent, intentionally open

### Platform lowering

- Actor: product
- Action: lower
- Object: internal platform
- Input: reverse commanded rotation
- Output: downward translation
- Character: continuous or intermittent, intentionally open

### Payload support

- Actor: platform
- Action: support
- Object: payload
- Input: load
- Output: maintained supported state
- Character: held throughout travel and pauses

## Expected quantitative bounds

- Platform travel: 80–100 mm, bounded and approximate
- Payload mass: approximately 1 kg

## Expected operating scenarios

### Rated-load raising

The user rotates the crank to raise the platform with approximately 1 kg through the required travel.

### Rated-load lowering

The user rotates the crank in the opposite commanded direction to lower the platform with approximately 1 kg.

### Intermediate pause

Input stops during travel. The product must avoid dangerous descent or instability. Self-locking is optional, not mandatory.

### End-of-travel approach

The platform approaches upper or lower limits without destructive interference or obvious jamming.

### Repeated cycling

The mechanism performs repeated raise/lower cycles.

## Expected design freedoms

- Transmission architecture
- Continuous or intermittent lifting
- Self-locking or controlled back-driving
- Shaft count
- Bearing arrangement
- Guide count and arrangement
- Support architecture
- Internal layout
- Housing proportions
- Material
- Manufacturing process
- Assembly architecture

## Forbidden Stage 01 outputs

- Lead screw selected
- Rack-and-pinion selected
- Cable drum selected
- Bevel gears selected
- Dual guides selected
- Gear ratio
- Screw pitch
- Bearing placement
- Housing dimensions
- Shaft diameter

---

# 02 Mechanical Architecture

## Responsibility

Generate and compare mechanically distinct physical-principle candidates.

Do not generate detailed geometry or exact dimensions.

## Expected functional chain

- Receive manual crank rotation.
- Support the rotating input.
- Transmit torque across the enclosure boundary.
- Transform or redirect motion.
- Produce vertical translation.
- Move the platform.
- Guide the platform.
- Support the payload.
- Control or tolerate reverse motion.
- Limit travel.
- Transfer loads into the housing.

## Expected candidate set

### Candidate A — Vertical lead screw

**Principle**

A rotating screw drives a translating nut connected to the platform.

**Conceptual roles**

- Hand crank
- Input shaft
- Rotational supports
- Optional right-angle transmission
- Lead screw
- Travelling nut
- Platform
- Linear guides
- Axial thrust support
- Travel stops

**Advantages**

- Mechanical advantage
- Predictable translation
- Compact vertical packaging
- Possible self-locking
- Good holding behaviour

**Risks**

- Friction
- Low efficiency
- Binding under guide misalignment
- Axial-thrust support requirement
- Screw buckling
- Thread-quality dependence

### Candidate B — Rack and pinion

**Principle**

A rotating pinion drives a vertically translating rack attached to the platform.

**Conceptual roles**

- Hand crank
- Input shaft
- Pinion
- Rack
- Platform
- Guides
- Shaft supports
- Optional holding feature
- Travel stops

**Advantages**

- Direct motion conversion
- High efficiency
- Predictable kinematics
- Faster travel

**Risks**

- Back-driving
- Mesh alignment
- Tooth loading
- Debris sensitivity
- Separate holding strategy may be needed

### Candidate C — Cable drum

**Principle**

A crank-driven drum winds or unwinds a flexible tension member connected to the platform.

**Conceptual roles**

- Hand crank
- Supported drum shaft
- Drum
- Cable or belt
- Platform attachment
- Guides
- Idlers if required
- Brake, ratchet, counterbalance, or other reverse-motion control
- Travel stops

**Advantages**

- Flexible packaging
- Long travel
- Reduced rigid transmission count

**Risks**

- Slack
- Winding consistency
- Uneven loading
- Back-driving
- Retention requirement
- Durability

### Candidate D — Crank-slider or scissor-derived lift

Potentially valid but less attractive for this envelope due to nonlinear motion, dead-centre behaviour, lateral space, and torque variation.

## Representative selection

**Horizontal input shaft + bevel pair + vertical lead screw + travelling nut + dual guides**

## Expected selected architecture content

- Primary physical principle
- Secondary transmission principle
- Functional chain
- Conceptual element roles
- Motion relations
- Force and load path
- Support obligations
- Holding/back-drive strategy
- Major interfaces
- Spatial implications
- Risks
- Requirement traceability
- Unresolved product-level decisions

## Expected obligations for Stage 03+

- Input shaft requires radial support.
- Lead screw requires radial support and axial-thrust support.
- Travelling nut requires anti-rotation.
- Platform requires guidance independent of the screw thread.
- Guide spacing must resist eccentric payload.
- Full platform swept volume must remain clear.
- Transmission must remain enclosed.
- Crank must remain externally accessible.
- Travel limits must be positive and non-destructive.
- Service access must exist.

---

# 03 Product Architecture

## Responsibility

Organize the selected mechanical architecture into a complete enclosed product.

## Expected major product pieces

- Main housing
- Service cover
- Lifting platform
- Hand crank
- Input shaft
- Shaft support elements
- Bevel pinion
- Bevel gear
- Lead screw
- Travelling nut or carriage
- Left guide
- Right guide
- Upper screw support
- Lower thrust/radial support
- Travel stops
- Retaining elements
- Fasteners where justified

## Expected product regions

- External user-interface zone
- Lower transmission compartment
- Vertical lifting chamber
- Platform swept volume
- Payload envelope
- Left guide-support zone
- Right guide-support zone
- Upper screw-support zone
- Lower thrust-support zone
- Service-access zone
- Stable base region

## Expected spatial organization

- Crank on the front or side housing wall.
- Horizontal input shaft enters the enclosed transmission compartment.
- Bevel pair redirects motion to the vertical screw.
- Screw lies near the platform load centre.
- Guides lie on opposite sides of the screw.
- Platform travels inside a protected vertical chamber.
- Payload area remains accessible.
- Service cover exposes the lower transmission.
- Crank sweep clears the desktop.
- Platform sweep clears all supports and gears.

## Expected load paths

### Payload

Payload → platform → nut/carriage and guide interfaces → screw/guides → lower support and housing columns → base → desktop

### User torque

Crank → input shaft → bevel pair → lead screw → nut → platform

### Eccentric payload

Off-centre payload → platform → guide sliders → guide supports → housing

## Expected assembly strategy

1. Install lower screw support.
2. Assemble lead screw and lower bevel gear.
3. Install upper screw support.
4. Install input shaft and supports.
5. Set bevel mesh.
6. Install guide elements.
7. Install travelling nut or carriage.
8. Attach platform.
9. Install travel stops.
10. Close service cover.
11. Attach crank.

## Expected unresolved decisions

- Crank side
- Transmission location
- Central or offset screw
- Guide type
- Guide spacing
- Platform dimensions
- Service-panel direction
- Housing split
- Holding strategy
- Process
- Material

---

# 04 Spatial Concept Analysis

## Responsibility

Create a non-authoritative spatial blueprint and identify integration contradictions.

## Expected views

- Exterior isometric
- Cutaway isometric
- Front orthographic
- Side section through crank and screw
- Top view showing screw and guide spacing
- Exploded assembly
- Platform at lower position
- Platform at upper position
- Full swept-volume overlay

## Expected annotations

- Crank axis
- Input shaft
- Bevel mesh
- Lead-screw axis
- Upper/lower screw supports
- Guide axes
- Platform lower and upper positions
- Payload envelope
- Service-cover removal direction
- Crank hand clearance
- Transmission partition

## Expected visual-spatial review

Potential issues should include:

- Crank sweep intersects desktop.
- Platform lower position intersects gear envelope.
- Guide spacing is too narrow.
- Upper screw support blocks payload access.
- Service cover is blocked by the crank.
- Carriage interferes with ribs.
- Gear diameter exceeds housing width.
- Screw is too far from payload centre.
- Guides cannot be assembled.
- Full travel is not available.

The output is a structured issue list for Stage 05.

---

# 05 Engineering Integration

## Responsibility

Use LLM reasoning to synthesize the actual parametric part topology, interfaces, feature sequence, and engineering commitments.

## Expected part topology

### Housing

- Tall enclosed shell
- Lower transmission compartment
- Vertical lifting chamber
- Guide-support towers
- Upper screw-support bridge
- Lower thrust-support pocket
- Input-shaft bores
- Service opening
- Crank-clearance recess
- Internal partition
- Stable feet
- Local ribs

### Platform

- Payload-support plate
- Underside reinforcement
- Nut/carriage mount
- Left and right guide interfaces
- Stop-contact features
- Edge clearances

### Lead screw

- Threaded working region
- Lower journal and thrust shoulder
- Upper journal
- Gear interface
- Axial-retention features

### Travelling nut/carriage

- Threaded nut body
- Anti-rotation geometry
- Platform attachment
- Guide-slider integration or interfaces
- Load-transfer ribs
- Assembly access

### Crank/input shaft

- External handle
- Crank arm
- Hub
- Shaft
- Two radial-support interfaces
- Gear interface
- Axial retention

### Guides

The LLM may choose:

- Round rods and bushings
- Prismatic rails
- Integrated channels
- Other mechanically justified guide geometry

## Expected parametric feature program

The program should include symbolic parameters for:

- Housing width, depth, height
- Wall thickness
- Transmission-compartment height
- Platform size
- Platform travel
- Screw diameter and pitch
- Screw-support spacing
- Guide spacing
- Guide size
- Slider length
- Input-shaft diameter
- Bearing/support spacing
- Gear module and tooth count
- Backlash
- Crank radius
- Service-opening size
- Motion clearances
- Travel-stop positions

Expected feature sequence:

- Build housing shell
- Create lifting chamber
- Create transmission compartment
- Create internal partition
- Create guide supports
- Create shaft-support bores
- Create lower thrust-support pocket
- Create upper screw support
- Cut full platform swept volume
- Create service opening
- Create cover interfaces
- Create crank clearance
- Create platform and ribs
- Create nut/carriage interfaces
- Create screw and journals
- Create transmission geometry
- Create guides and sliders
- Create stops and retention features

## Expected engineering commitments

- Horizontal externally actuated input shaft
- Two-point radial support for input shaft
- Right-angle transmission
- Vertical lead screw
- Two-end radial support for screw
- Lower axial-thrust support
- Anti-rotating travelling nut
- Two separated platform guides
- Parallel guide and screw axes
- Enclosed transmission
- Clear platform swept volume
- Positive upper and lower stops
- Positive crank retention
- Service access

## Expected engineering problems

- Crank torque
- Mechanical advantage
- Screw pitch
- Self-locking versus back-driving
- Screw buckling
- Screw torsion
- Thrust support
- Gear load
- Shaft bending
- Guide binding
- Eccentric payload stability
- Nut-to-platform load transfer
- Platform/gear interference
- Housing stiffness
- Crank clearance
- Assembly sequence
- Service access
- End-stop load
- Manufacturing compatibility

## Stage 05 exit condition

- Part topology fixed
- Interfaces fixed
- Symbolic parameters declared
- Equations and inequalities declared
- Motion envelope represented
- Load paths represented
- Assembly sequence represented
- Process assumptions explicit
- Stage 06 only needs numerical closure

---

# 06 Parametric Solver

## Responsibility

Solve dimensions and coupled constraints without changing topology.

## Representative solved output

### Product envelope

- Housing width: 140 mm
- Housing depth: 110 mm
- Housing height: 190 mm
- Base width: 150 mm
- Base depth: 120 mm

### Platform

- Width: 100 mm
- Depth: 80 mm
- Thickness: 6 mm
- Travel: 90 mm
- Lower height: 35 mm
- Upper height: 125 mm

### Payload

- Rated mass: 1.0 kg
- Design vertical load: 14.7 N
- Allowed eccentricity: 25 mm × 20 mm

### Lead screw

- Major diameter: 10 mm
- Pitch: 2 mm/rev
- Threaded length: 125 mm
- Effective length: 155 mm
- Journal diameter: 8 mm

### Crank

- Radius: 55 mm
- Handle length: 30 mm
- Estimated operating force: 8 N maximum target

### Input shaft

- Diameter: 8 mm
- Support spacing: 55 mm

### Bevel gears

- Ratio: 1:1
- Module: 1.25 mm
- Tooth count: 20/20
- Pitch angle: 45 degrees
- Backlash: 0.20 mm

### Guides

- Count: 2
- Diameter: 10 mm
- Spacing: 72 mm
- Slider length: 28 mm
- Running clearance: 0.15 mm

### Housing

- Nominal wall: 2.5 mm
- Guide tower wall: 4.0 mm
- Lower support wall: 5.0 mm
- Partition clearance: 2.0 mm

## Expected solver constraints

- 80 mm ≤ travel ≤ 100 mm
- Platform upper position clears upper support.
- Platform lower position clears transmission.
- Guide spacing resists eccentric payload.
- Crank force remains within selected ergonomic target.
- Screw buckling safety factor is adequate.
- Guide axes remain parallel.
- Bevel gear geometry is compatible.
- Fits and clearances are manufacturable.
- Full moving envelopes remain within housing.

## Expected solver failure classes

- Infeasible product envelope
- Excessive crank effort
- Screw buckling failure
- Platform/transmission collision
- Gear too large for housing
- Guide spacing incompatible with platform
- Underdetermined friction/material assumptions

---

# 07 CAD Builder

## Responsibility

Execute the Stage 05 feature program using Stage 06 values.

Do not redesign the product.

## Expected artifacts

- main_housing.step
- service_cover.step
- lifting_platform.step
- hand_crank.step
- input_shaft.step
- bevel_pinion.step
- bevel_gear.step
- lead_screw.step
- travelling_nut_carriage.step
- left_guide.step
- right_guide.step
- upper_support.step
- lower_thrust_support.step
- retainers.step
- full_assembly.step
- exploded_assembly.step
- motion model
- simulation asset

## Expected semantic references

- housing.input_shaft_bore_front
- housing.input_shaft_bore_rear
- housing.lower_thrust_seat
- housing.upper_screw_support
- housing.left_guide_axis
- housing.right_guide_axis
- platform.payload_surface
- platform.nut_mount
- platform.left_slider
- platform.right_slider
- lead_screw.axis
- lead_screw.threaded_region
- bevel_pair.mesh_reference
- crank.rotation_axis
- platform.lower_stop_face
- platform.upper_stop_face

## Build acceptance

- Valid solids
- Housing cavity exists
- Service opening exists
- Screw and guide axes align
- Gear pair has valid geometry
- Platform completes full travel
- No gross swept-volume interference
- Crank clears housing and desktop
- All rotating elements have supports
- Nut cannot rotate independently
- Service cover can be removed

---

# 08 Validation Planning

## Responsibility

Define evidence needed for each requirement and major engineering claim.

## Expected validation set

- Platform-travel measurement
- Rated-load raising
- Rated-load lowering
- Crank-effort calculation
- Platform guidance
- Tolerance-aware jamming sweep
- Eccentric-load platform stability
- Screw strength and buckling
- Input-shaft bending
- Thrust-support capacity
- Housing swept-volume interference
- End-stop behaviour
- Holding/back-drive behaviour
- Assembly feasibility
- Service access
- Manufacturability
- Enclosure compliance
- Repeated cycling

Each test must include:

- Linked requirement
- Claim
- Backend
- Assumptions
- Input artifacts
- Load case
- Observable
- Pass criterion
- Validity domain

---

# 09 Validation Execution

## Expected representative evidence

- Travel measured at 90 mm.
- Platform raises 1 kg.
- Platform lowers 1 kg without uncontrolled descent.
- Crank force measured or calculated.
- Full motion completes without binding.
- Eccentric payload remains stable.
- Screw buckling margin calculated.
- Shaft deflection calculated.
- No gross collision detected.
- Holding/back-drive behaviour characterized.
- Assembly sequence validated.
- Service access validated.
- Manufacturing checks completed.

---

# 10 Metric Extraction

## Expected metrics

- Platform travel
- Supported payload
- Peak crank force
- Crank turns per full travel
- Full-cycle time
- Maximum platform tilt
- Guide-binding count
- Collision count
- Screw buckling safety factor
- Shaft deflection
- Assembly operation count
- Holding/back-drive result
- Enclosure result
- Service-access result

Do not evaluate requirements in this stage.

---

# 11 Requirement Evaluation

## Responsibility

Compare valid evidence with each requirement.

Expected evaluation topics:

- External hand crank
- Raising
- Lowering
- 80–100 mm travel
- Approximately 1 kg payload
- Repeated operation
- Platform guidance
- No obvious jamming
- No unstable operation
- Enclosed mechanism
- Manual-only operation
- Desktop scale
- Safety
- Mechanical plausibility
- Assembly practicality
- Manufacturing practicality

Expected statuses include:

- PASS
- FAIL
- INVALID_TEST
- INSUFFICIENT_EVIDENCE
- NOT_APPLICABLE

Self-locking is optional. Absence of self-locking is not automatically a failure if controlled lowering and safe back-drive behaviour are demonstrated.

---

# 12 Revision Routing

## Responsibility

Route failure to the earliest incorrect decision.

## Expected routing examples

### Excessive crank effort

Return to Parametric Solver or Engineering Integration.

Targets:

- Screw pitch
- Crank radius
- Gear ratio
- Friction assumptions

### Platform binding

Return to Engineering Integration.

Targets:

- Guide topology
- Guide spacing
- Slider length
- Screw-guide alignment
- Tolerance strategy

### Platform collides with transmission

Return to Product Architecture or Engineering Integration.

Targets:

- Transmission compartment
- Lower platform position
- Gear placement
- Screw offset

### Lead-screw architecture too slow

Return to Mechanical Architecture.

Reconsider:

- Rack and pinion
- Cable drum
- Multi-start screw
- Alternative reduction

### Invalid structural test

Return to Validation Planning.

Do not redesign the product until the test method is corrected.

---

# Golden success criterion

BM-002 succeeds when the pipeline can transform the abstract crank-to-platform requirement into a complete product in which:

- Manual rotational input is transmitted into the enclosure.
- Vertical platform motion is generated.
- The platform is guided.
- The payload is supported.
- Reverse motion and holding are controlled or justified.
- The mechanism is spatially integrated into a housing.
- Supports, guides, stops, service access, and assembly are physically present.
- The parametric geometry is generated by the LLM rather than selected from a fixed geometry card.
- Deterministic checks and evidence validate the result.
