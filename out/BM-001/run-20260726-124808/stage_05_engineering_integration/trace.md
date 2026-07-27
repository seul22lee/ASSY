# Stage 05 - Engineering Integration Trace

The design loop, in order. Each line is one problem resolved.

- iterations: 84
- commitments: 88 (88 active)
- problems: 83 (0 still open)
- resolutions: 86
- checks: 26

## Loop

```text
merged duplicate problem into P-049
merged duplicate problem into P-050
merged duplicate problem into P-049
merged duplicate problem into P-050
merged duplicate problem into P-061
merged duplicate problem into P-062
merged duplicate problem into P-061
merged duplicate problem into P-062
merged duplicate problem into P-071
merged duplicate problem into P-072
merged duplicate problem into P-071
merged duplicate problem into P-072
merged duplicate problem into P-086
merged duplicate problem into P-087
merged duplicate problem into P-092
merged duplicate problem into P-093
merged duplicate problem into P-092
merged duplicate problem into P-093
merged duplicate problem into P-012
iter 1: P-001 <- R-001 (shroud the lid boundary and keep the running gap beneath it)
iter 2: P-002 <- R-002 (40 mm crank radius)
iter 3: P-003 <- R-003 (rear hinge axis, 105 deg swing on two knuckles)
iter 4: P-004 <- R-004 (rear hinge axis, 105 deg swing on two knuckles)
iter 5: P-005 <- R-005 (rear hinge axis, 105 deg swing on two knuckles)
iter 6: P-006 <- R-006 (rear hinge axis, 105 deg swing on two knuckles)
iter 7: P-007 <- R-007 (lid runs with a shrouded 1.5 mm gap to the static shell)
iter 8: P-008 <- R-008 (route lid load through the shell to the base)
iter 9: P-009 <- R-009 (route lid load through the shell to the base)
iter 10: P-010 <- R-010 (lid: PLA via FDM)
iter 11: P-011 <- R-011 (lid: PLA via FDM)
iter 12: P-012 <- R-012 (straddle-mount hinge_pin on two bushings)
iter 13: P-013 <- R-014 (shoulder one end of hinge_pin, retaining clip the other)
iter 14: P-014 <- R-015 (straddle-mount hinge_pin on two bushings)
iter 15: P-016 <- R-017 (route hinge_pin load through the shell to the base)
iter 16: P-017 <- R-018 (route hinge_pin load through the shell to the base)
iter 17: P-018 <- R-019 (hinge_pin: PLA via FDM)
iter 18: P-019 <- R-020 (hinge_pin: PLA via FDM)
iter 19: P-020 <- R-021 (12x6x1.2 mm cantilever, 0.8 mm undercut)
iter 20: P-021 <- R-022 (12x6x1.2 mm cantilever, 0.8 mm undercut)
iter 21: P-022 <- R-023 (12x6x1.2 mm cantilever, 0.8 mm undercut)
iter 22: P-023 <- R-024 (30 deg lead face, 60 deg retention face)
iter 23: P-024 <- R-025 (30 deg lead face, 60 deg retention face)
iter 24: P-025 <- R-026 (30 deg lead face, 60 deg retention face)
iter 25: P-026 <- R-027 (30 deg lead face, 60 deg retention face)
iter 26: P-027 <- R-028 (route snap_beam load through the shell to the base)
iter 27: P-028 <- R-029 (route snap_beam load through the shell to the base)
iter 28: P-029 <- R-030 (snap_beam: PLA via FDM)
iter 29: P-030 <- R-031 (snap_beam: PLA via FDM)
iter 30: P-031 <- R-032 (allocate 0.42 mm to the snap_beam chain)
iter 31: P-032 <- R-033 (30 deg lead face, 60 deg retention face)
iter 32: P-033 <- R-034 (30 deg lead face, 60 deg retention face)
iter 33: P-034 <- R-035 (route catch load through the shell to the base)
iter 34: P-035 <- R-036 (route catch load through the shell to the base)
iter 35: P-036 <- R-037 (catch: PLA via FDM)
iter 36: P-037 <- R-038 (catch: PLA via FDM)
iter 37: P-038 <- R-039 (internal envelope sized for 90 mm stroke)
iter 38: P-039 <- R-040 (removable side panel carrying one bushing of each pair)
iter 39: P-040 <- R-041 (removable side panel carrying one bushing of each pair)
iter 40: P-041 <- R-042 (removable side panel carrying one bushing of each pair)
iter 41: P-042 <- R-043 (route housing load through the shell to the base)
iter 42: P-043 <- R-044 (route housing load through the shell to the base)
iter 43: P-044 <- R-045 (housing: PLA via FDM)
iter 44: P-045 <- R-046 (housing: PLA via FDM)
iter 45: P-046 <- R-047 (rear hinge axis, 105 deg swing on two knuckles)
iter 46: P-047 <- R-048 (rear hinge axis, 105 deg swing on two knuckles)
iter 47: P-048 <- R-049 (rear hinge axis, 105 deg swing on two knuckles)
iter 48: P-049 <- R-050 (lid in PLA)
iter 49: P-050 <- R-051 (lid made by FDM)
iter 50: P-051 <- R-052 (lid runs with a shrouded 1.5 mm gap to the static shell)
iter 51: P-052 <- R-053 (shroud the lid boundary and keep the running gap beneath it)
iter 52: P-053 <- R-054 (route lid load through the shell to the base)
iter 53: P-058 <- R-055 (lid: PLA via FDM)
iter 54: P-059 <- R-056 (straddle-mount hinge_pin on two bushings)
iter 55: P-060 <- R-058 (shoulder one end of hinge_pin, retaining clip the other)
iter 56: P-061 <- R-059 (hinge_pin in PLA)
iter 57: P-062 <- R-060 (hinge_pin made by FDM)
iter 58: P-063 <- R-061 (route hinge_pin load through the shell to the base)
iter 59: P-068 <- R-062 (hinge_pin: PLA via FDM)
iter 60: P-069 <- R-063 (12x6x1.2 mm cantilever, 0.8 mm undercut)
iter 61: P-070 <- R-064 (12x6x1.2 mm cantilever, 0.8 mm undercut)
iter 62: P-071 <- R-065 (snap_beam in PLA)
iter 63: P-072 <- R-066 (snap_beam made by FDM)
iter 64: P-073 <- R-067 (30 deg lead face, 60 deg retention face)
iter 65: P-074 <- R-068 (30 deg lead face, 60 deg retention face)
iter 66: P-075 <- R-069 (30 deg lead face, 60 deg retention face)
iter 67: P-076 <- R-070 (allocate 0.42 mm to the snap_beam chain)
iter 68: P-077 <- R-071 (route snap_beam load through the shell to the base)
iter 69: P-082 <- R-072 (snap_beam: PLA via FDM)
iter 70: P-083 <- R-073 (30 deg lead face, 60 deg retention face)
iter 71: P-084 <- R-074 (30 deg lead face, 60 deg retention face)
iter 72: P-085 <- R-075 (route catch load through the shell to the base)
iter 73: P-086 <- R-076 (catch in PLA)
iter 74: P-087 <- R-077 (catch made by FDM)
iter 75: P-090 <- R-078 (catch: PLA via FDM)
iter 76: P-091 <- R-079 (removable side panel carrying one bushing of each pair)
iter 77: P-092 <- R-080 (housing in PLA)
iter 78: P-093 <- R-081 (housing made by FDM)
iter 79: P-094 <- R-082 (2.4 mm wall (FDM minimum 1.2 mm))
iter 80: P-095 <- R-083 (route housing load through the shell to the base)
iter 81: P-100 <- R-084 (housing: PLA via FDM)
iter 82: P-102 <- R-085 (removable side panel carrying one bushing of each pair)
iter 83: P-015 <- R-086 (low-friction bushing at hinge_pin)
```
