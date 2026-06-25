---
name: qa-mutation-testing-java
description: Use when measuring TEST QUALITY (not code coverage) for a Java 21 / Kotlin suite with mutation testing — run PIT/pitest to seed faults into JVM bytecode and prove the tests detect them, fail the build on a mutation-score threshold, and turn surviving mutants into missing-assertion findings. Triggers: "add mutation testing", "run pitest", "is my coverage real", "tests pass but catch nothing", "mutation score gate". JVM-only tool; the .NET sibling is Stryker.NET, the TS sibling is StrykerJS.
---

# QA — Mutation Testing (PIT / pitest, Java/Kotlin)

Mutation testing answers the question line/branch coverage **cannot**: **"if the production code were
wrong, would a test fail?"** Coverage proves a line *executed*; it says nothing about whether anything
*asserted* on the result. A test suite can have 95% line coverage and 0% real fault-detection — every test
calls the code and asserts nothing meaningful. Mutation testing is the only automated way to measure that
gap. **PIT (pitest)** is the state-of-the-art mutation engine for the JVM and the tool for this stack.

> **Stack scope:** PIT operates on **JVM bytecode** (Java, Kotlin), so this skill is the Java-stack
> implementation. The discipline is identical on other stacks but the tool changes — use the sibling skill,
> don't force PIT:
>
> | Stack | Tool | Skill |
> |---|---|---|
> | **Java / Kotlin** | **PIT (pitest)** | **this skill** |
> | **.NET (C#)** | **Stryker.NET** (`dotnet stryker`) | `qa/dotnet/skills/mutation-testing` |
> | **TypeScript / JS** | **StrykerJS** (`@stryker-mutator/core`) | `qa/typescript/skills/mutation-testing` |
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

## Running PIT when the tests live in a SEPARATE repository

This is the common shape here: the production code ("dev code") is in one repo, the test suite is in
another. Wiring PIT across that boundary is possible, but **first you must settle one question that decides
whether mutation testing is even applicable** — get it wrong and you'll burn days on a setup that can never
produce a useful result.

### ⚠️ Step 0 — does your separate-repo suite even drive PIT? (read before wiring anything)

PIT mutates **bytecode loaded into the same JVM as the tests** and re-runs only the tests that *cover* each
mutant. That means it can only be driven by tests that exercise the production code **in-process, as a
library** — they `new` up your classes / boot the app in the same JVM (Spring `@SpringBootTest`, `MockMvc`,
WebTestClient, RestAssured **against `MockMvc`/a same-JVM port**, plain component tests).

| Your separate-repo "API tests" are… | Can PIT use them? | What to do |
|---|---|---|
| **In-process** component/slice tests that load the prod classes (MockMvc / @SpringBootTest / RestAssured-vs-MockMvc) | ✅ Yes | Wire it — §A or §B below |
| **Black-box HTTP tests against a deployed/running service** (a different OS process / a URL) | ❌ **No** | PIT cannot mutate a service it reaches over the wire — every mutant would need a **rebuild + redeploy**, thousands of times. Mutation-test in the **dev repo against its own unit/component tests**; keep the black-box API suite as a separate coverage layer (it answers "does the deployed contract hold", not "are my unit assertions real"). |

If you're in the ❌ row, **stop** — the right home for PIT is the dev repo's build, mutating its own fast
unit tests. The cross-repo black-box suite is a different test pyramid layer and is measured differently.
If you're in the ✅ row, continue.

### The one flag that makes cross-repo work: mark the prod classes "mutable"

By default PIT only mutates the **current module's** compiled output (`target/classes` / `build/classes`).
When the production code arrives from *another repo* as a dependency jar, PIT sees it on the classpath but
**won't mutate it** unless you explicitly say so:

- **Maven:** `<mutableCodePaths>` → the dir/jar holding the production classes
- **Gradle:** `additionalMutableCodePaths` (+ `mainSourceSets`) → a `FileCollection` of the production classes/jar

This is *the* reason cross-repo PIT runs report "No mutations found" — the targetClasses glob matched, but the
classes weren't on the mutable list.

### Approach A — run PIT *from the test repo*, with the dev code as a dependency (recommended)

The test repo already depends on the production artifact (or you publish it). Add pitest to the **test
repo's** build, point `targetClasses` at the prod packages, and add the prod jar to the mutable paths. Supply
a checkout of the prod **sources at the same version** so the HTML report can link lines.

**Maven** (in the test repo's `pom.xml`):

```xml
<!-- the dev code under test, pulled as a normal dependency -->
<dependency><groupId>com.acme</groupId><artifactId>orders-service</artifactId><version>1.4.2</version></dependency>

<plugin>
  <groupId>org.pitest</groupId><artifactId>pitest-maven</artifactId><version>1.19.0</version>
  <dependencies>
    <dependency><groupId>org.pitest</groupId><artifactId>pitest-junit5-plugin</artifactId><version>1.2.1</version></dependency>
  </dependencies>
  <configuration>
    <targetClasses><param>com.acme.orders.*</param></targetClasses>     <!-- PROD packages (other repo) -->
    <targetTests><param>com.acme.apitests.*</param></targetTests>       <!-- THIS repo's in-process tests -->
    <mutableCodePaths>
      <!-- the jar that actually holds the prod classes; resolve from the local repo or an unpacked dir -->
      <param>${settings.localRepository}/com/acme/orders-service/1.4.2/orders-service-1.4.2.jar</param>
    </mutableCodePaths>
    <sourceDirs>
      <!-- a checkout of the prod sources at EXACTLY 1.4.2, so report line numbers map correctly -->
      <param>${project.basedir}/../orders-service/src/main/java</param>
    </sourceDirs>
    <mutators><mutator>DEFAULTS</mutator></mutators>
    <mutationThreshold>65</mutationThreshold>
    <outputFormats><param>HTML</param><param>XML</param></outputFormats>
  </configuration>
</plugin>
```

```bash
mvn test-compile org.pitest:pitest-maven:mutationCoverage   # run from the TEST repo
```

**Gradle** (in the test repo's `build.gradle.kts`) — declare a configuration whose files are the prod
classes, and hand it to `additionalMutableCodePaths`:

```kotlin
plugins { id("info.solidsoft.pitest") version "1.15.0" }

val devCode by configurations.creating          // resolves to the prod jar
dependencies {
    testImplementation("com.acme:orders-service:1.4.2")  // on the test classpath
    devCode("com.acme:orders-service:1.4.2")             // as mutable code
}

pitest {
    targetClasses.set(listOf("com.acme.orders.*"))
    targetTests.set(listOf("com.acme.apitests.*"))
    additionalMutableCodePaths.setFrom(devCode)   // <-- the key line: mutate the dependency
    junit5PluginVersion.set("1.2.1")
    mutationThreshold.set(65)
    outputFormats.set(listOf("HTML", "XML"))
}
```

> **Pin the version on both sides.** The `mutableCodePaths` jar and the `sourceDirs` checkout **must be the
> same revision** of the dev code, or PIT maps mutations to the wrong source lines and the report is garbage.
> Drive both from one artifact version.

### Approach B — both repos checked out locally, side by side (simplest)

When you have the **dev repo and the QA repo cloned next to each other** (`../orders-service` and `.`), you
don't need to publish or install anything — point PIT straight at the dev repo's **local build output** for
mutation and its **source tree** for the report. PIT mutates *bytecode*, so the dev repo must be **compiled
first** (`build/classes` / `target/classes` must exist and be current).

**Gradle — composite build (no install step).** Let Gradle wire the dev classes onto the test classpath via
`includeBuild`, then add its compiled output to the mutable set:

```kotlin
// settings.gradle.kts (QA repo)
includeBuild("../orders-service")
```
```kotlin
// build.gradle.kts (QA repo)
dependencies { testImplementation("com.acme:orders-service") }   // resolved from the included build
pitest {
    targetClasses.set(listOf("com.acme.orders.*"))
    targetTests.set(listOf("com.acme.apitests.*"))
    additionalMutableCodePaths.setFrom(files("../orders-service/build/classes/java/main"))
    junit5PluginVersion.set("1.2.1")
    mutationThreshold.set(65)
    outputFormats.set(listOf("HTML", "XML"))
}
```
```bash
./gradlew :orders-service:classes pitest   # compile dev code first, then mutate
```

**Maven — no composite build, so `install` the dev module once** (puts its classes on the test classpath as
a normal dependency), then point the mutable paths and sources at the local checkout:

```bash
mvn -f ../orders-service/pom.xml install -DskipTests   # compile + publish to local ~/.m2
```
```xml
<mutableCodePaths><param>${project.basedir}/../orders-service/target/classes</param></mutableCodePaths>
<sourceDirs><param>${project.basedir}/../orders-service/src/main/java</param></sourceDirs>
```

> **Keep the two trees in sync.** The classes PIT mutates and the sources it links in the report must be the
> **same revision** — same branch, and **recompiled** before each run. Edit dev code without rebuilding, or
> sit on mismatched branches, and mutations map to the wrong lines (or vanish as "No mutations found").

> **If the dev code and tests are actually in the *same* repo**, none of this applies — it's a plain
> multi-module build: PIT runs in the dev module against the test module's tests with ordinary
> `targetClasses` / `targetTests` (the §Setup config), no `mutableCodePaths` needed.

### Either approach: keep it scoped

Cross-repo runs are *more* expensive (you're mutating a whole external module), so the §Scope and speed rules
below matter even more — exclude slow integration tests, enable `withHistory`, and prefer diff-scoped runs
(`scmMutationCoverage` works against the **dev repo's** diff; pass its origin branch / last-commit range).

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
- [Mutation Testing with PITest — Baeldung](https://www.baeldung.com/java-mutation-testing-with-pitest)
- [Test Your Tests: Mutation Testing in Java with PIT — JAVAPRO](https://javapro.io/2026/01/21/test-your-tests-mutation-testing-in-java-with-pit/)
- [Mutation Testing With PIT — Java Code Geeks](https://www.javacodegeeks.com/2026/05/mutation-testing-with-pit-in-java-the-coverage-metric-youre-ignoring-that-actually-measures-test-quality.html)
- [arcmutate — Mutation Testing for Java & Kotlin](https://www.arcmutate.com/)
