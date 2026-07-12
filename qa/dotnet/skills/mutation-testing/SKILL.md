---
name: qa-mutation-testing-dotnet
description: Use when measuring TEST QUALITY (not code coverage) for a .NET 10 (8/9 supported) suite with mutation testing — run Stryker.NET (`dotnet stryker`) to seed faults into compiled C# and prove the tests detect them, fail the build on a mutation-score threshold, and turn surviving mutants into missing-assertion findings. Triggers: "add mutation testing", "run stryker", "is my coverage real", "tests pass but catch nothing", "mutation score gate". .NET-only tool; the JVM sibling is PIT/pitest, the TS sibling is StrykerJS.
---

# QA — Mutation Testing (Stryker.NET, C#)

Mutation testing answers the question line/branch coverage **cannot**: **"if the production code were
wrong, would a test fail?"** Coverage proves a line *executed*; it says nothing about whether anything
*asserted* on the result. A test suite can have 95% line coverage and 0% real fault-detection — every test
calls the code and asserts nothing meaningful. Mutation testing is the only automated way to measure that
gap. **Stryker.NET** (`dotnet stryker`) is the state-of-the-art mutation engine for .NET and the tool for
this stack.

> **Stack scope:** Stryker.NET mutates **C# source** (Roslyn-based) and drives the **.NET test runner**, so
> this skill is the .NET-stack implementation. The discipline is identical on other stacks but the tool
> changes — use the sibling skill, don't force Stryker.NET:
>
> | Stack | Tool | Skill |
> |---|---|---|
> | **.NET (C#)** | **Stryker.NET** (`dotnet stryker`) | **this skill** |
> | **Java / Kotlin** | **PIT (pitest)** | `qa/java/skills/mutation-testing` |
> | **TypeScript / JS** | **StrykerJS** (`@stryker-mutator/core`) | `qa/typescript/skills/mutation-testing` |
>
> The threshold philosophy, the "surviving mutant = missing assertion" workflow, the scope/incremental
> discipline, and the anti-patterns below carry over to the siblings — only the tool invocation differs.

## How it works (and why the score means something)

Stryker takes your **already-passing** unit tests, then systematically rewrites your production code to
introduce small faults — a **mutant** — and re-runs the tests that cover that code:

- A mutant is **killed** if at least one test now **fails** → the suite detected the fault. Good.
- A mutant **survives** if all tests still **pass** → the suite did **not** notice the code changed. That is
  a real, located **gap in your assertions** (or dead code).
- A mutant is **No coverage** if no test even runs the line — worse than a survivor: nothing exercises it.

**Mutation score = killed / (killed + survived + no-coverage + timeout)** (Stryker reports both a score
including and excluding no-coverage mutants). Unlike coverage, this is a *causal* metric: it can only go up
by writing a test that actually catches a behavioural change. Stryker is fast because it uses **coverage
analysis** to run only the tests that reach each mutant, not the whole suite per mutant.

### Example of a surviving mutant

```csharp
int ApplyDiscount(int price, int pct) =>
    price - (price * pct / 100);   // Stryker mutates '-' → '+' (arithmetic mutator)
```

```csharp
[Test]
public void DiscountsPrice()
{
    var result = _svc.ApplyDiscount(100, 10);
    Assert.That(result, Is.Not.Null);   // executes the line (100% coverage) but never checks the value
}
```

The `+`/`-` mutant **survives** — the test asserts nothing about the number. Coverage says "done"; Stryker
says "your test is blind". The fix is `Assert.That(result, Is.EqualTo(90))`. **That is the entire value of
the tool.**

## Mutators — what faults Stryker seeds

Stryker mutates by category and is **on-by-default for all mutators**; you *exclude* the ones you don't want
rather than opt in. The main categories:

| Category | Example mutation | Notes |
|---|---|---|
| **Arithmetic** | `+`→`-`, `*`→`/` | The classic; catches unasserted numeric results. |
| **Equality / relational** | `==`→`!=`, `>`→`>=` (boundary) | Boundary mutants surface off-by-one blindness. |
| **Logical / boolean** | `&&`→`||`, `true`→`false` | |
| **String** | `"x"`→`""`, interpolation emptying | Catches "asserts the call, not the text". |
| **Linq** | `.First()`→`.Last()`, `.All()`→`.Any()` | High-value for data-shaping code. |
| **Statement / block removal** | remove a method body, `return` | Proves the statement's effect is observed. |
| **Unary / update / checked / init** | `++`→`--`, `i = 0`→`i = 1` | |

Tune the set with `mutate` (file globs) and `excluded-mutations` in config, and keep it under version control
so the gate is reproducible. **Start with defaults**; only exclude a category once you've confirmed it
produces mostly equivalent mutants for your code.

## Setup — Stryker.NET

Stryker.NET is a **.NET tool**, not a NuGet package reference. Install it as a repo-local tool so the version
is pinned and reproducible (never `-g` global for a gated build):

```bash
dotnet new tool-manifest                       # if .config/dotnet-tools.json doesn't exist yet
dotnet tool install dotnet-stryker             # pins the version into the manifest (e.g. 4.16.0)
```

Run it **from the unit-test project directory** (or pass `--project` / a solution + `--test-project`):

```bash
cd tests/Orders.UnitTests
dotnet stryker                                 # full run; HTML report → StrykerOutput/**/reports/
```

`stryker-config.json` in the test-project folder — the reproducible gate (all config under the
`stryker-config` key):

```json
{
  "stryker-config": {
    "project": "Orders.csproj",
    "test-projects": ["../../tests/Orders.UnitTests/Orders.UnitTests.csproj"],
    "mutate": ["**/*.cs", "!**/Migrations/**", "!**/*.Generated.cs"],
    "excluded-mutations": [],
    "thresholds": { "high": 80, "low": 60, "break": 60 },
    "reporters": ["html", "progress", "cleartext"],
    "since": { "enabled": false }
  }
}
```

- **`project`** names the *production* project under test (needed when the test project references more than
  one). **`test-projects`** is the suite that drives the mutants.
- **`thresholds.break`** is the gate: Stryker exits non-zero (fails the build) when the score drops below it.
  `high`/`low` only colour the report. **Set `break` deliberately** — `0` (the default) never fails.
- **`mutate`** scopes what gets mutated — exclude generated code, migrations, and DTOs with no logic.

> **Version-aware:** Stryker.NET targets the project's TFM automatically — it builds and runs the suite as-is.
> net10 primary, net8/9 supported; there is no TFM-specific flag. Just pin the **tool** version in the
> manifest so the mutator set doesn't drift between runs.

## Scope and speed — the difference between "practical" and "abandoned"

Mutation testing gets a reputation for being slow **only when mis-scoped**. Three rules keep Stryker fast
enough for CI:

1. **Scope to the diff with `--since`.** Mutate only code changed versus a target branch — a developer pays
   the mutation cost only for code they touched. Reserve a full run for a nightly/main-branch build.

   ```bash
   dotnet stryker --since:main          # only mutate files changed vs origin/main
   ```
   Or in config: `"since": { "enabled": true, "target": "main", "ignore-changes-in": ["**/tests/**"] }`.

2. **Point `test-projects` at fast, isolated unit tests — never integration / Testcontainer / E2E suites.**
   They are slow by design; re-running them per mutant is *the* reason Stryker seems impractical. Mutation
   testing belongs on the tests with **real assertions**, in-process against the production classes.

3. **Use `--concurrency`** to match CI cores (Stryker parallelises test runs across mutants), and let coverage
   analysis (on by default) skip tests that don't reach a mutant.

An infinite-loop mutant shows up as a **timeout** — that counts as a *kill*, not an error; tune `--timeout`
only if legitimately slow tests are being flagged.

## Threshold philosophy — ratchet, never big-bang

| Don't | Do |
|---|---|
| Set `break` to 85 on a legacy codebase day one | **Start `break` at 60**, fail the build there, **raise it as you kill survivors** |
| Chase 100% (equivalent mutants make it unreachable) | Treat **85–90% as excellent** for critical code |
| Run Stryker on the whole solution every PR | `--since:main` on PRs, full run nightly |

The threshold is a **ratchet**: each PR may only raise it. A surviving-mutant report is a **to-do list of
missing assertions**, prioritised by where your tests are blind — not a vanity number.

## CI integration

- **PR gate:** `dotnet stryker --since:main --reporter dashboard --reporter cleartext`, fail on `break`. Fast
  because it only mutates the diff.
- **Nightly:** full `dotnet stryker`, publish `StrykerOutput/**/reports/mutation-report.html` as a build
  artifact.
- **Dashboard reporter** (Stryker Dashboard) tracks the score trend across runs; wire the token as an
  OIDC/secret env var, never in config.
- Wire the actual pipeline steps via the stack's CI skill (`qa/cicd/dotnet/skills/ci-pipelines`) — this skill
  defines *what good looks like*, the CI skill defines *where it runs*. The mutation-score gate is a **quality
  gate**, distinct from the coverage gate; both can fail a build.

## Anti-patterns

| Smell | Why it's wrong | Fix |
|---|---|---|
| Treating mutation score like coverage and gaming it | A high score from `Is.Not.Null` everywhere is meaningless | Survivors are the signal; kill them with **value/behaviour assertions** |
| Running Stryker over the whole solution every PR | Multi-hour builds → team disables it | `--since:main` + unit-test-only scope |
| Including integration/Testcontainer tests in `test-projects` | Each mutant re-runs slow tests | Scope to fast unit-test projects only |
| Chasing 100% | **Equivalent mutants** (semantically identical mutations) can't be killed | Cap expectations at ~85–90%; `// Stryker disable` a proven-equivalent mutant with a reason |
| Leaving `break: 0` | The gate never fails — the score is decorative | Set `break` to a real floor and ratchet it |
| Unpinned tool version | Mutator set changes between releases → non-reproducible gate | Install `dotnet-stryker` into the **tool manifest**, pin the version |
| Adding Stryker before the unit suite has real assertions | You'll drown in survivors with no path forward | Get a green default run on critical classes first, then ratchet |
| Forcing Stryker.NET on a JVM/TS repo | Stryker.NET is .NET-only | Route to **PIT / StrykerJS** (top of this skill) |

## Suppressing a proven-equivalent mutant

When a survivor is genuinely equivalent (the mutation can't change observable behaviour), don't chase it —
suppress it **with a documented reason** so the gate stays honest:

```csharp
// Stryker disable once Arithmetic: overflow path is unreachable for validated inputs (see FooValidator)
var total = a + b;
```

Blanket-disabling to hit a number is the same sin as `Is.Not.Null` padding — every suppression needs a reason
a reviewer would accept.

## Sources

- [Stryker.NET — official docs](https://stryker-mutator.io/docs/stryker-net/introduction/) · [Configuration](https://stryker-mutator.io/docs/stryker-net/configuration/)
- [dotnet-stryker on NuGet (4.16.0)](https://www.nuget.org/packages/dotnet-stryker) · [Quickstart — C#](https://stryker-mutator.io/stryker-net/quickstart)
- [Mutation Testing with Stryker in .NET Projects — Hamed Shirbandi](https://medium.com/@hamed.shirbandi/mutation-testing-with-stryker-in-net-projects-ff1f05ddce8f)
