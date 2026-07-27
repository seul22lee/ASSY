"""Validation backends.

Each backend is one method with an explicit validity domain. The framework
treats every method as evidence about the phenomena it can legitimately
represent, and no further (SYSTEM_ARCHITECTURE section 16).

    analytical  closed-form compliant-element behaviour
    mjcf        rigid-body motion, contact timing, swept clearance
"""

from assy.validation import analytical, mjcf

__all__ = ["analytical", "mjcf"]
