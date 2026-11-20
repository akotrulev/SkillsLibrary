# Bulk operations (ui-rules §5)

*Deep dive for [`fe-react:ui-rules`](../SKILL.md). Read it when the task contains a multi-select or a bulk action.*

- **Multi-select needs visible affordances:** a leading **checkbox column** (row-click-only selection is undiscoverable), a **tri-state select-all** header, selection styling stronger than hover (background tint + accent bar), and a persistent **selected-count**.
- **Select-all scopes to the visible, filtered page** when filtering/paging is server-side — never silently select rows the user isn't looking at. Tooltip it: "Select all visible rows (respects current filters)."
- **Where users grind row-by-row** (approve/cancel/resolve backlogs), provide **batch endpoints + bulk UI** — thirty click-confirm cycles for one logical operation is a workflow defect.
- **Stable `data-testid` on selection controls** so UI automation can drive bulk flows ([`test-ids`](../../test-ids/SKILL.md)).
- **A bulk write reports per item.** "12 of 15 archived — 3 failed" with the three named, still selected, and retryable. A blanket success toast over a partial failure is the worse half of the defect (the user believes all 15 went through); a blanket failure hiding the 12 that worked is the other half ([`error-handling`](../../error-handling/SKILL.md) owns the failure rendering).
