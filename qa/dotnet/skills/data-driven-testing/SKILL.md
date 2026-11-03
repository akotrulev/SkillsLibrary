---
name: data-driven-testing
description: Use when one .NET/NUnit test must run over many rows from an external CSV, JSON or spreadsheet. Triggers "run this test for every row". Not for building test objects (test-data-builder).
---

# Data-Driven Testing (.NET 10 / NUnit)

> **Ported from the canonical `qa-java:data-driven-testing`.** The four ideas and the section order are
> identical; only the runner API (NUnit `[TestCaseSource]` instead of TestNG `@DataProvider`) and the
> parsing libraries (CsvHelper / `System.Text.Json` / ClosedXML) change. See the Java file for the rationale
> behind the family; this file is the C# expression of the same discipline.

A **data-driven test** is **one test body** exercised against **many input rows**, where the rows live
**outside the test code** — an external CSV / JSON / Excel file checked into the repo. Add a row, get a
case; you never copy-paste a `[Test]` to cover a new input.

It is *not*: a **builder** constructing one richly-configured object in code (`qa-dotnet:test-data-builder`
— one object well, vs many rows; they **compose**); rows pulled from a **live database**
(`qa-dotnet:db-verification-queries`); or a **cross-browser/-device matrix** (`qa-dotnet:browser-cloud-setup`
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
| Rows from a **live DB / API** at test time | not this skill | `qa-dotnet:db-verification-queries` (DB), an API client (HTTP) |
| Each row is a whole complex domain object built in code | not this skill | `qa-dotnet:test-data-builder` (the builder can consume one row) |

**Rule of thumb:** *prefer CSV or JSON in git* (diffable, reviewable, mergeable). Reach for **Excel only**
when the data's owner won't touch a CSV. Use **inline `[TestCase]`** when there are few enough rows that a
separate file is more friction than it's worth. The format hides behind a **typed row record** — the test
body never knows which one fed it.

## Stack

- .NET 10 (8/9 supported — match the TFM), NUnit 4.x — `[TestCaseSource]` / `[TestCase]` / `[Values]`; nullable reference types on
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

public sealed record TaxCase(string Region, long AmountCents, long ExpectedTaxCents)
{
    public override string ToString() => $"{Region} @ {AmountCents}¢ → {ExpectedTaxCents}¢";
}
```

## Source 1 — inline (`[TestCase]` and a source method)

`[TestCase]` attributes are the few-rows form; a `[TestCaseSource]` method returning `TestCaseData` scales to
named cases and computed data.

```csharp
public class TaxCalculatorTests
{
    private readonly TaxCalculator _calc = new();

    [TestCase("DE", 10_000L, 1_900L)]
    [TestCase("US-OR", 5_000L, 0L)]
    [TestCase("GB", 2_000L, 400L)]
    public void Should_ReturnTheRegionsTax_When_AnAmountIsTaxed(string region, long amountCents, long expectedTaxCents)
    {
        Assert.That(_calc.TaxFor(region, amountCents), Is.EqualTo(expectedTaxCents));
    }

    private static IEnumerable<TestCaseData> InlineCases()
    {
        yield return new TestCaseData(new TaxCase("DE", 10_000L, 1_900L)).SetName("DE 19% VAT");
        yield return new TestCaseData(new TaxCase("US-OR", 5_000L, 0L)).SetName("Oregon no tax");
    }

    [TestCaseSource(nameof(InlineCases))]
    public void Should_ReturnTheRowsTax_When_TheRowComesFromASource(TaxCase tc)
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
        using var csv = new CsvReader(reader, CultureInfo.InvariantCulture);
        csv.Context.RegisterClassMap<TaxCaseMap>();
        foreach (var tc in csv.GetRecords<TaxCase>())
        {
            yield return new TestCaseData(tc).SetName($"CSV: {tc}");
        }
    }
}
```

```csharp
[TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.CsvTaxCases))]
public void Should_ReturnTheRowsTax_When_TheRowComesFromCsv(TaxCase tc)
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
    foreach (var c in JsonSerializer.Deserialize<List<CheckoutCase>>(json, opts)!)
    {
        yield return new TestCaseData(c).SetName($"JSON: {c.Name}");
    }
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
    foreach (var row in sheet.RowsUsed().Skip(1))
    {
        var tc = new TaxCase(
            Region: row.Cell(1).GetString(),
            AmountCents: (long)row.Cell(2).GetDouble(),
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

## Parallel data rows — `[Parallelizable]`, never for Playwright

When rows are **independent** and the fixture holds **no per-test instance state**, run them concurrently to
cut wall time. NUnit parallelizes the cases of one fixture when told to:

```csharp
[Parallelizable(ParallelScope.All)]
public class TaxCalculatorTests
{
    private readonly TaxCalculator _calc = new();
}
```

- `ParallelScope.All` runs every case on **one fixture instance**, concurrently — safe only when the fixture's
  fields are read-only and the cases share nothing (a pure-function calculator, a parser).
- **Never on a Playwright (or Appium) fixture.** `PageTest` — and the `BaseTest` every .NET UI fixture derives
  from — keeps `Page` and `Context` in instance properties, so two rows of one fixture running at once overwrite
  each other's page. Playwright supports only `ParallelScope.Self`, which `BaseTest` declares: rows run one
  after another inside the fixture, fixtures run in parallel
  (`qa/dotnet/skills/ui-test-author/playwright/references/lifecycle.md` §3).
- **Rows that need their own browser context** (a viewport, a locale, a device) are fixture parameters —
  `[TestFixture(...)]` / `[TestFixtureSource]` — not test cases: each row is its own fixture with its own
  `ContextOptions()`, and the rows run in parallel under `ParallelScope.Self`
  (`qa-dotnet:responsive-testing`, `qa-dotnet:language-testing`).
- The worker count is `[assembly: LevelOfParallelism(4)]` or `dotnet test -- NUnit.NumberOfTestWorkers=4`.

## Examples

**End-to-end: same test body, three sources, one typed row, named failures.**

```csharp
public class TaxCalculatorTests
{
    private readonly TaxCalculator _calc = new();

    [TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.CsvTaxCases))]
    public void Should_ReturnTheRowsTax_When_SourcedFromCsv(TaxCase tc)
        => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));

    [TestCaseSource(typeof(TaxCaseSources), nameof(TaxCaseSources.ExcelPricingCases))]
    public void Should_ReturnTheRowsTax_When_SourcedFromExcel(TaxCase tc)
        => Assert.That(_calc.TaxFor(tc.Region, tc.AmountCents), Is.EqualTo(tc.ExpectedTaxCents));
}
```

A run produces one NUnit/Allure result **per row**, each labelled with the case — so a regression points
straight at `CSV: DE @ 10000¢ → 1900¢`, not "(1)".

**Composing with a builder (the boundary made concrete):** a row supplies the *varying* fields; the
**builder** (`qa-dotnet:test-data-builder`) fills the rest with sane defaults.

```csharp
[TestCaseSource(typeof(OrderCaseSources), nameof(OrderCaseSources.CsvOrderCases))]
public void Should_ApplyTheRowsDiscount_When_TheOrderIsPriced(OrderCase row)
{
    var order = Orders.Standard()
        .WithRegion(row.Region)
        .WithSubtotalCents(row.SubtotalCents)
        .Build();

    Assert.That(_discountEngine.Apply(order), Is.EqualTo(row.ExpectedDiscountCents));
}
```

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `test-data.md` and `automation.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in `qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this skill's recipes disagree, the rule files win.

## Conventions

- Inline `[TestCase]` / a source method for a handful of rows; an external CSV / JSON / Excel file (copied to output, versioned) beyond that.
- Lazy `yield return` for huge datasets. `ParallelScope.All` only for fixtures with no per-test instance state, never for Playwright or Appium, whose rows stay `ParallelScope.Self` or become fixture parameters.

## Cross-references

- `qa-java:data-driven-testing` — **the canonical file**: same four ideas, TestNG `@DataProvider` (returning
  `Object[][]` / `Iterator<Object[]>`, `dataProviderClass`, `parallel = true`), OpenCSV `CsvToBean`, Jackson
  `TypeReference`, Apache POI. Read it for the family rationale.
- `qa-typescript:data-driven-testing` — same four ideas, Vitest `test.for` / `describe.each` and a
  test-per-row loop in Playwright, `csv-parse/sync` + `JSON.parse` + the `xlsx` (SheetJS) lib, **Zod** to
  validate/coerce parsed rows.
- `qa-dotnet:test-data-builder` — the **boundary**: a builder/ObjectMother constructs **one** complex object
  in code with defaults; data-driven feeds **many** rows from a file. They **compose** — a row drives a
  builder's varying fields (see the last example).
- `qa-dotnet:db-verification-queries` — when rows come from a **live database** at test time rather than
  a static file; the safe assertion-SQL counterpart to file-sourced data.
- `qa-dotnet:browser-cloud-setup` — parameterizing the **environment** (browser/device matrix) rather
  than the **data**; orthogonal matrices that can multiply.
- `qa-dotnet:api-tests` / `qa-dotnet:ui-tests-playwright` — where the data-driven test
  *bodies* are authored; this skill supplies their rows. `qa-dotnet:test-reports` — each row renders as a
  separate, named result.
