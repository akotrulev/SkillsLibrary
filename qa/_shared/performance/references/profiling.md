# Profiler hand-off — per stack

Read after a load-test threshold failed **and** the client/server split put the time inside the service
(`SKILL.md`, *When a threshold fails*). QA captures the evidence and hands it over; the service's developers read
the profile and fix. Run every capture against **one instance** at the load step that breached, during the
measured window, for 30–60 s.

| Stack | First look (is it CPU, GC, threads, locks?) | CPU / wall-clock profile | View it in | Continuous (Grafana) |
|---|---|---|---|---|
| .NET | `dotnet-counters` | `dotnet-trace collect` | speedscope, PerfView, Visual Studio | Pyroscope .NET profiler |
| Java | JFR (`jcmd JFR.start`) | async-profiler (`asprof`) | the HTML flame graph; JDK Mission Control for JFR | Pyroscope Java agent |
| Node | `--cpu-prof` on a run, or Clinic.js `doctor` | `--cpu-prof` | Chrome DevTools, speedscope | `@pyroscope/nodejs` |

## .NET — dotnet-counters, dotnet-trace, speedscope

```bash
dotnet-counters ps
dotnet-counters collect --process-id <pid> --refresh-interval 1 --format csv -o counters.csv \
  --counters System.Runtime,Microsoft.AspNetCore.Hosting
dotnet-trace collect --process-id <pid> --duration 00:00:01:00 --format Speedscope -o checkout-breach
```

- `dotnet-counters` reads the `System.Runtime` meter on .NET 9+ (`dotnet.gc.pause.time`,
  `dotnet.thread_pool.queue.length`, `dotnet.monitor.lock_contentions`, `dotnet.process.cpu.time`); on .NET 8 and
  lower it falls back to the older EventCounters. A growing thread-pool queue with low CPU is starvation
  (sync-over-async), not a CPU problem — say so in the bug.
- `dotnet-trace collect` with no `--profile` enables `dotnet-common` + `dotnet-sampled-thread-time` (current tool,
  9.0.661903+). The old `cpu-sampling` profile name is gone; do not copy it from old guides.
- `--format Speedscope` converts after capture and **keeps the `.nettrace`** beside it — attach both. Open the
  `.speedscope.json` at speedscope.app; the `.nettrace` opens in PerfView or Visual Studio.
- `--duration` is `dd:hh:mm:ss`. The tool must run as the same user as the app (or root) and share its `TMPDIR`;
  in a container that means running it inside the pod (`kubectl exec`) or through a shared diagnostic port.
- On .NET 10, `dnx dotnet-counters ...` runs the tool without installing it.

## Java — JFR and async-profiler

```bash
jcmd <pid> JFR.start name=breach settings=profile duration=60s filename=/tmp/checkout-breach.jfr
asprof -e cpu -d 60 -o flamegraph -f /tmp/checkout-breach-cpu.html <pid>
asprof -e wall -d 60 -o flamegraph -f /tmp/checkout-breach-wall.html <pid>
```

- **JFR first** — it is in every JDK 11+ and records CPU samples, GC, allocation, lock and I/O events together.
  `settings=profile` costs more than `default`, which is why the recording is time-boxed. The file is written when
  the recording stops; open it in JDK Mission Control, or `jfr summary` / `jfr print --events jdk.ExecutionSample`.
- **async-profiler** (4.x, launcher `asprof`) for the flame graph: `-e cpu` for on-CPU time, `-e wall` when
  threads wait (pools, locks, I/O), `-e alloc` for allocation pressure, `-e lock` for contention. Pass `-o` with
  the format; `-o jfr -f breach.jfr` writes JFR instead.
- Attach the HTML flame graph (it opens in any browser, no tool needed) and the raw `.jfr`.

## Node — --cpu-prof, Clinic.js

```bash
node --cpu-prof --cpu-prof-dir=./profiles --cpu-prof-name='checkout.${pid}.cpuprofile' server.js
```

- The `.cpuprofile` is written **when the process exits normally** — handle `SIGTERM` by closing the server and
  calling `process.exit()`, or the profile is lost. Stop the server after the measured window, not before.
- `--cpu-prof-interval` is the sampling interval in microseconds (default `1000`). `--heap-prof` writes a
  `.heapprofile` the same way. Both flag families are stable (Node 22.4+ / 20.16+).
- Open the `.cpuprofile` in Chrome DevTools (Performance → load profile) or speedscope.
- **Clinic.js** (`clinic doctor -- node server.js`, `clinic flame -- node server.js`) gives a first diagnosis
  and a flame graph in one step, but its README states it is not actively maintained and may give inaccurate
  results on current Node — use it for a first look, and attach the `--cpu-prof` profile as the evidence.

## Continuous profiling — Grafana Pyroscope

Our telemetry stack is Grafana (Loki, Prometheus, Tempo); Pyroscope is its profiling store. With it running in
the perf environment, the hand-off needs no capture at all: link the profile for the run window.

| Stack | How it sends profiles | Notes |
|---|---|---|
| .NET 8 / 9 / 10 | The Pyroscope .NET profiler, enabled by `CORECLR_ENABLE_PROFILING=1`, `CORECLR_PROFILER={BD1A650D-AC5D-4896-B64F-D6FA25D6B26A}`, `CORECLR_PROFILER_PATH`, `PYROSCOPE_PROFILING_ENABLED=1`, `PYROSCOPE_APPLICATION_NAME`, `PYROSCOPE_SERVER_ADDRESS` | CPU, wall, allocations, lock contention, exceptions, live heap |
| Java | `java -javaagent:pyroscope.jar` with `PYROSCOPE_APPLICATION_NAME`, `PYROSCOPE_SERVER_ADDRESS`, `PYROSCOPE_FORMAT=jfr` | Built on async-profiler; JFR format carries several event types at once |
| Node | `@pyroscope/nodejs`: `Pyroscope.init({ serverAddress, appName })` then `Pyroscope.start()` | Wall and heap; CPU time needs `wall.collectCpuTime: true` |
| Any (no code change) | Grafana Alloy `pyroscope.ebpf` | Host-level CPU profiles via eBPF |

- **Span profiles** link a slow trace in Tempo to the profile of that request (Go, Java, Ruby, .NET and Python
  per the Pyroscope docs; not Node). Where enabled, attach the slow requests' trace ids and the linked profiles.
- Compare the failing run's window with the last passing run's in Pyroscope's comparison (diff) view; attach the
  diff link.
- Label profiles with the same `service` and environment labels as the metrics, so one Grafana time range shows
  the threshold breach, the traces and the profile together.

## Evidence checklist for the failing run

| Item | Example |
|---|---|
| The breach | Scenario `checkout-average`, route `POST /api/checkout`, threshold p95 < 300 ms, measured 870 ms at 120 RPS |
| The split | Server p95 840 ms (Prometheus query + value), client p95 870 ms |
| Counters for the window | `counters.csv` / JFR summary / Node `--cpu-prof` run log |
| The profile | `.nettrace` + `.speedscope.json` · `.jfr` + flame graph HTML · `.cpuprofile` · or a Pyroscope link with the time range |
| Slow requests | 2–3 trace ids from Tempo |
| Where | Build SHA, environment, instance / pod name, instance size |
| How | The exact capture commands, so the developer can reproduce |
