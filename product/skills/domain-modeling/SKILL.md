---
name: domain-modeling
description: Use when a design session settles a term or a hard-to-reverse decision, to write the glossary and ADRs inline. Triggers "what do we call this". Not for running the whole feature interview (feature).
disable-model-invocation: true
---

# Domain modeling: the glossary and ADRs, written as they settle

Loaded by `/product:plan-feature` during its interview, by `solution-planner` while it writes the system plan's §3, and by any plan task recording a decision. It changes the project's language and its record of decisions while the design is being argued, so that the next session names things the same way and does not reopen a settled choice. Reading the glossary before naming code is a separate, lighter habit every agent already has (`engineering/agent-orientation-cache`).

| Artifact | Path | Format |
|---|---|---|
| Glossary | `docs/business-model/glossary.md` | `references/glossary-format.md` |
| ADRs | `docs/adr/NNNN-<slug>.md` | `references/adr-format.md` |

Both are created lazily: the glossary with its first settled term, `docs/adr/` with its first ADR. Read `references/glossary-format.md` before the first glossary write, and `references/adr-format.md` before offering the first ADR.

## Procedure

Run these on every answer of the session, not at the end.

1. **Challenge against the glossary.** When a word the user says has a row, and they use it with a different meaning, say so at once and ask which meaning holds. When the word is in a row's `Avoid` cell, name the canonical term and use it from then on. Done when every term used this round matches its row or is a question.
2. **Sharpen fuzzy words.** A vague or overloaded word ("account", "item", "process") gets one proposed canonical term, with the rejected words listed for `Avoid`: "account" splits into *Member* (the person who logs in) and *Billing account* (who pays). Done when every term in the design names one concept.
3. **Probe with a scenario.** Where two concepts meet, invent the edge case that forces the boundary: "a member books for a friend who is not a member: whose booking is it?". Done when every relationship discussed has one scenario answered.
4. **Check the code.** When the user says how something behaves today, read the code that does it. A disagreement ("the code cancels the whole order; you said one line") is a question, never a silent pick. Done when every claim about current behaviour is confirmed in the code or asked.
5. **Write each settled term now.** Add or update its glossary row the moment the user settles it; never batch rows for the end. Done when the glossary holds every term settled so far.
6. **Offer an ADR only when the three tests hold.** Hard to reverse, surprising without context, the result of a real trade-off: all three, or no offer. On a yes, write it at once (`references/adr-format.md`). Done when every decision that passed the three tests has been offered, and each accepted one is written.

## Rules

- **A synonym is ruled out; drift is a finding.** Two words for one concept: one row, the other words under `Avoid`. One word for two concepts: both meanings stay in the row, marked **Drift**, and the decision is the `business-analyst` agent's. Never merge the two cases.
- **The glossary is language only.** A row says what a term *is*. How it is built, a plan step or a decision's reasoning goes in the spec, the plan or an ADR.
- **Only this project's terms.** A general programming concept (timeout, retry, DTO, cache) gets no row, however often it is used.
- **Technical decisions only in `docs/adr/`.** A business rule table is a `DEC-` file in the business-model KB, the `business-analyst` agent's.
