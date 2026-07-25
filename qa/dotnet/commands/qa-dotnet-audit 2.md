---
description: Audit this .NET test suite against the qa-dotnet plugin conventions — read-only, saves a findings report to docs/audits/
argument-hint: [optional: test project, path, or sections to limit the sweep to]
---

Run a **qa-dotnet conformance audit** on this repository: sweep the **test suite** against the conventions this plugin defines, and save a findings report.

1. `Read` the engine at `${CLAUDE_PLUGIN_ROOT}/engineering-practices/conformance-audit/SKILL.md` (fall back to `engineering-practices/conformance-audit/SKILL.md` inside the SkillsLibrary repo) — it owns Mode A/B, the artifact contract, evidence rules, severity, and the report templates.
2. `Read` the stack skill at `${CLAUDE_PLUGIN_ROOT}/qa/dotnet/skills/conformance-audit/SKILL.md` (fall back to `qa/dotnet/skills/conformance-audit/SKILL.md`), then its `references/conformance-checklist.md` **end-to-end**.
3. Follow them exactly — the suite-lane detection, the applicability matrix, the section-by-section sweep (A–N), the evidence rules, the report template, and the hostile self-review all apply.
4. Check `docs/audits/` first: a prior `…-qa-dotnet-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
5. Load the owning `qa/dotnet/skills/<skill>/SKILL.md` (or the `qa/reporting/dotnet` / `qa/cicd` sibling for sections L and M) whenever a check is ambiguous, tool-keyed, or you are about to write its fix direction.

**THE SCOPE FENCE: this audits the test suite, not the application.** Every finding must be about test code — structure, layering, waits, data, assertions, reporting, CI. Application defects the suite exposes are bug reports (`qa/manual/bug-report-writer`); application conventions belong to `be-dotnet-conformance-audit` / the `fe-*` audits. A brittle locator is a *suite* finding even when a missing `data-testid` caused it — report the locator strategy and hand the testid list to the frontend peer.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; the matching `qa-*-dotnet` agent applies them in a separate run.

**Evidence is static-first.** Read code, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run `dotnet build` / `dotnet test` or probe a live environment if the user explicitly opts in — and let execution corroborate a code trace, never replace it.

**Tool lane first.** Detect the runner (NUnit / xUnit / MSTest), the UI driver (Playwright .NET / Selenium / Appium / none), the API stack, Reqnroll, Testcontainers, Allure, and the CI host before judging anything. A suite is never in violation for lacking a tool it doesn't use — those rows are N/A. A documented house convention that differs from a plugin default is a **deviation**, not a finding.

Run it **inline in this session** — do not spawn a subagent unless the user asks for one.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, audit every test project in the repository: detect the suite lane, build the applicability matrix, and sweep every applicable section A–N.

When done, report the engine's output contract (detected lane · applicability · coverage · report path · finding counts by severity · highest-leverage item) and the path to the saved report.
