---
name: qa-exploratory-charter-writer
description: Use when the user asks to write a session-based exploratory testing charter — bounded, mission-driven, deliberate exploration of a feature or area with a clear time-box and reportable outcome. Triggers: "write a charter for X", "plan an exploratory session for feature Y", "session-based test plan", "what should we explore in the Z release", "design a test tour". Do NOT use for formal test cases (use `qa/manual/test-case-writer`), bug reports (use `qa/manual/bug-report-writer`), or test strategy (use `qa/manual/test-strategy`).
---

# QA — Exploratory Test Charter Writer

Produces a Session-Based Test Management (SBTM) charter: a short, mission-shaped brief that scopes one or two hours of deliberate, evidence-producing exploration. Charters are the lightweight planning artifact between "the suite of automated tests" and "let's poke around and see what breaks" — they keep exploration learnable, comparable, and reportable.

## When to use

- A new feature is ready and the automated suite is intentionally thin pending learning
- Risk-tilting tests in `qa/manual/test-strategy` call out "exploratory: high"
- A regression has surfaced and you want a focused investigation
- Onboarding a new tester — charters double as a tour of the system
- Post-incident learning: explore the area to find adjacent risks
- Pre-release "shake-down" before a major launch

## When NOT to use

- Step-by-step formal test cases → `qa/manual/test-case-writer`
- Filing a defect → `qa/manual/bug-report-writer`
- The whole release plan → `qa/manual/test-strategy`
- Automated regression scaffolding → the per-stack `qa/<stack>/skills/api-test-author/...` / `qa/<stack>/skills/ui-test-author/...`

## What a charter is (and isn't)

A charter is a **mission**, not a script. It says *what we're exploring* and *why* — never *how* step by step. The tester picks heuristics, tours, and oracles during the session.

| A charter has | A charter does not have |
|---|---|
| A short mission statement | Step-by-step instructions |
| A scope (areas in / out) | A pass/fail outcome (it's notes + findings) |
| A time-box (60 / 90 / 120 min) | A schedule for every minute |
| Risks to probe | Bug reports inside it |
| Heuristics / oracles to apply | Boilerplate test-management cruft |
| A deliverable shape (notes, bugs, questions) | A predicted result |

## Inputs needed

1. **Feature / area** to explore
2. **Recent context** — what just shipped, what's risky, what stakeholders worry about
3. **Tester** (single person — sessions are 1-up)
4. **Time-box** — typical 60–120 min
5. **Heuristics / tour** the tester will lean on (see below)
6. **Environment + data** — test env, seeded user, feature flags toggled
7. **Reportable outcome** — bug list, question list, areas-to-revisit list, automation candidates

## Heuristics & tours

Heuristics are mental shortcuts that point at gaps. Common families:

| Heuristic | What it asks |
|---|---|
| **CRUD** | Can I create / read / update / delete this? Concurrent? |
| **SFDIPOT** (Bach's mnemonic) | Structure, Function, Data, Interfaces, Platform, Operations, Time — apply each to the area |
| **FEW HICCUPPS** | Familiarity, Explainability, World, History, Image, Comparable products, Claims, Users, Product, Purpose, Statutes |
| **Boundaries** | Empty, one, many, max, max+1, negative, null, very long |
| **Error guessing** | Where would a developer cut corners? |
| **Time** | What happens at clock changes, end-of-month, leap day, time zone shifts |

Tours are *guided walks* of the product through a theme:

| Tour | Walk through… |
|---|---|
| **Feature tour** | Every visible feature of the area; just enumerate |
| **Money tour** | Every flow involving payment, refund, currency |
| **Money-back tour** | Cancellations, refunds, chargebacks, partial returns |
| **Configuration tour** | Every toggle, setting, preference, feature flag |
| **Internationalization tour** | Locales, currencies, time zones, RTL |
| **History tour** | Audit trails, event logs, "what changed when" |
| **Variability tour** | Same flow with different roles, tenants, data shapes |
| **Performance tour** | Same flow at scale (10x data, slow network) |

Pick one or two tours per session — more is unfocused.

## Output format

```markdown
# Charter: <short, mission-shaped title>

**Tester:** <name>      **Date:** <YYYY-MM-DD>      **Time-box:** 90 minutes
**Build / version:** <git sha / release>            **Environment:** staging
**Feature flags:** <flag=value, flag=value>

## Mission
Explore **<area>** using **<tour / heuristics>** to discover **<risk class / question class>**.

Example: *Explore the refund flow using the money-back tour and SFDIPOT to discover invariant violations between order, payment, and ledger.*

## In scope
- <UI / API / job / endpoint that's fair game>

## Out of scope
- <explicit exclusion + reason>

## Risks to probe
- <risk> — _why we suspect it_
- <risk> — _why we suspect it_

## Heuristics / oracles
- Boundaries: empty / one / many / max
- Money: rounding, currency mismatches, partial refunds
- Comparable product: how does the competitor handle this case?
- Claims oracle: does the spec say this? does the UI say this?

## Setup / data
- Seeded user: `bob.tester@yourco.com` (role: Customer, tenant: 42)
- Order seed: 3× `Paid` orders, 1× `Cancelled` order, 1× `Refunded` order
- Feature flags: `partial-refunds=on`

## Reporting
- Bugs filed via `qa/manual/bug-report-writer` linked to this charter
- Open questions / unverified hypotheses appended to the session notes
- Automation candidates flagged with `#automate` tag

## Stop criteria
- Time-box expires, OR
- Mission is exhausted (no new questions surfacing for 15+ minutes)
```

After the session, append the **session report**:

```markdown
## Session report

**Actual duration:** 95 minutes (5 minute overrun)
**Test design / charter / setup / opportunity (TBS):** 25 / 50 / 15 / 5 %
**Test ideas generated / executed:** 18 / 14

### Findings summary

| # | Area | Severity | Type | Summary | Link |
|---|------|----------|------|---------|------|
| 1 | Refund form | Major | Bug | Partial refund of last item leaves total at -€5 | BUG-1201 |
| 2 | Refund form | Minor | UX | No loading state on submit — double-click double-submits | BUG-1202 |
| 3 | Order history | — | Observation | Ledger entries render newest-last, spec silent on order | — |

Severity = the `bug-report-writer` scale (Blocker / Critical / Major / Minor / Cosmetic); `—` for non-bug observations.
Type ∈ Bug / UX / Security / Performance / Accessibility / Missing feature / Observation.
Every Bug row links to a report filed via `qa/manual/bug-report-writer` — detail (repro steps, evidence, expected vs actual) lives **there**, one line of it here.

### Evidence
- Screenshots / console excerpts / failed-request traces captured during the session, named per finding (`finding-1-cart-total.png`) and attached to the filed bugs

### Questions raised
- <question for product / spec author>

### Areas to revisit
- <area> — _why_

### Test-case candidates
- <behavior worth a formal scripted case> — technique it maps to (e.g. BVA on refund amount) → hand to `qa/manual/test-case-writer`

### Automation candidates
- <flow> — would benefit from an API contract test

### Coverage notes
- Tested: <bullets>
- Did not test: <bullets, with reason — a gap with no reason reads as "covered">
```

The session report is the **deliverable**. A charter without a report is half a charter.

## Execution tooling & evidence (web sessions)

When the session target is a web page, drive and evidence it with the **Playwright CLI** via `npx` — `npx playwright open <url>` (headed exploration), `npx playwright codegen <url>` (record an interaction that reproduces a finding), `npx playwright screenshot <url> <file.png>` (evidence). Throwaway probe scripts go in `specs/`. Prefer the CLI over the Playwright MCP server for exploration — same observations, far cheaper; the MCP server is for `pom-builder`-style extraction workflows. During the session, keep the **console and network tabs in scope**: JS errors, failed/slow requests, and unexpected redirects are findings even when the UI looks fine.

## Time-boxes

Typical SBTM uses 60 / 90 / 120-minute sessions:

| Length | When |
|---|---|
| 60 min | Tight focus, single hypothesis, time-constrained tester |
| 90 min | Standard — long enough to find depth, short enough to stay focused |
| 120 min | Complex feature or unfamiliar area; usually with breaks |

Past 120 min the returns drop sharply — fatigue compounds, observation degrades. Schedule a fresh charter rather than extending.

## Mission shaping — the cheat sheet

A good mission has three parts:

1. **Explore** _what_
2. **Using** _what_ (tour / heuristic / model)
3. **To discover** _what_ (risk class / question class / invariant)

Examples:

| ✅ Strong | ❌ Weak |
|---|---|
| Explore the **partial refund flow** using the **money-back tour + boundary heuristic** to discover **rounding and ledger invariant violations** | Test the refund feature |
| Explore the **multi-tenant admin UI** using the **variability tour** to discover **cross-tenant data exposure** | Look at the admin screens |
| Explore the **time zone handling on the recurring deposits screen** using **time/boundary heuristics** to discover **off-by-one date and DST bugs** | Check dates |

If you can't fill in *all three* parts, the charter isn't ready.

## Risks to flag in advance

Charters work best when they probe **named** risks:

- Data: PII leaks, cross-tenant exposure
- Money: rounding, currency mismatch, partial refunds, double-charge
- Auth: privilege escalation, expired sessions, MFA bypass
- Time: time zones, DST, clock skew, end-of-month, leap year
- Performance: slow network, many items, large file
- I18N: long strings, RTL, special characters, locales
- State: concurrency, idempotency, replay, half-applied changes

Pick the two or three that fit the area. A charter that says "look for bugs" probes nothing in particular.

## Rules

- One mission per charter; one charter per session
- Mission has all three parts (explore X, using Y, to discover Z)
- Time-box explicit; default 90 min
- In-scope and out-of-scope explicit
- Heuristics + tour named (not just "exploratory testing")
- Setup + data + flags reproducible
- Reportable outcome shape declared up front
- Session report appended after the session
- Bugs filed via `qa/manual/bug-report-writer`, linked to the charter, not duplicated inline
- Charter + report kept in the project's QA wiki or repo — they're part of the history

## What NOT to do

- No step-by-step instructions in a charter
- No vague missions ("explore the new feature")
- No 240-minute marathon sessions
- No charter without an out-of-scope section
- No charter without named risks or a tour
- No "bug list" inside the charter (charters point at bugs; they aren't bug logs)
- No "pass / fail" outcome — it's notes + findings
- No deferred reporting — write the session report within the same day, or the details rot
- No charters owned by "the QA team" — one tester, one charter
- No charter that duplicates an automated test path — automation owns that; exploration owns the unscripted

## Generation steps

1. Read the BA / spec / epic for the area; confirm what's risky
2. Pick a tour + heuristics that fit the risks
3. Shape the mission with all three parts
4. Set time-box, environment, data, feature flags
5. Draft in / out of scope
6. List 2–3 named risks
7. Define the reportable outcome
8. Hand off to the tester; the tester runs the session, fills in the report
9. Bugs/questions feed back to the team

## Handoffs

- Bugs found during the session → `qa/manual/bug-report-writer`
- Strategy that includes exploratory effort → `qa/manual/test-strategy`
- Automation candidates → `qa/<stack>/skills/api-test-author/generator/<stack>` / `qa/<stack>/skills/ui-test-author/<stack>`
- Cross-team status update → `communication/stakeholder-updates`
