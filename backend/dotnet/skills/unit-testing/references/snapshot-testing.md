# Snapshot (approval) testing with Verify

Read this when a unit's output is a **large, structured value** whose whole shape is the contract: a mapper that
builds a 30-field DTO, a ProblemDetails translation, a generated document, a rendered template, a serialized
payload. Verify serializes the value to a `*.verified.*` file the first time, a person approves it, and every
later run diffs the new output against that file.

## Snapshot or targeted assertion

| The behaviour under test | Use |
|---|---|
| One value, one rule (a total, a status, a rounding boundary) | A targeted `Assert.That` — a snapshot hides the one thing the test is about inside a file nobody reads |
| A branch of a mapper or validator | A targeted assertion per branch — the coverage floor counts asserting tests, and a snapshot asserts everything at once |
| The full shape of a large output, where any unintended change is a defect (field renamed, null appeared, order changed) | **A snapshot** |
| Output with no single owner of truth (generated SQL, an OpenAPI document, an email body) | **A snapshot**, reviewed in the diff like code |

A snapshot is **one logical assertion** — "the output equals the approved output" — so it obeys the one-assertion
rule. It never replaces the boundary tests: keep `[TestCase]` rows for the rules, add one snapshot for the shape.

## Packages and version lane

| Runner in the repo | Package | Version |
|---|---|---|
| NUnit 4.x | `Verify.NUnit` | **33.1.5** — needs `NUnit` ≥ **4.6.1**; raise the repo's NUnit pin to 4.6.1 in the same change (a lower explicit pin fails restore with `NU1605`) |
| NUnit 5 | `Verify.NUnit` | **33.4.0** (the first NUnit-5-only line is 33.2.0) |

Both target net8, net9 and net10 (verified on nuget.org, 2026-11). Pin in `Directory.Packages.props`.

**Licence check before adding it.** Verify joined the Open Source Maintenance Fee: every version released after
1 September 2026 (all of 32.0.1 and later) is fee-bearing for organizations with revenue, and from v33 a build-time
`SponsorCheck` reads the declaration from `Directory.Build.props` (`<Verify_GitHubSponsorAccount>` or an exemption
such as `<Verify_SponsorshipExemption>`). Record the decision with the change; a team that will not pay pins
`Verify.NUnit` **32.0.0**, the last release before the cut-off.

## Settings once, in a module initializer

Global settings go in one `[ModuleInitializer]` in the test project, never in a test:

```csharp
using System.Runtime.CompilerServices;

namespace Ordering.Application.Tests;

internal static class VerifyInitializer
{
    [ModuleInitializer]
    internal static void Initialize()
    {
        VerifierSettings.ScrubInlineGuids();
        VerifierSettings.ScrubInlineDateTimes("yyyy-MM-ddTHH:mm:ss");
        VerifierSettings.SortPropertiesAlphabetically();
    }
}
```

## Scrubbers — what makes a snapshot stable

- **Guid and date members are scrubbed by default.** A `Guid` property becomes `Guid_1`, a `DateTime` /
  `DateTimeOffset` / `DateOnly` / `TimeOnly` property becomes `DateTime_1`; the same value always maps to the same
  counter, so "these two ids are equal" survives scrubbing.
- **Inline values inside strings are not.** A URL with an id in it, a message with a timestamp: turn on
  `ScrubInlineGuids()` / `ScrubInlineDateTimes(format)` for those.
- **Anything else that varies per run** — a token, a host name, a port — goes through `ScrubLinesWithReplace` or
  `ScrubReplace(find, replacement)` scoped to the one test that needs it.
- **Prefer fixing the seam to scrubbing.** A value that comes from `TimeProvider` or an `IIdGenerator` stub is
  already fixed; scrubbing is for values the test cannot control.

```csharp
[Test]
public Task Should_MapEveryOrderField_When_OrderIsShipped()
{
    var order = new OrderBuilder().WithStatus(OrderStatus.Shipped).Build();

    var dto = OrderMapper.ToDto(order);

    return Verify(dto);
}
```

`Verify(...)` is in scope through the package's implicit usings (`<ImplicitUsings>enable</ImplicitUsings>`);
without them, call `Verifier.Verify(...)`.

## Source control

- `.gitignore`: `*.received.*` — the received file is the failed run's output, never committed.
- **Commit every `*.verified.*`**, reviewed in the pull request like code.
- `.gitattributes`: `*.verified.txt text eol=lf working-tree-encoding=UTF-8` (and `.json`, `.xml`, `.html` the same
  way) — Verify rejects a verified file containing a carriage return.

## CI never accepts a snapshot

- A test with **no `.verified.` file fails** and writes a `.received.` file. That is the behaviour CI must keep: a
  missing snapshot is a test that was never approved.
- **Never call `AutoVerify()`** in a module initializer, a test, or behind a CI flag. Accepting a snapshot is a
  human decision, made locally with a diff tool, the Rider/ReSharper Verify plugin, or by moving the received file.
- On a failed run, upload `**/*.received.*` as a build artifact (`if: failure()` / `condition: failed()`) so the
  reviewer sees what changed without re-running.
- Updating the Verify package can change snapshot formatting in a minor version: bump `Verify.*` packages alone,
  re-run, review the diffs, then accept.
