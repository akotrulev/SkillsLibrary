---
description: Run the whole design audit on this UI — visual identity, tokens, IA, heuristics, flow, responsiveness, UI code, copy, charts, icons, WCAG 2.2 design decisions, ethics, AI UX, motion, landing structure — read-only, saved to docs/audits/
argument-hint: [optional: the app URL / how to start it, or a scope limiter]
---

Run a **full design audit** on this project as the **`design-auditor`** agent.

Sixteen lettered sections, A–P: visual identity · token system · IA & shell · Nielsen heuristics · flow friction · responsiveness budget · UI-code guidelines · copy voice · charts · iconography · brand fidelity · **design-time accessibility (WCAG 2.2)** · **ethical patterns** · **AI experience** · **motion** · **landing structure**. Five are applicability-gated — N only where the app ships an AI or agent feature, M only where it asks for money, consent, data, or a device permission, O only where anything animates, P only where a marketing page ships.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/design/agents/design-auditor.md` (fall back to `design/agents/design-auditor.md` when working inside the SkillsLibrary repo itself).
2. Follow it as your operating instructions for the rest of this task: its invariants (read-only, the browser contract, the artifact and permanent IDs, the corpus as source of truth), every-run start (rules, orientation, engine and corpus, round, evidence mode and driver), sections, steps, re-audit paragraph, boundaries and report all apply.
3. Load each section's owning `design/<skill>/SKILL.md` **before sweeping that section** — its `## Review checklist` is the section's rule set and its check numbers are the finding IDs.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and the orientation cache, nothing else; the `fe-*` / `mobile-*` agent applies fixes in a separate run. Driving Claude in Chrome means driving the user's real browser: the agent's browser contract applies in full.

**Scope limiter / how to reach the app (optional):**

$ARGUMENTS

If nothing was given above, ask once how to start or reach the app (and whether to drive it), then audit the whole UI: build the applicability matrix and sweep every applicable section A–P.

When done, relay the agent's report block (stack · evidence mode · driver · applicability · coverage · report path · finding counts by severity · cross-altitude count · highest-leverage item) and the path to the saved report.
