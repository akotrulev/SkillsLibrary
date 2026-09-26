---
name: qa-bug-report-writer
description: Use when the user describes a defect they found and wants a formal bug report written, or asks to improve an existing bug report. Triggers: "write a bug report for X", "I found a bug — help me file it", "rewrite this Jira ticket so devs can reproduce it". Not for test cases (test-case-writer) or exploratory session notes (exploratory-charter-writer).
---

# QA Bug Report Writer

Turns a rough defect observation into a high-signal bug report that a developer can reproduce, triage, and fix without needing follow-up questions.

## When to use

- The user describes a bug they observed and wants it written up formally
- The user has a draft bug report and wants it sharpened
- The user wants the same bug written for different audiences (engineering vs product)

## When NOT to use

- The user wants to derive test cases from requirements → `qa/manual/test-case-writer`
- The user wants an exploratory session charter → `qa/manual/exploratory-charter-writer`
- The user wants to triage / prioritize a backlog of bugs → out of scope

## Inputs needed

Ask only what's missing:

1. **What did you observe?** (the symptom)
2. **What did you expect?**
3. **How did you get there?** (steps)
4. **Environment** — build version, OS, browser/device, user role, env (dev/staging/prod)
5. **Evidence** — logs, screenshots, request/response, network traces, video
6. **Frequency** — always, intermittent, once
7. **Impact** — what does this block?

If the user has logs or HAR files, ask to see the relevant slice — don't fabricate.

## Procedure

1. Separate **what was observed** from **what was inferred**. Only the observation goes in the report; the inference goes in the analysis section if at all.
2. Reproduction steps must be:
   - Numbered, atomic, in imperative mood ("Click X", not "I clicked X")
   - Free of irrelevant clicks (don't include "open browser" unless that's part of the bug)
   - Self-contained — a developer should be able to follow them with no prior context
3. Severity and priority are **different**:
   - **Severity** = how broken (cosmetic, minor, major, critical, blocker)
   - **Priority** = how soon to fix (P1–P4)
   - A typo in the footer can be high priority (CEO sees it) but low severity. Don't conflate.
4. Add log excerpts as code blocks with the relevant lines only — not the whole file.
5. Note any reproduction steps you couldn't verify yourself and label them as such.

## Output format

```markdown
# [BUG] <one-line summary, action + outcome>

**Severity**: <Cosmetic / Minor / Major / Critical / Blocker>
**Priority**: <P1 / P2 / P3 / P4>
**Status**: New
**Environment**: <env, build, OS, browser, device>
**Reproducibility**: <Always / Intermittent (N/M) / Once>
**Reporter**: <name>
**Date**: <YYYY-MM-DD>

## Summary

<2–3 sentence description: what happens, where, and why it matters.>

## Steps to Reproduce

1. Step
2. Step
3. Step

## Expected Result

<What should have happened, and which AC / spec / convention says so.>

## Actual Result

<What actually happened. Stick to observations.>

## Evidence

- Screenshot: `<path or attachment ID>`
- Video: `<path>`
- Console log excerpt:
  ```
  <relevant lines>
  ```
- Network trace (request that failed):
  ```
  POST /api/orders → 500
  X-Request-ID: abc-123-def
  Trace ID: 1a2b3c...
  ```

## Impact

<Who is affected, how often, what they can/can't do as a result.>

## Workaround

<If known. "None" if not.>

## Notes / Analysis

<Hypotheses, not facts. Link to related bugs. Flag anything you didn't verify.>
```

## Quality bar

A bug report passes if:

- [ ] Title reads as `<action> <object> <unexpected outcome>` — e.g. "Submitting order with empty cart returns 500 instead of 400"
- [ ] A developer with zero context can reproduce it from the steps
- [ ] Expected result cites a source (AC, spec, prior behavior, convention)
- [ ] Severity and priority are set separately and justified
- [ ] At least one piece of evidence is attached (or marked "evidence unavailable, reason: X")
- [ ] No "I think" / "it seems" in the Actual Result section — those go in Notes
- [ ] Trace IDs or request IDs included when available

## Severity guide

| Severity   | Definition                                                                 |
|------------|----------------------------------------------------------------------------|
| Blocker    | No usable workflow. Release cannot ship.                                   |
| Critical   | Major function broken, data loss, security issue, or whole feature down.   |
| Major      | A feature works incorrectly, real user impact, workaround exists but ugly. |
| Minor      | Small functional issue, low user impact.                                   |
| Cosmetic   | Visual / textual issue with no functional impact.                          |

## Priority guide

| Priority | Definition                                                          |
|----------|---------------------------------------------------------------------|
| P1       | Fix now. Blocks release or affects production users right now.      |
| P2       | Fix this sprint.                                                    |
| P3       | Fix when convenient or next release.                                |
| P4       | Track but no commitment.                                            |

## Example

### Input from user (rough)

> "When I add stuff to cart and then remove the last item, the cart total shows -€5 instead of 0. It's confusing. Happens on Chrome staging."

### Generated bug report

```markdown
# [BUG] Cart total displays negative value (-€5.00) after removing last item

**Severity**: Major
**Priority**: P2
**Status**: New
**Environment**: staging, build 2026.05.21-rc3, Chrome 135 / macOS 14.5
**Reproducibility**: Always (5/5)
**Reporter**: Aleks
**Date**: 2026-05-27

## Summary

Removing the last item from a cart that previously had a shipping discount applied leaves the cart total at a negative value instead of resetting to €0.00. The cart UI shows "-€5.00" and the checkout button remains enabled.

## Steps to Reproduce

1. Sign in as a user with an active loyalty tier (≥5 years).
2. Add one item priced €25.00 to the cart.
3. Apply the "FREE_SHIP" promo code (loyalty members get €5 off shipping).
4. Confirm cart total reads "€20.00" (€25 - €5 shipping discount).
5. Click "Remove" on the only item.
6. Observe the cart total.

## Expected Result

Cart total displays "€0.00" and the checkout button is disabled.
*(Source: AC-CART-12 — "An empty cart shows a zero total and disables checkout.")*

## Actual Result

Cart total displays "-€5.00". Checkout button remains enabled. Clicking checkout produces a 500 from `POST /api/orders`.

## Evidence

- Screenshot: `cart-negative-total.png`
- Console log excerpt:
  ```
  CartReducer: REMOVE_ITEM { itemId: "sku-9981" }
  CartTotal: { items: 0, shippingDiscount: -5, total: -5 }
  ```
- Failing request:
  ```
  POST /api/orders → 500
  X-Request-ID: 7f3b-22ae-0091
  Trace ID: a0b1c2d3e4f5...
  Body: { items: [], total: -5.00 }
  ```

## Impact

Any loyalty user who applies a shipping discount and then empties their cart sees an inconsistent total and an unusable checkout. Worst case: order is submitted with a negative total and crashes the order service. Observed in staging; production telemetry shows 3 similar 500s in the past 24h.

## Workaround

Refresh the page after emptying the cart — total recalculates to €0.00.

## Notes / Analysis

The shipping discount is being kept in cart state after the item that triggered eligibility is removed. Likely fix is to recompute applicable promos on every `REMOVE_ITEM` action, not just on add or checkout. Possibly related to BUG-1188 (promo persistence across sessions) — not verified.
```

## Anti-examples

> "Login broken"

Useless. Force a rewrite with: title that names the action and outcome, env, repro steps, evidence.

> "App crashes sometimes when I click stuff"

Cannot be acted on. Push back for: which stuff, when, what crash (white screen, exception, hang), any patterns (after N actions, after idle, etc).
