# Lint mode and the automation-candidate score

Loaded from `SKILL.md` when existing manual cases are checked or ranked for automation.

## 1. Lint mode — existing cases, findings only

Given an existing suite (Markdown, CSV export, or a test-management dump), read every case and report what would
make two testers get different results. **Never rewrite a case**: each finding names the case, the field and the
one-line fix direction; the author applies it.

| Rule | Flags | Example | Severity |
|---|---|---|---|
| **Vague action** | A step a tester could perform two ways: "check", "verify", "test", "try", "navigate around", "use the form" | "Verify the discount works" | major |
| **Vague data** | A value left to the tester: "a valid email", "some amount", "any user", `<invalid>`, "test data" | "Enter a valid card" | major |
| **Non-observable expected result** | No value, status or record a tester can see: "works correctly", "as expected", "is handled", "no errors", a message with no effect | "The order is processed correctly" | major (blocker on a P1 case) |
| **Unbounded wait** | A wait with no condition or no limit: "wait a while", "wait for it to finish", "after some time", a fixed "wait 30 s" | "Wait for the email" | major |
| **Multiple behaviours per case** | Two goals, two invalid inputs, or two outcomes joined by "and"/"or" that can fail independently; a step with no checkpoint before a dependent one | "Log in, change the password and update the address" | major |
| **Either-or expected result** | Two acceptable outcomes: "200 or 204", "shown or hidden" | "An error or a warning is shown" | major |
| **Missing field** | Empty Priority, Type, Technique or Source; preconditions that act instead of describing state | — | minor |

Output uses the house review table, then one line of totals:

```
| Severity | Location            | Issue                                        | Suggested fix                                         |
|----------|---------------------|----------------------------------------------|-------------------------------------------------------|
| major    | TC-CART-004 step 3  | Vague data: "enter a valid coupon"           | Name the coupon and its effect: `SPRING15`, −15 %     |
| blocker  | TC-CART-002 expected| Non-observable on a P1 case: "total updates" | State the figure: €80.00 → €68.00                     |
| major    | TC-CART-007 step 2  | Unbounded wait: "wait for the email"         | `within ASYNC_BUDGET`, the email in the inbox         |
```

`Lint: 24 cases · 9 findings (1 blocker, 7 major, 1 minor) · 15 clean.`

## 2. Automation-candidate score

After lint, rank the **clean** cases for automation (a case with open blocker or major findings is not a candidate
until fixed). Score each factor 1–3 and compute:

**score = frequency × risk × stability ÷ automation cost**

| Factor | 1 | 2 | 3 |
|---|---|---|---|
| **Frequency** — how often it must run | Release only | Every sprint | Every build / every deploy |
| **Risk** — what a miss costs | Cosmetic | A feature degraded | Money, entitlement, data loss, security (every P1) |
| **Stability** — how settled the behaviour and UI are | Changing now | Changes occasionally | Settled |
| **Automation cost** — effort to automate | Data and hooks exist | Needs new data or a test hook | Needs a device, a third party, a clock or a human judgement |

**≥ 6** automate first · **2 – 6** automation backlog · **< 2** stays manual. Ties go to the case with the higher
risk. Add the score as a column (`Auto`) beside Priority; it does not replace Priority.
