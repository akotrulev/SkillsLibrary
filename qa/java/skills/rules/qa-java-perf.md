---
paths:
  - "**/src/gatling/**"
  - "**/*Simulation.java"
---

<!-- qa-java rules v1 (2026-11-03): performance. Installed by /qa-java:rules; edit the paths above to where this project keeps its Gatling simulations. -->

# Gatling load-test standards

Severity tags as in the core qa-java rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- Every simulation states its workload model (open or closed, arrival rate, duration, warm-up) and thresholds before it runs. *major*
- Open-loop injection (`constantUsersPerSec`, `rampUsersPerSec`) by default; `injectClosed` only for a fixed concurrency cap. No `repeat(…)` to fake throughput. *major*
- An `assertions(...)` block on every simulation, per route through `details("group")` plus `global().failedRequests()`; never latency on `global()` alone. *major*
- Every logical endpoint inside a `group("…")`. *minor*
- Nothing blocks the engine: no `Thread.sleep` or blocking call in `exec`; think time is `pause()`. *blocker*
- All HTTP goes through the Gatling DSL, never RestAssured in a scenario. *major*
- URLs and tokens come from system properties fed from the environment. *blocker*
- Data from feeders, namespaced per run (`perf-<uuid>`); payloads from `StringBody` / `ElFileBody`, never string concatenation. *minor*
- One simulation class per scenario, named `<Name>Simulation`; Java or Scala per module, not both. *minor*
- Never load an environment you are not authorized to, or mutate data in production. *blocker*
