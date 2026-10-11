---
name: data-driven-testing
description: Use when one Java 21 / TestNG test body must run against **many rows of data sourced from an external file**. Triggers: "run this test for every row in a CSV / spreadsheet", "data-drive these tests from a JSON file", "parameterize this test with external test data". Do NOT use for building the objects themselves (`qa-java:test-data-builder`).
---

# Data-Driven Testing (Java 21 / TestNG) — **canonical stack**

This is the **canonical** stack of the `qa/java/skills/data-driven-testing/` family, and it leads by judgment (the
"lead where the tool is most authentic" call WireMock / Kafka / flaky-quarantine made):
TestNG's `@DataProvider` is the **archetypal** data-driven mechanism — a first-class language feature
returning rows to a test method, with native support for separate provider classes, lazy iterators, and
parallel rows. The `dotnet` (NUnit `[TestCaseSource]`) and `typescript` (Vitest `test.for` / a
test-per-row loop in Playwright) siblings are **ported** from this file — the *moves* are identical; only
the runner API and the parsing library change.

## What "data-driven" means (and what it does not)

A **data-driven test** is **one test body** exercised against **many input rows**, where the rows live
**outside the test code** — an external CSV / JSON / Excel file checked into the repo. Add a row, get a
case; you never copy-paste a test method to cover a new input.

It is *not*:

- a **builder** constructing one richly-configured object in code (that's `qa-java:test-data-builder`; a
  builder makes **one** object well — data-driven feeds **many** rows; they **compose**: a row can drive a
  builder);
- rows pulled from a **live database** at test time (that's `qa-java:db-verification-queries` — a different
  *source*; this skill is about **static files** that are part of the test's arranged world);
- a **cross-browser / cross-device matrix** (that's `qa-java:browser-cloud-setup` — parameterizing the
  *environment*, not the *data*).

> **The discipline this skill encodes** — four ideas, identical across all three stacks:
>
> 1. **Separate data from logic.** The test asserts behaviour **once**; the rows live in a file. One body,
>    N cases. This is the *sanctioned* alternative to the CLAUDE.md ban on `if` / `for` driving assertions —
>    you don't loop inside a test, you **parameterize** it.
> 2. **Bind each row to a typed object, not a raw `Object[]` of strings.** Parse into a `record`/bean with a
>    **real** library (OpenCSV / Jackson / POI), never `line.split(",")`. This is the data-layer analogue of
>    "page objects expose intent, not selectors": a row exposes `case.expectedTax()`, not `row[3]`.
> 3. **Each row is an independent, individually-named case.** A failing row **names the input that broke it**;
>    one row's failure doesn't stop the others; rows run in any order. (TestNG reports each invocation
>    separately; name it via the data object's `toString()` or `ITestResult` parameters.)
> 4. **One logical assertion per row; pick the source for the data's shape.** Inline for a handful; CSV for
>    flat tabular; JSON for nested/hierarchical; Excel **only** when non-technical stakeholders own the sheet.

## Decision matrix — which data source for which job

| Data shape / situation | Source | Mechanism |
|------------------------|--------|-----------|
| A handful of flat rows, owned by engineers, lives with the test | **Inline `@DataProvider`** | `Object[][]` literal returned from the provider |
| Many flat tabular rows (one record per line), engineer-owned | **CSV file** | OpenCSV `CsvToBean` + `@CsvBindByName` → `List<Row>` |
| Nested / hierarchical cases (a row has sub-objects or lists) | **JSON file** | Jackson `readValue(…, new TypeReference<List<Row>>(){})` |
| Tabular data **owned/edited by non-technical stakeholders** | **Excel `.xlsx`** | Apache POI `WorkbookFactory` → bind cells → `List<Row>` |
| Huge dataset (don't hold it all in memory) | any of the above, **lazy** | `@DataProvider` returns `Iterator<Object[]>`, reads row-by-row |
| Rows from a **live DB / API** at test time | not this skill | `qa-java:db-verification-queries` (DB), an API client (HTTP) |
| Each row is a whole complex domain object built in code | not this skill | `qa-java:test-data-builder` (the builder can consume one row) |

**Rule of thumb:** *prefer CSV or JSON in git* (diffable, reviewable, mergeable). Reach for **Excel only**
when the data's owner won't touch a CSV. Use **inline** when there are few enough rows that a separate file
is more friction than it's worth. The format is an implementation detail behind a **typed row record** — the
test body never knows which one fed it.

## Stack

- Java 21, TestNG 7.x — `@DataProvider` / `@Test(dataProvider = …)`; **no `Thread.sleep`** anywhere
- `com.opencsv:opencsv` — CSV → bean binding (`CsvToBean`, `@CsvBindByName`); robust quoting/escaping
- `com.fasterxml.jackson.core:jackson-databind` — JSON → typed list (`ObjectMapper`, `TypeReference`)
- `org.apache.poi:poi-ooxml` — Excel `.xlsx` reading (`WorkbookFactory`, `XSSFWorkbook`)
- `org.assertj:assertj-core` — fluent assertions (one logical assertion per row)
- Test data files under `src/test/resources/data/` — versioned with the tests they feed

```
src/test/
├── java/com/acme/tests/
│   ├── data/
│   │   ├── TaxCase.java            ← the typed row record (CSV/JSON/Excel all bind to it)
│   │   └── TaxCaseProviders.java   ← @DataProvider methods (one per source, reusable class)
│   └── TaxCalculatorTest.java      ← one test body, many rows
└── resources/data/
    ├── tax-cases.csv               ← flat tabular, engineer-owned
    ├── checkout-cases.json         ← nested cases
    └── pricing-cases.xlsx          ← stakeholder-owned sheet
```

## The typed row — bind data to meaning, not to indexes

Every source binds to the **same record**. The test body depends on `TaxCase`, never on a column order or
an array index — so changing the file format (CSV → JSON) never touches a test.

```java
package com.acme.tests.data;

import com.opencsv.bean.CsvBindByName;

/** One data-driven case. CSV binds by header name; Jackson binds by JSON key; POI sets fields per column. */
public class TaxCase {
    @CsvBindByName(column = "region")        private String region;
    @CsvBindByName(column = "amount_cents")  private long amountCents;
    @CsvBindByName(column = "expected_tax")  private long expectedTaxCents;

    public String region()         { return region; }
    public long amountCents()      { return amountCents; }
    public long expectedTaxCents() { return expectedTaxCents; }

    @Override public String toString() {
        return "%s @ %d¢ → %d¢".formatted(region, amountCents, expectedTaxCents);
    }
}
```

> OpenCSV needs a no-arg constructor and setters; the test sees only the intent-named getters, and `toString()`
> names the case so a failing row reports the **input** that broke it, not "row 7".
>
> Why a `record` isn't used here: OpenCSV's `@CsvBindByName` binding needs a mutable no-arg bean. For
> **JSON** (Jackson) and **inline** rows you *can* use a `record TaxCase(String region, long amountCents,
> long expectedTaxCents)` — Jackson binds records natively. Keep the type's **getters intent-named** either
> way; that's the contract the test sees.

## Source 1 — inline `@DataProvider` (the few-rows case)

A `@DataProvider` is a method that returns the rows. `@Test(dataProvider = "…")` runs the body once per row.

```java
public class TaxCalculatorTest {

    @DataProvider(name = "taxCases")
    public Object[][] taxCases() {
        return new Object[][] {
            { "DE", 10_000L, 1_900L },
            { "US-OR", 5_000L, 0L },
            { "GB", 2_000L, 400L },
        };
    }

    @Test(dataProvider = "taxCases")
    public void Should_ComputeRegionalTax_When_AmountIsGiven(String region, long amountCents, long expectedTaxCents) {
        long tax = new TaxCalculator().taxFor(region, amountCents);

        assertThat(tax).as("region=%s amount=%d", region, amountCents).isEqualTo(expectedTaxCents);
    }
}
```

The rows are 19% VAT (DE), no sales tax (US-OR) and 20% VAT (GB); one logical assertion per row.

Each row is reported as a **separate** invocation in TestNG/Allure; the `.as(...)` description (or the
typed `toString()` below) makes a failure say **which input** broke, not just "test failed".

## Source 2 — external CSV (OpenCSV bean binding)

For flat tabular data, store it in a CSV and bind each line to the typed record with **OpenCSV** — never
`split(",")` (that breaks on quoted commas, escapes, and embedded newlines). Put the provider in a
**reusable class** so many tests share it.

`src/test/resources/data/tax-cases.csv`:

```csv
region,amount_cents,expected_tax
DE,10000,1900
US-OR,5000,0
GB,2000,400
```

```java
package com.acme.tests.data;

import com.opencsv.bean.CsvToBeanBuilder;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import org.testng.annotations.DataProvider;

public final class TaxCaseProviders {

    @DataProvider(name = "csvTaxCases")
    public static Object[][] csvTaxCases() {
        var stream = TaxCaseProviders.class.getResourceAsStream("/data/tax-cases.csv");
        var reader = new InputStreamReader(stream, StandardCharsets.UTF_8);
        var cases = new CsvToBeanBuilder<TaxCase>(reader)
                .withType(TaxCase.class)
                .withIgnoreLeadingWhiteSpace(true)
                .build()
                .parse();
        return cases.stream().map(c -> new Object[]{ c }).toArray(Object[][]::new);
    }
}
```

```java
@Test(dataProvider = "csvTaxCases", dataProviderClass = TaxCaseProviders.class)
public void Should_ComputeTax_When_CaseComesFromCsv(TaxCase tc) {
    long tax = new TaxCalculator().taxFor(tc.region(), tc.amountCents());

    assertThat(tax).as("case=%s", tc).isEqualTo(tc.expectedTaxCents());
}
```

`withType` binds header names to the `@CsvBindByName` fields and `parse()` returns a fully typed
`List<TaxCase>`. The test takes one typed argument, not three loose columns, and `tc.toString()` names the row.
`dataProviderClass` lets a single provider class feed tests across many test classes — the data lives once.

## Source 3 — external JSON (Jackson, for nested cases)

When a case has **sub-objects or lists** (a CSV can't express nesting cleanly), use JSON + Jackson. Bind the
whole file to a `List<Row>` with a `TypeReference`.

`src/test/resources/data/checkout-cases.json`:

```json
[
  { "name": "two items, one coupon",
    "items": [ { "sku": "A", "qty": 2 }, { "sku": "B", "qty": 1 } ],
    "coupon": "SAVE10", "expectedTotalCents": 4410 },
  { "name": "empty cart",
    "items": [], "coupon": null, "expectedTotalCents": 0 }
]
```

```java
@DataProvider(name = "jsonCheckoutCases")
public static Object[][] jsonCheckoutCases() throws Exception {
    var mapper = new ObjectMapper();
    try (var in = TaxCaseProviders.class.getResourceAsStream("/data/checkout-cases.json")) {
        List<CheckoutCase> cases = mapper.readValue(in, new TypeReference<>() {});
        return cases.stream().map(c -> new Object[]{ c }).toArray(Object[][]::new);
    }
}
```

`CheckoutCase` is a `record` with `String name`, `List<Item> items`, `String coupon`, `long
expectedTotalCents` — Jackson binds records natively. The `name` field is the row's report label.

## Source 4 — external Excel (Apache POI, stakeholder-owned)

Use Excel **only** when non-technical stakeholders own and edit the sheet — it's binary, doesn't diff or
merge in git, and is heavier than CSV. Read `.xlsx` with **Apache POI**, skip the header row, bind cells to
the record. Read cells **by their typed accessor**, and prefer the **cell name/index map** over magic
indexes where you can.

```java
@DataProvider(name = "excelPricingCases")
public static Object[][] excelPricingCases() throws Exception {
    var cases = new ArrayList<TaxCase>();
    try (var in = TaxCaseProviders.class.getResourceAsStream("/data/pricing-cases.xlsx");
         var workbook = WorkbookFactory.create(in)) {
        var sheet = workbook.getSheetAt(0);
        for (int r = 1; r <= sheet.getLastRowNum(); r++) {
            var row = sheet.getRow(r);
            if (row == null) continue;
            var tc = new TaxCase();
            tc.setRegion(row.getCell(0).getStringCellValue());
            tc.setAmountCents((long) row.getCell(1).getNumericCellValue());
            tc.setExpectedTaxCents((long) row.getCell(2).getNumericCellValue());
            cases.add(tc);
        }
    }
    return cases.stream().map(c -> new Object[]{ c }).toArray(Object[][]::new);
}
```

`WorkbookFactory` picks XSSF for `.xlsx`; the loop starts at row 1 to skip the header and tolerates trailing
blank rows.

> **Excel gotchas to encode:** numeric cells come back as `double` (cast deliberately, watch precision on
> money — store cents as integers, never floating dollars); a "number" a user typed may be a *text* cell
> (`getStringCellValue` vs `getNumericCellValue` — use a `DataFormatter` or check `getCellType()` if the
> column is mixed); empty trailing rows return `null`. POI 5.x: use `WorkbookFactory.create` (don't
> hard-code `XSSFWorkbook`) so `.xls`/`.xlsx` both work.

## Lazy rows for huge datasets — return an `Iterator`

A `@DataProvider` returning `Object[][]` **materializes every row up front**. For a large file, return an
`Iterator<Object[]>` instead — TestNG pulls one row at a time, so memory stays flat.

```java
@DataProvider(name = "bigCsv")
public static Iterator<Object[]> bigCsv() {
    var reader = new InputStreamReader(
        TaxCaseProviders.class.getResourceAsStream("/data/many-rows.csv"), StandardCharsets.UTF_8);
    var beanIterator = new CsvToBeanBuilder<TaxCase>(reader).withType(TaxCase.class).build().iterator();
    return new Iterator<>() {
        public boolean hasNext() { return beanIterator.hasNext(); }
        public Object[] next()   { return new Object[]{ beanIterator.next() }; }
    };
}
```

## Parallel data rows — `@DataProvider(parallel = true)`, never with Playwright or Appium

When rows are **independent** (they are, by the test-independence rule) **and the test body drives no browser or
device**, run them concurrently to cut wall time. TestNG fans the rows across its data-provider thread pool.

```java
@DataProvider(name = "csvTaxCasesInParallel", parallel = true)
public static Object[][] csvTaxCasesInParallel() {
    return csvTaxCases();
}
```

Set the pool size in the suite: `<suite data-provider-thread-count="4">`. Parallel rows demand the test body
hold **no shared mutable state** (CLAUDE.md: no static mutable state) — each invocation must stand alone.

**A Playwright or Appium test class keeps its data providers sequential.** Every row of a class runs on the same
instance, so parallel rows would share its one `page` (or driver) and call Playwright from a thread that did not
create it — Playwright for Java is not thread-safe. J1's `BaseTest` therefore runs the suite with
`parallel="classes"`: the class is the unit of parallelism, and its rows run one after another on its thread
(`qa/java/skills/ui-test-author/playwright/references/lifecycle.md` §1, plan D8). A row that needs its own
context options (a viewport, a locale) is a `@Factory` row instead — one instance per row
(`qa-java:responsive-testing`, `qa-java:language-testing`).

## Anti-patterns

- **`line.split(",")` instead of a CSV library.** Breaks the moment a field contains a comma, a quote, or a
  newline. *Fix:* OpenCSV `CsvToBean` (or Apache Commons CSV) — it handles RFC-4180 quoting for you.
- **Returning `Object[]` of loose strings and indexing in the test.** `args[3]` is a mystery and a column
  reorder silently breaks it. *Fix:* bind to a **typed record** with intent-named getters; pass one typed arg.
- **A `for` loop over rows *inside one `@Test`*.** One failure aborts the rest, and you get **one** result
  for N cases. *Fix:* that's exactly what `@DataProvider` replaces — one invocation per row, each reported.
- **Excel for engineer-owned data.** Binary, un-diffable, un-mergeable, needs POI to read. *Fix:* CSV or
  JSON in git; reserve Excel for sheets a non-technical owner actually maintains.
- **Money as Excel/CSV floating-point.** `0.1 + 0.2` and POI `getNumericCellValue` round-off corrupt totals.
  *Fix:* store **integer cents** (or `BigDecimal`); assert on those.
- **Unnamed rows.** A failure that says "iteration 12 failed" sends you counting lines. *Fix:* a meaningful
  `toString()` / `.as(...)` description so the **input** is in the failure message.
- **Loading a 100k-row file into `Object[][]`.** Memory blows up at discovery. *Fix:* return
  `Iterator<Object[]>` and read lazily.
- **Secrets or real PII in a committed data file.** It's in git history forever. *Fix:* synthetic data; real
  secrets via env (cross-link `qa-java:test-login-tokens`).

## Examples

**End-to-end: same test body, three sources, one typed row, named failures.**

```java
public class TaxCalculatorTest {

    private final TaxCalculator calc = new TaxCalculator();

    @Test(dataProvider = "csvTaxCases", dataProviderClass = TaxCaseProviders.class)
    public void Should_ComputeTax_When_CaseComesFromCsv(TaxCase tc) {
        assertThat(calc.taxFor(tc.region(), tc.amountCents()))
            .as("case=%s", tc)
            .isEqualTo(tc.expectedTaxCents());
    }

    @Test(dataProvider = "excelPricingCases", dataProviderClass = TaxCaseProviders.class)
    public void Should_ComputeTax_When_CaseComesFromExcel(TaxCase tc) {
        assertThat(calc.taxFor(tc.region(), tc.amountCents()))
            .as("case=%s", tc)
            .isEqualTo(tc.expectedTaxCents());
    }
}
```

Engineer-owned flat data comes from CSV, stakeholder-owned pricing from Excel — the same body shape and the same
typed row. A run produces one Allure result **per row**, each labelled with the case — so a regression points
straight at `DE @ 10000¢ → 1900¢`, not "row 1".

**Composing with a builder (the boundary made concrete):** a row supplies the *varying* fields; the
**builder** (`qa-java:test-data-builder`) fills the rest — the ObjectMother default is the unchanging 90%.

```java
@Test(dataProvider = "csvOrderCases", dataProviderClass = OrderCaseProviders.class)
public void Should_ApplyDiscount_When_OrderMatchesTheRow(OrderCase row) {
    var order = Orders.standard()
        .withRegion(row.region())
        .withSubtotalCents(row.subtotalCents())
        .build();

    assertThat(discountEngine.apply(order)).isEqualTo(row.expectedDiscountCents());
}
```

## Rules (hard constraints)

- **Data lives outside the test body** — inline `@DataProvider` for a handful, an external CSV/JSON/Excel
  file (under `src/test/resources/data/`, versioned) beyond that. One test body, N rows; **never** a `for`
  loop or `if` branch driving assertions inside a test (CLAUDE.md — parameterize instead).
- **Parse with a real library, bind to a typed object** — OpenCSV `CsvToBean` (CSV), Jackson `TypeReference`
  (JSON), Apache POI `WorkbookFactory` (Excel). **Never** `split(",")`; never index a loose `Object[]` in the
  test. The row record's getters expose **intent**, not column order.
- **Each row is an independent, named case** — one logical assertion per row; the failure message carries the
  **input** (`toString()` / `.as(...)`). Rows run in any order; parallel rows hold no shared mutable state.
- **Pick the source for the shape** — CSV for flat tabular, JSON for nested, Excel **only** for
  stakeholder-owned sheets, inline for a few. Prefer diffable CSV/JSON in git over binary Excel.
- **Money is integer cents / `BigDecimal`, never float** (Excel/CSV round-off corrupts it). No secrets or
  real PII in committed data files (synthetic data; secrets via env — `qa-java:test-login-tokens`).
- **Lazy `Iterator<Object[]>` for huge datasets**; `@DataProvider(parallel = true)` + suite
  `data-provider-thread-count` for independent rows **only where no browser or device is driven** — a
  Playwright or Appium class keeps its rows sequential (`parallel="classes"`, plan D8). No `Thread.sleep`;
  structured logging; constructor injection.

## Cross-references

- `qa-dotnet:data-driven-testing` — same four ideas, NUnit: `[TestCaseSource]` (a static method/property
  returning `IEnumerable<TestCaseData>`, named via `.SetName(...)`), CsvHelper `GetRecords<T>()`,
  `System.Text.Json` for JSON, ClosedXML for Excel. Structure ported, not code.
- `qa-typescript:data-driven-testing` — same four ideas, Vitest `test.for` / `describe.each` and a
  test-per-row loop in Playwright (read the file at module scope), `csv-parse/sync` + `JSON.parse` + the
  `xlsx` (SheetJS) lib, **Zod** to validate/coerce parsed rows into a typed object.
- `qa-java:test-data-builder` — the **boundary**: a builder/ObjectMother constructs **one** complex object in
  code with defaults; data-driven feeds **many** rows from a file. They **compose** — a row drives a builder's
  varying fields (see the last example).
- `qa-java:db-verification-queries` — when the rows come from a **live database** at test time rather
  than a static file; the safe assertion-SQL counterpart to file-sourced data.
- `qa-java:browser-cloud-setup` — parameterizing the **environment** (browser/device matrix) rather than
  the **data**; the two matrices are orthogonal and can multiply.
- `qa-java:api-tests` / `qa-java:ui-tests-playwright` — where the data-driven test
  *bodies* are authored; this skill supplies their rows.
- `qa-java:test-reports` — each row renders as a separate, named Allure result; parameters show the
  per-row input. `qa-<stack>:quality-metrics` — coverage that scales by rows, not methods.
