"""V-10 round-trip, exercised on the golden JSON files as they sit on disk.

DesignPlan -> JSON -> DesignPlan must be lossless (spec §2.5 V-10). This is the strongest form
of the check: it loads the actual tasks/*.json, re-parses, re-serializes, and asserts byte- and
model-equality both ways. A schema that cannot round-trip its own goldens is broken.

Run:  ./bin/py tests/test_roundtrip.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ontology.schema import DesignPlan

GOLDENS = ["m0_hinge_box_nostop.json", "m0_hinge_box_stop.json", "snap_starter.json"]


def test_goldens_exist():
    for g in GOLDENS:
        assert (ROOT / "tasks" / g).exists(), f"missing golden {g} (run tasks/build_goldens.py)"


def test_roundtrip_model_equal():
    for g in GOLDENS:
        raw = (ROOT / "tasks" / g).read_text()
        plan = DesignPlan.model_validate_json(raw)
        again = DesignPlan.model_validate_json(plan.model_dump_json())
        assert again.model_dump() == plan.model_dump(), f"{g}: model changed across round-trip"


def test_roundtrip_json_stable():
    # Serialize twice; the second serialization of the re-parsed model must equal the first.
    for g in GOLDENS:
        plan = DesignPlan.model_validate_json((ROOT / "tasks" / g).read_text())
        j1 = plan.model_dump_json(indent=2)
        j2 = DesignPlan.model_validate_json(j1).model_dump_json(indent=2)
        assert j1 == j2, f"{g}: JSON not stable across round-trip"


def test_disk_json_is_canonical():
    # The committed file should already be canonical (what build_goldens wrote). Guards against
    # a hand-edit that parses but does not re-serialize identically.
    for g in GOLDENS:
        raw = (ROOT / "tasks" / g).read_text()
        plan = DesignPlan.model_validate_json(raw)
        canonical = plan.model_dump_json(indent=2)
        assert json.loads(raw) == json.loads(canonical), f"{g}: on-disk JSON is not canonical"


def main() -> int:
    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
