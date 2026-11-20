---
name: test-quality-check
description: Use when measuring test quality in a Java suite with mutation testing (PIT), gating on mutation score. Triggers "add mutation testing". Not for pruning low-value tests (test-audit).
disable-model-invocation: true
---

# QA — Mutation Testing (PIT / pitest, Java/Kotlin)

Mutation testing answers the question line/branch coverage **cannot**: **"if the production code were
wrong, would a test fail?"** Coverage proves a line *executed*; it says nothing about whether anything
*asserted* on the result. A test suite can have 95% line coverage and 0% real fault-detection — every test
calls the code and asserts nothing meaningful. Mutation testing is the only automated way to measure that
gap. **PIT (pitest)** is the state-of-the-art mutation engine for the JVM and the tool for this stack.

Mutation proves a test catches faults; `test-audit` proves it is worth keeping.

> **Stack scope:** PIT operates on **JVM bytecode** (Java, Kotlin), so this skill is the Java-stack
> implementation. The discipline is identical on other stacks but the tool changes — use the sibling skill,
> don't force PIT:
>
> | Stack | Tool | Skill |
> |---|---|---|
> | **Java / Kotlin** | **PIT (pitest)** | **this skill** |
> | **.NET (C#)** | **Stryker.NET** (`dotnet stryker`) | `qa/dotnet/skills/test-quality-check` |
> | **TypeScript / JS** | **StrykerJS** (`@stryker-mutator/core`) | no house skill yet |
>
> The threshold philosophy, the "surviving mutant = missing assertion" workflow, the scope/incremental
> discipline, and the anti-patterns below carry over to the siblings — only the tool invocation differs.

## How it works (and why the score means something)

PIT takes your **already-passing** unit tests, then systematically rewrites your production bytecode to
introduce small faults — a **mutant** — and re-runs the tests that cover that line:

- A mutant is **killed** if at least one test now **fails** → the suite detected the fault. Good.
- A mutant **survives** if all tests still **pass** → the suite did **not** notice the code changed. That is
  a real, located **gap in your assertions** (or dead code).

**Mutation score = killed mutants / total non-equivalent mutants.** Unlike coverage, this is a *causal*
metric: it can only go up by writing a test that actually catches a behavioural change. PIT is fast because
it works on bytecode and uses coverage data to run **only the tests that reach each mutant**, not the whole
suite per mutant.

### Example of a surviving mutant

```java
int applyDiscount(int price, int pct) {
    return price - (price * pct / 100);   // PIT mutates '-' → '+' (Math mutator)
}
```

```java
@Test void discountsPrice() {
    var result = svc.applyDiscount(100, 10);
    assertThat(result).isNotNull();   // executes the line (100% coverage) but never checks the value
}
```

The `+`/`-` mutant **survives** — the test asserts nothing about the number. Coverage says "done"; PIT says
"your test is blind". The fix is `assertThat(result).isEqualTo(90)`. **That is the entire value of the tool.**

## Mutators — what faults PIT seeds

Mutators are grouped; you select a group and/or individual operators. **Use `DEFAULTS` to start, move to
`STRONGER` once green, and avoid `ALL`** (it adds noise and equivalent mutants).

| Group | Contains | Use when |
|---|---|---|
| **DEFAULTS** | Conditionals boundary (`>`→`>=`), negate conditionals (`==`→`!=`), math (`+`→`-`), increments (`++`→`--`), invert negatives, void-method-calls, empty/false/true/null/primitive **returns** | **Start here.** Fast, low false-positive rate. |
| **STRONGER** | DEFAULTS + remove-conditionals, switch, experimental return-vals, etc. | After DEFAULTS is green and you want more rigour. |
| **ALL** | Every mutator incl. experimental | Rarely. High equivalent-mutant + noise rate. |

You can tune individual mutators (e.g. add `REMOVE_CONDITIONALS`, drop `INVERT_NEGS`) — keep the set in the
build file under version control so the gate is reproducible.

## Setup — PIT for JVM

### Maven (`pitest-maven`)

```xml
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <version>1.19.0</version> <!-- pin it; mutator behaviour changes between releases -->
  <dependencies>
    <!-- REQUIRED for JUnit 5 / Jupiter; omit only for legacy JUnit 4 -->
    <dependency>
      <groupId>org.pitest</groupId>
      <artifactId>pitest-junit5-plugin</artifactId>
      <version>1.2.1</version>
    </dependency>
  </dependencies>
  <configuration>
    <targetClasses><param>com.acme.orders.*</param></targetClasses>      <!-- scope to YOUR code -->
    <targetTests><param>com.acme.orders.*Test</param></targetTests>
    <excludedTestClasses><param>*IT</param><param>*IntegrationTest</param></excludedTestClasses>
    <mutators><mutator>DEFAULTS</mutator></mutators>
    <mutationThreshold>65</mutationThreshold>   <!-- fail build below this score -->
    <coverageThreshold>80</coverageThreshold>
    <withHistory>true</withHistory>             <!-- incremental: skip unchanged code next run -->
    <outputFormats><param>HTML</param><param>XML</param></outputFormats>
  </configuration>
</plugin>
```

```bash
mvn test-compile org.pitest:pitest-maven:mutationCoverage   # full run
# Report → target/pit-reports/index.html ; XML for CI parsing
```

### Gradle (`gradle-pitest-plugin`, Kotlin DSL)

```kotlin
plugins { id("info.solidsoft.pitest") version "1.15.0" }

pitest {
    targetClasses.set(listOf("com.acme.orders.*"))
    excludedTestClasses.set(listOf("*IT", "*IntegrationTest"))
    mutators.set(listOf("DEFAULTS"))
    mutationThreshold.set(65)
    coverageThreshold.set(80)
    withHistory.set(true)
    junit5PluginVersion.set("1.2.1")   // for JUnit 5
    outputFormats.set(listOf("HTML", "XML"))
}
```

```bash
./gradlew pitest    # report → build/reports/pitest/
```

> **Kotlin:** add the `pitest-kotlin` plugin so PIT skips Kotlin-generated synthetic constructs (null
> checks, `when` exhaustiveness) that otherwise show up as un-killable / equivalent mutants.

## Running PIT when the tests live in a separate repository

Production code in one repo and the suite in another: read `references/separate-repo.md` first. Its Step 0 decides whether PIT applies at all (only in-process tests can drive it; black-box HTTP tests against a deployed service cannot), then Approach A runs PIT from the test repo and Approach B from two local checkouts. The dev code and the tests in one repo need none of it: PIT runs in the dev module with the Setup config above.

## Scope and speed — the difference between "practical" and "abandoned"

Mutation testing gets a reputation for being slow **only when mis-scoped**. Three rules keep PIT fast enough
for CI:

1. **Scope to changed/critical code, not the whole repo.** Use **`scmMutationCoverage`** to mutate only
   classes flagged ADDED/MODIFIED vs an origin branch — a developer pays the mutation cost only for code they
   touched. Reserve full `mutationCoverage` for a nightly/main-branch run.

   ```bash
   mvn org.pitest:pitest-maven:scmMutationCoverage \
       -DoriginBranch=origin/main -DanalyseLastCommit=true
   ```

2. **Exclude integration / Testcontainer / E2E tests** (`excludedTestClasses` above). They are slow by
   design; re-running them thousands of times per campaign is *the* reason PIT seems impractical. **PIT
   belongs on your fast, isolated unit tests** — the ones with real assertions.
3. **Enable `withHistory`** — PIT stores hashes of test+production classes and skips re-mutating unchanged
   code on the next run (incremental analysis).

Also tune `timeoutConstant`/`timeoutFactor` only if you see legitimate slow tests flagged as `TIMED_OUT`
(an infinite-loop mutant looks like a timeout — that is a *kill*, not an error).

## Threshold philosophy — ratchet, never big-bang

| Don't | Do |
|---|---|
| Set `mutationThreshold` to 85 on a legacy codebase day one | **Start at 60–65%**, fail the build there, **raise it as you kill survivors** |
| Chase 100% (equivalent mutants make it unreachable) | Treat **85–90% as excellent** for critical code |
| Run PIT on everything every PR | `scmMutationCoverage` on PRs, full run nightly |

The threshold is a **ratchet**: each PR may only raise it. A surviving-mutant report is a **to-do list of
missing assertions**, prioritised by where your tests are blind — not a vanity number.

## CI integration

- **PR gate:** `scmMutationCoverage` against `origin/main`, fail on threshold. Fast because it only mutates
  the diff.
- **Nightly:** full `mutationCoverage` with `withHistory`, publish the HTML report as a build artifact.
- **Parse the XML** (`mutations.xml`) for trend dashboards; the HTML report is for humans triaging survivors.
- Wire the actual pipeline steps via the stack's CI skill (`qa/cicd/<stack>/skills/ci-pipelines`) — this
  skill defines *what good looks like*, the CI skill defines *where it runs*.

> **arcmutate** (commercial, same authors) extends PIT with first-class Git/PR integration, Kotlin, Spring,
> and faster large-codebase runs. Reach for it when OSS PIT's `scmMutationCoverage` isn't fast enough at
> scale — but the OSS plugin covers the vast majority of projects. Don't introduce a paid dependency before
> you've hit its limit.

## Anti-patterns

| Smell | Why it's wrong | Fix |
|---|---|---|
| Treating mutation score like coverage and gaming it | A high score from `assertThat(x).isNotNull()` everywhere is meaningless | Survivors are the signal; kill them with **value/behaviour assertions** |
| Running PIT over the entire repo every PR | Multi-hour builds → team disables it | `scmMutationCoverage` + `withHistory` + unit-test-only scope |
| Including integration/Testcontainer tests in scope | Each mutant re-runs slow tests | `excludedTestClasses` |
| Chasing 100% | **Equivalent mutants** (semantically identical mutations) can't be killed | Cap expectations at ~85–90%; mark known-equivalent survivors as accepted |
| Unpinned plugin version | Mutator set changes between releases → non-reproducible gate | Pin the plugin **and** the junit5/kotlin sub-plugin |
| Adding PIT before the unit suite has real assertions | You'll drown in survivors with no path forward | Get a green DEFAULTS run on critical classes first, then ratchet |
| Forcing PIT on a .NET/TS repo | PIT is JVM-bytecode only | Route to **Stryker.NET / StrykerJS** (top of this skill) |

## Sources

- [PIT Mutation Testing — official site](https://pitest.org/) · [hcoles/pitest (GitHub)](https://github.com/hcoles/pitest)
- [gradle-pitest-plugin (szpak)](https://github.com/szpak/gradle-pitest-plugin) · [pitest-kotlin](https://github.com/pitest/pitest-kotlin)
- [Mutation Testing with PITest — Baeldung](https://www.baeldung.com/java-test-quality-check-with-pitest)
- [Test Your Tests: Mutation Testing in Java with PIT — JAVAPRO](https://javapro.io/2026/01/21/test-your-tests-test-quality-check-in-java-with-pit/)
- [Mutation Testing With PIT — Java Code Geeks](https://www.javacodegeeks.com/2026/05/test-quality-check-with-pit-in-java-the-coverage-metric-youre-ignoring-that-actually-measures-test-quality.html)
- [arcmutate — Mutation Testing for Java & Kotlin](https://www.arcmutate.com/)
