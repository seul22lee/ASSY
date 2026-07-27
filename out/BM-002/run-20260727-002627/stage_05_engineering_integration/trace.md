# Stage 05 - Engineering Integration Trace

The design loop, in order. Each line is one problem resolved.

- iterations: 84
- commitments: 85 (85 active)
- problems: 85 (2 still open)
- resolutions: 92
- checks: 26

## Loop

```text
merged duplicate problem into P-052
merged duplicate problem into P-053
merged duplicate problem into P-060
merged duplicate problem into P-061
merged duplicate problem into P-060
merged duplicate problem into P-061
merged duplicate problem into P-070
merged duplicate problem into P-071
merged duplicate problem into P-070
merged duplicate problem into P-071
merged duplicate problem into P-081
merged duplicate problem into P-082
merged duplicate problem into P-081
merged duplicate problem into P-082
merged duplicate problem into P-090
merged duplicate problem into P-091
merged duplicate problem into P-096
merged duplicate problem into P-097
merged duplicate problem into P-096
merged duplicate problem into P-097
merged duplicate problem into P-001
merged duplicate problem into P-009
merged duplicate problem into P-017
iter 1: P-001 <- R-001 (straddle-mount crank on two bushings)
iter 2: P-002 <- R-003 (shoulder one end of crank, retaining clip the other)
iter 3: P-003 <- R-004 (straddle-mount crank on two bushings)
iter 4: P-005 <- R-006 (shroud the crank boundary and keep the running gap beneath it)
iter 5: P-006 <- R-007 (40 mm crank radius)
iter 6: P-007 <- R-008 (crank: PLA via FDM)
iter 7: P-008 <- R-009 (crank: PLA via FDM)
iter 8: P-009 <- R-010 (straddle-mount drive_shaft on two bushings)
iter 9: P-010 <- R-012 (shoulder one end of drive_shaft, retaining clip the other)
iter 10: P-011 <- R-013 (straddle-mount drive_shaft on two bushings)
iter 11: P-013 <- R-015 (route drive_shaft load through the shell to the base)
iter 12: P-014 <- R-016 (route drive_shaft load through the shell to the base)
iter 13: P-015 <- R-017 (drive_shaft: PLA via FDM)
iter 14: P-016 <- R-018 (drive_shaft: PLA via FDM)
iter 15: P-017 <- R-019 (straddle-mount lift_screw on two bushings)
iter 16: P-018 <- R-021 (shoulder one end of lift_screw, retaining clip the other)
iter 17: P-019 <- R-022 (straddle-mount lift_screw on two bushings)
iter 18: P-021 <- R-024 (M8 x 2 mm lead screw (self-locking))
iter 19: P-022 <- R-025 (M8 x 2 mm lead screw (self-locking))
iter 20: P-023 <- R-026 (M8 x 2 mm lead screw (self-locking))
iter 21: P-024 <- R-027 (route lift_screw load through the shell to the base)
iter 22: P-025 <- R-028 (route lift_screw load through the shell to the base)
iter 23: P-026 <- R-029 (lift_screw: PLA via FDM)
iter 24: P-027 <- R-030 (lift_screw: PLA via FDM)
iter 25: P-028 <- R-031 (two parallel guide rails for platform)
iter 26: P-029 <- R-032 (platform travels 90 mm with clearance at both ends)
iter 27: P-030 <- R-033 (two parallel guide rails for platform)
iter 28: P-031 <- R-034 (hard stops at both ends of platform travel)
iter 29: P-032 <- R-035 (route platform load through the shell to the base)
iter 30: P-033 <- R-036 (route platform load through the shell to the base)
iter 31: P-034 <- R-037 (platform: PLA via FDM)
iter 32: P-035 <- R-038 (platform: PLA via FDM)
iter 33: P-036 <- R-039 (route guide_rail load through the shell to the base)
iter 34: P-037 <- R-040 (route guide_rail load through the shell to the base)
iter 35: P-038 <- R-041 (guide_rail: PLA via FDM)
iter 36: P-039 <- R-042 (guide_rail: PLA via FDM)
iter 37: P-040 <- R-043 (internal envelope sized for 90 mm stroke)
iter 38: P-041 <- R-044 (removable side panel carrying one bushing of each pair)
iter 39: P-042 <- R-045 (removable side panel carrying one bushing of each pair)
iter 40: P-043 <- R-046 (removable side panel carrying one bushing of each pair)
iter 41: P-044 <- R-047 (route housing load through the shell to the base)
iter 42: P-045 <- R-048 (route housing load through the shell to the base)
iter 43: P-046 <- R-049 (housing: PLA via FDM)
iter 44: P-047 <- R-050 (housing: PLA via FDM)
iter 45: P-050 <- R-051 (straddle-mount crank on two bushings)
iter 46: P-051 <- R-053 (shoulder one end of crank, retaining clip the other)
iter 47: P-052 <- R-054 (crank in PLA)
iter 48: P-053 <- R-055 (crank made by FDM)
iter 49: P-054 <- R-056 (shroud the crank boundary and keep the running gap beneath it)
iter 50: P-057 <- R-057 (crank: PLA via FDM)
iter 51: P-058 <- R-058 (straddle-mount drive_shaft on two bushings)
iter 52: P-059 <- R-060 (shoulder one end of drive_shaft, retaining clip the other)
iter 53: P-060 <- R-061 (drive_shaft in PLA)
iter 54: P-061 <- R-062 (drive_shaft made by FDM)
iter 55: P-062 <- R-063 (route drive_shaft load through the shell to the base)
iter 56: P-067 <- R-064 (drive_shaft: PLA via FDM)
iter 57: P-068 <- R-065 (straddle-mount lift_screw on two bushings)
iter 58: P-069 <- R-067 (shoulder one end of lift_screw, retaining clip the other)
iter 59: P-070 <- R-068 (lift_screw in PLA)
iter 60: P-071 <- R-069 (lift_screw made by FDM)
iter 61: P-072 <- R-070 (route lift_screw load through the shell to the base)
iter 62: P-077 <- R-071 (lift_screw: PLA via FDM)
iter 63: P-078 <- R-072 (two parallel guide rails for platform)
iter 64: P-079 <- R-073 (platform travels 90 mm with clearance at both ends)
iter 65: P-080 <- R-074 (hard stops at both ends of platform travel)
iter 66: P-081 <- R-075 (platform in PLA)
iter 67: P-082 <- R-076 (platform made by FDM)
iter 68: P-083 <- R-077 (route platform load through the shell to the base)
iter 69: P-088 <- R-078 (platform: PLA via FDM)
iter 70: P-089 <- R-079 (route guide_rail load through the shell to the base)
iter 71: P-090 <- R-080 (guide_rail in PLA)
iter 72: P-091 <- R-081 (guide_rail made by FDM)
iter 73: P-094 <- R-082 (guide_rail: PLA via FDM)
iter 74: P-095 <- R-083 (removable side panel carrying one bushing of each pair)
iter 75: P-096 <- R-084 (housing in PLA)
iter 76: P-097 <- R-085 (housing made by FDM)
iter 77: P-098 <- R-086 (2.4 mm wall (FDM minimum 1.2 mm))
iter 78: P-099 <- R-087 (route housing load through the shell to the base)
iter 79: P-104 <- R-088 (housing: PLA via FDM)
iter 80: P-108 <- R-089 (removable side panel carrying one bushing of each pair)
iter 81: P-004 <- R-090 (low-friction bushing at crank)
iter 82: P-012 <- R-091 (low-friction bushing at drive_shaft)
iter 83: P-020 <- R-092 (low-friction bushing at lift_screw)
```

## Open problems

| id | severity | phenomenon | statement |
|---|---|---|---|
| `P-048` | low | requirement_REQ-001 | travel between 80 and 100 mm |
| `P-049` | low | requirement_REQ-002 | payload >= 1 kg |
