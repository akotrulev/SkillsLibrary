---
name: benchmarks
description: Use when writing BenchmarkDotNet microbenchmarks in .NET or gating a hot path's speed and allocations in CI. Triggers "benchmark this method", "which is faster". Not for load (load-testing).
---

# QA — Microbenchmarks with BenchmarkDotNet (.NET)

Scaffolds **BenchmarkDotNet** microbenchmarks: a method or a small group of methods measured in-process, in a
Release build, with warm-up, many iterations and statistics, reporting time **and allocations** per operation. It
answers "is implementation B faster or leaner than A?" and "did this change make the hot path slower?".

## Microbenchmark or load test

| Question | Tool |
|---|---|
| Is this parser, mapper, serializer or LINQ chain faster / allocating less than the alternative? | **BenchmarkDotNet** |
| Did a change regress a hot method's time or allocations? | **BenchmarkDotNet**, compared against a stored baseline |
| What is the p95 latency of `POST /orders` at 200 requests/s? | `load-testing` (NBomber) — a microbenchmark has no network, no concurrency, no database |
| Where does the service spend its time under load? | `load-testing` + the service's traces; a profiler, not a benchmark |
| Is the SLO met? | `load-testing` against the SLO from `qa/_shared/performance` |

A microbenchmark result is a ratio between alternatives on one machine, never a production latency number.

## When NOT to use

- Endpoint latency, throughput, soak, spike → `load-testing`
- Fault tolerance under slow dependencies → `failure-injection-testing`
- Correctness of the code being measured → unit tests first (`be-dotnet` `unit-testing`); benchmark only code that
  is already tested

## Inputs needed

1. The method(s) to measure and the alternative or baseline to compare against.
2. The input sizes that matter (`[Params]`): the typical size and the large one production sees.

## Version lane

| Package | Version | Note |
|---|---|---|
| `BenchmarkDotNet` | **0.15.8** (net8 + netstandard2.0, verified on nuget.org 2026-11) | Pin in `Directory.Packages.props` |

The benchmark project targets the **same TFM as the code under test**. To compare runtimes, list them:
`--runtimes net8.0 net10.0` (the first is the baseline) — the project then multi-targets those TFMs.

## Project setup

A **separate console project** that references the code under test — never a test project, never the production
project:

```
benchmarks/
└── Ordering.Benchmarks/
    ├── Ordering.Benchmarks.csproj     <OutputType>Exe</OutputType>, <Nullable>enable</Nullable>, <IsPackable>false</IsPackable>
    ├── Program.cs
    └── Pricing/PriceCalculatorBenchmarks.cs
```

```csharp
using BenchmarkDotNet.Running;

BenchmarkSwitcher.FromAssembly(typeof(Program).Assembly).Run(args);
```

Run it **in Release, from the command line, with no debugger attached**:

```bash
dotnet run -c Release --project benchmarks/Ordering.Benchmarks -- --filter "*PriceCalculator*"
```

- BenchmarkDotNet refuses a non-optimized (Debug) assembly; never silence that with
  `ConfigOptions.DisableOptimizationsValidator`. Pressing F5 in the IDE attaches a debugger, which distorts the
  JIT and the timings — results from it are discarded.
- Close other heavy work on the machine; laptops on battery throttle. The results table prints the environment
  (CPU, runtime, GC mode) — keep it with any number you quote.

## A benchmark class

```csharp
using BenchmarkDotNet.Attributes;

namespace Ordering.Benchmarks.Pricing;

[MemoryDiagnoser]
public class PriceCalculatorBenchmarks
{
    private const int Seed = 20_261_114;

    private IReadOnlyList<OrderLine> _lines = [];

    [Params(10, 1_000)]
    public int LineCount { get; set; }

    [GlobalSetup]
    public void CreateLines()
    {
        var random = new Random(Seed);
        _lines = Enumerable.Range(0, LineCount)
            .Select(_ => new OrderLineBuilder().WithQuantity(random.Next(1, 20)).WithUnitPrice(random.Next(1, 500)).Build())
            .ToList();
    }

    [Benchmark(Baseline = true)]
    public decimal LinqSum() => PriceCalculator.TotalWithLinq(_lines);

    [Benchmark]
    public decimal LoopSum() => PriceCalculator.TotalWithLoop(_lines);
}
```

- **`[MemoryDiagnoser]`** on every class: allocations per operation are often the real finding, and unlike time
  they are deterministic.
- **`[GlobalSetup]` builds the inputs**; nothing in a `[Benchmark]` method creates test data, reads a file, or
  calls the network. Inputs come from a fixed seed so every run measures the same data.
- **`[Params]`** for input sizes; each value is a separate row. Keep the matrix small — every combination is a
  full benchmark run.
- **`Baseline = true`** on the current implementation; the `Ratio` column then reads directly as "B is 0.42× A".

### Keep the work from being optimized away

The JIT removes work whose result nobody uses. Every benchmark method **returns its result** (BenchmarkDotNet
consumes the return value), and:

- A lazy query is not work: returning `IEnumerable<T>` from `Where(...)` measures building the iterator.
  BenchmarkDotNet rejects deferred-execution return types; materialize (`.ToList()`) or consume it with a
  `Consumer` (`_lines.Where(...).Consume(_consumer)`, from `BenchmarkDotNet.Engines`).
- Do not compute a constant: an input the JIT can see at compile time (a literal, a `const`) can be folded. Read
  inputs from fields set in `[GlobalSetup]`.
- `[ReturnValueValidator]` on the class fails the run when the alternatives return different values — a fast
  wrong answer is not a win.
- Async benchmarks return `Task<T>` / `ValueTask<T>`; never block on them.

## Reading the results

| Column | Read it as |
|---|---|
| `Mean` / `Median` | Time per operation; prefer the median when the distribution is skewed |
| `Error`, `StdDev` | Half the 99.9% confidence interval, and the spread. Two means whose intervals overlap are **not** different |
| `Ratio` | Against the baseline row of the same `[Params]` value |
| `Allocated` | Bytes allocated per operation — compare exactly |
| `Gen0` / `Gen1` / `Gen2` | GC collections per 1,000 operations; any `Gen2` in a hot path is a finding |

A difference smaller than the error is noise. A claim like "B is faster" states the ratio, the input size, and the
environment line, and holds across at least two runs.

`--statisticalTest 5%` adds a Mann–Whitney test against the baseline row **within one run**, marking each row
`Faster`, `Slower` or `Same` — useful to stop reading noise as a win.

## Comparing runs in CI

Hosted CI runners share hardware, so timings drift by 10–20% between runs of the same code. Gate accordingly:

- **Allocations gate strictly** — any increase in `Allocated` on a gated benchmark fails.
- **Time gates loosely, and only on stable hardware** — a dedicated or self-hosted runner of one fixed machine
  type, comparing medians with a threshold (start at 10%). On shared runners, report time and do not fail on it.
- **The baseline comes from the default branch on the same runner type**, stored as an artifact, never from a
  developer laptop.
- `--job short` makes a quick smoke run (does every benchmark compile and execute) — never a gate.

```bash
dotnet run -c Release --project benchmarks/Ordering.Benchmarks -- \
  --filter "*" --exporters briefjson --artifacts "$RUNNER_TEMP/bench-current"
python3 ci/compare-benchmarks.py "$BASELINE_DIR/results" "$RUNNER_TEMP/bench-current/results" 0.10
```

`ci/compare-benchmarks.py` reads the `*-report-brief.json` files (`Benchmarks[].FullName`,
`Statistics.Median` in ns, `Memory.BytesAllocatedPerOperation`) and exits non-zero on a regression:

```python
import glob
import json
import sys


def load(directory):
    results = {}
    for path in glob.glob(f"{directory}/*-report-brief.json"):
        with open(path, encoding="utf-8") as report:
            for benchmark in json.load(report)["Benchmarks"]:
                memory = benchmark.get("Memory") or {}
                results[benchmark["FullName"]] = (
                    benchmark["Statistics"]["Median"],
                    memory.get("BytesAllocatedPerOperation"),
                )
    return results


baseline, current, threshold = load(sys.argv[1]), load(sys.argv[2]), float(sys.argv[3])
failures = []
for name, (median, allocated) in current.items():
    if name not in baseline:
        print(f"new, not gated: {name}")
        continue
    base_median, base_allocated = baseline[name]
    if median > base_median * (1 + threshold):
        failures.append(f"{name}: median {base_median:.1f} ns -> {median:.1f} ns")
    if allocated is not None and base_allocated is not None and allocated > base_allocated:
        failures.append(f"{name}: allocated {base_allocated} B -> {allocated} B")

print("\n".join(failures) or "No regression beyond the threshold.")
sys.exit(1 if failures else 0)
```

Upload `BenchmarkDotNet.Artifacts/results/` (the Markdown and JSON reports) on every run, so a failed gate
carries both tables. The pipeline wiring is `qa/cicd/dotnet/skills/ci-pipelines`.

## Rules

The standards this skill's output must meet are the qa-dotnet rule files, not a list here: `performance.md` and
`automation.md`. Read the project's copy in `.claude/rules/qa-dotnet/`, or the plugin's in
`qa/dotnet/skills/rules/` when the project has not installed them (`/qa-dotnet:rules` does). Where they and this
skill's recipes disagree, the rule files win.

## Output format

```
Created: benchmarks/<Area>.Benchmarks/<Area>.Benchmarks.csproj   Purpose: Release console host
Created: benchmarks/<Area>.Benchmarks/<Feature>Benchmarks.cs     Purpose: baseline + alternatives, [MemoryDiagnoser]
```

Then the results table (Median, Ratio, Allocated per `[Params]` value), the environment line, and a one-line
reading ("`LoopSum` is 0.31× the baseline at 1,000 lines and allocates 0 B vs 32 B").

## Anti-examples

- **A `Stopwatch` loop inside an NUnit test** — no warm-up, no statistics, JIT tiering mid-measurement, and a
  debugger-attached run looks the same as a real one. Use BenchmarkDotNet.
- **Benchmarking an HTTP endpoint** — that is a load test, with the network and the server in the number.
- **A benchmark that returns nothing** — the JIT is free to delete the work; the result is a few nanoseconds of
  nothing.
- **Gating on time on shared CI runners** — the gate fails on noise and gets disabled; gate allocations there.

## Handoffs

- Endpoint load and SLOs → `load-testing`, `qa/_shared/performance`
- The CI job and artifact upload → `qa/cicd/dotnet/skills/ci-pipelines`
- Making the benchmarked code testable / tested → `be-dotnet` `unit-testing`
