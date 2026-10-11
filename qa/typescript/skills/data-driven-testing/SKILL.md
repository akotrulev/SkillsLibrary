---
name: data-driven-testing
description: Use when one Node 24 (22 supported) / TypeScript test body must run against **many rows of data sourced from an external file**. Triggers: "run this test for every row in a CSV / spreadsheet", "data-drive these tests from a JSON file", "parameterize these Playwright/Vitest tests with external data". Do NOT use for building single test objects (`qa-typescript:test-data-builder`) or seeding a database (`qa-typescript:db-connection`).
---

# Data-Driven Testing (Node 24 / TypeScript — Vitest + Playwright)

> **Ported from the canonical `qa-java:data-driven-testing`.** The four ideas and the section order are
> identical; only the runner API (Vitest `test.for` / a Playwright test-per-row loop instead of TestNG
> `@DataProvider`) and the parsing libraries (`csv-parse` / `JSON.parse` / `xlsx`) change — plus one
> stack-native addition: **Zod** validates and coerces parsed rows, because in TS the file content arrives
> untyped (`unknown`/strings) and we type it at the boundary. See the Java file for the family rationale.

A **data-driven test** is **one test body** exercised against **many input rows**, where the rows live
**outside the test code** — an external CSV / JSON / Excel file checked into the repo. Add a row, get a
case; you never copy-paste a test to cover a new input.

It is *not*: a **builder** constructing one richly-configured object in code (`qa-typescript:test-data-builder`
— one object well, vs many rows; they **compose**); rows pulled from a **live database**
(`qa-typescript:db-verification-queries`); or a **cross-browser/-device matrix** (`qa-typescript:browser-cloud-setup`
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
| Rows from a **live DB / API** at test time | not this skill | `qa-typescript:db-verification-queries` (DB), `fetch` (HTTP) |
| Each row is a whole complex domain object built in code | not this skill | `qa-typescript:test-data-builder` (the builder can consume one row) |

**Rule of thumb:** *prefer CSV or JSON in git* (diffable, reviewable, mergeable). Reach for **Excel only**
when the data's owner won't touch a CSV. Use **inline `test.for`** when there are few enough rows that a
separate file is more friction than it's worth. The format hides behind a **Zod-typed row** — the test body
never knows which one fed it.

## Stack

- Node 24, TypeScript (strict), Vitest (unit) + `@playwright/test` (UI) — **no `waitForTimeout`** anywhere
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
import { z } from "zod";

export const TaxCaseSchema = z.object({
  region: z.string().min(1),
  amountCents: z.coerce.number().int(),
  expectedTaxCents: z.coerce.number().int(),
});

export type TaxCase = z.infer<typeof TaxCaseSchema>;

export const label = (c: TaxCase) => `${c.region}_${c.amountCents}`;
```

`tests/data/tax-case.ts`. `z.coerce` turns the CSV's `"10000"` into `10000`; `TaxCase` is the typed row the test
body sees; `label` names the case by its **input**, so a failing row reports `DE_10000`, not "row 7". The test
body depends on `TaxCase`, never on a column order or a tuple index — so changing the file format (CSV → JSON)
never touches a test.

## Source 1 — inline (`test.for`)

Vitest's `test.for` runs the body once per row. **Prefer `test.for` over `test.each` in new code** —
`test.each` *spreads* array args (a Jest-compat quirk) and gives no test context; `test.for` passes the row
as one value and exposes the context.

```typescript
import { test, expect } from "vitest";
import type { TaxCase } from "./data/tax-case";
import { TaxCalculator } from "../src/tax-calculator";

const cases: readonly TaxCase[] = [
  { region: "DE", amountCents: 10_000, expectedTaxCents: 1_900 },
  { region: "US-OR", amountCents: 5_000, expectedTaxCents: 0 },
  { region: "GB", amountCents: 2_000, expectedTaxCents: 400 },
];

test.for(cases)("Should_ChargeExpectedTax_When_RegionIs $region on $amountCents", (tc) => {
  expect(new TaxCalculator().taxFor(tc.region, tc.amountCents)).toBe(tc.expectedTaxCents);
});
```

The title placeholders (`$region`, `$amountCents`) interpolate the row, so a failure names **which input**
broke — DE at 19 %, US-OR with no sales tax, GB at 20 %.
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
import { readFileSync } from "node:fs";
import { parse } from "csv-parse/sync";
import { z } from "zod";
import { TaxCaseSchema, type TaxCase } from "./tax-case";

export function loadCsvTaxCases(path: string): TaxCase[] {
  const records = parse(readFileSync(path, "utf8"), {
    columns: true,
    skip_empty_lines: true,
    trim: true,
  });
  return z.array(TaxCaseSchema).parse(records);
}
```

`tests/data/load-cases.ts`. `columns: true` maps the header line onto string-valued objects; the Zod parse
validates **all** rows, coerces strings to numbers and throws on a bad row, naming the field.

```typescript
import { fileURLToPath } from "node:url";
import { test, expect } from "vitest";
import { loadCsvTaxCases } from "./data/load-cases";
import type { TaxCase } from "./data/tax-case";
import { TaxCalculator } from "../src/tax-calculator";

const cases = loadCsvTaxCases(fileURLToPath(new URL("./data/tax-cases.csv", import.meta.url)));

test.for(cases)("Should_ChargeExpectedTax_When_RegionIs $region", (tc: TaxCase) => {
  expect(new TaxCalculator().taxFor(tc.region, tc.amountCents)).toBe(tc.expectedTaxCents);
});
```

> `tests/tax-calculator.test.ts`: one typed argument, not three loose columns. Vitest interpolates object
> fields in the title with `$field`. Resolve the file path
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
  items: z.array(z.object({ sku: z.string(), qty: z.number().int() })),
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
  const rows = XLSX.utils.sheet_to_json(sheet);
  return z.array(TaxCaseSchema).parse(rows);
}
```

> **Excel gotchas to encode:** `sheet_to_json` returns numbers as JS `number` and dates as serial numbers
> unless you pass `{ raw: false }` (then they're formatted strings) — let `z.coerce` normalize either way.
> Money precision: store **integer cents**, never floating dollars (JS `number` is a double; assert on
> cents). A mixed-type column comes back inconsistently typed — `z.coerce` + an `.int()`/`.refine` guard
> catches it loudly. Blank trailing rows are simply absent from `sheet_to_json`.

## Playwright — one `test()` per row (read at module scope)

Playwright runs in Node, so you read and parse the file **at module/collection scope** — at the top of the
spec, **not inside a test** — and generate **one `test()` per row**. This is the *sanctioned* loop: it sits
outside every test body and creates independent, individually-reported tests, not a single test that loops
internally. The page object reaches the test as a fixture (`qa/typescript/skills/ui-test-author/playwright`).

```typescript
import { fileURLToPath } from "node:url";
import { loadCsvTaxCases } from "./data/load-cases";
import { label } from "./data/tax-case";
import { expect, test } from "./fixtures";

const cases = loadCsvTaxCases(fileURLToPath(new URL("./data/tax-cases.csv", import.meta.url)));

for (const tc of cases) {
  test(`Should_ShowExpectedTax_When_Cart_${label(tc)}`, async ({ checkoutPage }) => {
    await checkoutPage.goto();

    await checkoutPage.priceCart(tc.region, tc.amountCents);

    await expect(checkoutPage.tax).toHaveText(`${tc.expectedTaxCents}¢`);
  });
}
```

`tests/checkout.spec.ts`. `priceCart` is the page object's intent; `tax` is a `Locator`, so the assertion is
web-first.

- **Looping with assertions *inside one* `test()` is never the answer** — a failure on row 3 would abort rows
  4-N and report one result for all of them. One `test()` per row keeps each independent and reported.
- **Titles must be unique** — Playwright refuses two tests with the same title in one file, so `label` must
  differ per row; a duplicate row is a data defect the run reports at collection.
- **A row that sets a browser option** (viewport, locale, time zone) generates a `test.describe` per row with
  `test.use({ ... })` inside it — `test.use` is not allowed inside a test. `qa-typescript:responsive-testing` and
  `qa-typescript:language-testing` use exactly that shape.
- In a CommonJS Playwright project (no `"type": "module"`), resolve the file with `path.join(__dirname, ...)`
  instead of `import.meta.url`.

## Streaming rows for huge datasets

`csv-parse` exposes an **async iterator** — for a large file, stream it instead of `readFileSync` + full
materialization, so memory stays flat:

```typescript
import { parse } from "csv-parse";
import { createReadStream } from "node:fs";

export async function* streamTaxCases(path: string): AsyncGenerator<TaxCase> {
  const parser = createReadStream(path).pipe(parse({ columns: true, trim: true }));
  for await (const record of parser) yield TaxCaseSchema.parse(record);
}
```

Streaming keeps the **parse** flat; the runner still needs every row at collection to name a test after it. So
collect at module scope (Vitest supports top-level `await`; `Array.fromAsync(streamTaxCases(path))` on Node 22
and 24) and hand the array to `test.for`. Never assert rows one by one inside a single streaming test — that is
the loop-in-a-test this skill exists to replace. A dataset too large to name every row is a load or batch job
(`qa-typescript:load-testing`), not a data-driven suite.

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
  secrets via env (cross-link `qa-typescript:test-login-tokens`).

## Examples

One loader feeds the Vitest body and the Playwright journey above; each run reports one result **per row**,
titled by its input (`DE_10000`), never "row 1".

**Composing with a builder (the boundary made concrete):** a row supplies the *varying* fields; the
**builder** (`qa-typescript:test-data-builder`) fills the rest with sane defaults.

```typescript
test.for(loadCsvOrderCases(ordersCsv))("Should_ApplyExpectedDiscount_When_RegionIs $region", (row) => {
  const order = anOrder().withRegion(row.region).withSubtotalCents(row.subtotalCents).build();

  expect(discountEngine.apply(order)).toBe(row.expectedDiscountCents);
});
```

The builder supplies the unchanging defaults; the row drives only what **varies**.

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
  `qa-typescript:test-login-tokens`).
- Titles are `Should_X_When_Y` plus the row's input, unique per file. No `waitForTimeout`; no inline comments;
  page objects reach Playwright tests as fixtures; `strict: true`.

## Cross-references

- `qa-java:data-driven-testing` (**the canonical file**: TestNG `@DataProvider`, OpenCSV, Jackson, POI) ·
  `qa-dotnet:data-driven-testing` (NUnit `[TestCaseSource]`, CsvHelper, `System.Text.Json`, ClosedXML) — the
  sibling stacks; same four ideas.
- `qa-typescript:test-data-builder` — the **boundary**: a builder constructs **one** complex object in code
  with defaults; data-driven feeds **many** rows from a file. They **compose** — a row drives a builder's
  varying fields (see the last example).
- `qa-typescript:db-verification-queries` — when rows come from a **live database** at test time rather
  than a static file; the assertion-query counterpart to file-sourced data.
- `qa-typescript:browser-cloud-setup` — parameterizing the **environment** (browser/device matrix) via
  Playwright projects rather than the **data**; orthogonal matrices that can multiply.
- `qa-typescript:ui-tests-playwright` — the fixtures and page objects the data-driven journey reuses.
  `qa-typescript:test-reports` — each row renders as a separate, named result.
