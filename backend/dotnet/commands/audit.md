---
description: Audit this .NET service against the be-dotnet plugin conventions — read-only, saves a findings report to docs/audits/
argument-hint: [optional: project, path, or sections to limit the sweep to]
---

Run a **be-dotnet conformance audit** on this repository: sweep the service against the conventions and flows this plugin defines, and save a findings report.

1. `Read` the engine at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/standards-audit-engine/SKILL.md` (fall back to `engineering-practices/standards-audit-engine/SKILL.md` inside the SkillsLibrary repo) — it owns Mode A/B, the artifact contract, evidence rules, severity, and the report templates.
2. `Read` the stack skill at `${CLAUDE_PLUGIN_ROOT}/backend/dotnet/skills/standards-audit/SKILL.md` (fall back to `backend/dotnet/skills/standards-audit/SKILL.md`), then its `references/conformance-checklist.md` **end-to-end**.
3. Follow them exactly — the TFM/version gate, the applicability matrix, the section-by-section sweep (A–N), the evidence rules, the report template, and the hostile self-review all apply.
4. Check `docs/audits/` first: a prior `…-be-dotnet-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
5. Load the owning `backend/dotnet/skills/<skill>/SKILL.md` (or the bundled `observability/*` skill for section L) whenever a check is ambiguous, version-keyed, or you are about to write its fix direction.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; the `be-dotnet` agent applies them in a separate run.

**Evidence is static-first.** Read code, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run `dotnet build` / `dotnet test` / analyzers or probe a live service if the user explicitly opts in for this audit — and let execution corroborate a code trace, never replace it.

**Version gate first.** Detect the TFM (net8/9/10, and any mix — a mixed solution is finding A2), the EF Core major, and `Nullable` state before judging anything. Never flag a down-level project for lacking an up-level API, and never propose one as a fix.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, audit the whole repository: detect the version lane, build the applicability matrix, and sweep every applicable section A–N.

When done, report the engine's output contract (detected lane · applicability · coverage · report path · finding counts by severity · highest-leverage item) and the path to the saved report.
