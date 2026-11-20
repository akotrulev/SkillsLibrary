# Glossary format

The single source for `docs/business-model/glossary.md`. Every writer follows it: `product:feature`'s interview (through `domain-modeling`), the business-model KB (`knowledge-base`), and the `documenter` agent's KB runs (`business-documentation`). There is one glossary per project.

## The table

```markdown
# Glossary

| Term (client) | Means | Avoid | Called in code | Where the client sees it | Notes |
|---|---|---|---|---|---|
| Order | A confirmed purchase, from placement to delivery | Purchase, transaction | `Order` | order confirmation email | US2 `#confirmed` |
| Customer | **Drift:** the person (E1 accounts, US4) · the billing entity (E3 invoicing, US21) | — | — | — | CONF-004, open |
```

| Column | Holds |
|---|---|
| Term (client) | The canonical term, in the client's words. One row per term |
| Means | What the term *is*, in one or two sentences. Never how it is built |
| Avoid | The rejected synonyms, comma-separated; `—` when there are none |
| Called in code | The identifier the code uses for it; `—` until code exists or when the row comes from requirements |
| Where the client sees it | The screen, document or message where a client meets the term; `—` when nowhere |
| Notes | The source (story, BRD section, `file:line`, interview date) and the confidence tag (`#confirmed`, `#observed`, `#inferred`) |

## Rules

- **Synonyms are ruled out.** Two words for one concept: pick the one the client uses, and list the others under `Avoid`. From then on, every document and every new identifier uses the canonical term.
- **Drift is a finding, never a merge.** One word for two concepts: keep both meanings in the one row, marked **Drift**, each with its source, and put the `CONF-` id of the terminology-drift finding in *Notes*. The `business-analyst` agent resolves it. A drift row's `Avoid` is `—`.
- **Only this project's terms.** Ask of each candidate: is it particular to this domain, or a general concept? Timeouts, error types, DTOs and utility patterns get no row.
- **Language, not design.** A row holds no implementation detail, no plan step and no decision's reasoning.
- **Group by area when clusters appear.** A `## <Area>` heading over its own table is fine once the glossary covers several areas; one area stays one table.

## Creating and adopting it

- **Created lazily.** With no `docs/business-model/` at all, the first settled term creates `docs/business-model/glossary.md` alone: the `# Glossary` heading, the header row and that term. No other KB file is created with it.
- **Adopted, never replaced.** A KB initialized later (`knowledge-base`, "Initializing a KB") keeps the existing `glossary.md` and adds it to `INDEX.md`.
- **An older glossary without `Avoid`** gains the column, as `—` on every existing row, the first time a writer adds a row to it.
