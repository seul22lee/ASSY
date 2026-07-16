"""StageFailure — the typed failure a pipeline stage raises so rollback (spec §4) can route it.

Each carries a machine code (the rollback key) and a detail payload (what was violated + by how
much), so a human and the router both learn something. Codes used this session:
  INFEASIBLE      stage 5 could not satisfy the force-window inequalities (roll back to ④)
  COMPILE_DRIFT   stage 8 re-measured geometry disagrees with the IR (a compiler bug)
  INTERFERENCE / UNDERCUT_MISMATCH / SWEEP_HIT   Tier0 three-way check (§5.2)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StageFailure(Exception):
    stage: str
    code: str
    detail: str
    data: dict = field(default_factory=dict)  # violated items + margins, for the router/report

    def __str__(self) -> str:
        return f"StageFailure[{self.stage}/{self.code}]: {self.detail}"
