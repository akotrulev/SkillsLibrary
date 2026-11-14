# Risk hotspots — choosing what to test first

Read this when a change lands in, or a test backlog is being planned for, **existing code with thin coverage**,
and the question is where a test buys the most. The coverage floor scopes to the code a change wrote; this is
how to rank the code around it.

## CRAP

The CRAP score (Change Risk Anti-Patterns) combines a method's cyclomatic complexity with how little of it the
tests cover:

```
CRAP(m) = comp(m)² × (1 − cov(m))³ + comp(m)
```

`comp(m)` is the method's cyclomatic complexity and `cov(m)` its coverage as a fraction (0.0 – 1.0). Fully covered,
CRAP equals the complexity; uncovered, it is complexity² + complexity. A method with complexity 10 scores 110
uncovered, 61 at 20% coverage, 23 at 50%, 10 at 100%. Only two things lower it: tests, or splitting the method.

ReportGenerator computes it per method from the Cobertura file coverlet writes, using the method's `complexity`
and **line** coverage (`line-rate`), and lists the methods above its thresholds as **risk hotspots**.

## Producing the hotspot list

```bash
dotnet test --collect:"XPlat Code Coverage" --results-directory TestResults
dotnet tool run reportgenerator -reports:"TestResults/*/coverage.cobertura.xml" \
  -targetdir:TestResults/hotspots -reporttypes:"Html;MarkdownSummary" \
  -riskhotspotassemblyfilters:"+Ordering.*;-*.Tests" \
  riskHotspotsAnalysisThresholds:metricThresholdForCrapScore=30 \
  riskHotspotsAnalysisThresholds:metricThresholdForCyclomaticComplexity=15
```

- The **Risk Hotspots** table is in `TestResults/hotspots/index.html` and in `Summary.md`: assembly, class,
  method, then each metric with the threshold breaches highlighted.
- 30 for CRAP and 15 for complexity are ReportGenerator's defaults, written out so the run states them. A method
  is listed only when a metric is **above** its threshold.
- `-riskhotspotassemblyfilters` / `-riskhotspotclassfilters` take the same `+`/`-` wildcard syntax as the other
  filters; exclude test projects and generated code so they do not crowd the list.
- ReportGenerator is the local tool `dotnet-reportgenerator-globaltool` (5.6.0 verified 2026-11), the same one the
  coverage floor uses.

## Reading the list

| Hotspot | Action |
|---|---|
| High CRAP, high complexity, near-zero coverage | **Test first.** Write characterization tests that pin today's behaviour (the snapshot reference fits a large output), then refactor under them |
| High complexity, already well covered | Its CRAP is near its complexity: a refactoring candidate, not a testing one. Split it when it is next changed |
| High CRAP on a method the selection matrix says not to unit-test (a `DbContext` query, a controller) | Not a unit-test target: route it to the integration lane, or move the logic out to where a unit test reaches it |
| Generated code, migrations | Exclude them with the filters; never test them to lower a number |

Rank by CRAP, take the top of the list that the change touches or that the next piece of work will touch, and
stop. This is a way to spend test effort where change risk is highest — the score itself is never a gate, and a
test written only to lower it is the same hollow test the coverage floor forbids.
