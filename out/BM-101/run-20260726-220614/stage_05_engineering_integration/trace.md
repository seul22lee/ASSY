# Stage 05 - Engineering Integration Trace

The design loop, in order. Each line is one problem resolved.

- iterations: 64
- commitments: 58 (58 active)
- problems: 63 (9 still open)
- resolutions: 63
- checks: 26

## Loop

```text
merged duplicate problem into P-041
merged duplicate problem into P-042
merged duplicate problem into P-049
merged duplicate problem into P-050
merged duplicate problem into P-049
merged duplicate problem into P-050
merged duplicate problem into P-059
merged duplicate problem into P-060
merged duplicate problem into P-059
merged duplicate problem into P-060
merged duplicate problem into P-068
merged duplicate problem into P-069
merged duplicate problem into P-068
merged duplicate problem into P-069
merged duplicate problem into P-001
merged duplicate problem into P-009
merged duplicate problem into P-020
iter 1: P-001 <- R-001 (straddle-mount crank on two bushings)
iter 2: P-002 <- R-003 (shoulder one end of crank, retaining clip the other)
iter 3: P-003 <- R-004 (straddle-mount crank on two bushings)
iter 4: P-005 <- R-006 (shroud the crank boundary and keep the running gap beneath it)
iter 5: P-006 <- R-007 (40 mm crank radius)
iter 6: P-007 <- R-008 (crank: PLA via FDM)
iter 7: P-008 <- R-009 (crank: PLA via FDM)
iter 8: P-009 <- R-010 (straddle-mount driver_disc on two bushings)
iter 9: P-010 <- R-012 (shoulder one end of driver_disc, retaining clip the other)
iter 10: P-011 <- R-013 (straddle-mount driver_disc on two bushings)
iter 11: P-016 <- R-015 (route driver_disc load through the shell to the base)
iter 12: P-017 <- R-016 (route driver_disc load through the shell to the base)
iter 13: P-018 <- R-017 (driver_disc: PLA via FDM)
iter 14: P-019 <- R-018 (driver_disc: PLA via FDM)
iter 15: P-020 <- R-019 (straddle-mount geneva_wheel on two bushings)
iter 16: P-021 <- R-021 (shoulder one end of geneva_wheel, retaining clip the other)
iter 17: P-022 <- R-022 (straddle-mount geneva_wheel on two bushings)
iter 18: P-027 <- R-024 (route geneva_wheel load through the shell to the base)
iter 19: P-028 <- R-025 (route geneva_wheel load through the shell to the base)
iter 20: P-029 <- R-026 (geneva_wheel: PLA via FDM)
iter 21: P-030 <- R-027 (geneva_wheel: PLA via FDM)
iter 22: P-031 <- R-028 (internal envelope sized for 90 mm stroke)
iter 23: P-032 <- R-029 (removable side panel carrying one bushing of each pair)
iter 24: P-033 <- R-030 (removable side panel carrying one bushing of each pair)
iter 25: P-034 <- R-031 (removable side panel carrying one bushing of each pair)
iter 26: P-035 <- R-032 (route housing load through the shell to the base)
iter 27: P-036 <- R-033 (route housing load through the shell to the base)
iter 28: P-037 <- R-034 (housing: PLA via FDM)
iter 29: P-038 <- R-035 (housing: PLA via FDM)
iter 30: P-039 <- R-036 (straddle-mount crank on two bushings)
iter 31: P-040 <- R-038 (shoulder one end of crank, retaining clip the other)
iter 32: P-041 <- R-039 (crank in PLA)
iter 33: P-042 <- R-040 (crank made by FDM)
iter 34: P-043 <- R-041 (shroud the crank boundary and keep the running gap beneath it)
iter 35: P-046 <- R-042 (crank: PLA via FDM)
iter 36: P-047 <- R-043 (straddle-mount driver_disc on two bushings)
iter 37: P-048 <- R-045 (shoulder one end of driver_disc, retaining clip the other)
iter 38: P-049 <- R-046 (driver_disc in PLA)
iter 39: P-050 <- R-047 (driver_disc made by FDM)
iter 40: P-051 <- R-048 (route driver_disc load through the shell to the base)
iter 41: P-056 <- R-049 (driver_disc: PLA via FDM)
iter 42: P-057 <- R-050 (straddle-mount geneva_wheel on two bushings)
iter 43: P-058 <- R-052 (shoulder one end of geneva_wheel, retaining clip the other)
iter 44: P-059 <- R-053 (geneva_wheel in PLA)
iter 45: P-060 <- R-054 (geneva_wheel made by FDM)
iter 46: P-061 <- R-055 (route geneva_wheel load through the shell to the base)
iter 47: P-066 <- R-056 (geneva_wheel: PLA via FDM)
iter 48: P-067 <- R-057 (removable side panel carrying one bushing of each pair)
iter 49: P-068 <- R-058 (housing in PLA)
iter 50: P-069 <- R-059 (housing made by FDM)
iter 51: P-070 <- R-060 (2.4 mm wall (FDM minimum 1.2 mm))
iter 52: P-071 <- R-061 (route housing load through the shell to the base)
iter 53: P-076 <- R-062 (housing: PLA via FDM)
iter 54: P-080 <- R-063 (removable side panel carrying one bushing of each pair)
iter 55: no resolver for 'index_relation' (P-013)
iter 56: no resolver for 'dwell_retention' (P-014)
iter 57: no resolver for 'engagement_clearance' (P-015)
iter 58: no resolver for 'index_relation' (P-024)
iter 59: no resolver for 'dwell_retention' (P-025)
iter 60: no resolver for 'engagement_clearance' (P-026)
iter 61: no resolver for 'index_relation' (P-013)
iter 62: no resolver for 'index_relation' (P-013)
iter 63: no resolver for 'index_relation' (P-013)
iter 64: P-013 exceeded repeat budget
```

## Open problems

| id | severity | phenomenon | statement |
|---|---|---|---|
| `P-013` | high | index_relation | driver_disc: index relation undetermined [no resolver in knowledge base] [no resolver in knowledge base] [no resolver in knowledge base] [no resolver in knowledge base] |
| `P-014` | high | dwell_retention | driver_disc: dwell retention undetermined [no resolver in knowledge base] |
| `P-015` | high | engagement_clearance | driver_disc: engagement clearance undetermined [no resolver in knowledge base] |
| `P-024` | high | index_relation | geneva_wheel: index relation undetermined [no resolver in knowledge base] |
| `P-025` | high | dwell_retention | geneva_wheel: dwell retention undetermined [no resolver in knowledge base] |
| `P-026` | high | engagement_clearance | geneva_wheel: engagement clearance undetermined [no resolver in knowledge base] |
| `P-004` | medium | friction_wear | crank: friction wear undetermined |
| `P-012` | medium | friction_wear | driver_disc: friction wear undetermined |
| `P-023` | medium | friction_wear | geneva_wheel: friction wear undetermined |
