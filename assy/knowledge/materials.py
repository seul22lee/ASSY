"""Material and process property tables.

Explicit, inspectable engineering data (STAGE_05 section 15). Values are typical
engineering figures adequate for pre-CAD screening, not certified design data.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    density_kg_m3: float
    youngs_modulus_mpa: float
    yield_strength_mpa: float
    friction_vs_self: float
    friction_vs_steel: float
    notes: str = ""


MATERIALS: dict[str, Material] = {
    "PLA": Material("PLA", 1240, 3500, 50, 0.35, 0.30, "FDM default; creeps under sustained load"),
    "PETG": Material("PETG", 1270, 2100, 50, 0.40, 0.32, "tougher than PLA, more ductile"),
    "ABS": Material("ABS", 1040, 2200, 40, 0.45, 0.35, "warps on large flat prints"),
    "NYLON": Material("NYLON", 1150, 2000, 60, 0.25, 0.20, "good bearing surface, absorbs moisture"),
    "POM": Material("POM", 1410, 2800, 65, 0.20, 0.15, "excellent low-friction bearing material"),
    "STEEL": Material("STEEL", 7850, 210000, 250, 0.60, 0.40, "shafts and fasteners"),
    "BRONZE": Material("BRONZE", 8800, 100000, 140, 0.30, 0.18, "plain bearing bushings"),
}


@dataclass(frozen=True)
class Process:
    name: str
    min_wall_mm: float
    min_feature_mm: float
    max_overhang_deg: float
    tolerance_mm: float
    anisotropic: bool
    needs_draft: bool
    compatible: tuple[str, ...]


PROCESSES: dict[str, Process] = {
    "FDM": Process("FDM", 1.2, 0.8, 45.0, 0.20, True, False, ("PLA", "PETG", "ABS", "NYLON")),
    "SLA": Process("SLA", 0.8, 0.3, 30.0, 0.10, False, False, ("PLA",)),
    "INJECTION": Process("INJECTION", 1.0, 0.5, 90.0, 0.05, False, True, ("PLA", "PETG", "ABS", "POM", "NYLON")),
    "MACHINED": Process("MACHINED", 0.5, 0.2, 90.0, 0.02, False, False, ("POM", "NYLON", "STEEL", "BRONZE")),
}


def compatible(material: str, process: str) -> bool:
    proc = PROCESSES.get(process)
    return bool(proc and material in proc.compatible)


def material(name: str) -> Material:
    return MATERIALS[name]


def process(name: str) -> Process:
    return PROCESSES[name]
