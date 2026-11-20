---
name: atomic-simulation
description: Use when running MITRE ATT&CK techniques (Atomic Red Team, Caldera) in an owned lab to prove detections fire. Triggers "simulate T1003 in our lab". Not for asserting alerts (detection-validation).
disable-model-invocation: true
---

# Purple Team — Atomic Simulation (Atomic Red Team · Apache Caldera · Stratus Red Team)

Atomic simulation is the **red half of purple**: you *deliberately* run a known MITRE ATT&CK technique — or a chained sequence of them — against **your own authorized environment**, so the paired blue half (`penetration-testing:detection-validation`) can go and check whether the guardrail, SIEM rule, or alert that is *supposed* to catch it actually fired. This is not exploitation to gain access; the technique is expected, scheduled, scoped, and cleaned up. Its whole purpose is to answer one question per technique: **detected, or not?**

Run on a schedule, it catches **security drift** — the detection that worked in March and silently broke in August (a log source stopped shipping, a rule was disabled during an incident, a field was renamed, a SIEM upgrade changed parsing). A detection is a hypothesis until a real technique fires against it; drift is what turns a green coverage map into a false one.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed engagement scope file.** Atomic simulation **executes real offensive techniques** against a live environment, so it is bound by the full engagement safety model (the nine controls in the `penetration-tester` agent's Invariants). Every run is gated by `docs/security/engagement-<NNN>.md` and its `#volatile` authorization line: the scope file's in-scope hosts/accounts/clusters are the **only** things you may detonate against, its hard exclusions are never touched, its blast-radius cap bounds every run, and **production is a separate, louder second sign-off** — the default target is a designated lab/throwaway. Running an ATT&CK atomic against a system you do not own or are not authorized to test is an attack, not a test. **Read the scope file before every technique; if the next technique would fall outside it, halt the run and report.**

```
Authorization: engagement=<NNN>  in-scope=<hosts/accounts/clusters>  exclusions=<never-touch>
               authorized-by=<name>  window=<start>..<expiry>  environment=lab|production(2nd sign-off)
```

This skill is **language-agnostic** (every tool is a PowerShell module, a Go binary, or a Python server — no per-stack split, per the library's anti-triplication rule) and is loaded by the **`purple-team-engineer`** agent in its **Simulate** step. It owns *running the technique and cleaning it up*; it does **not** assert whether the detection fired — that is the blue half, `penetration-testing:detection-validation`, which the agent runs immediately after against the log/alert store.

> **The single spine is MITRE ATT&CK Enterprise (v19, pinned).** Every simulated technique is named by its ATT&CK **technique id** — `T1003.001` LSASS memory, `T1021.001` RDP, `T1059.001` PowerShell, `T1110` brute force — the shared language red simulation and blue detection both speak. **Pin the version** (v19, 2026-04-28): technique/tactic ids move between versions — v18 added structured **Detection Strategies / Analytics / Data Components**, and **v19 retired `Defense Evasion` and split it in two — `Stealth` keeps the old id `TA0005`, and `Defense Impairment` is the new `TA0112`**, so a technique catalogued under the old tactic slug is now mis-mapped. **The per-technique report gate is detected / not-detected**, *not* the offensive CVSS score the kill-chain lane uses — a simulation proves whether a control works, not how bad a vuln is. Where a not-detected technique is a genuine gap, its urgency is scored on the library's blocker/major/minor/nit table via the detection it should have tripped, never CVSS.

## The purple loop — simulate, then immediately validate

Atomic simulation is never run alone. The value is the **pair**, one technique at a time:

1. **Pick the technique** from the threat model or the detection you want to prove (`security-governance:detection-engineering` authored a rule for `T1003.001` — does it fire?).
2. **Simulate** it here — smallest atomic that exercises the behavior, logged as it runs.
3. **Validate** it in the blue half (`penetration-testing:detection-validation`) — query the log/alert store, assert the alert fired for that ATT&CK id.
4. **Clean up** the atomic's artifacts and **verify** the cleanup.
5. **Record** the outcome: detected / not-detected / partial, per ATT&CK id, into the purple-team result matrix (VECTR or the report).

Run this pair on a schedule and the matrix becomes a **drift monitor**: a technique that was `detected` last round and is `not-detected` this round is a regression to route to `security-governance:detection-engineering` (rule broke) or `observability-engineer-*` (telemetry broke).

## Decision matrix — which tool for which surface

| Need | Tool | Surface | Notes |
|------|------|---------|-------|
| Run one host/endpoint ATT&CK technique with prereqs + cleanup | **Atomic Red Team** (`Invoke-AtomicTest`) | Windows · Linux · macOS endpoint | The atomic unit; `-GetPrereqs` / `-Cleanup` built in |
| Orchestrate a **chain** of techniques (adversary profile) across agents | **Apache Caldera** | multi-host, autonomous operation | Server + agents; abilities ↔ ATT&CK; `emu` plugin ships CTID emulation plans |
| Simulate a **cloud / Kubernetes** technique | **Stratus Red Team** | AWS · Azure · GCP · K8s | Self-contained Go binary; warmup → detonate → cleanup; ATT&CK **Cloud/Containers** matrix |
| Track outcomes + benchmark coverage across ATT&CK over time | **VECTR** (SRA) | reporting/tracking, not execution | Community Edition self-hosted; the drift/coverage matrix |

**Rule of thumb:** Atomic Red Team is the scalpel (one technique, run-and-clean); Caldera is the campaign (a chain of techniques an autonomous agent walks); Stratus is the cloud equivalent of an atomic; VECTR is the scoreboard. Start with a single atomic and its paired detection; graduate to a Caldera adversary profile only once individual detections are proven.

## Atomic Red Team — the scalpel (one technique, run-and-clean)

**Atomic Red Team** (Red Canary) runs small, portable tests each mapped to an ATT&CK technique via the
**`invoke-atomicredteam`** PowerShell module: check, stage prereqs, run exactly one numbered test, then
always clean up and verify. Pin both the module version and the `atomics/` folder commit — the two update
on separate schedules, and "we ran the T1003.001 atomic" is not reproducible without both. Full install,
invocation sequence and the scope/cleanup rules: `references/atomic-red-team.md`.

## Apache Caldera — the campaign (a chain of techniques)

**Apache Caldera** (v5.3.0, now `apache/caldera`) is an autonomous adversary-emulation platform: a server,
agents on in-scope hosts, and **abilities** mapped to ATT&CK technique ids that chain into an **adversary
profile** run as an **operation** — the multi-technique scenario a single atomic can't express. The
`atomic` plugin imports Atomic Red Team tests as abilities; `emu` ships CTID's ready emulation plans.
**Scope discipline is louder here than for a single atomic** — an autonomous planner can pivot further
than you expect; bound it to the in-scope hosts and cap the operation. Full setup and the pivot-abort
rule: `references/caldera.md`.

## Stratus Red Team & VECTR — cloud/K8s atomics, and the scoreboard

**Stratus Red Team** (Datadog) is the cloud equivalent of a single atomic: a Go binary that
**warmup → detonate → cleanup**s a granular AWS/Azure/GCP/K8s technique, mapped to ATT&CK
Cloud/Containers — the point is the telemetry it generates for the blue half to query. **VECTR** (SRA) is
where purple-team outcomes are tracked over time, not executed: technique, tool and outcome
(blocked/alerted/logged/no signal) building the coverage matrix and, round over round, the **drift** view;
optional, since the report's detected/not-detected matrix carries the same data. Full invocation and
lifecycle: `references/stratus-vectr.md`.

## Anti-patterns

- **Running an atomic with no paired detection check.** Detonating `T1003.001` and not asking "did anything catch it?" is noise, not a purple-team run. *Fix:* every simulate is immediately followed by `penetration-testing:detection-validation` for the same ATT&CK id.
- **`Invoke-AtomicTest <technique>` with no `-TestNumbers`.** Runs every atomic under the technique, some more intrusive than intended. *Fix:* select one test, read `-ShowDetailsBrief` first, run it, clean it up.
- **Skipping `-Cleanup` / `stratus cleanup`.** Leaves users, files, services, or cloud resources behind — a cleanup-verification violation and, in the cloud, an ongoing cost. *Fix:* cleanup is part of every technique's run, followed by a verification that the artifact is gone.
- **Letting a Caldera operation run unbounded.** An autonomous planner can pivot further than the scope allows. *Fix:* deploy agents only on in-scope hosts, cap the operation, re-read the scope file before starting, abort on an out-of-scope next step.
- **Detonating a cloud technique against the wrong account.** Stratus creates real resources; the default profile is not the lab. *Fix:* pin the cloud profile/credentials to the in-scope account; confirm before `detonate`.
- **Treating "the atomic ran" as "the detection works".** The red half only proves the *technique fired*; the control is proven only by the blue assertion. *Fix:* the outcome is `detected`/`not-detected`, decided by the blue half, never by a successful detonation alone.
- **Mapping to a stale ATT&CK version.** A technique catalogued under `defense-evasion` is mis-tagged after v19's Stealth/Defense-Impairment split. *Fix:* pin the ATT&CK version; re-map on upgrade.
- **Simulating against production without the second sign-off.** "Owned infra" is not enough for a live technique on prod. *Fix:* default to lab/throwaway; production is a separate, louder authorization in the scope file.

## Hard rules

- **The engagement scope file gates every technique.** Only in-scope targets are detonated against; hard exclusions are never touched; the blast-radius cap bounds every run; re-read the scope file before each technique and **halt if the next one would exceed it**.
- **Production is a separate, louder gate than lab.** Default target is a designated lab/throwaway; a production simulation needs the second sign-off and the smallest, safest atomics.
- **Every technique is cleaned up and the cleanup is verified.** `-Cleanup` / `stratus cleanup` / the operation's reverse cleanup runs, then you confirm the artifact is gone — enumerated in the report's cleanup-verification section.
- **No DoS, ever** — not as a technique, not as a side effect. A simulation proves a detection fires; it never risks the availability of the in-scope service.
- **The spine is ATT&CK Enterprise, pinned (v19).** Every simulated technique carries its technique id; cloud/K8s atomics carry the Cloud/Containers id. The report gate is **detected / not-detected**, not CVSS.
- **Simulate then validate — never simulate alone.** The red run is half the loop; the paired `penetration-testing:detection-validation` assertion is the other half and the actual deliverable.
- **Log every technique as it runs** — tool, technique id, target, timestamp — into the engagement action log (per `penetration-testing:reporting`), so the run is reproducible and provably in scope.
- **Pin the tools and the atomics.** Module version *and* atomics-folder commit for Atomic Red Team; Caldera 5.3.0 (`apache/caldera`); Stratus v2.32.1 — "we ran the atomic" is not reproducible without them.
- **Redaction.** Anything a technique recovers (a dumped credential, a token) is handled per the loot rule — reported as *that it was recovered + blast radius*, never contents; nothing sensitive committed under `docs/security/`.
