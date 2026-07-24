---
name: qa-data-driven-testing-dotnet
description: Run one .NET 10 (8-9 supported) / NUnit test body against **many rows of data sourced from an external file**. Triggers: "run this test for every row in a CSV / spreadsheet", "data-drive these tests from a JSON file", "parameterize this NUnit test with external test data". For end-to-end suite work prefer the phased agent `qa-api-dotnet` / `qa-ui-dotnet` / `qa-mobile-dotnet` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# Data-Driven Testing (.NET 8 / NUnit)

> **Ported from the canonical `qa-data-driven-testing-java`.** The four ideas and the section order are
> identical; only the runner API (NUnit `[TestCaseSource]` instead of TestNG `@DataProvider`) and the
> parsing libraries (CsvHelper / `System.Text.Json` / ClosedXML) change. See the Java file for the rationale
> behind the family; this file is the C# expression of the same discipline.

A **data-driven test** is **one test body** exercised against **many input rows**, where the rows live
**outside the test code** — an external CSV / JSON / Excel file checked into the repo. Add a row, get a
case; you never copy-paste a `[Test]` to cover a new input.

It is *not*: a **builder** constructing one richly-configured object in code (`qa-test-data-builder-dotnet`
— one object well, vs many rows; they **compose**); rows pulled from a **live database**
(`qa-db-testing-query-author-dotnet`); or a **cross-browser/-device matrix** (`qa-cloud-grid-config-dotnet`
— parameterizing the *environment*, not the *data*).

> **The discipline this skill encodes** — four ideas, identical across all three stacks:
>
> 1. **Separate data from logic.** The body asserts **once**; the rows live in a file. One body, N cases.
>    This is the *sanctioned* alternative to the CLAUDE.md ban on `if`/`for` driving assertions — you don't
>    loop inside a test, you **parameterize** it.
> 2. **Bind each row to a typed object, not loose `object[]` columns.** Parse into a `record` with a **real**
>    library (CsvHelper / `System.Text.Json` / ClosedXML), never `line.Split(',')`. The data-layer analogue
>    of "page objects expose intent, not selectors": a row exposes `c.ExpectedTax`, not `args[3]`.
> 3. **Each row is an independent, individually-named case.** A failing row **names the input that broke it**
>    (`TestCaseData(...).SetName(...)`); one row's failure doesn't stop the others; rows run in any order.
> 4. **One logical assertion per row; pick the source for the data's shape.** Inline for a handful; CSV for
>    flat tabular; JSON for nested/hierarchical; Excel **only** when non-technical stakeholders own the sheet.

## Decision matrix — which data source for which job

| Data shape / situation | Source | Mechanism |
|------------------------|--------|-----------|
| A handful of flat rows, owned by engineers, lives with the test | **`[TestCase]` / inline source** | `[TestCase(...)]` attrs or a `yield return` source method |
| Many flat tabular rows (one record per line), engineer-owned | **CSV file** | CsvHelper `GetRecords<Row>()` (+ a `ClassMap`) → `IEnumerable<TestCaseData>` |
| Nested / hierarchical cases (a row has sub-objects or lists) | **JSON file** | `JsonSerializer.Deserialize<List<Row>>(…)` |
| Tabular data **owned/edited by non-technical stakeholders** | **Excel `.xlsx`** | ClosedXML `XLWorkbook` → bind cells → `IEnumerable<Row>` |
| Huge dataset (don't hold it all in memory) | any of the above, **lazy** | source method `yield return`s one `TestCaseData` per row |
| Rows from a **live DB / API** at test time | not this skill | `qa-db-testing-query-author-dotnet` (DB), an API client (HTTP) |
| Each row is a whole complex domain object built in code | not this skill | `qa-test-data-builder-dotnet` (the builder can consume one row) |

**Rule of thumb:** *prefer CSV or JSON in git* (diffable, reviewable, mergeable). Reach for **Excel only**
when the data's owner won't touch a CSV. Use **inline `[TestCase]`** when there are few enough rows that a
separate file is more friction than it's worth. The format hides behind a **typed row record** — the test
body never knows which one fed it.

## Stack

- .NET 8, NUnit 4.x — `[TestCaseSource]` / `[TestCase]` / `[Values]`; nullable reference types on
- `CsvHelper` — CSV → typed records (`GetRecords<T>()`, `ClassMap` for header mapping); RFC-4180 quoting
- `System.Text.Json` — JSON → typed list (`JsonSerializer.Deserialize`, source-gen optional)
- `ClosedXML` — Excel `.xlsx` reading (`XLWorkbook`), no Office install, no COM (the modern POI-equivalent)
- Test data files copied to output (`CopyToOutputDirectory`) so the source method can read them at run time

```
Tests/
├── Data/
│   ├── TaxCase.cs              ← the typed row record (CSV/JSON/Excel all bind to it)
│   └── TaxCaseSources.cs       ← [TestCaseSource] methods (one per source, reusable static class)
├── TaxCalculatorTests.cs       ← one test body, many rows
└── Data/Files/
    ├── tax-cases.csv           ← flat tabular, engineer-owned   (CopyToOutputDirectory=PreserveNewest)
    ├── checkout-cases.json     ← nested cases
    └── pricing-cases.xlsx      ← stakeholder-owned sheet
```

> Mark the data files `<None Update="Data\Files\*"><CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory></None>`
> in the `.csproj` (or set "Copy if newer" in the IDE) so they sit next to the test assembly at run time.

## The typed row — bind data to meaning, not to indexes

Every source binds to the **same record**. The test body depends on `TaxCase`, never on a column order or an
array index — so changing the file format (CSV → JSON) never touches a test. Records are immutable, which
fits CLAUDE.md's prefer-immutability rule; CsvHelper and `System.Text.Json` both bind records.

```csharp
namespace Acme.Tests.Data;

// CsvHelper maps by header name (see the ClassMap); System.Text.Json maps by property name; ClosedXML sets per column.
public sealed record TaxCase(string Region, long AmountCents, long ExpectedTaxCents)
{
    // Name the case so a failing row reports the INPUT that broke it, not "TestCaseSource(2)".
    public override string ToString() => $"{Region} @ {AmountCents}¢ → {ExpectedTaxCents}¢";
}
```

## Source 1 — inline (`[TestCase]` and a source method)

`[TestCase]` attributes are the few-rows form; a `[TestCaseSource]` method returning `TestCaseData` scales to
named cases and computed data.

```csharp
public class TaxCalculatorTests
{
    private readonly TaxCalculator _calc = new();   // constructor-style init; no shared mutable state

    [TestCase("DE",    10_000L, 1_900L)]   // 19% VAT
    [TestCase("US-OR",  5_000L,     0L)]   // no sales tax
    [TestCase("GB",     2_000L,   400L)]   // 20% VAT
    public void Should_ComputeTax_For_Region(string region, long amountCents, long expectedTaxCents)
    {
        Assert.That(_calc.TaxFor(region, amountCents), Is.EqualTo(expectedTaxCents));  // one logical assertion
    }

    // The source-method form: name each case so a failure says WHICH input broke.
    private static IEnumerable<TestCaseData> InlineCases()
    {
        yield return new TestCaseData(new TaxCase("DE",    10_000L, 1_900L)).SetName("DE 19% VAT");
        yield return new TestCaseData(new TaxCase("US-OR",  5_000L,     0L)).SetName("Oregon no tax");
    }

    [TestCaseSource(nameof(InlineCases))]
    public void Should_ComputeTax_From_Source(TaxCase tc)
        => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));
}
```

> **Discovery-time gotcha (the NUnit analogue of TestNG's load-time providers):** `[TestCaseSource]` resolves
> at **test-discovery** time and must be a **static** member with no per-instance dependencies — the test
> runner enumerates it before any `[SetUp]` runs. Read files and build cases there; do not depend on
> instance fixtures inside the source.

## Source 2 — external CSV (CsvHelper)

For flat tabular data, store it in a CSV and bind each line to the typed record with **CsvHelper** — never
`Split(',')` (it breaks on quoted commas, escapes, embedded newlines). Put the source in a **reusable static
class** so many test classes share it.

`Tests/Data/Files/tax-cases.csv`:

```csv
region,amount_cents,expected_tax
DE,10000,1900
US-OR,5000,0
GB,2000,400
```

A `ClassMap` maps the snake_case headers to the record (or name headers to match and skip the map):

```csharp
using CsvHelper.Configuration;

public sealed class TaxCaseMap : ClassMap<TaxCase>
{
    public TaxCaseMap()
    {
        Map(m => m.Region).Name("region");
        Map(m => m.AmountCents).Name("amount_cents");
        Map(m => m.ExpectedTaxCents).Name("expected_tax");
    }
}
```

```csharp
public static class TaxCaseSources
{
    private static string DataDir =>
        Path.Combine(TestContext.CurrentContext.TestDirectory, "Data", "Files");

    public static IEnumerable<TestCaseData> CsvTaxCases()
    {
        using var reader = new StreamReader(Path.Combine(DataDir, "tax-cases.csv"));
        using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);   // invariant: '.' decimals, no locale surprises
        csv.Context.RegisterClassMap<TaxCaseMap>();
        foreach (var tc in csv.GetRecords<TaxCase>())                          // typed rows, RFC-4180 quoting handled
            yield return new TestCaseData(tc).SetName($"CSV: {tc}");           // tc.ToString() names the row
    }
}
```

```csharp
[TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.CsvTaxCases))]
public void Should_ComputeTax_From_Csv(TaxCase tc)          // one typed arg, not three loose columns
    => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));
```

`[TestCaseSource(typeof(X), nameof(...))]` lets a single source class feed tests across many test classes —
the data lives once.

## Source 3 — external JSON (`System.Text.Json`, for nested cases)

When a case has **sub-objects or lists** (a CSV can't express nesting cleanly), use JSON. Deserialize the
whole file to a `List<Row>`.

`Tests/Data/Files/checkout-cases.json`:

```json
[
  { "name": "two items, one coupon",
    "items": [ { "sku": "A", "qty": 2 }, { "sku": "B", "qty": 1 } ],
    "coupon": "SAVE10", "expectedTotalCents": 4410 },
  { "name": "empty cart",
    "items": [], "coupon": null, "expectedTotalCents": 0 }
]
```

```csharp
public static IEnumerable<TestCaseData> JsonCheckoutCases()
{
    var json = File.ReadAllText(Path.Combine(DataDir, "checkout-cases.json"));
    var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
    foreach (var c in JsonSerializer.Deserialize<List<CheckoutCase>>(json, opts)!)   // nested → typed
        yield return new TestCaseData(c).SetName($"JSON: {c.Name}");                 // Name is the row label
}
```

`CheckoutCase` is a `record CheckoutCase(string Name, IReadOnlyList<Item> Items, string? Coupon, long
ExpectedTotalCents)` — `System.Text.Json` binds records natively. The `Name` field is the row's report label.

## Source 4 — external Excel (ClosedXML, stakeholder-owned)

Use Excel **only** when non-technical stakeholders own and edit the sheet — it's binary, doesn't diff or
merge in git, and is heavier than CSV. Read `.xlsx` with **ClosedXML** (`XLWorkbook` — no Office install, no
COM), skip the header row, bind cells to the record with a **typed cell accessor**.

```csharp
public static IEnumerable<TestCaseData> ExcelPricingCases()
{
    using var workbook = new XLWorkbook(Path.Combine(DataDir, "pricing-cases.xlsx"));
    var sheet = workbook.Worksheet(1);
    // RowsUsed() skips trailing blanks; Skip(1) drops the header row.
    foreach (var row in sheet.RowsUsed().Skip(1))
    {
        var tc = new TaxCase(
            Region:           row.Cell(1).GetString(),
            AmountCents:      (long)row.Cell(2).GetDouble(),     // Excel numbers are doubles
            ExpectedTaxCents: (long)row.Cell(3).GetDouble());
        yield return new TestCaseData(tc).SetName($"XLSX: {tc}");
    }
}
```

> **Excel gotchas to encode:** numeric cells come back as `double` — cast deliberately and watch money
> precision (store **integer cents**, never floating dollars; assert on those). A "number" a user typed may
> be a *text* cell — `GetString()` vs `GetValue<long>()`; use `cell.GetValue<T>()` with a guard, or
> `cell.DataType`, if a column is mixed. `RowsUsed()` tolerates trailing blanks. ClosedXML reads `.xlsx`
> only (the OOXML format) — for legacy `.xls`, convert first.

## Lazy rows for huge datasets — `yield return`

A `[TestCaseSource]` that builds a `List<TestCaseData>` **materializes every row up front**. A method that
`yield return`s streams them — NUnit pulls one at a time, so memory stays flat. (The CsvHelper example above
already does this — `GetRecords<T>()` is itself lazy and each row is yielded.) Keep the source as an iterator
method, not an eager `.ToList()`, for large files.

## Parallel data rows — `[Parallelizable]`

When rows are **independent** (they are, by the test-independence rule), run them concurrently to cut wall
time. NUnit parallelizes test cases within a fixture when told to:

```csharp
[TestFixture]
[Parallelizable(ParallelScope.All)]            // the source's cases run concurrently
public class TaxCalculatorTests { /* … */ }
```

Set the worker count via `[assembly: LevelOfParallelism(4)]`. Parallel rows demand the test body hold **no
shared mutable state** (CLAUDE.md: no static mutable state) — each case must stand alone.

## Anti-patterns

- **`line.Split(',')` instead of a CSV library.** Breaks the moment a field contains a comma, a quote, or a
  newline. *Fix:* CsvHelper `GetRecords<T>()` — RFC-4180 quoting handled.
- **Returning `object[]` of loose values and indexing in the test.** `args[3]` is a mystery and a column
  reorder silently breaks it. *Fix:* bind to a **typed record**; pass one typed arg.
- **A `foreach` over rows *inside one `[Test]`*.** One failure aborts the rest, and you get **one** result
  for N cases. *Fix:* that's what `[TestCaseSource]` replaces — one case per row, each reported.
- **Excel for engineer-owned data.** Binary, un-diffable, un-mergeable. *Fix:* CSV or JSON in git; Excel only
  for sheets a non-technical owner maintains.
- **Money as Excel/CSV floating-point.** `double` round-off corrupts totals. *Fix:* **integer cents** (or
  `decimal`); assert on those. (Use `CultureInfo.InvariantCulture` in CsvHelper so `.`/`,` decimals don't
  flip by locale.)
- **Unnamed cases.** `Should_ComputeTax_From_Csv(TaxCase)` with no `.SetName` shows as `(1)`, `(2)`… *Fix:*
  `TestCaseData(...).SetName($"…{tc}")` so the **input** is in the failure.
- **Instance state in a `[TestCaseSource]`.** It resolves at discovery before `[SetUp]`; an instance
  dependency is null. *Fix:* keep the source **static** and self-contained.
- **Secrets or real PII in a committed data file.** It's in git history forever. *Fix:* synthetic data; real
  secrets via env (cross-link `qa-auth0-test-tokens-dotnet`).

## Examples

**End-to-end: same test body, three sources, one typed row, named failures.**

```csharp
[TestFixture]
public class TaxCalculatorTests
{
    private readonly TaxCalculator _calc = new();   // no shared mutable state

    [TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.CsvTaxCases))]
    public void Should_ComputeTax_When_SourcedFromCsv(TaxCase tc)
        => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));

    [TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.ExcelPricingCases))]
    public void Should_ComputeTax_When_SourcedFromExcel(TaxCase tc)   // SAME body shape, SAME typed row
        => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));
}
```

A run produces one NUnit/Allure result **per row**, each labelled with the case — so a regression points
straight at `CSV: DE @ 10000¢ → 1900¢`, not "(1)".

**Composing with a builder (the boundary made concrete):** a row supplies the *varying* fields; the
**builder** (`qa-test-data-builder-dotnet`) fills the rest with sane defaults.

```csharp
[TestCaseSource(typeof(OrderCaseSources), nameof(OrderCaseSources.CsvOrderCases))]
public void Should_ApplyDiscount(OrderCase row)
{
    var order = Orders.Standard()            // ObjectMother default — the unchanging 90%
        .WithRegion(row.Region)              // the row drives only what VARIES
        .WithSubtotalCents(row.SubtotalCents)
        .Build();
    Assert.That(_discountEngine.Apply(order), Is.EqualTo(row.ExpectedDiscountCents));
}
```

## Rules (hard constraints)

- **Data lives outside the test body** — inline `[TestCase]`/source method for a handful, an external
  CSV/JSON/Excel file (copied to output, versioned) beyond that. One body, N rows; **never** a `foreach` or
  `if` driving assertions inside a test (CLAUDE.md — parameterize instead).
- **Parse with a real library, bind to a typed record** — CsvHelper `GetRecords<T>()` (CSV),
  `JsonSerializer.Deserialize` (JSON), ClosedXML `XLWorkbook` (Excel). **Never** `Split(',')`; never index a
  loose `object[]` in the test. The record's properties expose **intent**, not column order.
- **Each row is an independent, named case** — one logical assertion per row; the failure carries the
  **input** (`TestCaseData(...).SetName(...)`). Rows run in any order; parallel cases hold no shared mutable
  state. `[TestCaseSource]` is **static** and resolves at discovery.
- **Pick the source for the shape** — CSV for flat tabular, JSON for nested, Excel **only** for
  stakeholder-owned sheets, inline for a few. Prefer diffable CSV/JSON in git over binary Excel.
- **Money is integer cents / `decimal`, never `double`** (round-off corrupts it); `CultureInfo.InvariantCulture`
  for CsvHelper. No secrets or real PII in committed data files (synthetic; secrets via env —
  `qa-auth0-test-tokens-dotnet`).
- **Lazy `yield return` for huge datasets**; `[Parallelizable]` + `[assembly: LevelOfParallelism]` for
  independent rows. No `Thread.Sleep`; structured logging; constructor injection; nullable enabled.

## Cross-references

- `qa-data-driven-testing-java` — **the canonical file**: same four ideas, TestNG `@DataProvider` (returning
  `Object[][]` / `Iterator<Object[]>`, `dataProviderClass`, `parallel = true`), OpenCSV `CsvToBean`, Jackson
  `TypeReference`, Apache POI. Read it for the family rationale.
- `qa-data-driven-testing-typescript` — same four ideas, Vitest `test.for` / `describe.each` and a
  test-per-row loop in Playwright, `csv-parse/sync` + `JSON.parse` + the `xlsx` (SheetJS) lib, **Zod** to
  validate/coerce parsed rows.
- `qa-test-data-builder-dotnet` — the **boundary**: a builder/ObjectMother constructs **one** complex object
  in code with defaults; data-driven feeds **many** rows from a file. They **compose** — a row drives a
  builder's varying fields (see the last example).
- `qa-db-testing-query-author-dotnet` — when rows come from a **live database** at test time rather than
  a static file; the safe assertion-SQL counterpart to file-sourced data.
- `qa-cloud-grid-config-dotnet` — parameterizing the **environment** (browser/device matrix) rather
  than the **data**; orthogonal matrices that can multiply.
- `qa-api-test-author-generator-dotnet` / `qa-ui-test-author-playwright-dotnet` — where the data-driven test
  *bodies* are authored; this skill supplies their rows. `qa-allure-reporting-dotnet` — each row renders as a
  separate, named result.
