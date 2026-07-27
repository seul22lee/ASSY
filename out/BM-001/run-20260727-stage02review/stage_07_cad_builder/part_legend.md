# Part Legend

Semantic identity is owned upstream; the mapping to files below is generated
*by* the CAD builder and is never the authority for engineering identity.

| part | role(s) | material | bbox (mm) | mass (g) | STEP |
|---|---|---|---|---|---|
| `closure_member` | moving_boundary, user_contact, user_release, manufactured | PLA | 20 x 20 x 10 | 4.96 | `closure_member.step` |
| `opening_interface` | hinged, load_bearing, manufactured | PLA | 110 x 90 x 6 | 73.66 | `opening_interface.step` |
| `detent_feature` | retention_interface, manufactured | PLA | 8.4 x 2.4 x 5 | 0.12 | `detent_feature.step` |
| `opening_stop` | load_bearing, manufactured | PLA | 8 x 8 x 116 | 7.23 | `opening_stop.step` |
| `housing` | enclosure, load_bearing, manufactured | PLA | 114.8 x 94.8 x 124.8 | 171.77 | `housing.step` |

## Views

- isometric: `visualizations/isometric.png`
- transparent: `visualizations/transparent.png`
- exploded: `visualizations/exploded.png`
- section: `visualizations/section.png`
