"""Parametric host templates (MECHSYNTH §2.2 HostTemplate, SNAPFIT §4-⑥).

A template is a build123d function that returns a bare parametric skeleton PLUS its declared
anchors as metadata — the named geometric features (rim_underside_*, side_wall_*) that the IR's
bindings reference (V-02). Element geometry (hooks, windows) is NOT in the template; it is added
by each card's carve() at compile time. Templates are the skeleton; carve is the flesh.
"""

from knowledge.templates.host_templates import (AnchorGeom, TemplateResult, box_shell,
                                                lid_panel, flat_panel_mount, retained_board,
                                                cabinet_shell, drawer_tray, knob_shaft, rack_bar,
                                                TEMPLATES, TEMPLATE_COLLISION)

__all__ = ["AnchorGeom", "TemplateResult", "box_shell", "lid_panel", "flat_panel_mount",
           "retained_board", "cabinet_shell", "drawer_tray", "knob_shaft", "rack_bar",
           "TEMPLATES", "TEMPLATE_COLLISION"]
