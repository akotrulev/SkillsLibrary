---
name: design-ethical-patterns
description: Use when a flow asks the user for money, consent, data, or permission — and when reviewing one for deceptive design. Owns the symmetry rules (cancel as easy as subscribe, reject as prominent as accept), consent granularity, pricing disclosure, permission priming, and the dark-pattern taxonomy now prohibited under DSA Article 25 and enforced by the FTC. Triggers "review this signup/checkout/cancellation flow", "is this a dark pattern", "cookie consent design", "how should we ask for this permission". Not for the words themselves (`design-ux-writing`) or auth mechanics (a stack's `auth0`).
---

# Ethical patterns — the flows that ask for something

Owns the design of every moment the interface asks the user to **give** something — money, consent, personal data, a device permission, their continued subscription — and the review of those moments for deceptive design. Everything else in `design/` optimizes for the user getting their task done; this one governs the places where the product's interest and the user's diverge, which is exactly where good craft quietly becomes manipulation.

**This is no longer a values conversation.** The EU **Digital Services Act, Article 25** prohibits dark patterns outright — naming three categories of autonomy violation: **deception, manipulation, and distortion or impairment** of the user's ability to make free choices. The US FTC treats them as unfair or deceptive acts under §5; its **September 2025 settlement with Amazon was $2.5 billion**, and the complaint turned on two design decisions: enrolment repeatedly pushed during checkout with the opt-out obscured, and a cancellation flow of **four pages, six clicks, and fifteen options**. GDPR/ePrivacy consent must be a clear, unambiguous, freely given indication, separate from other terms, and free of confusing design.

**Why a code-generating library needs this as a house rule, not a nicety:** measurement of LLM-generated e-commerce components found deceptive designs present **by default** — the patterns below are what a model reaches for when asked to "increase conversion" without constraint. An agent that writes UI needs the taxonomy as an explicit prohibition, because the training distribution supplies it as a suggestion.

## The symmetry rule — the one rule most of this reduces to

**Leaving must cost no more than arriving. Declining must be no harder to find than accepting.**

Applied concretely:

- **Cancel where you subscribed, in the same number of steps.** If sign-up is three clicks in the app, cancellation is not a phone call, a support ticket, a retention gauntlet, or a page in a different product. One retention offer is defensible; a chain of them is the roach motel the FTC settled over.
- **Reject and accept get equal visual weight** — same size, same contrast, same level of the hierarchy. "Reject all" one level deeper than "Accept all" is the single most-cited consent violation, and it is a *design* choice every time.
- **Unsubscribe is one click from the email**, and the preference it changes is the one the user expected.
- **Downgrade is as available as upgrade**, and does not require contacting anyone.

If a flow fails symmetry, no amount of honest copy rescues it — the structure is the deception.

## The taxonomy — what is prohibited, and what it looks like

| Pattern | What it does | The rule |
|---|---|---|
| **Roach motel** | Easy in, hard out | Symmetry rule, above. The canonical DSA/FTC target |
| **Obscured opt-out** | The decline path is small, low-contrast, off-path, or worded as a loss | Equal weight, plain verb, on the same screen |
| **Confirmshaming** | Declining requires agreeing to an insult ("No thanks, I like paying full price") | The decline label states the action, neutrally, and nothing else |
| **Preselection** | Consent, add-ons, or upgrades ticked by default | Nothing that costs money, data, or privacy is pre-selected. Ever |
| **Sneak into basket** | Items or subscriptions added by the flow itself | The user adds; the system never does |
| **Drip pricing / hidden costs** | Fees, shipping, or tax appear only at the final step | Total cost, including fees, is visible at the point of commitment |
| **Forced continuity** | A trial converts silently to a paid plan | The charge date and amount are stated at sign-up and again before charging |
| **Fake urgency / scarcity** | Countdown timers that reset, "3 people viewing", invented stock levels | A timer or count reflects a real constraint, or it does not exist |
| **Nagging** | The same request repeated after refusal | A refusal is remembered. One re-ask, much later, at most |
| **Trick wording** | Double negatives, inverted checkboxes ("Untick to not receive…") | One positive statement, one action, no negation to unpick |
| **Bundled consent** | One switch covering analytics, marketing, and third-party sharing | Granular, per-purpose, individually refusable |
| **Disguised ads** | Sponsored content styled as native results or system UI | Labeled, visually distinguishable |
| **Privacy zuckering** | Defaults set to maximum disclosure | Defaults are the privacy-protective option |

## Consent

- **Granular and unbundled.** One switch per purpose — essential (no consent needed) · analytics · marketing · third-party sharing. A single "accept all" may exist beside them; it may not replace them.
- **Freely given means refusable without penalty.** If refusing degrades the core product, it was not freely given.
- **Revocable in one obvious place**, as easily as it was granted, and the withdrawal takes effect without a support conversation.
- **Separate from terms.** Consent bundled into "I agree to the Terms" is not consent.
- **Not a wall on first paint** where the law does not require one; where it does, the dialog carries a real reject control at the top level.

## Money

- **State the total where the commitment happens** — the price the user will actually be charged, including fees and shipping, before the button that commits them.
- **Recurring means saying so in the same breath as the price**: the amount, the interval, the first charge date, and what happens when a trial ends. Then again, before the first charge.
- **Guest checkout exists.** Forced account creation is measured to cost roughly a third of customers, and it converts a purchase into a data collection.
- **Ask only for the fields the order needs.** The average checkout carries **~15 fields against the 6–8 actually required** — every extra one is friction the user pays for and the product does not need.
- **One flat sequence, no steps within steps** — the most-cited single source of checkout confusion.

## Permissions and data

- **Prime before you prompt.** Explain what the permission unlocks *in the interface*, and only then trigger the OS dialog — a system prompt on first launch with no context is refused permanently, which serves nobody.
- **Ask at the moment of value**, attached to the action that needs it, never in an onboarding sweep.
- **Ask for the least that works** — coarse location over precise, one photo over the library.
- **A refusal is a legitimate answer.** The feature degrades gracefully, states what is unavailable, and offers the path back if the user changes their mind.
- **Disclose the use in the flow**, not only in the policy — what is collected, what it is for, who else sees it.

## Review checklist

- **Symmetry holds**: cancel/downgrade/unsubscribe cost no more than subscribe/upgrade/subscribe, and decline is as prominent as accept.
- **Nothing that costs money, data, or privacy is preselected**; nothing is added to a basket by the system.
- **Total cost, recurrence, and the first charge date** are visible at the point of commitment.
- **No pattern from the taxonomy table** is present.
- **Consent is granular, unbundled, refusable without penalty, and revocable in one place.**
- **Permissions are primed, asked at the moment of value, minimal, and gracefully refusable.**
- **Urgency and scarcity signals correspond to something real.**
- **A refusal is remembered** — no re-ask on the next visit.
- **Every decline control is a neutral verb** — no shaming, no double negative, no inverted checkbox.

## What NOT to do

- Do not treat "the flow is legal in our market" as the standard — DSA Art. 25 and FTC §5 both bite on structure, not jurisdiction of incorporation, and the taxonomy above is the enforcement surface.
- Do not fix a structural violation with better copy. If leaving is harder than arriving, rewording the button changes nothing.
- Do not let a conversion target enter this skill's decisions. Optimizing the flow is legitimate; optimizing the *user's ability to refuse* is the thing being prohibited.
- Do not implement a requested dark pattern silently. Name it, state the rule and the exposure, offer the compliant version that serves the same business goal — then follow the human's decision and record it.

## Related

- [`design/ux-writing`](../ux-writing/SKILL.md) — the **words** in these flows: neutral decline labels, confirmations that name the object, errors that don't blame. This skill owns the *structure*, that one owns the *sentence*.
- [`design/ux-patterns`](../ux-patterns/SKILL.md) — form layout and the surface rule the consent and checkout screens are built on.
- [`design/ux-review`](../ux-review/SKILL.md) — Nielsen's ten will not catch an asymmetric cancellation: heuristic #3 is about exits from a *state*, not exits from a *commitment*. This is the missing lane, not a subset of that one.
- [`design/accessible-by-design`](../accessible-by-design/SKILL.md) — 3.3.7 (redundant entry) and 3.3.8 (accessible authentication) share this skill's flows; a cognitive-function test at sign-in is both an access failure and a friction the user did not agree to.
- A stack's `ui-rules` — confirmation-by-object-name and the compliance-flag rules these decisions are implemented with.
