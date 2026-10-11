# Golden example — promo codes

The filled input and output for `qa/manual/requirements-breakdown`, moved out of its SKILL.md unchanged. It predates the §4/§6 rebalancing: a new basis puts V-1's schema constraint in the §6 data dictionary and keeps §4 for business validations, and it ends with a §8 Connections section.

## Example

### Input

> **Story**: As a shopper, I want a promo code at checkout so I get a discount.
> **AC1**: A valid, active promo code reduces the order total by its percentage.
> **AC2**: An expired or unknown code shows "This code isn't valid" and the total is unchanged.
> **AC3**: Only one promo code per order.
> Promo codes are 6–10 uppercase alphanumeric characters. (from the API schema)

### Output

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

## 4. Validations & restrictions
| # | Field / action | Rule | On violation | Source |
|---|---|---|---|---|
| V-1 | code | 6–10 chars, uppercase alphanumeric | (format rejection behavior not specified) | API schema |
| V-2 | code | must exist and be active | "This code isn't valid", total unchanged | AC2 |
| V-3 | apply code | only one per order | (behavior on 2nd code not specified) | AC3 |

## 5. Workflow & states
No stateful behavior — applying a code is a single-shot action on the cart.

## 6. Data dictionary
| Field | Type | Required | Range / format | Notes |
|---|---|---|---|---|
| code | string | yes | 6–10 chars, A–Z 0–9 | case sensitivity vs. lowercase input unspecified |

## 7. High-level implementation notes
- Discount is a **percentage** of order total (AC1) — rounding rule not specified.
- Validation presumably server-side (it checks code existence/active state) — confirm client also blocks malformed input.

## Open questions & flags
- ❓ V-1: what happens to a code outside 6–10 chars or with lowercase/symbols — inline format error, or treated as "not valid" (V-2)?
- ❓ BR-3/V-3: applying a *second* code — does it replace the first, or is it rejected with a message?
- ❓ Rounding: 15% off $9.99 — round how?
- 🏷️ `#assumption`: codes are case-sensitive (schema says uppercase) until confirmed.
```

Notice the output is shorter than a full case suite, every row cites a source, and the four things the story never actually answered are flagged instead of guessed.
