"""m25 — the CONTACT SCHEDULE: classify each task's mating pairs into the ①/②/③ contact doctrine.

This is the GENERIC source the contact-layer runner reads (the §14 fit schedule / T3-ARCH mating-face map
supplies which pairs mate; this file tags each with its contact class). The runner enables collision ONLY
for `class2_limit` pairs and PRINTS the exclusions. Classification is DATA; the runner carries no
element-specific logic.

  ① driving curved contact (R2b) — V-B deferred (m17/D-M1-7)
  ② landings / stops / retention-ride — verified by real contact (limit carriers) OR realized by the
     declared DoF + fit clearance (ride/guidance, which carry no LIMIT)
  ③ elastic members (D3) — forces by formula (Bayer), not rigid-body sim
"""

SCHEDULE = {
    "screw_lift": {
        "class2_limit": [
            {"pair": "platform×top_collar", "role": "TOP stop = thread-runout shoulder (full stroke)"},
            {"pair": "platform×bottom_stop", "role": "BOTTOM landing on the base frame (s=0)"},
        ],
        "class2_dof": ["platform×guide_columns"],   # guidance = the slide DoF + 0.35 fit clearance (no LIMIT)
        "class1_excluded": [
            ("screw×nut_thread", "driving helical thread flank = R2b curved contact; V-B deferred (m17/D-M1-7)"),
        ],
        "class3_excluded": [],
        "fused": [("coupling_hub×crank", "rigid grip, fused to the input shaft (m20) — no contact pair")],
    },
    "latched_drawer": {
        "class2_limit": [
            {"pair": "panel×face_frame", "role": "CLOSED landing = the front-panel-on-face-frame hard stop (s=0)"},
        ],
        "class2_dof": ["tray×rail"],                # ride + retention = the slide DoF + 0.35 clearance (no LIMIT)
        "class1_excluded": [],
        "class3_excluded": [
            ("clip×bump", "elastic cantilever deflection = D3; retention is the SOURCED Bayer W_out=30.4 N "
             "(sourced-threshold latch, m23/D-M22-3) — not a rigid contact"),
        ],
        "fused": [],
    },
}
