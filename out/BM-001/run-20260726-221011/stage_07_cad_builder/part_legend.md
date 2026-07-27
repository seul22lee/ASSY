# Part Legend

Semantic identity is owned upstream; the mapping to files below is generated
*by* the CAD builder and is never the authority for engineering identity.

| part | role(s) | material | bbox (mm) | mass (g) | STEP |
|---|---|---|---|---|---|
| `lid` | hinged, moving_boundary, user_contact, load_bearing, manufactured | PLA | 110 x 90 x 6 | 73.66 | `lid.step` |
| `hinge_pin` | rotating, load_bearing, manufactured | PLA | 80 x 8 x 8 | 4.99 | `hinge_pin.step` |
| `snap_beam` | compliant, retention_interface, user_release, precision_interface, load_bearing, manufactured | PLA | 6 x 2 x 12 | 0.12 | `snap_beam.step` |
| `catch` | retention_interface, load_bearing, manufactured | PLA | 8.4 x 2.4 x 5 | 0.12 | `catch.step` |
| `housing` | enclosure, load_bearing, manufactured | PLA | 114.8 x 94.8 x 124.8 | 171.77 | `housing.step` |

## Views

- isometric: `visualizations/isometric.png`
- transparent: `visualizations/transparent.png`
- exploded: `visualizations/exploded.png`
- section: `visualizations/section.png`
