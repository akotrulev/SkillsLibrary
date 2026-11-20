# Running PIT when the tests live in a separate repository

This is the common shape here: the production code ("dev code") is in one repo, the test suite is in
another. Wiring PIT across that boundary is possible, but **first you must settle one question that decides
whether mutation testing is even applicable** — get it wrong and you'll burn days on a setup that can never
produce a useful result.

### Step 0 — does your separate-repo suite even drive PIT? (read before wiring anything)

PIT mutates **bytecode loaded into the same JVM as the tests** and re-runs only the tests that *cover* each
mutant. That means it can only be driven by tests that exercise the production code **in-process, as a
library** — they `new` up your classes / boot the app in the same JVM (Spring `@SpringBootTest`, `MockMvc`,
WebTestClient, RestAssured **against `MockMvc`/a same-JVM port**, plain component tests).

| Your separate-repo "API tests" are… | Can PIT use them? | What to do |
|---|---|---|
| **In-process** component/slice tests that load the prod classes (MockMvc / @SpringBootTest / RestAssured-vs-MockMvc) | ✅ Yes | Wire it — Approach A or B below |
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
> `targetClasses` / `targetTests` (the Setup config in `SKILL.md`), no `mutableCodePaths` needed.

### Either approach: keep it scoped

Cross-repo runs are *more* expensive (you're mutating a whole external module), so the "Scope and speed" rules in `SKILL.md`
matter even more — exclude slow integration tests, enable `withHistory`, and prefer diff-scoped runs
(`scmMutationCoverage` works against the **dev repo's** diff; pass its origin branch / last-commit range).
