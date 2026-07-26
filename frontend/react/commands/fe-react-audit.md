---
description: Audit this React/Next.js codebase against the fe-react plugin conventions — read-only, saves a findings report to docs/audits/
argument-hint: [optional: path, app, or sections to limit the sweep to]
---

Run a **fe-react conformance audit** on this repository: sweep the codebase against the conventions and flows this plugin defines, and save a findings report.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/frontend/react/skills/standards-audit/SKILL.md` (fall back to `frontend/react/skills/standards-audit/SKILL.md` when working inside the SkillsLibrary repo itself), then its `references/conformance-checklist.md` **end-to-end** and `references/report-template.md`.
2. Follow it exactly — the version gate, the applicability matrix, the section-by-section sweep, the evidence rules, the report template, and the hostile self-review all apply.
3. Check `docs/audits/` first: a prior `…-fe-react-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
4. Load the owning `frontend/react/skills/<skill>/SKILL.md` whenever a check is ambiguous, version-keyed, or you are about to write its fix direction.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; the `fe-react` agent applies them in a separate run.

**Evidence is static-first.** Read code, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run builds, type-checks, tests, or a live app if the user explicitly opts in for this audit — and let execution corroborate a code trace, never replace it.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, audit the whole repository: detect the render target and React/Next majors, build the applicability matrix, and sweep every applicable section A–S.

When done, report the output contract from the skill (detected lane · applicability · coverage · report path · finding counts by severity · highest-leverage item) and the path to the saved report.
