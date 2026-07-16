"""Material constants (MECHSYNTH_SPEC §3.1) — single PETG instance (D8).

Data only. The numbers here are the spec's §3.1 values; Gate G3.1 (every constant
cross-checked against >=2 sources to within +-20%) is a knowledge-base task, not this
session's. Present so validator V-05 has a material to check card `requires` against.
"""

from __future__ import annotations

from ontology.schema import Citation, Material

PETG = Material(
    name="PETG",
    E_MPa=2100.0,
    eps_allow_pct=4.0,  # short-term allowable strain (snap-fit)
    mu_friction=0.30,
    density_kg_m3=1270.0,
    yield_MPa=50.0,
    print_min_wall_mm=1.2,
    print_clearance_mm=0.30,
    citations=[
        Citation(doc="BASF Snap-Fit Design Guide"),
        Citation(doc="generic PETG datasheet range"),
    ],
)

MATERIALS: dict[str, Material] = {PETG.name: PETG}
