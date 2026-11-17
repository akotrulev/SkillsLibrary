# Decision — Credit return on cancellation (DEC-001)

**Created:** 2026-08-02
**Owned by:** `business-analysis:decision-table`

**Question**: are a booking's credits returned when it is cancelled? **Output**: yes / no
**Hit policy**: U
**Contributed by**: AREA-004 credits

## Inputs
| Input | Type | Partitions | Glossary |
|---|---|---|---|
| cancelled_by | enum | member · staff | |
| notice | duration | ≥ 24 h · < 24 h | |

## Rules
| # | cancelled_by | notice | → returned | Feature | Source |
|---|---|---|---|---|---|
| R1 | member | ≥ 24 h | yes | AREA-004 credits | US8 AC1 |
| R2 | member | < 24 h | no | AREA-004 credits | US8 AC2 |
| R3 | staff | - | yes | AREA-004 credits | CONF-001 |

## Checks
- Completeness: ✅ all combinations covered (R1–R3)
- Overlap: none
