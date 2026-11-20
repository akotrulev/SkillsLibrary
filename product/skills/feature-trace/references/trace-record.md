# Trace record shape

Load this before writing the trace record (or a persisted `.trace/<area>.md`). Sections are in this order; a `guide`-profile record writes no Tests & telemetry section.

```markdown
## Area: <name> — trace evidence
**Traced:** YYYY-MM-DD · **Depth:** full | shallow · **Profile:** full | guide · **Commit:** <sha>
**Entry points covered:** <n>/<n> — <any not covered, and why>

### Tasks
| # | Task (the person's words) | Who | Screen › control | Entry points it calls | Source |

### Capabilities
| # | Capability | Actor | Entry point | Contract † | Authorization † | Evidence |

### Business rules
| # | Rule | Condition | Effect | Inputs | Met in | Evidence | Tier |

### Validations & gates
| # | Check | Applies to | On failure (user-visible) | Exact message shown (verbatim, source) | Technical outcome † | Evidence |

### Entity states
| Entity | States (shown to the person: label, where) | Transitions (trigger → from → to) | Refused transitions | Evidence |

### Decision points
| # | Decision | Inputs | Outcomes | Evidence |

### Integrations
| System | Trigger | Sends † | Expects † | What people notice | On failure | Evidence |

### Edges
| # | Entry point | Kind | Reads † | Writes † | Also written by † | Emits | Reacted to by (one hop out) | Mode † | On failure | What people notice | Evidence |

### Configuration & switches
| # | Key / constant | Defined at † | Default | Effect | Varies by † | Who can change it, where | Evidence |

### Tests & telemetry †
| # | Kind (test / log / span / metric) | Name / path | Covers | Gap | Evidence |

### Client vocabulary
| Client term | Where seen | Where in the product (screen › control) | Code name |

### Intent notes (`#inferred`)
| Observation | Probable purpose | Basis (story / `#confirmed` KB / comment / test / commit / naming) | Question for the business |

### Findings (not documentation)
| # | What | Evidence | Kind (defect / unreachable / contradiction / stale comment / planned, not built) |
```

† recorded in the `full` profile only. The `guide` profile writes no Tests & telemetry section.

## Handling what is not documentation

You are tracing, not auditing; handle these and keep moving:

| Found | Do |
|---|---|
| A defect (wrong calculation, missing check, unhandled failure) | A **finding to report**, with evidence. Never fix it, switch to auditing, or document it as intended behavior |
| Unreachable code (no route, dead flag, no caller anywhere) | Record it as unreachable; **never document it as a capability** — the most common way generated docs go wrong |
| A trigger whose caller is outside the repository (a message nothing here publishes, a handler another service calls) | **Not unreachable.** A capability, plus a finding and the open question "who triggers this?" |
| Two contradicting rules | Both with evidence; escalate — `business-analyst` owns which wins |
| A rule whose purpose is unrecoverable | The behavior plus an open question — a normal outcome, not a failed trace |
| Something that should obviously change | Route it to the owning `be-<stack>` agent; you do not change code |
