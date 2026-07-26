
# STAGE_04_CONCEPT_VISUALIZATION.md

# Stage 04 — Concept Visualization

> This stage transforms Product Architecture into one or more concept images that preserve engineering intent while remaining lightweight, explainable, and independent of detailed geometry.

---

# Purpose

Concept Visualization exists to improve spatial reasoning.

Its purpose is **not** to create final industrial design artwork.

It provides an engineering-oriented visual hypothesis before detailed engineering begins.

Generated images are references, not engineering truth.

---

# Engineering Question

> What might this product plausibly look like while remaining faithful to the current engineering intent?

---

# Inputs

- RequirementSpec
- Selected Mechanical Architecture
- Product Architecture

The original user prompt should not be required beyond Stage 01.

---

# Outputs

`ConceptVisualizationResult`

Contains:

- visualization brief
- generated image(s)
- assumptions
- multimodal review
- detected inconsistencies
- confidence
- preserved engineering intent summary

---

# Responsibilities

Responsible for:

- communicating product organization visually
- exposing obvious packaging issues
- improving human understanding
- preserving engineering intent

Not responsible for:

- CAD generation
- geometry definition
- dimensions
- tolerances
- manufacturability validation
- structural validation

---

# Image Philosophy

Images are engineering hypotheses.

They may simplify details.

They may contain mistakes.

They are never the source of truth.

Structured engineering data from previous stages always has priority.

---

# Prompt Generation

Prompt construction should be as deterministic as possible.

Pipeline:

Product Architecture
        ↓
Deterministic Prompt Builder
        ↓
Compact Visualization Prompt

Avoid using an additional LLM solely to rewrite prompts.

---

# Token Efficiency Rules

Include only:

- product purpose
- major mechanisms
- product regions
- packaging strategy
- user interaction
- manufacturing intent (high level)
- safety constraints
- forbidden inventions

Avoid repetitive descriptions and unnecessary artistic language.

---

# Engineering Grounding

Every prompt should reinforce:

- prioritize mechanical plausibility
- preserve mechanism placement
- avoid floating components
- avoid unsupported shafts
- respect motion paths
- avoid impossible assemblies
- preserve product architecture

---

# Adaptive Candidate Policy

Generate one or more images depending on engineering uncertainty.

Additional images must represent genuinely different spatial organizations, not cosmetic variations.

---

# Multimodal Review

Compare:

- Product Architecture
- Mechanical Architecture
- Generated Image

Detect:

- missing mechanisms
- invented mechanisms
- impossible packaging
- impossible support
- inaccessible assembly
- obvious motion conflicts

Produce structured findings only.

---

# Relationship to Stage 05

Stage 05 receives:

- Product Architecture
- Mechanical Architecture
- Concept Visualization

Images provide spatial inspiration only.

If an image conflicts with structured engineering data, structured data always wins.

---

# Failure Handling

If review detects purely visual errors:

- regenerate the image.

If review reveals architectural ambiguity:

- report back to Stage 03 or Stage 02.

Visualization must never silently modify engineering intent.

---

# Success Criteria

The stage is complete when:

- engineering intent is visually preserved
- prompts remain token-efficient
- visualization improves spatial reasoning
- no unsupported engineering information is introduced
- Stage 05 can safely use the visualization while relying on structured engineering data as the engineering source of truth.
