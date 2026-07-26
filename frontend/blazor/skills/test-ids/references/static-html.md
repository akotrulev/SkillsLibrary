# Static HTML / JS-template UIs — testid mechanics

For non-Blazor surfaces in a hybrid app (a static HTML admin tool, a simulator page, a jQuery-era UI), the SKILL.md naming (Rule 2), const (Rule 3), coverage (Rule 5), row (Rule 6), and data-derivation (Rule 7) rules apply unchanged. Only the mechanics differ.

## Static markup

`<button>`, `<input>`, `<select>`, `<table>`, sectioning `<div>`s: set `data-testid="..."` inline as a plain HTML attribute. No forwarding needed — the browser puts the attribute on the element directly.

## JS-rendered rows

Template strings appended via `$tbody.append`, `insertAdjacentHTML`, `el.innerHTML`, or framework loops: hardcode the parent locator as a `const` near the render function and interpolate it into every child element. Never put a per-row id into the locator value.

```js
// ✅ Hardcoded parent locator, namespaced children
const ROW = 'Simulator.OrderBook.Row';
$tbody.append(`
    <tr data-testid="${ROW}">
        <td data-testid="${ROW}.OrderId">${escapeHtml(order.orderId)}</td>
        <td data-testid="${ROW}.Symbol">${escapeHtml(order.symbol)}</td>
    </tr>
`);

// ❌ Per-row id leaks into the locator
// <tr data-testid="Simulator.OrderBook.Row.${order.orderId}">
```

## Other surfaces

- **Modals / dialogs** (e.g. Bootstrap `data-bs-target`): tag the modal's outer `<div>` and every form control / submit button inside.
- **Sub-templates that render the same data twice** (e.g. cards view vs table view): give each its own sub-namespace (`Quotes.Card`, `Quotes.Row`) per the Rule 6 sub-namespace pattern.
- **Pagination buttons**: `${ParentLocator}.Page.{n}` is acceptable — the page number is the role, not an opaque id.
- **Empty-state rows**: tag the placeholder `<tr>` with `${Section}.EmptyState` so tests can assert "no data" cleanly.

Apply Rule 5 unchanged: tag interactive elements, list/grid containers, and read-only cells the tests will read; skip decorative wrappers.
