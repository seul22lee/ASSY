# Stage 05 - Engineering Integration Trace

The design loop, in order. Each line is one problem resolved.

- iterations: 108
- commitments: 100 (100 active)
- problems: 109 (2 still open)
- resolutions: 116
- checks: 26

## Loop

```text
merged duplicate problem into P-064
merged duplicate problem into P-065
merged duplicate problem into P-071
merged duplicate problem into P-072
merged duplicate problem into P-078
merged duplicate problem into P-079
merged duplicate problem into P-078
merged duplicate problem into P-079
merged duplicate problem into P-088
merged duplicate problem into P-089
merged duplicate problem into P-088
merged duplicate problem into P-089
merged duplicate problem into P-097
merged duplicate problem into P-098
merged duplicate problem into P-105
merged duplicate problem into P-106
merged duplicate problem into P-105
merged duplicate problem into P-106
merged duplicate problem into P-114
merged duplicate problem into P-115
merged duplicate problem into P-120
merged duplicate problem into P-121
merged duplicate problem into P-126
merged duplicate problem into P-127
merged duplicate problem into P-126
merged duplicate problem into P-127
merged duplicate problem into P-001
merged duplicate problem into P-013
merged duplicate problem into P-021
iter 1: P-001 <- R-001 (straddle-mount input_member on two bushings)
iter 2: P-002 <- R-003 (shoulder one end of input_member, retaining clip the other)
iter 3: P-003 <- R-004 (straddle-mount input_member on two bushings)
iter 4: P-005 <- R-006 (shroud the input_member boundary and keep the running gap beneath it)
iter 5: P-006 <- R-007 (40 mm crank radius)
iter 6: P-007 <- R-008 (input_member: PLA via FDM)
iter 7: P-008 <- R-009 (input_member: PLA via FDM)
iter 8: P-009 <- R-010 (route input_support load through the shell to the base)
iter 9: P-010 <- R-011 (route input_support load through the shell to the base)
iter 10: P-011 <- R-012 (input_support: PLA via FDM)
iter 11: P-012 <- R-013 (input_support: PLA via FDM)
iter 12: P-013 <- R-014 (straddle-mount transmission_shaft on two bushings)
iter 13: P-014 <- R-016 (shoulder one end of transmission_shaft, retaining clip the other)
iter 14: P-015 <- R-017 (straddle-mount transmission_shaft on two bushings)
iter 15: P-017 <- R-019 (route transmission_shaft load through the shell to the base)
iter 16: P-018 <- R-020 (route transmission_shaft load through the shell to the base)
iter 17: P-019 <- R-021 (transmission_shaft: PLA via FDM)
iter 18: P-020 <- R-022 (transmission_shaft: PLA via FDM)
iter 19: P-021 <- R-023 (straddle-mount threaded_member on two bushings)
iter 20: P-022 <- R-025 (shoulder one end of threaded_member, retaining clip the other)
iter 21: P-023 <- R-026 (straddle-mount threaded_member on two bushings)
iter 22: P-025 <- R-028 (M8 x 2 mm lead screw (self-locking))
iter 23: P-026 <- R-029 (M8 x 2 mm lead screw (self-locking))
iter 24: P-027 <- R-030 (M8 x 2 mm lead screw (self-locking))
iter 25: P-028 <- R-031 (route threaded_member load through the shell to the base)
iter 26: P-029 <- R-032 (route threaded_member load through the shell to the base)
iter 27: P-030 <- R-033 (threaded_member: PLA via FDM)
iter 28: P-031 <- R-034 (threaded_member: PLA via FDM)
iter 29: P-032 <- R-035 (route thrust_support load through the shell to the base)
iter 30: P-033 <- R-036 (route thrust_support load through the shell to the base)
iter 31: P-034 <- R-037 (thrust_support: PLA via FDM)
iter 32: P-035 <- R-038 (thrust_support: PLA via FDM)
iter 33: P-036 <- R-039 (two parallel guide rails for travelling_member)
iter 34: P-037 <- R-040 (travelling_member travels 90 mm with clearance at both ends)
iter 35: P-038 <- R-041 (two parallel guide rails for travelling_member)
iter 36: P-039 <- R-042 (hard stops at both ends of travelling_member travel)
iter 37: P-040 <- R-043 (route travelling_member load through the shell to the base)
iter 38: P-041 <- R-044 (route travelling_member load through the shell to the base)
iter 39: P-042 <- R-045 (travelling_member: PLA via FDM)
iter 40: P-043 <- R-046 (travelling_member: PLA via FDM)
iter 41: P-044 <- R-047 (route guide_member load through the shell to the base)
iter 42: P-045 <- R-048 (route guide_member load through the shell to the base)
iter 43: P-046 <- R-049 (guide_member: PLA via FDM)
iter 44: P-047 <- R-050 (guide_member: PLA via FDM)
iter 45: P-048 <- R-051 (route travel_stop load through the shell to the base)
iter 46: P-049 <- R-052 (route travel_stop load through the shell to the base)
iter 47: P-050 <- R-053 (travel_stop: PLA via FDM)
iter 48: P-051 <- R-054 (travel_stop: PLA via FDM)
iter 49: P-052 <- R-055 (internal envelope sized for 90 mm stroke)
iter 50: P-053 <- R-056 (removable side panel carrying one bushing of each pair)
iter 51: P-054 <- R-057 (removable side panel carrying one bushing of each pair)
iter 52: P-055 <- R-058 (removable side panel carrying one bushing of each pair)
iter 53: P-056 <- R-059 (route housing load through the shell to the base)
iter 54: P-057 <- R-060 (route housing load through the shell to the base)
iter 55: P-058 <- R-061 (housing: PLA via FDM)
iter 56: P-059 <- R-062 (housing: PLA via FDM)
iter 57: P-062 <- R-063 (straddle-mount input_member on two bushings)
iter 58: P-063 <- R-065 (shoulder one end of input_member, retaining clip the other)
iter 59: P-064 <- R-066 (input_member in PLA)
iter 60: P-065 <- R-067 (input_member made by FDM)
iter 61: P-066 <- R-068 (shroud the input_member boundary and keep the running gap beneath it)
iter 62: P-069 <- R-069 (input_member: PLA via FDM)
iter 63: P-070 <- R-070 (route input_support load through the shell to the base)
iter 64: P-071 <- R-071 (input_support in PLA)
iter 65: P-072 <- R-072 (input_support made by FDM)
iter 66: P-075 <- R-073 (input_support: PLA via FDM)
iter 67: P-076 <- R-074 (straddle-mount transmission_shaft on two bushings)
iter 68: P-077 <- R-076 (shoulder one end of transmission_shaft, retaining clip the other)
iter 69: P-078 <- R-077 (transmission_shaft in PLA)
iter 70: P-079 <- R-078 (transmission_shaft made by FDM)
iter 71: P-080 <- R-079 (route transmission_shaft load through the shell to the base)
iter 72: P-085 <- R-080 (transmission_shaft: PLA via FDM)
iter 73: P-086 <- R-081 (straddle-mount threaded_member on two bushings)
iter 74: P-087 <- R-083 (shoulder one end of threaded_member, retaining clip the other)
iter 75: P-088 <- R-084 (threaded_member in PLA)
iter 76: P-089 <- R-085 (threaded_member made by FDM)
iter 77: P-090 <- R-086 (route threaded_member load through the shell to the base)
iter 78: P-095 <- R-087 (threaded_member: PLA via FDM)
iter 79: P-096 <- R-088 (route thrust_support load through the shell to the base)
iter 80: P-097 <- R-089 (thrust_support in PLA)
iter 81: P-098 <- R-090 (thrust_support made by FDM)
iter 82: P-101 <- R-091 (thrust_support: PLA via FDM)
iter 83: P-102 <- R-092 (two parallel guide rails for travelling_member)
iter 84: P-103 <- R-093 (travelling_member travels 90 mm with clearance at both ends)
iter 85: P-104 <- R-094 (hard stops at both ends of travelling_member travel)
iter 86: P-105 <- R-095 (travelling_member in PLA)
iter 87: P-106 <- R-096 (travelling_member made by FDM)
iter 88: P-107 <- R-097 (route travelling_member load through the shell to the base)
iter 89: P-112 <- R-098 (travelling_member: PLA via FDM)
iter 90: P-113 <- R-099 (route guide_member load through the shell to the base)
iter 91: P-114 <- R-100 (guide_member in PLA)
iter 92: P-115 <- R-101 (guide_member made by FDM)
iter 93: P-118 <- R-102 (guide_member: PLA via FDM)
iter 94: P-119 <- R-103 (route travel_stop load through the shell to the base)
iter 95: P-120 <- R-104 (travel_stop in PLA)
iter 96: P-121 <- R-105 (travel_stop made by FDM)
iter 97: P-124 <- R-106 (travel_stop: PLA via FDM)
iter 98: P-125 <- R-107 (removable side panel carrying one bushing of each pair)
iter 99: P-126 <- R-108 (housing in PLA)
iter 100: P-127 <- R-109 (housing made by FDM)
iter 101: P-128 <- R-110 (2.4 mm wall (FDM minimum 1.2 mm))
iter 102: P-129 <- R-111 (route housing load through the shell to the base)
iter 103: P-134 <- R-112 (housing: PLA via FDM)
iter 104: P-138 <- R-113 (removable side panel carrying one bushing of each pair)
iter 105: P-004 <- R-114 (low-friction bushing at input_member)
iter 106: P-016 <- R-115 (low-friction bushing at transmission_shaft)
iter 107: P-024 <- R-116 (low-friction bushing at threaded_member)
```

## Open problems

| id | severity | phenomenon | statement |
|---|---|---|---|
| `P-060` | low | requirement_REQ-002 | The platform must move approximately 80-100 mm during operation |
| `P-061` | low | requirement_REQ-003 | The platform must support a payload of approximately 1 kg |
