---
paths:
  - "docs/audits/*-requirements.md"
  - "docs/audits/*-audit-r*.md"
---

<!-- dev rules v1 (2026-11-03): audits. Installed by /dev:rules; edit the paths above if this project keeps its audits elsewhere. -->

# Audit register and round standards

For anyone who writes, edits or acts on an audit file. Severity: **blocker** breaks round-over-round comparison or claims what was not proven, **major** weakens the evidence, **minor** is form. Where the project consistently keeps audits another way, follow it.

## Every round

- A delivered round (`<NNN>-<slug>-…-r<N>.md`) is never edited, overwritten or regenerated; the next round is a new file. *blocker*
- `<NNN>` is minted once per subject and every round reuses it. Requirement ids, surface letters and finding numbers are permanent: new ones continue the sequence, none is renumbered or reused. *blocker*
- Fixing a finding never edits the audit: cite its id in your commit or report. **Resolved** is claimed only in a new round after re-reading the code that round, never on a commit, ticket, green test or `#inferred` evidence. *blocker*

## code-auditor's files (written by `dev:audit-spec` or `dev:audit-feature`)

- The register is append-only: a new or descoped requirement takes the next free id, marked `Added r<N>` / `Descoped r<N>`. A source's own id goes in `Source`, never as the id. *blocker*
- One checkable statement per requirement, every source cited. Contradicting sources stay two entries marked `⚠️ CONFLICT`; never pick a winner. *major*
- Every claim cites `file:line` read that round, tagged `#confirmed` (traced end to end) or `#inferred` (a chain of more than one link is a guess); a negative claim names its search; never assert from a name; comments and docs are `#inferred` at best. *blocker*
- Every finding sits under exactly one of **Data issues / Code issues / Logical conflicts**; all three headings in every round, `None.` when empty. A logical conflict or `Divergent` verdict names who decides, never a side. *major*
- A finding has a concrete failure scenario behind its severity and a one-line fix direction naming who applies it, never an applied fix. *major*
- Each section or surface closes with a 2–4 sentence summary (state, pattern, next action), never a walk through its rows; a re-audit keeps **Closed this round**. *minor*
- Sequencing is by leverage, not severity. What could not be settled goes to Open questions, never guessed. *minor*
