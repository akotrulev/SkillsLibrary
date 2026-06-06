---
name: qa-data-driven-testing-typescript
description: >-
  Run one Node 20 / TypeScript test body against **many rows of data sourced from an external file** — CSV,
  JSON, or Excel — so coverage scales by adding rows, not by copy-pasting tests. Covers Vitest `test.for` /
  `test.each` / `describe.each` for unit-level data-driving, the **test-per-row loop** in Playwright (read
  the file at module scope, generate one `test()` per row), reading rows with a **real parser**
  (`csv-parse/sync` with `columns:true`, native `JSON.parse`, the `xlsx`/SheetJS lib for `.xlsx`), validating
  and coercing each parsed row into a **typed object with Zod** (CSV is all strings — `z.coerce` turns them
  into numbers/dates and fails loudly on a bad row), naming each row so a failure reports the input that broke
  it, and choosing the right source for the data's shape. Triggers: "run this test for every row in a CSV /
  spreadsheet", "data-drive these tests from a JSON file", "parameterize these Playwright/Vitest tests with
  external data", "load test cases from Excel", "I'm copy-pasting the same test with different inputs". Do
  NOT use for: the Java stack (use qa-data-driven-testing-java), the .NET stack (use
  qa-data-driven-testing-dotnet), constructing one complex object in code (use qa-test-data-builder-typescript
  — a builder makes one object, this feeds many rows; they compose), sourcing rows from a live database query
  (use qa-db-testing-query-author-typescript), a cross-browser/-device environment matrix (use
  qa-cloud-grid-config-typescript), or eventual-consistency waits inside a test (use the condition-wait /
  `expect.poll` in qa-db-testing-client-typescript).
---

# Data-Driven Testing (Node 20 / TypeScript — Vitest + Playwright)

> **Ported from the canonical `qa-data-driven-testing-java`.** The four ideas and the section order are
> identical; only the runner API (Vitest `test.for` / a Playwright test-per-row loop instead of TestNG
> `@DataProvider`) and the parsing libraries (`csv-parse` / `JSON.parse` / `xlsx`) change — plus one
> stack-native addition: **Zod** validates and coerces parsed rows, because in TS the file content arrives
> untyped (`unknown`/strings) and we type it at the boundary. See the Java file for the family rationale.

A **data-driven test** is **one test body** exercised against **many input rows**, where the rows live
**outside the test code** — an external CSV / JSON / Excel file checked into the repo. Add a row, get a
case; you never copy-paste a test to cover a new input.

It is *not*: a **builder** constructing one richly-configured object in code (`qa-test-data-builder-typescript`
— one object well, vs many rows; they **compose**); rows pulled from a **live database**
(`qa-db-testing-query-author-typescript`); or a **cross-browser/-device matrix** (`qa-cloud-grid-config-typescript`
— parameterizing the *environment*, not the *data*).

> **The discipline this skill encodes** — four ideas, identical across all three stacks:
>
> 1. **Separate data from logic.** The body asserts **once**; the rows live in a file. One body, N cases.
>    This is the *sanctioned* alternative to the CLAUDE.md ban on `if`/`for` driving assertions — you don't
>    loop *inside* a test, you generate **one test per row**.
> 2. **Bind each row to a typed object, not loose tuples/`any`.** Parse with a **real** library
>    (`csv-parse` / `xlsx`), then **validate + coerce with Zod** into a typed row. The data-layer analogue of
>    "page objects expose intent, not selectors": a row exposes `row.expectedTax`, not `cols[3]`.
> 3. **Each row is an independent, individually-named case.** A failing row **names the input that broke it**
>    (the `test.for`/`test()` title interpolates the row); one row's failure doesn't stop the others; rows run
>    in any order.
> 4. **One logical assertion per row; pick the source for the data's shape.** Inline for a handful; CSV for
>    flat tabular; JSON for nested/hierarchical; Excel **only** when non-technical stakeholders own the sheet.

## Decision matrix — which data source for which job

| Data shape / situation | Source | Mechanism |
|------------------------|--------|-----------|
| A handful of flat rows, owned by engineers, lives with the test | **Inline `test.for`** | array literal passed to `test.for([...])` |
| Many flat tabular rows (one record per line), engineer-owned | **CSV file** | `csv-parse/sync` `{ columns: true }` → Zod-validated `Row[]` |
| Nested / hierarchical cases (a row has sub-objects or lists) | **JSON file** | `JSON.parse` → `z.array(RowSchema).parse(...)` |
| Tabular data **owned/edited by non-technical stakeholders** | **Excel `.xlsx`** | `xlsx` (SheetJS) `sheet_to_json` → Zod-validated `Row[]` |
| Huge dataset (don't hold it all in memory) | CSV, **streaming** | `csv-parse` async iterator (`for await (const row of parse(...))`) |
| Rows from a **live DB / API** at test time | not this skill | `qa-db-testing-query-author-typescript` (DB), `fetch` (HTTP) |
| Each row is a whole complex domain object built in code | not this skill | `qa-test-data-builder-typescript` (the builder can consume one row) |

**Rule of thumb:** *prefer CSV or JSON in git* (diffable, reviewable, mergeable). Reach for **Excel only**
when the data's owner won't touch a CSV. Use **inline `test.for`** when there are few enough rows that a
separate file is more friction than it's worth. The format hides behind a **Zod-typed row** — the test body
never knows which one fed it.

## Stack

- Node 20, TypeScript (strict), Vitest (unit) + `@playwright/test` (UI) — **no `waitForTimeout`** anywhere
- `csv-parse` — CSV → records (`parse(content, { columns: true })`); RFC-4180 quoting; sync + streaming
- native `JSON.parse` — JSON → `unknown`, then validated
- `xlsx` (SheetJS) — Excel `.xlsx` reading (`read` + `utils.sheet_to_json`)
- `zod` — validate + **coerce** the parsed row into a typed object (CSV/Excel cells arrive as strings)

```
tests/
├── data/
│   ├── tax-case.ts          ← the Zod schema + inferred Row type (one source of truth)
│   ├── load-cases.ts        ← loaders (one per source) returning TaxCase[]
│   ├── tax-cases.csv        ← flat tabular, engineer-owned
│   ├── checkout-cases.json  ← nested cases
│   └── pricing-cases.xlsx   ← stakeholder-owned sheet
├── tax-calculator.test.ts   ← Vitest: one body, many rows
└── checkout.spec.ts         ← Playwright: one test per row
```

## The typed row — validate + coerce at the boundary (Zod)

In TS the file content arrives **untyped** — CSV cells are all strings, `JSON.parse` returns `any`. Type it
**once, at the boundary**, with a Zod schema: `z.coerce` turns `"10000"` into `10000`, and a malformed row
**fails loudly with the offending field** instead of silently flowing through as `NaN`.

```typescript
// tests/data/tax-case.ts
import { z } from "zod";

export const TaxCaseSchema = z.object({
  region: z.string().min(1),
  amountCents: z.coerce.number().int(),      // CSV gives "10000" (string) → coerced to 10000
  expectedTaxCents: z.coerce.number().int(),
});

export type TaxCase = z.infer<typeof TaxCaseSchema>;   // the typed row the test body sees

// Name the case so a failing row reports the INPUT that broke it, not "row 7".
export const label = (c: TaxCase) => `${c.region} @ ${c.amountCents}¢ → ${c.expectedTaxCents}¢`;
```

The test body depends on `TaxCase`, never on a column order or a tuple index — so changing the file format
(CSV → JSON) never touches a test.

## Source 1 — inline (`test.for`)

Vitest's `test.for` runs the body once per row. **Prefer `test.for` over `test.each` in new code** —
`test.each` *spreads* array args (a Jest-compat quirk) and gives no test context; `test.for` passes the row
as one value and exposes the context.

```typescript
import { test, expect } from "vitest";
import { TaxCalculator } from "../src/tax-calculator";

const cases: [string, number, number][] = [
  ["DE", 10_000, 1_900],   // 19% VAT
  ["US-OR", 5_000, 0],     // no sales tax
  ["GB", 2_000, 400],      // 20% VAT
];

test.for(cases)("computes tax for %s on %i¢", ([region, amount, expected]) => {
  expect(new TaxCalculator().taxFor(region, amount)).toBe(expected);   // one logical assertion per row
});
```

The title placeholders (`%s`, `%i`) interpolate the row, so a failure names **which input** broke.
`describe.each` does the same at the suite level when each row needs its own `beforeEach`/teardown.

## Source 2 — external CSV (`csv-parse`)

For flat tabular data, store it in a CSV and parse with **`csv-parse`** (`columns: true` → array of objects
keyed by header) — never `content.split("\n")` then `split(",")` (it breaks on quoted commas, escapes,
embedded newlines). Then **Zod-validate + coerce** into the typed row.

`tests/data/tax-cases.csv`:

```csv
region,amountCents,expectedTaxCents
DE,10000,1900
US-OR,5000,0
GB,2000,400
```

```typescript
// tests/data/load-cases.ts
import { readFileSync } from "node:fs";
import { parse } from "csv-parse/sync";
import { z } from "zod";
import { TaxCaseSchema, type TaxCase } from "./tax-case";

export function loadCsvTaxCases(path: string): TaxCase[] {
  const records = parse(readFileSync(path, "utf8"), {
    columns: true,           // first line = headers → array of { region, amountCents, ... } string objects
    skip_empty_lines: true,
    trim: true,
  });
  return z.array(TaxCaseSchema).parse(records);   // validate ALL rows + coerce strings → numbers; throws on a bad row
}
```

```typescript
// tests/tax-calculator.test.ts
import { test, expect } from "vitest";
import { loadCsvTaxCases } from "./data/load-cases";
import { label, type TaxCase } from "./data/tax-case";
import { TaxCalculator } from "../src/tax-calculator";

const cases = loadCsvTaxCases(new URL("./data/tax-cases.csv", import.meta.url).pathname);

test.for(cases)("$region tax", (tc: TaxCase) => {   // one typed arg, not three loose columns
  expect(new TaxCalculator().taxFor(tc.region, tc.amountCents)).toBe(tc.expectedTaxCents);
});
```

> Vitest interpolates object fields in the title with `$field` (`"$region tax"`). Resolve the file path
> relative to the test module (`import.meta.url`), not the process cwd, so the test runs from anywhere.

## Source 3 — external JSON (native, for nested cases)

When a case has **sub-objects or lists** (a CSV can't express nesting cleanly), use JSON. `JSON.parse` →
**validate the whole array with Zod**.

`tests/data/checkout-cases.json`:

```json
[
  { "name": "two items, one coupon",
    "items": [ { "sku": "A", "qty": 2 }, { "sku": "B", "qty": 1 } ],
    "coupon": "SAVE10", "expectedTotalCents": 4410 },
  { "name": "empty cart",
    "items": [], "coupon": null, "expectedTotalCents": 0 }
]
```

```typescript
const CheckoutCaseSchema = z.object({
  name: z.string(),
  items: z.array(z.object({ sku: z.string(), qty: z.number().int() })),   // nested → typed
  coupon: z.string().nullable(),
  expectedTotalCents: z.number().int(),
});
type CheckoutCase = z.infer<typeof CheckoutCaseSchema>;

export function loadJsonCheckoutCases(path: string): CheckoutCase[] {
  return z.array(CheckoutCaseSchema).parse(JSON.parse(readFileSync(path, "utf8")));
}
```

The `name` field is the row's report label. (For a typed import without a loader you can
`import cases from "./checkout-cases.json"` with `resolveJsonModule`, but routing through Zod still buys you
validation.)

## Source 4 — external Excel (`xlsx`/SheetJS, stakeholder-owned)

Use Excel **only** when non-technical stakeholders own and edit the sheet — it's binary, doesn't diff or
merge in git, and is heavier than CSV. Read `.xlsx` with **`xlsx` (SheetJS)**: `read` the workbook,
`sheet_to_json` the first sheet to header-keyed objects, then Zod-coerce.

```typescript
import * as XLSX from "xlsx";

export function loadExcelTaxCases(path: string): TaxCase[] {
  const wb = XLSX.read(readFileSync(path), { type: "buffer" });
  const sheet = wb.Sheets[wb.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet);     // header row → array of objects (values typed by the cell)
  return z.array(TaxCaseSchema).parse(rows);        // coerce + validate; throws naming the bad cell
}
```

> **Excel gotchas to encode:** `sheet_to_json` returns numbers as JS `number` and dates as serial numbers
> unless you pass `{ raw: false }` (then they're formatted strings) — let `z.coerce` normalize either way.
> Money precision: store **integer cents**, never floating dollars (JS `number` is a double; assert on
> cents). A mixed-type column comes back inconsistently typed — `z.coerce` + an `.int()`/`.refine` guard
> catches it loudly. Blank trailing rows are simply absent from `sheet_to_json`.

## Playwright — one `test()` per row (read at module scope)

Playwright runs in Node, so you read and parse the file **at module/collection scope** — at the top of the
spec, **not inside a test** — and generate **one `test()` per row** in a loop. This is the *sanctioned* loop:
it creates independent, individually-reported tests, not a single test that loops internally.

```typescript
// tests/checkout.spec.ts
import { test, expect } from "@playwright/test";
import { loadCsvTaxCases } from "./data/load-cases";
import { label } from "./data/tax-case";
import { CheckoutPage } from "./pages/checkout-page";   // page object — ui-test-author/playwright

const cases = loadCsvTaxCases(new URL("./data/tax-cases.csv", import.meta.url).pathname);

for (const tc of cases) {
  test(`shows ${label(tc)}`, async ({ page }) => {       // ONE test per row — each reported, each retryable
    const checkout = new CheckoutPage(page);
    await checkout.goto();
    await checkout.enterRegion(tc.region);               // page object exposes intent, not selectors
    await checkout.enterAmountCents(tc.amountCents);
    await expect(checkout.taxField).toHaveText(`${tc.expectedTaxCents}¢`);   // one logical assertion
  });
}
```

> Generating tests in a loop is fine; **looping with assertions *inside one* `test()` is not** — a failure on
> row 3 would abort rows 4-N and report one result for all of them. One `test()` per row keeps each
> independent, retryable, and reported (cross-link `qa-flaky-test-quarantine-typescript` for per-test retry).

## Streaming rows for huge datasets

`csv-parse` exposes an **async iterator** — for a large file, stream it instead of `readFileSync` + full
materialization, so memory stays flat:

```typescript
import { parse } from "csv-parse";
import { createReadStream } from "node:fs";

export async function* streamTaxCases(path: string): AsyncGenerator<TaxCase> {
  const parser = createReadStream(path).pipe(parse({ columns: true, trim: true }));
  for await (const record of parser) yield TaxCaseSchema.parse(record);   // one row at a time
}
```

(For Vitest, await-collect into an array before `test.for`, or assert inside a single streaming test only if
order independence is preserved.)

## Anti-patterns

- **`content.split("\n").map(l => l.split(","))` instead of a CSV library.** Breaks the moment a field
  contains a comma, a quote, or a newline. *Fix:* `csv-parse` with `columns: true`.
- **`any`/loose tuples indexed in the test.** `cols[3]` is a mystery and a column reorder silently breaks it.
  *Fix:* **Zod-validate into a typed row**; pass one typed object; let a bad row throw at load.
- **`test.each` spreading args in new code.** It's the Jest-compat path with no test context. *Fix:* prefer
  `test.for` (one value, with context).
- **A `for` loop with assertions *inside one* `test()`.** One failure aborts the rest, and you get **one**
  result for N cases. *Fix:* generate **one `test()` per row** (Playwright) / use `test.for` (Vitest).
- **Reading the data file inside the test body / from `process.cwd()`.** Playwright needs the rows at
  collection; cwd-relative paths break when run from elsewhere. *Fix:* read at **module scope**, path via
  `import.meta.url`.
- **Excel for engineer-owned data.** Binary, un-diffable, un-mergeable. *Fix:* CSV or JSON in git; Excel only
  for sheets a non-technical owner maintains.
- **Money as floating-point.** JS `number` is a double; `0.1 + 0.2` corrupts totals. *Fix:* **integer cents**;
  assert on those.
- **Secrets or real PII in a committed data file.** It's in git history forever. *Fix:* synthetic data; real
  secrets via env (cross-link `qa-auth0-test-tokens-typescript`).

## Examples

**End-to-end: same loader feeds a Vitest unit body and a Playwright journey, named failures.** (Shown
above.) A run produces one result **per row** — Vitest titles via `$region`, Playwright via the `label(tc)`
title — so a regression points straight at `DE @ 10000¢ → 1900¢`, not "row 1".

**Composing with a builder (the boundary made concrete):** a row supplies the *varying* fields; the
**builder** (`qa-test-data-builder-typescript`) fills the rest with sane defaults.

```typescript
test.for(loadCsvOrderCases(ordersCsv))("applies discount for $region", (row) => {
  const order = anOrder()                 // builder default — the unchanging 90%
    .withRegion(row.region)               // the row drives only what VARIES
    .withSubtotalCents(row.subtotalCents)
    .build();
  expect(discountEngine.apply(order)).toBe(row.expectedDiscountCents);
});
```

## Rules (hard constraints)

- **Data lives outside the test body** — inline `test.for` for a handful, an external CSV/JSON/Excel file
  (under `tests/data/`, versioned) beyond that. One body, N rows; **never** a `for` loop or `if` branch with
  assertions inside a single test (CLAUDE.md — generate one test per row instead).
- **Parse with a real library, validate + coerce with Zod into a typed row** — `csv-parse` `{ columns: true }`
  (CSV), `JSON.parse` (JSON), `xlsx` `sheet_to_json` (Excel), then `z.array(Schema).parse(...)`. **Never**
  `split(",")`; never index a loose tuple/`any`. The schema is the one source of truth for the row type.
- **Each row is an independent, named case** — one logical assertion per row; the title carries the **input**
  (`$field` / `label(row)`). Rows run in any order. In Playwright, read at module scope and generate **one
  `test()` per row**.
- **Pick the source for the shape** — CSV for flat tabular, JSON for nested, Excel **only** for
  stakeholder-owned sheets, inline for a few. Prefer diffable CSV/JSON in git over binary Excel.
- **Money is integer cents, never float**; a malformed row **throws at load** (Zod), it does not flow through
  as `NaN`. No secrets or real PII in committed data files (synthetic; secrets via env —
  `qa-auth0-test-tokens-typescript`).
- **Streaming async-iterator for huge datasets**. No `waitForTimeout`; `strict: true`; page objects expose
  intent, not selectors.

## Cross-references

- `qa-data-driven-testing-java` — **the canonical file**: same four ideas, TestNG `@DataProvider` (returning
  `Object[][]` / `Iterator<Object[]>`, `dataProviderClass`, `parallel = true`), OpenCSV `CsvToBean`, Jackson
  `TypeReference`, Apache POI. Read it for the family rationale.
- `qa-data-driven-testing-dotnet` — same four ideas, NUnit `[TestCaseSource]` (`IEnumerable<TestCaseData>` +
  `.SetName(...)`), CsvHelper `GetRecords<T>()` + a `ClassMap`, `System.Text.Json`, ClosedXML for Excel.
- `qa-test-data-builder-typescript` — the **boundary**: a builder constructs **one** complex object in code
  with defaults; data-driven feeds **many** rows from a file. They **compose** — a row drives a builder's
  varying fields (see the last example).
- `qa-db-testing-query-author-typescript` (#3) — when rows come from a **live database** at test time rather
  than a static file; the assertion-query counterpart to file-sourced data.
- `qa-cloud-grid-config-typescript` (#15) — parameterizing the **environment** (browser/device matrix) via
  Playwright projects rather than the **data**; orthogonal matrices that can multiply.
- `qa-ui-test-author-playwright-typescript` — the page objects the data-driven journey reuses; this skill
  supplies their rows. `qa-flaky-test-quarantine-typescript` (#36) — per-row retry/flaky handling for the
  generated tests. `qa-allure-reporting-typescript` — each row renders as a separate, named result.
