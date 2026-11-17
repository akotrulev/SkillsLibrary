# Density, hierarchy, and feedback

The depth behind [`ux-patterns`](../SKILL.md) §5 and §7.

## §5 — density and hierarchy

- **Pick one density for the app and state it** — *comfortable* for consumer and occasional use, *compact* for tools people use all day with tables on most pages. A user-facing density toggle is earned only when both audiences are real.
- **Hierarchy comes from three text tones and weight, not from many sizes.** Primary text, secondary/muted, and disabled/placeholder; headings step the type scale, body does not. (The scale and tones are tokens — [`design/design-tokens`](../../design-tokens/SKILL.md).)
- **Whitespace groups; lines separate.** Related controls sit closer to each other than to anything else; a divider is for unrelated regions.
- **Tables are the densest element on the page and set its rhythm** — row height, cell padding and column alignment are decided once app-wide (`ui-rules` owns alignment/truncation correctness).

## §7 — feedback and notifications

The user must never wonder whether something happened.

| Signal | Use for | Never for |
|---|---|---|
| **Inline state** (the row updates, the badge changes, "Saved" beside the button) | Anything visible on the current screen | — it is always the first choice |
| **Toast** (transient, auto-dismissing) | Success of an action whose result is *not* visible on screen ("Invoice sent"), with an Undo where reversible | Errors (they persist — `error-handling`), or repeating what the screen already shows |
| **Persistent notification** (top-right, closes only by hand) | Failures (`error-handling` owns it) | Successes |
| **Notification centre / inbox** (a shell utility with a badge) | Asynchronous events the user must come back to: a report finished, an approval requested of them, a job failed overnight | Apps with no asynchronous events — an empty bell is a broken promise |

One toast at a time; a bulk operation reports once, per item (`ui-rules`).
