---
description: Run the whole design audit on this UI — visual identity, tokens, IA, heuristics, flow, responsiveness, UI code, copy, charts, icons — read-only, saved to docs/audits/
argument-hint: [optional: the app URL / how to start it, or a scope limiter]
---

Run a **full design audit** on this project as the **`design-auditor`** agent.

1. `Read` the agent definition at `${CLAUDE_PLUGIN_ROOT}/design/agents/design-auditor.md` (fall back to `design/agents/design-auditor.md` when working inside the SkillsLibrary repo itself), then follow it as your operating instructions for the rest of this task.
2. Load `engineering-practices/agent-orientation-cache` first, then `engineering-practices/standards-audit-engine` for the Mode A/B procedure, the evidence rules, and `references/report-template.md`.
3. Load each section's owning `design/<skill>/SKILL.md` **before sweeping that section** — its `## Review checklist` is the section's rule set and its check numbers are the finding IDs.
4. Check `docs/audits/` first: a prior `…-design-audit-r<N>.md` means **Mode B (re-audit)** — reuse its section letters and finding IDs verbatim, never renumber. Otherwise **Mode A (baseline)**.

**Declare the evidence mode and the capture driver before judging anything.** Sections A · C · D · E · F are about pixels: with a running app, capture each primary task end to end at desktop **and** the narrowest supported width — through the **Playwright MCP** by default, falling back to **Claude in Chrome** (`mcp__claude-in-chrome__*`) when Playwright is absent or the app is only reachable through the user's own session. With only screenshots, sweep just those screens; with neither, mark those sections **Unverifiable** and say so — never quietly downgrade this to a code audit.

**Driving Chrome means driving the user's real browser**, so the read-only contract extends to it: work in a new tab, prefer a local or staging target, never complete a destructive or state-changing action against real data (walk up to the final control, capture it, stop), never trigger a native `alert`/`confirm` dialog — read the handler in source instead — and record the driver, environment, and account context in the report header.

**Read-only.** `Write`/`Edit` are for the report under `docs/audits/` and the orientation cache, nothing else — never fix, restyle, or "quickly correct" anything found, however trivial. Findings carry a one-line fix direction and the owning design skill; the `fe-blazor` / `fe-react` agent applies them in a separate run.

**Scope limiter / how to reach the app (optional):**

$ARGUMENTS

If nothing was given above, ask once how to start or reach the app (and whether to drive it), then audit the whole UI: build the applicability matrix and sweep every applicable section A–K.

When done, report the agent's output contract (stack · evidence mode · applicability · coverage · report path · finding counts by severity · cross-altitude count · highest-leverage item) and the path to the saved report.
