---
name: benchmarks
description: Use when writing Vitest micro-benchmarks (vitest bench) in TypeScript or gating a hot path's speed in CI. Triggers "benchmark this function", "which is faster". Not for load (load-testing).
---

# QA — Micro-benchmarks with Vitest bench (TypeScript)

Scaffolds **Vitest benchmarks**: a function or a small group of functions measured in-process, with warm-up, many
iterations and statistics, by Vitest's built-in provider (tinybench). It answers "is implementation B faster than
A?" and "did this change make the hot path slower?".

## Micro-benchmark or load test

| Question | Tool |
|---|---|
| Is this parser, mapper, serializer or array pipeline faster than the alternative? | **`vitest bench`** |
| Did a change regress a hot function's time? | **`vitest bench`**, compared against a stored baseline |
| What is the p95 latency of `POST /orders` at 200 requests/s? | `load-testing` (k6) — a micro-benchmark has no network, no concurrency, no database |
| Where does the service spend its time under load? | `load-testing` + the service's traces; a profiler, not a benchmark |
| Is the SLO met? | `load-testing` against the SLO from `qa/_shared/performance` |

A benchmark result is a ratio between alternatives on one machine, never a production latency number.

## When NOT to use

- Endpoint latency, throughput, soak, spike → `load-testing`
- Fault tolerance under slow dependencies → `failure-injection-testing`
- Correctness of the code being measured → unit tests first (`be-node` `unit-testing`); benchmark only code that is
  already tested, including a test that the alternatives return the same value — a fast wrong answer is not a win

## Inputs needed

1. The function(s) to measure and the alternative or baseline to compare against.
2. The input sizes that matter: the typical size and the large one production sees.

## Version lane

| Package | Version | Note |
|---|---|---|
| `vitest` | **5.1.0** (Node 22.12+ / 24, verified on npm 2026-11) | `bench` is a **test-context fixture**: `test('…', async ({ bench }) => …)` |
| `vitest` 3.x / 4.x | 4.1.12 latest 4.x | `bench` is a **top-level import** with `--outputJson` / `--compare` (§ Vitest 3–4 lane) |
| `tinybench` | 6.2.3 | Vitest 5's built-in provider; a dependency of `vitest`, never installed beside it |

Detect the Vitest major first and write the matching lane. Vitest 5 **removed** module-scope `bench()`,
`bench.skip/only/todo`, `benchmark.outputFile`, `--outputJson` and `--compare`; moving a suite from 4 to 5 rewrites
every bench file, so it is its own change, never a side effect of adding one benchmark.

## Project setup

Benchmark files match `benchmark.include` (default `**/*.{bench,benchmark}.?(c|m)[jt]s?(x)`) and run in their own
project: plain `vitest` skips them, `vitest bench` runs only them, files one at a time, tests in a file in sequence.
Keep them out of `src/` and away from the unit tests:

```
benchmarks/
└── pricing/
    └── price-calculator.bench.ts
```

```bash
npx vitest bench --run                       # all benchmarks
npx vitest bench --run pricing -t "order total"
```

- **Measure what ships.** Vitest's module runner turns every import into a getter; called millions of times, the
  getter is the measurement. Import the **built** output (`dist/`, or the package name that resolves to it), or set
  `experimental: { viteModuleRunner: false }` in the bench project (Node then loads the files natively, so `.ts`
  needs Node's type stripping, 22.18+ / 24). Vitest prints a warning when it sees excessive getter calls — never
  silence it with `benchmark.suppressExportGetterWarnings` while the overhead is still there.
- **No inspector attached.** `--inspect` or an IDE debug run changes how V8 optimizes; discard those numbers.
- Close other heavy work; a laptop on battery throttles. Quote every number with the machine, Node version and
  Vitest version it came from.

## A benchmark file (Vitest 5)

```ts
import { expect, test } from 'vitest';
import { totalWithLoop, totalWithReduce } from '../../dist/pricing/price-calculator.js';
import { OrderLineBuilder } from '../../tests/builders/order-line.builder.js';
import type { OrderLine } from '../../dist/pricing/order-line.js';

const loopTotal = totalWithLoop;
const reduceTotal = totalWithReduce;

function linesOf(count: number): OrderLine[] {
  return Array.from({ length: count }, (_, index) =>
    new OrderLineBuilder().withQuantity((index % 19) + 1).withUnitPriceMinor(((index * 37) % 499) + 1).build(),
  );
}

test.for([10, 1_000])('order total over %i lines', async (lineCount, { bench }) => {
  const lines = linesOf(lineCount);
  let checksum = 0;

  await bench.compare(
    bench('reduce', { writeResult: `./bench-results/order-total-reduce-${lineCount}.json` }, () => {
      checksum += reduceTotal(lines);
    }),
    bench('loop', { writeResult: `./bench-results/order-total-loop-${lineCount}.json` }, () => {
      checksum += loopTotal(lines);
    }),
    { time: 1_000, warmupTime: 500 },
  );

  expect(checksum).toBeGreaterThan(0);
});
```

- **Inputs are built before the benchmark, deterministically.** Nothing inside a bench function creates test
  data, reads a file or calls the network; the inputs come from index arithmetic (Node has no seeded
  `Math.random`), so every run measures the same data.
- **`test.for` for input sizes**; each value is its own test and its own table. Keep the matrix small — every
  combination is a full run.
- **`bench.compare`** interleaves the alternatives' iterations, so throttling and GC pressure hit both alike. Run
  options (`time`, `iterations`, `warmupTime`, `warmupIterations`) go last; per-bench options (`beforeEach`,
  `writeResult`) go **second**, `bench(name, options, fn)` — options after the function throw.
- **Local references** (`loopTotal`) bypass the module getter on every call.
- **`writeResult`** writes the result (`latency`, `throughput`, `period`, `totalTime`) after each successful run;
  the CI gate below reads these files.

### Keep the work from being optimized away

V8 removes work whose result nobody uses. Every bench function **feeds its result into something observable** — the
test-local `checksum` above, asserted after the run — and:

- **Consistent shapes.** Inputs whose objects differ in shape (some with an optional field, some without) make V8
  deoptimize mid-run; build every input through the same builder path.
- **Allocate outside the measured function.** An array built inside the bench function adds GC noise to every
  sample. Per-iteration state that must be fresh (a copy to sort in place) goes in the per-bench `beforeEach`.
- **No constant inputs.** A literal the JIT can see is folded; read inputs from variables built before the run.
- **Async functions are awaited** — return the promise from the bench function; never fire and forget.

### Asserting relative speed in one run

When "B stays faster than A" is a requirement, assert it **within one run**, where both share the machine:

```ts
const result = await bench.compare(
  bench('reduce', () => {
    checksum += reduceTotal(lines);
  }),
  bench('loop', () => {
    checksum += loopTotal(lines);
  }),
);

expect(result.get('loop')).toBeFasterThan(result.get('reduce'), { delta: 0.2 });
```

`toBeFasterThan` / `toBeSlowerThan` compare mean latency; `delta: 0.2` demands at least a 20% gap, which keeps noise
from passing or failing it. No `retry` on a benchmark test: a claim that needs retries to pass is measuring noise —
widen the delta or drop the claim.

## Reading the results

| Field | Read it as |
|---|---|
| `throughput.mean` | Operations per second (the table's ops/sec column) |
| `latency.mean` / `latency.p50` | Milliseconds per operation; prefer the median (`p50`) when the distribution is skewed |
| `latency.rme`, `latency.moe` | Relative margin of error (%) and its absolute value. Two means whose `mean ± moe` ranges overlap are **not** different |
| `latency.p99` | Tail per operation — GC pauses and deoptimizations show up here first |
| `latency.samplesCount` | Samples behind the numbers; a few dozen on a slow function means a noisy result — raise `time` |

A difference smaller than the margin of error is noise. A claim like "B is faster" states the ratio, the input size
and the environment, and holds across at least two runs. Vitest's benchmark measures **time only**; allocation
questions go to the profiler (§ Handoff to the profiler).

## Comparing runs in CI

Hosted runners share hardware, so timings drift by 10–20% between runs of the same code, and there is no
deterministic allocation figure to gate on instead. Gate accordingly:

- **Time gates only on stable hardware** — a dedicated or self-hosted runner of one fixed machine type, comparing
  medians with a threshold (start at 10%). On shared runners, report time and do not fail on it.
- **The baseline comes from the default branch on the same runner type**, stored as a build artifact, never from a
  developer laptop and never committed from one.
- The in-run `toBeFasterThan` claim above is the one timing assertion that is safe on shared runners.

```bash
npx vitest bench --run --reporter=default --reporter=json --outputFile=bench-results/report.json
node ci/compare-benchmarks.mjs "$BASELINE_DIR" bench-results 0.10
```

`ci/compare-benchmarks.mjs` reads the `writeResult` files of both runs and exits non-zero on a regression:

```js
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const [baselineDir, currentDir, thresholdArg] = process.argv.slice(2);
const threshold = Number(thresholdArg);

const load = (dir) =>
  new Map(
    readdirSync(dir)
      .filter((file) => file.endsWith('.json') && file !== 'report.json')
      .map((file) => [file, JSON.parse(readFileSync(join(dir, file), 'utf8'))]),
  );

const baseline = load(baselineDir);
const failures = [];
for (const [name, current] of load(currentDir)) {
  const base = baseline.get(name);
  if (!base) {
    console.log(`new, not gated: ${name}`);
    continue;
  }
  if (current.latency.p50 > base.latency.p50 * (1 + threshold)) {
    failures.push(`${name}: median ${base.latency.p50.toFixed(5)} ms -> ${current.latency.p50.toFixed(5)} ms`);
  }
}

console.log(failures.join('\n') || 'No regression beyond the threshold.');
process.exit(failures.length > 0 ? 1 : 0);
```

Keep `bench-results/` out of source control and upload it on every run, so a failed gate carries both runs' numbers
and the JSON report (whose test cases carry a `benchmarks` field). The pipeline wiring is
`qa/cicd/typescript/skills/ci-pipelines`.

## Vitest 3–4 lane

Before Vitest 5, `bench` is imported from `vitest` and grouped with `describe`; options are the third argument:

```ts
import { bench, describe } from 'vitest';

describe('order total over 1,000 lines', () => {
  const lines = linesOf(1_000);
  let checksum = 0;

  bench('reduce', () => {
    checksum += reduceTotal(lines);
  }, { time: 1_000, warmupTime: 500 });
  bench('loop', () => {
    checksum += loopTotal(lines);
  }, { time: 1_000, warmupTime: 500 });
});
```

```bash
npx vitest bench --run --outputJson bench-results/bench.json        # write this run
npx vitest bench --run --compare "$BASELINE_DIR/bench.json"          # print this run against a stored one
```

`--compare` only prints the comparison; it never fails the run. The gate script reads
`files[].groups[].benchmarks[]` (`name`, `median` in ms) from both `--outputJson` files instead of `writeResult`
files; the thresholds and runner rules above are the same.

## Handoff to the profiler

A benchmark says **that** a function is slow; a CPU profile says **where**. Profile the same function outside Vitest,
from a short driver script that calls it in a loop on the same inputs and prints a checksum:

```bash
node --cpu-prof --cpu-prof-dir=./profiles benchmarks/pricing/profile-order-total.mjs
node --heap-prof --heap-prof-dir=./profiles benchmarks/pricing/profile-order-total.mjs
```

Open the `.cpuprofile` in Chrome DevTools or speedscope; the `.heapprofile` answers the allocation question the
benchmark cannot. Attach both with the benchmark table. The flags and the evidence checklist are
`qa/_shared/performance/references/profiling.md` (Node).

## Rules

The standards this skill's output must meet are the qa-typescript rule files, not a list here: `qa-typescript.md` and,
for the CI gate, `ci-tests.md`. Read the project's copy in `.claude/rules/qa-typescript/`, or the plugin's in
`qa/typescript/skills/rules/` when the project has not installed them (`/qa-typescript:rules` does). Where they and
this skill's recipes disagree, the rule files win.

## Output format

```
Created: benchmarks/<area>/<feature>.bench.ts   Purpose: baseline + alternatives, writeResult per bench
Created: ci/compare-benchmarks.mjs              Purpose: median regression gate against the default branch
```

Then the comparison table (ops/sec, median, rme per input size), the environment line, and a one-line reading
("`loop` is 0.31× the latency of `reduce` at 1,000 lines, rme under 2%").

## Anti-examples

- **A `performance.now()` loop inside a unit test** — no warm-up, no statistics, JIT tiering mid-measurement, and a
  debugger-attached run looks the same as a real one. Use `vitest bench`.
- **Benchmarking an HTTP endpoint** — that is a load test, with the network and the server in the number.
- **A bench function whose result goes nowhere** — V8 is free to delete the work; the result is a few nanoseconds of
  nothing.
- **Gating on time on shared CI runners** — the gate fails on noise and gets disabled; report time there.
- **Benchmarking `src/` through the module runner** — the import getters dominate the number; measure the built
  output.

## Handoffs

- Endpoint load and SLOs → `load-testing`, `qa/_shared/performance`
- CPU and heap profiles → `qa/_shared/performance/references/profiling.md`
- The CI job and artifact upload → `qa/cicd/typescript/skills/ci-pipelines`
- Making the benchmarked code testable / tested → `be-node` `unit-testing`
