# Golden example — promo codes

The filled input and output for `qa/manual/requirements-breakdown`. A filled §8 Connections is in `qa/manual/cross-feature-test-design/references/example-cancel-booking.md`; this basis is single-feature, so its §8 says so.

## Input

> **Story**: As a shopper, I want a promo code at checkout so I get a discount.
> **AC1**: A valid, active promo code reduces the order total by its percentage.
> **AC2**: An expired or unknown code shows "This code isn't valid" and the total is unchanged.
> **AC3**: Only one promo code per order.
> Promo codes are 6–10 uppercase alphanumeric characters. (from the API schema)

## Output

```markdown
# Test Basis — Checkout Promo Codes

**Sources**: STORY-2210 (AC1–AC3); checkout API schema `POST /cart/promo` field `code`
**Scope**: Applying a promo code at checkout. Out: creating/managing codes (admin), stacking with loyalty points.
**Analyzed**: 2026-06-09
**Status**: draft — pending author confirmation of the flagged items below

## 1. Summary
Shoppers enter a promo code at checkout to reduce the order total by a percentage. Codes can be valid, expired, or unknown; at most one applies per order.

## 2. Actors & roles
| Actor | Can do here |
|---|---|
| Shopper | Apply one promo code to their own cart |

## 3. Business logic & rules
| # | Rule | Source |
|---|---|---|
| BR-1 | A valid, active code reduces the total by its percentage | AC1 |
| BR-2 | An expired or unknown code leaves the total unchanged | AC2 |
| BR-3 | At most one promo code per order | AC3 |

### Calculations
| # | Figure | Formula | Rounding / order | Worked example | Where it shows | Source |
|---|---|---|---|---|---|---|
| C-1 | Discount | order total × code percentage ÷ 100 | ❓ rounding not stated; ❓ whether "order total" is before or after tax and delivery | 15 % of $80.00 = $12.00 | basket | AC1 |
| C-2 | Total to pay | order total − discount | — | $80.00 − $12.00 = $68.00 | basket; the confirmation and the invoice `#assumption` | AC1 |

## 4. Validations & restrictions
| # | Field / action | Rule | On violation | Source |
|---|---|---|---|---|
| V-1 | code | must exist and be active | "This code isn't valid", total unchanged | AC2 |
| V-2 | apply code | only one per order | ❓ behavior on a second code not specified | AC3 |

## 5. Journeys, workflow & states
### Journeys
| # | Actor · goal | Path | Business outcome, and where it shows | Source |
|---|---|---|---|---|
| J-1 | Shopper · pay less with a code | basket → apply code → checkout → pay → confirmation | the order is placed at the discounted total, and the confirmation shows the same total `#assumption` | STORY-2210 |
| J-2 | Shopper · recover from a code that does not work | basket → apply an expired code → message → apply a valid code → checkout | the first attempt changes nothing; the order is placed with the second code's discount | AC2, AC1 |

### States
No stateful behavior of its own — applying a code is a single-shot action on the cart. ❓ Whether a code stays applied when the cart changes afterwards is not stated.

## 6. Data dictionary
| Field | Type | Required | Range / format | On violation | Notes |
|---|---|---|---|---|---|
| code | string | yes | 6–10 chars, A–Z 0–9 | ❓ not specified | case sensitivity for lowercase input unspecified |

## 7. High-level implementation notes
- The existence and active check must be server-side (AC2); confirm whether the client also blocks malformed input.

## 8. Connections
Not built — single-feature basis.

## Open questions & flags
- ❓ C-1: how is the discount rounded — 15 % of $9.99 is $1.4985?
- ❓ C-1: is the percentage taken from the total before or after tax and delivery?
- ❓ V-2: a second code — does it replace the first, or is it refused with a message?
- ❓ §6: a code outside 6–10 chars, or with lowercase or symbols — a format error, or "This code isn't valid" (V-1)?
- ❓ §5: does an applied code survive a change to the cart (an item removed, the total dropping)?
- 🏷️ `#assumption`: codes are case-sensitive (the schema says uppercase) until confirmed.
- 🏷️ `#assumption`: the discounted total is what the confirmation and the invoice show (J-1, C-2).
```

Notice three things. The output is shorter than a case suite and every row cites a source. The story's one sentence about "a discount" became two calculations and two journeys, and that is where four of the five open questions came from: none of them is about the format of the field. And nothing the story left undecided was filled in from intuition.
