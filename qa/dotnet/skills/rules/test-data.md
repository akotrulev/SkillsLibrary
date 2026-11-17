---
paths:
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,TestCore}/**/{Builders,Mothers,TestData}/**"
  - "**/*{ApiTests,UiTests,AppiumTests,MobileTests,E2ETests,IntegrationTests,AcceptanceTests,BddTests,Bdd.Tests,TestCore}/**/*{Builder,Mother}.cs"
---

<!-- qa-dotnet rules v2 (2026-11-17): test data. Installed by /qa-dotnet:rules; edit the paths above to where this project keeps its builders and data files. -->

# Test data standards (builders, rows, environment)

Severity tags as in the core rules. The codebase wins where it consistently does otherwise.

## Builders

- One sealed builder per aggregate, in the test project's `Builders/` (ObjectMothers in `Mothers/`); never in a production assembly. *minor*
- Every field has a valid, deterministic default; randomness only on id-like fields, seeded, never on a value a test asserts. *major*
- `With<X>` / `For<X>` / `<Verb>At` return `this`; `Build()` is the only terminal and returns the real type (a record), never the builder, `object` or `dynamic`. *major*
- `Build()` is pure and idempotent: no persistence, no logging, no async; collections are snapshotted. *major*
- An ObjectMother returns a builder so tests can refine it; no AutoFixture stacked over the builders. *minor*

## Data-driven rows

- Rows bind to a typed record through a real parser (CsvHelper with `InvariantCulture`, `System.Text.Json`, ClosedXML), never `Split(',')` or an indexed `object[]`. *major*
- A `[TestCaseSource]` is static, and each row is a named case (`SetName`) so the input shows in the failure. *minor*
- CSV or JSON in git; Excel only for a sheet a non-technical owner maintains. *minor*
- Money is integer cents or `decimal`, never `double`. *major*
- No secret or real personal data in a committed data file; synthetic only. *blocker*

## Environment data

- A test creates what it changes, unique per test, registered for teardown. *major*
- Reference data: a search or filter test may read curated environment data, named in the test or feature, never modified; it asserts a non-empty result before asserting on its rows. *blocker for a missing guard*
- Pre-clean: setup or a `Given … does not exist` step may also delete a leftover, via the API or a seeder, not a long UI sequence. *minor*
- Keep on failure: teardown may keep a failed test's data and log its ids, deleting on a pass; names are then unique per run. The check is the teardown registry's legal branch. *major*
