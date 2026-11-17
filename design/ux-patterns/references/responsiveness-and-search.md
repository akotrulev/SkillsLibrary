# The responsiveness budget, and search results

The depth behind [`ux-patterns`](../SKILL.md) §9 and §10. The §9 windows table stays in the skill.

## §9 — beyond the windows

- **Optimistic updates for reversible, low-conflict actions** (star, toggle, reorder, mark read) — the screen changes at once and reconciles on the response; a failure reverts *and* says so. Never optimistic for money, sends, or deletes.
- **No layout shift on load:** skeletons and images reserve their space; content arriving does not push what the user is reading.
- **Navigation feels instant:** the shell renders immediately and only the page region loads; likely next routes are prefetched (the stack's `routing` / `performance`).
- **One region's wait never blocks the page.** Independent regions load independently.

**The same budget, in the field's measuring vocabulary.** The windows above are the *design* requirement; **Core Web Vitals** are how it is measured in production, at the **75th percentile** of real sessions — not the median, and not your machine. **LCP < 2.5 s** (the main content is on screen) · **INP < 200 ms** (every interaction acknowledges — INP replaced FID in March 2024, measures *all* interactions and reports the worst, and is now the most-failed of the three) · **CLS < 0.1** (nothing moves under the reader — the metric form of the no-layout-shift rule above). Write the budget as design acceptance criteria; the stack's `performance` skill owns hitting the numbers and `frontend/_shared/product-analytics` owns measuring them in the field. A design that meets the windows and a build that fails INP are the same defect reported twice.

## §10 — search results and filtering

§6 covers how search gets the user *to* a destination. This is the surface they land on when the answer is a **result set** — the second half of every list, catalogue, and knowledge base.

- **Autocomplete is instant or it is noise.** Suggestions appear as the user types, and any perceptible lag breaks the flow; a suggestion list that arrives after the user has finished typing has cost them time rather than saved it. Suggest destinations and records, never just query strings.
- **Match the user's vocabulary, not the database's.** Synonyms (couch/sofa), the domain's slang, brand terms and misspellings resolve to the same results. A high refinement rate — most users searching twice — is a **matching defect**, not user behaviour.
- **Facets are derived from the result set, not from the schema.** Show only facets that would change *this* result set; hide the ones that return nothing or everything. Order them by what people actually use.
- **Active filters are always visible and individually removable** — chips with a count and a clear-all, above the results. A filter the user cannot see is a filter they will blame the results for.
- **Quick filters apply instantly; advanced filters get an Apply.** The split is by cost: a single-value toggle re-queries on click, a multi-condition builder waits for a deliberate submit. An Apply button on a quick filter is a reliably confusing pattern — users don't know whether their click took.
- **Zero results is a state with work to do, never a dead end.** Say plainly that nothing matched *this* query, then offer the way forward: spelling correction, the broadened query, the filter to clear, or popular/related records. The words are [`ux-writing`](../../ux-writing/SKILL.md)'s; that the state offers an *action* is decided here.
- **The query and the filters live in the URL.** A result set is the most-shared thing in an app — if it cannot be linked, pasted, or reloaded, the user re-derives it every time (`ui-rules` owns the URL-reflection mechanics).
- **Preserve the search on return.** Coming back from a result to the list restores the query, filters, sort, and scroll position; losing them is the most common reason a person abandons a search-driven task.
