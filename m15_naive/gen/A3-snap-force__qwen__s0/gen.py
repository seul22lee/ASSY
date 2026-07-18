import sys as _s0
_s0.path[:] = [p for p in _s0.path if 'm15_naive' not in p]
from build123d import *

# Design parameters
box_length = 100.0
box_width = 80.0
box_height = 40.0
wall_thickness = 2.0
lid_snap_gap = 0.3
lid_snap_height = 5.0
lid_snap_width = 8.0
lid_snap_depth = 3.0
snap_lid_thickness = 1.5

class SnapLidBox:
    def __init__(self, length, width, height, wall_thickness):
        self.length = length
        self.width = width
        self.height = height
        self.wall_thickness = wall_thickness
        
    def create_box(self):
        # Create the main box body
        box = Box(self.length, self.width, self.height)
        
        # Subtract inner cavity with wall thickness
        inner_length = self.length - 2 * self.wall_thickness
        inner_width = self.width - 2 * self.wall_thickness
        inner_height = self.height - 2 * self.wall_thickness
        
        cavity = Box(inner_length, inner_width, inner_height)
        box = box - cavity
        
        # Add snap features to the lid
        return box
    
    def create_lid(self):
        # Create the lid with snap features
        lid = Box(self.length, self.width, self.wall_thickness)
        
        # Create snap tabs on the lid
        tab_count = 4
        tab_spacing = (self.length - 2 * self.wall_thickness) / (tab_count + 1)
        
        for i in range(tab_count):
            tab_x = self.wall_thickness + tab_spacing * (i + 1)
            tab_y = self.width - self.wall_thickness
            
            # Create snap tab on lid
            tab = Box(lid_snap_width, lid_snap_depth, lid_snap_height)
            tab = tab.locate(Placement((tab_x - lid_snap_width/2, tab_y - lid_snap_depth, 0)))
            lid = lid - tab
            
        # Create snap features on the box sides
        box_side_tabs = []
        for i in range(tab_count):
            tab_x = self.wall_thickness + tab_spacing * (i + 1)
            
            # Create snap feature on box side
            snap_feature = Box(lid_snap_width, lid_snap_depth, lid_snap_height)
            snap_feature = snap_feature.locate(Placement((tab_x - lid_snap_width/2, self.width - self.wall_thickness, 0)))
            box_side_tabs.append(snap_feature)
            
        return lid, box_side_tabs

# Create the box and lid
box_model = SnapLidBox(box_length, box_width, box_height, wall_thickness)
box_body = box_model.create_box()

# Create lid with snap features
lid, side_tabs = box_model.create_lid()

# Adjust lid to be slightly smaller for clearance
lid_adjusted = Box(box_length - 2 * wall_thickness, box_width - 2 * wall_thickness, wall_thickness)

# Create the final parts
result = [box_body, lid_adjusted]

# --- m15 export harness (appended) ---
import sys as _sys
_sys.path[:] = [p for p in _sys.path if "m15_naive/gen" not in p]  # never shadow stdlib
import json as _json
from pathlib import Path as _P
try:
    from build123d import export_stl as _export
    _parts = result if isinstance(result, (list, tuple)) else [result]
    _od = _P(_sys.argv[1]); _od.mkdir(parents=True, exist_ok=True)
    _n = 0
    for _i, _p in enumerate(_parts):
        _solid = getattr(_p, "part", _p)
        try:
            _export(_solid, str(_od / f"part_{_i}.stl"), tolerance=0.2, angular_tolerance=0.4)
            _n += 1
        except Exception as _e:
            pass
    print("M15_STATUS " + _json.dumps({"ok": True, "n_parts": len(_parts), "n_exported": _n}))
except Exception as _e:
    print("M15_STATUS " + _json.dumps({"ok": False, "error": type(_e).__name__ + ": " + str(_e)[:200]}))
