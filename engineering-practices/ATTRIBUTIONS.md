# Attributions — `engineering-practices/`

Provenance for the borrowed artifacts shipped inside the developer-workflow spine. `engineering-practices/` is
registered in the `dev` plugin, so this file ships wherever the borrowed material ships. One section per
artifact. The four skills adapted from `obra/superpowers` (`brainstorming`, `writing-plans`,
`systematic-debugging`, `verify-before-done`) predate this file.

---

## `quality-constraints` — addyosmani constraint-driven-development

- Upstream: `addyosmani/agent-skills`, `https://github.com/addyosmani/agent-skills`, skill `constraint-driven-development`
- Snapshot commit: `8bfcc1f9916f2eea55494d8c1fa7f4bde867dd9e` (2026-10-31)
- Retrieved: **2026-10-31**
- License: MIT at import time.
- Mode: **adapted** — the idea is rewritten in house register. The house skill checks the agent's run against
  CLAUDE.md and the plan's acceptance tests, each item with the evidence that proves it, and does not adopt
  upstream's constraints file (plan 009 D1).

---

## `source-grounding` — addyosmani source-driven-development

- Upstream: `addyosmani/agent-skills`, `https://github.com/addyosmani/agent-skills`, skill `source-driven-development`
- Snapshot commit: `8bfcc1f9916f2eea55494d8c1fa7f4bde867dd9e` (2026-10-31)
- Retrieved: **2026-10-31**
- License: MIT at import time.
- Mode: **adapted** — detects the project's version first, fetches that version's official doc, cites URL plus
  version in the output, and defers to `design/ui-ux-pro-max` for design facts.

---

## `decision-interview` — mattpocock grilling

- Upstream: `mattpocock/skills`, `https://github.com/mattpocock/skills`, skills `grilling` and `grill-me`
- Snapshot commit: `a496f5513d4a4cf889bc48e189e579f4b0bdf6aa` (2026-10-29)
- Retrieved: **2026-10-31**
- License: MIT at import time.
- Mode: **adapted** — one question per message instead of a frontier per round, no subagents, each answer
  restated with the branch it closes or opens, and a hand-off to `/dev:design` or a plan's answered questions.

---

## `notebooklm` — PleasePrompto notebooklm-skill

The whole of `engineering-practices/vendor/notebooklm/` is vendored from PleasePrompto.

- Upstream: `PleasePrompto/notebooklm-skill`, `https://github.com/PleasePrompto/notebooklm-skill` (**archived 2026-09-10**)
- Snapshot commit: `c80722d3f27d65e06b6579add201bf69b99101d0` (2026-09-10)
- Retrieved / vendored: **2026-10-31**
- License: MIT at import time — the upstream notice is kept verbatim at
  `engineering-practices/vendor/notebooklm/LICENSE`.
- Mode: **vendored** — the tree is byte-for-byte upstream minus `.git/`, `data/` and `.venv/`.

**Unchanged from upstream, byte for byte.** It is not registered as a skill. The house entry point is
[`notebooklm`](notebooklm/SKILL.md), which routes into it and holds every library override: the
archived-upstream banner, local Claude Code only, a dedicated Google account, public notebooks with nothing
sensitive, and a per-run query budget against the free-tier cap. Browser session state lives inside the
vendored folder, so an installed plugin keeps it in the plugin cache and an update wipes it; the wrapper says
so. The root `.gitignore` excludes `data/` and `.venv/` there.
