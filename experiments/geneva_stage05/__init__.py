"""Geneva falsification of the Stage 05 working-state model.

Implementation evidence for one architectural hypothesis. See README.md.
Not a benchmark: it does not evaluate the complete pipeline.
"""

GENEVA_REQUEST = (
    "Design an enclosed hand-cranked indexing turntable. "
    "Turning the external crank should index the turntable intermittently through "
    "6 equal stations with a dwell between each index. "
    "The drive mechanism should be enclosed. "
    "The product should be safe, easy to assemble, and practical to manufacture."
)

GENEVA_CLARIFICATIONS = [
    "Desktop-sized product.",
    "Manual operation only.",
    "Positive station location is required.",
]

__all__ = ["GENEVA_CLARIFICATIONS", "GENEVA_REQUEST"]
