---
name: r8-caller
description: Use when a fixture points into another skill. Triggers "lint r8 caller". Not for owners (r8-owner).
disable-model-invocation: true
---

# Caller

- By name: `r8-owner` + `references/guide.md`.
- By plugin name: `dev:r8-owner`'s `references/guide.md`.
- By path: `../owner`'s `references/guide.md`.
- By a file inside it: `owner/SKILL.md` explains it in that skill's
  `references/guide.md`, wrapped onto the next line.
- Unqualified, still dangling: `references/guide.md`.
