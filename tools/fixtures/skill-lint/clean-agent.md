---
name: clean-agent
description: Use when a fixture needs a clean agent. Triggers "lint the clean agent". Not for skills (front-door).
tools: Read
model: inherit
---

# Senior Fixture — Clean agent

Owns nothing beyond passing the lint.

## Steps

| # | Step | Load | Done when |
|---|---|---|---|
| 1 | Read | `engineering-practices/writing-for-agents` · the task writes a rule file → `engineering-practices/writing-for-agents/references/skill-mechanics.md` | every file is read |
| 2 | Report | — | the report is written |

### Notes

Read the standard's rule table before step 1.

## Report

```
Mode: BUILD | FIX — <one line>
Changed: <path> — <one line each>
```
