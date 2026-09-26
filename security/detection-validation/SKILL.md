---
name: purpleteam-detection-validation
description: Use to assert that the rule or alert meant to catch a simulated MITRE ATT&CK technique actually fired, by querying the log/alert store in the detonation window — the blue half of a purple-team run answering "are our detections working?". Gates every assertion on a telemetry backend. Triggers "did our SIEM catch T1003?", "validate the detection fired". Not for running the technique (`purpleteam-atomic-simulation`) or authoring it (`secgov-detection-engineering`).
---

# Purple Team — Detection Validation (assert the guardrail actually fired)

Detection validation is the **blue half of purple**, and the actual deliverable of a purple-team run. For each technique the red half (`purpleteam-atomic-simulation`) just detonated, you go to the **log/alert store** and ask one question: **within the detonation window, did the control that is supposed to catch this technique fire?** The answer per ATT&CK id — **detected or not** — is the whole point. Authoring a detection is a hypothesis; a pentest proves an attacker can chain findings; this proves the *defense* works, on a schedule, before an incident tests it for you.

Unlike the red half, this skill **sends no payload and touches no target** — it only *reads* the telemetry store — so it carries **no offensive authorization gate**. It has a different hard prerequisite that is just as load-bearing: **a telemetry backend must exist to query.** A detection assertion against a system with no SIEM/observability is not a passing control — it is *nothing to assert against*, and saying "detected: no" there would be a lie of omission (you did not fail to detect; you had no way to detect). This skill reports that honestly.

This skill is **language-agnostic** (Sigma is vendor-neutral YAML; the query languages are your SIEM's; the log store is your observability stack) and is loaded by the **`purple-team-engineer`** agent in its **Validate** step, immediately after each `purpleteam-atomic-simulation` detonation. It owns *asserting the detection fired*; it does not run the technique (the red half) or author the rule (`secgov-detection-engineering`).

> **The single spine is MITRE ATT&CK Enterprise (v19, pinned)** — the same technique id the red half detonated is the join key here: "did an alert tagged `T1003.001` fire between `detonate_ts` and `detonate_ts + window`?" **The per-technique gate is detected / not-detected**, scored as an outcome tier (below), *not* CVSS. Where a not-detected result is a real gap, its urgency rides the library's blocker/major/minor/nit table via the missing/broken detection, routed to `secgov-detection-engineering`.

## The telemetry-backend gate — the load-bearing prerequisite

**Run this check before asserting anything.** The blue half is only meaningful against a real detection surface:

1. **Is there a log/alert store to query at all?** A SIEM (Splunk, Elastic, Sentinel, QRadar, Chronicle) or the observability stack the `observability/` domain owns (Loki for logs, Prometheus/Mimir for metric-based alerts, Alertmanager for alert state). If **none exists**, stop and report **"no detection surface to assert against"** for every technique in the run — do **not** record `not-detected` (which implies a detection could have fired and didn't). This is a finding routed to `observability-engineer-*`: *stand up the telemetry backend before purple-team validation is meaningful.*
2. **Does the store carry the log source this technique needs?** A backend that exists but never ingests `windows/security` (or the cloud audit log, or the EDR feed) cannot see the technique even if a rule exists. This is the **telemetry gap** — distinct from a rule gap — and the same handoff to `observability-engineer-*` / `observability-queries` to wire the source.
3. **Only then** query for the detection and score the outcome.

> **Green ≠ safe, and empty ≠ detected-nothing.** A query returning no alert has *three* different meanings, and conflating them is the classic purple-team lie: **(a)** the event landed but no rule matched → **rule gap** (route to `secgov-detection-engineering`); **(b)** the event never reached the store → **telemetry gap** (route to `observability-engineer-*`); **(c)** there is no store → **no detection surface** (stand one up first). This skill's job is to say *which* — a single "not detected" that hides a telemetry gap sends the blue team to fix a rule that was never the problem.

## The four outcome tiers — the honest score

Per technique, the assertion resolves to exactly one tier (the VECTR outcome model — the shared purple-team vocabulary):

| Tier | Meaning | Evidence to capture | Routes to |
|------|---------|---------------------|-----------|
| **Blocked** | A control *prevented* the technique (WAF, EDR kill, policy deny) | the block/deny event + the enforcing control | best outcome — record it |
| **Alerted** | The event landed **and** an alert fired for the ATT&CK id in-window | the alert id/name, its ATT&CK tag, the firing time within the window | detection works — record it |
| **Logged only** | The event is in the store but **no alert fired** | the raw log line proving the event landed | **rule gap** → `secgov-detection-engineering` (author/fix the rule) |
| **No signal** | The event is **not in the store** at all | the query that returned empty + the log source that should carry it | **telemetry gap** → `observability-engineer-*` (wire the source) |

"Detected" = **Blocked** or **Alerted**. "Not detected" = **Logged only** (rule) or **No signal** (telemetry) — and the tier is what makes the fix routable. A fifth state, **No detection surface**, is reported when the telemetry-backend gate fails outright.

## Sigma-converted queries — the detection's own logic, run as an assertion

The cleanest validation queries the store with **the same detection logic the rule uses**, converted to the target backend — so you are testing the actual rule, not an approximation. Reuse `secgov-detection-engineering`'s Sigma source and **sigma-cli 3.1.0**:

```bash
# Convert the authored Sigma rule to the SIEM query language, then run it over the detonation window.
sigma convert -t splunk       -p splunk_windows  rules/t1003_001_lsass_dump.yml   # → SPL for Splunk
sigma convert -t elasticsearch -p ecs_windows    rules/t1003_001_lsass_dump.yml   # → ES|QL / DSL for Elastic
sigma convert -t microsoft365defender            rules/t1003_001_lsass_dump.yml   # → KQL for Sentinel/Defender
sigma convert -t loki          -p loki_promtail_sysmon rules/t1003_001_lsass_dump.yml  # → LogQL for Loki
```

Then two assertions against the store, both scoped to the detonation window (`detonate_ts .. detonate_ts + window`, from the red half's action-log timestamp):

- **Did the event land?** Run the rule's `selection` (the raw match) — proves the log source carries it (distinguishes *logged-only* from *no-signal*).
- **Did the alert fire?** Query the SIEM's alert/notable index (or Alertmanager) for a firing tagged with the ATT&CK id in-window — proves the rule triggered (distinguishes *alerted* from *logged-only*).

## Querying the log/alert store — the library's Loki/Prometheus stack

Where the target runs the library's default observability stack (`observability/` domain), the assertion is LogQL against Loki (did the event land?) plus PromQL against Alertmanager/Prometheus (did an alert fire?). The query mechanics are owned by **`observability-queries`** — this skill supplies the **security assertion** over them.

```logql
# Did the technique's event land in the log store, in-window? (distinguishes logged-only from no-signal)
count_over_time(
  {service="edr", host="lab-web-01"} | json | event_type="process_access" | target_image=~".*lsass.exe"  [5m]
)
# Empty over the detonation window → NO SIGNAL (telemetry gap). Non-empty → the event landed; now check the alert.
```

```promql
# Did an alert fire for this ATT&CK technique, in-window? Alertmanager exposes firing alerts as the ALERTS series.
ALERTS{alertname="LSASS_Memory_Access", attack_technique="T1003.001", alertstate="firing"}
# Present in-window → ALERTED (detected). Absent while the event landed → LOGGED ONLY (rule gap).
```

- **The detonation timestamp is the join key.** The red half logs *when* it detonated each technique; every query here is bounded to that window — an alert that fired an hour before the test is not evidence this run's technique was caught.
- **Tag alerts with the ATT&CK id.** A firing alert is only usable evidence if it carries the technique id (`secgov-detection-engineering` puts it in the rule's `tags`; the alert rule should propagate it as a label). An alert with no ATT&CK tag can't be joined to the simulated technique deterministically — flag that as a detection-hygiene gap.
- **Prevention lives elsewhere than alerts.** A *blocked* outcome shows up as a WAF/EDR deny event, not a SIEM alert — query the enforcing control's log for the block, in-window, to score **Blocked**.
- **SIEM-native stores** (Splunk `index=notable`, Elastic `.alerts-security.alerts-*`, Sentinel `SecurityAlert`/`SecurityIncident`, Sentinel Watchlists) are queried the same way conceptually — the store and dialect change, the two assertions (event landed? alert fired?) and the four tiers do not.

## Continuous validation & drift — the scheduled cadence

Purple-team validation earns its keep **run round over round**. Store each round's per-technique outcome (in VECTR, or the report's matrix) and compare:

- **Still detected** — was detected last round, still is. The steady state.
- **Newly detected** — a detection authored since last round now proves out.
- **Regressed (drift)** — **was detected last round, now not** — the highest-signal finding this lane produces. A log source stopped shipping, a rule was disabled during an incident and never re-enabled, a SIEM upgrade broke field parsing. Route by tier: *logged-only* regression → the rule broke (`secgov-detection-engineering`); *no-signal* regression → the telemetry broke (`observability-engineer-*`).
- **Still not detected** — a known gap that has not been closed; carries forward with its route.

Drift is invisible to a one-shot scan and to a coverage map built from *authored* rules — only re-running the technique against the live store finds it. That is why this lane is scheduled, not one-and-done.

## Anti-patterns

- **Recording `not-detected` when there is no telemetry backend.** Implies a detection could have fired and didn't; the truth is there was nothing to fire. *Fix:* the telemetry-backend gate — report "no detection surface", route to `observability-engineer-*`, do not score the techniques.
- **Conflating logged-only with no-signal.** Both look like "not detected", but one is a rule gap and one is a telemetry gap — routed to different owners. *Fix:* the two-assertion pattern (did the event land? did the alert fire?) resolves which, every time.
- **Querying without the detonation window.** An alert that fired yesterday is not evidence this run's technique was caught. *Fix:* bound every query to `detonate_ts .. detonate_ts + window` from the red half's action log.
- **Trusting an untagged alert.** An alert with no ATT&CK id can't be deterministically joined to the simulated technique. *Fix:* require the technique id on the alert; a missing tag is a detection-hygiene finding.
- **Asserting against an approximation of the rule instead of the rule.** Hand-writing a query that "roughly matches" tests your query, not the deployed detection. *Fix:* `sigma convert` the actual rule and run its own logic.
- **Calling a scheduled run without comparing to the prior round.** Then you never see drift — the whole reason to schedule. *Fix:* diff against last round; surface Regressed first.
- **Claiming coverage from authored rules.** "We have 40 detections" ≠ "40 techniques are detected." *Fix:* coverage is what *validated* this round, per tier — not what was authored.

## Hard rules

- **The telemetry-backend gate runs first.** No store to query → report **"no detection surface to assert against"** and route to `observability-engineer-*`; never silently pass and never score it as not-detected.
- **Distinguish the three empty-result meanings** — rule gap (logged-only) vs telemetry gap (no-signal) vs no surface — via the two-assertion pattern; report the **tier**, not a bare detected/not.
- **Every assertion is windowed** to the technique's detonation timestamp from the red half's action log; an out-of-window alert is not evidence.
- **The spine is ATT&CK Enterprise, pinned (v19).** Join red detonation to blue alert on the technique id; require the id as an alert tag; the gate is **detected / not-detected** by tier, not CVSS.
- **Read-only.** This skill queries the log/alert store and nothing else — it authors no rule (`secgov-detection-engineering`), fixes no telemetry (`observability-engineer-*`), and runs no technique (`purpleteam-atomic-simulation`).
- **Validated ≠ authored.** Report which techniques were *proven to fire this round*, per tier — coverage is validation, not rule count.
- **Test the deployed rule, not an approximation** — `sigma convert` the real Sigma source; a hand-written near-match tests the query, not the control.
- **Redaction.** A log line captured as evidence carries no real secret/PII — redact per the loot rule; nothing sensitive committed under `docs/security/`.

## Cross-references

- **`purple-team-engineer`** (`security/agents/purple-team-engineer.md`) — the orchestrator that runs this skill in its **Validate** step, immediately after each `purpleteam-atomic-simulation` detonation, and owns the telemetry-backend gate.
- **`purpleteam-atomic-simulation`** — the **red half**: it detonates the technique and logs the detonation timestamp this skill windows its queries to. Simulate then validate; neither stands alone.
- **`secgov-detection-engineering`** (`security/detection-engineering/`, `security-governance` plugin) — **authors** the Sigma rules this skill converts and validates. A **logged-only** result is a rule gap routed here to author/fix; a validated technique promotes its rule from *authored* to *validated coverage*. Author there, validate here — the two halves of one loop.
- **`observability-engineer-*`** + **`observability-queries`** / **`observability-dashboards`** *(peers, named not loaded)* — own the telemetry substrate this skill queries (Loki/Prometheus/Tempo, Alertmanager, the log pipeline) and the query-language mechanics. A **no-signal** result or a failed telemetry-backend gate is a handoff to them: this lane authors the *security assertion*; they own the *substrate* it runs against.
- **`security-architect`** (`security/agents/security-architect.md`, `security-governance` plugin) — consumes this lane's per-tier outcomes: a *validated* technique becomes proven coverage in its ATT&CK coverage map, a *regressed* one a fresh risk-register item. Author (detection-engineering) → validate (here) → roll up (security-architect).
- **`penetration-tester`** (`security/agents/penetration-tester.md`) — the offensive sibling: a chain it completed *undetected* is the exact hypothesis for a detection to author and then validate here.
- **`pentest-reporting`** (`security/pentest-reporting/`) — the report contract the purple-team run closes with; the detected/not-detected matrix and the drift view are its purple-team-specific sections.
