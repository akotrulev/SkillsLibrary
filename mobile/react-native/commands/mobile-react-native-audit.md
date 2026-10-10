---
description: Audit this React Native / Expo app against the mobile-react-native plugin conventions — read-only, saves a findings report to docs/audits/
argument-hint: [optional: path, feature area, or sections to limit the sweep to]
---

Run a **mobile-react-native conformance audit** on this repository: sweep the codebase against the conventions and flows this plugin defines, and save a findings report.

1. `Read` the skill at `${CLAUDE_PLUGIN_ROOT}/mobile/react-native/skills/standards-audit/SKILL.md` (fall back to `mobile/react-native/skills/standards-audit/SKILL.md` when working inside the SkillsLibrary repo itself), then its `references/conformance-checklist.md` **end-to-end** and the engine's `references/report-template.md`.
2. Follow it exactly — the version gate, the applicability matrix, the section-by-section sweep, the evidence rules, the report template, and the hostile self-review all apply.
3. Check `docs/audits/` first: a prior `…-mobile-react-native-conformance-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.
4. Load the owning `mobile/react-native/skills/<skill>/SKILL.md` whenever a check is ambiguous, version-keyed, or you are about to write its fix direction; sections K, L, T, U and X are read from the `mobile/_shared/*/references/audit-checks.md` fragments.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and nothing else — never fix, reformat, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning skill; the `mobile-react-native` agent applies them in a separate run. A row a static read cannot prove is reported **unverified → `qa-security`**, never passed.

**Evidence is static-first.** Read code, cite `file:line`, tag `#confirmed` / `#inferred`, and name the search behind every negative claim. Only run builds, type-checks, tests, `expo-doctor`, or a simulator if the user explicitly opts in for this audit — and let execution corroborate a code trace, never replace it.

**Scope limiter (optional):**

$ARGUMENTS

If nothing was given above, audit the whole repository: detect the Expo SDK and workflow, build the applicability matrix, and sweep every applicable section A–X.

When done, report the output contract from the engine (detected lane · applicability · coverage · report path · finding counts by severity · highest-leverage item) and the path to the saved report.
