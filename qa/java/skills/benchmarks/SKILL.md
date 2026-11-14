---
name: benchmarks
description: Use when writing JMH microbenchmarks in Java or gating a hot path's speed and allocations in CI. Triggers "benchmark this method", "which is faster". Not for load (load-testing).
---

# QA — Microbenchmarks with JMH (Java 21)

Scaffolds **JMH** microbenchmarks: a method or a small group of methods measured in forked JVMs, with warm-up,
many iterations and statistics, reporting time **and allocations** per operation. It answers "is implementation B
faster or leaner than A?" and "did this change make the hot path slower?".

## Microbenchmark or load test

| Question | Tool |
|---|---|
| Is this parser, mapper, serializer or stream pipeline faster / allocating less than the alternative? | **JMH** |
| Did a change regress a hot method's time or allocations? | **JMH**, compared against a stored baseline |
| What is the p95 latency of `POST /orders` at 200 requests/s? | `load-testing` (Gatling) — a microbenchmark has no network, no concurrency, no database |
| Where does the service spend its time under load? | `load-testing` + the service's traces and a profiler, not a benchmark |
| Is the SLO met? | `load-testing` against the SLO from `qa/_shared/performance` |

A microbenchmark result is a ratio between alternatives on one machine and one JDK, never a production latency
number.

## When NOT to use

- Endpoint latency, throughput, soak, spike → `load-testing`
- Fault tolerance under slow dependencies → `failure-injection-testing`
- Correctness of the code being measured → unit tests first (`be-java` `unit-testing`); benchmark only code that
  is already tested

## Inputs needed

1. The method(s) to measure and the alternative or baseline to compare against.
2. The input sizes that matter (`@Param`): the typical size and the large one production sees.

## Version lane

| Dependency | Version | Note |
|---|---|---|
| JMH (`org.openjdk.jmh:jmh-core`, `jmh-generator-annprocess`) | **1.37** (verified on Maven Central, 2026-11) | Set through the plugin's `jmhVersion`; never left to the plugin's default |
| Gradle plugin `me.champeau.jmh` | **0.7.4** (verified on the Gradle Plugin Portal, 2026-11) | Gradle 8 needs 0.7.0+; adds the `jmh` source set and the `jmh` / `jmhJar` tasks |

The benchmarks run on the **same JDK as production** — the toolchain the module already declares. A result from
another JDK major measures another JIT.

## Project setup

The plugin goes on the module that owns the code under test, and benchmarks live in their own source set — never in
`src/test`, never in `src/main`:

```
ordering/
├── build.gradle.kts
└── src/
    ├── main/java/com/acme/ordering/pricing/PriceCalculator.java
    └── jmh/java/com/acme/ordering/pricing/PriceCalculatorBenchmark.java
```

```kotlin
// ordering/build.gradle.kts
plugins {
    id("me.champeau.jmh") version "0.7.4"
}

jmh {
    jmhVersion = "1.37"
    includeTests = true
}
```

The `jmh` source set sees the main classes, and with `includeTests` the test builders too, so benchmark inputs are
built the way the tests build them. The annotation processor generates the harness. Build the self-contained benchmark jar and run it **from the command line, with no IDE or
debugger attached**:

```bash
./gradlew :ordering:jmhJar
java -jar ordering/build/libs/ordering-*-jmh.jar PriceCalculator -prof gc
```

- The positional argument is a regex over benchmark names; `-l` lists them.
- A run inside the IDE or with an agent attached measures the agent too — results from it are discarded.
- Close other heavy work on the machine; laptops on battery throttle. The run header prints the JDK, VM and options —
  keep it with any number you quote.

## A benchmark class

```java
package com.acme.ordering.pricing;

import static com.acme.ordering.builders.OrderLineBuilder.anOrderLine;

import java.math.BigDecimal;
import java.util.List;
import java.util.Random;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Fork;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Measurement;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.OutputTimeUnit;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Warmup;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 5, time = 1)
@Fork(2)
@State(Scope.Benchmark)
public class PriceCalculatorBenchmark {
    private static final long SEED = 20_261_114L;

    @Param({"10", "1000"})
    int lineCount;

    private List<OrderLine> lines;

    @Setup(Level.Trial)
    public void createLines() {
        var random = new Random(SEED);
        lines = IntStream.range(0, lineCount)
            .mapToObj(i -> anOrderLine()
                .withQuantity(random.nextInt(1, 20))
                .withUnitPrice(BigDecimal.valueOf(random.nextInt(1, 500)))
                .build())
            .toList();
    }

    @Benchmark
    public BigDecimal streamSum() {
        return PriceCalculator.totalWithStream(lines);
    }

    @Benchmark
    public BigDecimal loopSum() {
        return PriceCalculator.totalWithLoop(lines);
    }
}
```

- **The run shape lives on the class** — `@Warmup`, `@Measurement`, `@Fork`, `@BenchmarkMode`, `@OutputTimeUnit` —
  so every run, local or CI, measures the same thing. Command-line flags override them for a quick look only.
- **`@Fork` is at least 1, and 2+ for anything quoted.** `-f 0` runs inside the launcher's JVM with its profile
  pollution; separate forks also expose run-to-run variance that one JVM hides.
- **`@State` holds the inputs; `@Setup(Level.Trial)` builds them** from a fixed seed, so every fork measures the same
  data. Nothing in a `@Benchmark` method creates test data, reads a file, or calls the network. `Level.Invocation`
  setup adds timer overhead to every call — avoid it unless the operation mutates its input.
- **`@Param`** for input sizes; each value is a separate row. Keep the matrix small — every combination is a full run.
- **The current implementation is the first method, its alternatives beside it**; the reading compares rows with the
  same `@Param` value.
- **Alternatives return the same answer** — a fast wrong answer is not a win. A unit test (or a property test) in
  `be-java` `unit-testing` asserts the implementations agree before the benchmark is trusted.

### Keep the work from being optimized away

The JIT removes work whose result nobody uses and folds values it can see at compile time:

- Every benchmark method **returns its result**; JMH consumes the return value.
- More than one result, or a `void` operation's effect: take a `Blackhole` parameter and `bh.consume(...)` each one.
- **No loop inside a `@Benchmark` method** to "make it measurable" — JMH already calls it in a loop, and a hand loop
  invites unrolling and hoisting. A batch operation measures the batch.
- **Read inputs from `@State` fields, never from `static final` constants or literals** — the JIT can constant-fold
  those.
- A lazy result is not work: returning a `Stream` measures building the pipeline. Terminate it (`.toList()`, `.sum()`).

## Reading the results

```
Benchmark                                         (lineCount)  Mode  Cnt     Score     Error   Units
PriceCalculatorBenchmark.loopSum                         1000  avgt   10  4210.551 ±  61.208   ns/op
PriceCalculatorBenchmark.loopSum:gc.alloc.rate.norm      1000  avgt   10 64016.004 ±   0.001    B/op
PriceCalculatorBenchmark.streamSum                       1000  avgt   10  7932.117 ± 140.775   ns/op
PriceCalculatorBenchmark.streamSum:gc.alloc.rate.norm    1000  avgt   10 64184.011 ±   0.002    B/op
```

| Column / row | Read it as |
|---|---|
| `Score` | Time per operation (`avgt`) averaged over every measured iteration of every fork |
| `Error` | Half the 99.9% confidence interval. Two scores whose intervals overlap are **not** different |
| `Cnt` | Measured iterations × forks — fewer than 10 is too few to quote |
| `:gc.alloc.rate.norm` | Bytes allocated per operation (needs `-prof gc`) — nearly deterministic, so compare closely; the row is absent when the benchmark allocated nothing |
| `:gc.count`, `:gc.time` | GCs during the measurement; any in a hot path's run is a finding |

JMH prints no ratio column: the ratio is `Score(B) ÷ Score(A)` for rows with the same `@Param` value. A claim like
"B is faster" states the ratio, the input size, and the JDK line, and holds across at least two runs.

## Comparing runs in CI

Hosted CI runners share hardware, so timings drift by 10–20% between runs of the same code. Gate accordingly:

- **Allocations gate strictly** — any increase in `gc.alloc.rate.norm` on a gated benchmark fails, compared after
  rounding to whole bytes (the per-op figure carries sub-byte noise).
- **Time gates loosely, and only on stable hardware** — a dedicated or self-hosted runner of one fixed machine type,
  comparing medians with a threshold (start at 10%). On shared runners, report time and do not fail on it.
- **The baseline comes from the default branch on the same runner type**, stored as an artifact, never from a
  developer laptop.
- `-f 1 -wi 1 -i 1` makes a quick smoke run (does every benchmark compile and execute) — never a gate.

```bash
./gradlew :ordering:jmhJar
java -jar ordering/build/libs/ordering-*-jmh.jar -prof gc -rf json -rff "$RUNNER_TEMP/jmh-current.json"
python3 ci/compare-benchmarks.py "$BASELINE_DIR/jmh-results.json" "$RUNNER_TEMP/jmh-current.json" 0.10
```

`ci/compare-benchmarks.py` reads the JMH JSON (`benchmark`, `params`, `primaryMetric.scorePercentiles["50.0"]`,
`secondaryMetrics["gc.alloc.rate.norm"].score`) and exits non-zero on a regression:

```python
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as report:
        runs = json.load(report)
    results = {}
    for run in runs:
        params = ",".join(f"{key}={value}" for key, value in sorted(run.get("params", {}).items()))
        allocated = run["secondaryMetrics"].get("gc.alloc.rate.norm", {"score": 0.0})["score"]
        results[f"{run['benchmark']}({params})"] = (run["primaryMetric"]["scorePercentiles"]["50.0"], round(allocated))
    return results


baseline, current, threshold = load(sys.argv[1]), load(sys.argv[2]), float(sys.argv[3])
failures = []
for name, (median, allocated) in current.items():
    if name not in baseline:
        print(f"new, not gated: {name}")
        continue
    base_median, base_allocated = baseline[name]
    if median > base_median * (1 + threshold):
        failures.append(f"{name}: median {base_median:.1f} -> {median:.1f} ns/op")
    if allocated > base_allocated:
        failures.append(f"{name}: allocated {base_allocated} B/op -> {allocated} B/op")

print("\n".join(failures) or "No regression beyond the threshold.")
sys.exit(1 if failures else 0)
```

A missing `gc.alloc.rate.norm` counts as 0 B/op, which is right only because the gate run always passes `-prof gc`.
Upload the JSON and the console output on every run, so a failed gate carries both. The pipeline wiring is
`qa/cicd/java/skills/ci-pipelines`.

## Handing a slow benchmark to the profiler

A benchmark says *that* B is slower; a profiler says *where*. JMH attaches one to the forked JVM:

```bash
java -jar ordering/build/libs/ordering-*-jmh.jar PriceCalculatorBenchmark.streamSum -p lineCount=1000 \
  -prof jfr:dir=build/jmh-profiles
java -jar ordering/build/libs/ordering-*-jmh.jar PriceCalculatorBenchmark.streamSum -p lineCount=1000 \
  -prof "async:libPath=/opt/async-profiler/lib/libasyncProfiler.so;output=flamegraph;dir=build/jmh-profiles"
```

- **`-prof jfr`** needs nothing installed: a `profile.jfr` per fork under `dir`, opened in JDK Mission Control or
  `jfr print`.
- **`-prof async`** gives the flame graph through async-profiler's native library (`event=alloc` for allocation
  pressure, `event=wall` when threads wait).
- Narrow the run to the one benchmark and `@Param` row first; a profile across the whole class mixes them.
- Reading JFR and async-profiler output, and what to attach to the bug, is
  `qa/_shared/performance/references/profiling.md`.

## Rules

The standards this skill's output must meet are the qa-java rule files, not a list here: `qa-java-perf.md`, plus
`qa-java-suite.md` for the build. Read the project's copy in `.claude/rules/qa-java/`, or the plugin's in
`qa/java/skills/rules/` when the project has not installed them (`/qa-java:rules` does). Where they and this skill's
recipes disagree, the rule files win.

## Output format

```
Edited:  <module>/build.gradle.kts                                 Purpose: me.champeau.jmh + jmhVersion
Created: <module>/src/jmh/java/<package>/<Feature>Benchmark.java   Purpose: current + alternatives, fixed seed, @Param sizes
```

Then the results table (Score ± Error and `gc.alloc.rate.norm` per `@Param` value), the JDK line, and a one-line
reading ("`loopSum` is 0.53× `streamSum` at 1,000 lines and allocates 168 B less per op").

## Anti-examples

- **A `System.nanoTime()` loop inside a TestNG or JUnit test** — no warm-up, no forks, no statistics, JIT
  compilation mid-measurement. Use JMH.
- **Benchmarking an HTTP endpoint** — that is a load test, with the network and the server in the number.
- **A benchmark that returns nothing and consumes nothing** — the JIT is free to delete the work; the result is a
  few nanoseconds of nothing.
- **`@Fork(0)` to make it faster** — one polluted JVM; the numbers do not transfer.
- **Gating on time on shared CI runners** — the gate fails on noise and gets disabled; gate allocations there.

## Handoffs

- Endpoint load and SLOs → `load-testing`, `qa/_shared/performance`
- Where the time goes → `qa/_shared/performance/references/profiling.md`
- The CI job and artifact upload → `qa/cicd/java/skills/ci-pipelines`
- Making the benchmarked code testable / tested → `be-java` `unit-testing`
