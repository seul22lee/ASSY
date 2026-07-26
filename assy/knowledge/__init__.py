"""Explicit, inspectable engineering knowledge.

Kept as data and pure functions rather than prompt text, so that it can be
tested, audited, and extended per domain (STAGE_05 section 15).
"""

from assy.knowledge import checks, elements, materials, spawning

__all__ = ["checks", "elements", "materials", "spawning"]
