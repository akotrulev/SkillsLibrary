---
name: atomic-simulation
description: Use to run MITRE ATT&CK techniques against an authorized lab/owned environment, so a paired assertion proves the guardrails still fire — the red half of a purple-team run. Atomic Red Team + Caldera + Stratus. Owned/lab only, under a committed scope file. Triggers "simulate T1003 against our lab", "test our detections for drift". Not for exploiting a real target (`penetration-testing:initial-access`), proving one app vuln (`qa-security`), or asserting the detection fired (`penetration-testing:detection-validation`).
---

# Purple Team — Atomic Simulation (Atomic Red Team · Apache Caldera · Stratus Red Team)

Atomic simulation is the **red half of purple**: you *deliberately* run a known MITRE ATT&CK technique — or a chained sequence of them — against **your own authorized environment**, so the paired blue half (`penetration-testing:detection-validation`) can go and check whether the guardrail, SIEM rule, or alert that is *supposed* to catch it actually fired. This is not exploitation to gain access; the technique is expected, scheduled, scoped, and cleaned up. Its whole purpose is to answer one question per technique: **detected, or not?**

Run on a schedule, it catches **security drift** — the detection that worked in March and silently broke in August (a log source stopped shipping, a rule was disabled during an incident, a field was renamed, a SIEM upgrade changed parsing). A detection is a hypothesis until a real technique fires against it; drift is what turns a green coverage map into a false one.

> **⚠️ Authorized self-testing only — owned/lab targets, under a committed engagement scope file.** Atomic simulation **executes real offensive techniques** against a live environment, so it is bound by the full engagement safety model (see the `penetration-tester` agent, §5). Every run is gated by `docs/security/engagement-<NNN>.md` and its `#volatile` authorization line: the scope file's in-scope hosts/accounts/clusters are the **only** things you may detonate against, its hard exclusions are never touched, its blast-radius cap bounds every run, and **production is a separate, louder second sign-off** — the default target is a designated lab/throwaway. Running an ATT&CK atomic against a system you do not own or are not authorized to test is an attack, not a test. **Read the scope file before every technique; if the next technique would fall outside it, halt the run and report.**

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

**Atomic Red Team** (Red Canary) is a library of small, portable tests each mapped to an ATT&CK technique, executed by the **`invoke-atomicredteam`** PowerShell module. Pin honestly: the **module** (`redcanaryco/invoke-atomicredteam`) is mature and rarely re-tagged — last tag **v2.3.0** — while the **`atomics/` technique library** (`redcanaryco/atomic-red-team`) updates continuously and is synced separately. **For a reproducible run, pin the module version AND the atomics-folder commit** — "we ran the T1003.001 atomic" is not reproducible unless you record which atomics commit it came from.

```powershell
# Install the module + atomics folder (bootstrap). Do this on the AUTHORIZED lab host, not a workstation.
IEX (IWR 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -UseBasicParsing)
Install-AtomicRedTeam -getAtomics                       # pulls the atomics/ library beside the module
Import-Module invoke-atomicredteam -Force

# The disciplined per-technique sequence — check, prereqs, run one test, then always clean up.
Invoke-AtomicTest T1003.001 -ShowDetailsBrief           # what it will do — read before running
Invoke-AtomicTest T1003.001 -CheckPrereqs               # does the host meet the test's prerequisites?
Invoke-AtomicTest T1003.001 -GetPrereqs                 # stage prerequisites (opt-in — it changes the host)
Invoke-AtomicTest T1003.001 -TestNumbers 1              # run exactly one test, not the whole technique blindly
Invoke-AtomicTest T1003.001 -TestNumbers 1 -Cleanup     # clean up — revert what the test planted
```

- **`-TestNumbers`/`-TestGuids` scope the run.** Never `Invoke-AtomicTest T1003.001` with no test selector against a live env — that runs *every* atomic under the technique, some of which are more intrusive than you intend.
- **`-Cleanup` is not optional.** Many atomics create files, registry keys, users, or services. The cleanup command is part of the technique definition; run it and then *verify* the artifact is gone (the §5 cleanup-verification rule — a planted artifact you did not confirm removed is a finding against your own run).
- **`-GetPrereqs` changes the host** (downloads tools, creates fixtures). It is an opt-in act under the scope file's allowed-techniques list, not a silent default.
- **Run over PowerShell Core** to drive Linux/macOS targets, or the built-in `-Session` to run against a remote authorized host; the remote host must be in scope.

## Apache Caldera — the campaign (a chain of techniques)

**Apache Caldera** (v5.3.0; **note the governance move — the repo is now `apache/caldera`, relocated from `mitre/caldera`;** older tutorials pointing at `mitre/caldera` and pre-5.x plugin layouts are stale) is an autonomous adversary-emulation platform: a server, lightweight agents (`sandcat`/`manx`) on the in-scope hosts, and **abilities** each mapped to an ATT&CK technique that chain into an **adversary profile** and run as an **operation**.

- **Abilities ↔ ATT&CK.** Each ability carries its technique id; a profile is an ordered chain (initial access → discovery → collection → …) — the multi-technique scenario a single atomic can't express.
- **Planners** (`atomic`, `batch`) decide the order abilities run; **fact sources** feed values (a discovered credential) from one ability into the next.
- **The `atomic` plugin imports the Atomic Red Team tests** as abilities, so a Caldera profile can chain ART atomics; the **`emu` plugin** ships the Center for Threat-Informed Defense (CTID) **adversary-emulation plans** (e.g. an APT profile) as ready ATT&CK-mapped chains.
- **`debrief`** produces the operation report (techniques run, per-step results) — the red-side evidence the blue half validates against.
- **Cleanup is first-class:** an operation runs its abilities' cleanup commands in reverse on completion; still verify, and remove the agents when the engagement ends.

> **Scope discipline is louder for Caldera than for a single atomic** — an autonomous operation walks a chain and can reach further than you expect. Bound it to the in-scope hosts (the agents you deployed), cap the operation, and re-read the scope file before starting it. A planner that would pivot to an out-of-scope host is a mid-run abort, not a continue.

## Stratus Red Team — cloud & Kubernetes atomics

**Stratus Red Team** (Datadog, v2.32.1) is the cloud equivalent of a single atomic — a **self-contained Go binary** that detonates a granular cloud/K8s attack technique against AWS, Azure, GCP, or Kubernetes, mapped to the **ATT&CK Cloud/Containers** matrices.

```bash
stratus list                                            # techniques available, with ATT&CK ids
stratus warmup   aws.credential-access.ec2-get-password-data   # prepare prerequisite infra (opt-in)
stratus detonate aws.credential-access.ec2-get-password-data   # run the technique — the CloudTrail event to detect
stratus cleanup  aws.credential-access.ec2-get-password-data   # clean up — tear the technique's resources down
stratus status                                          # what is warm / detonated / to be cleaned
```

- **warmup → detonate → cleanup** is the lifecycle; `cleanup` is mandatory and Stratus tracks state so a forgotten `detonate` is visible in `status`.
- The point is the **telemetry it generates** — a detonated technique produces the exact CloudTrail / Azure Activity Log / GCP Audit Log event your cloud detection should catch; the blue half then queries the log store for it.
- Use Stratus for the cloud/K8s row of the coverage matrix; use Atomic Red Team/Caldera for the host/endpoint rows. It runs against **the in-scope cloud account only** — a detonation creates and deletes real cloud resources, so a wrong account is both a scope breach and a cost.

## VECTR — the scoreboard (track, benchmark, spot drift)

**VECTR** (Security Risk Advisors; Community Edition **ce-9.14.1**, self-hosted; Enterprise Edition is the commercial benchmarking/executive-reporting variant) is where purple-team outcomes are *tracked over time*, not executed. Each test case records the technique (ATT&CK id), the tool that ran it, and the outcome — **blocked / alerted / logged / no signal** — building the coverage matrix across the ATT&CK map and, run round over round, the **drift** view. SRA's **Threat Simulation Index 2026** is a ready benchmark catalogue of techniques worth simulating. VECTR is optional — the purple-team report's detected/not-detected matrix carries the same data — but it is the natural home when the cadence is continuous and the audience wants a benchmarked trend.

## Anti-patterns

- **Running an atomic with no paired detection check.** Detonating `T1003.001` and not asking "did anything catch it?" is noise, not a purple-team run. *Fix:* every simulate is immediately followed by `penetration-testing:detection-validation` for the same ATT&CK id.
- **`Invoke-AtomicTest <technique>` with no `-TestNumbers`.** Runs every atomic under the technique, some more intrusive than intended. *Fix:* select one test, read `-ShowDetailsBrief` first, run it, clean it up.
- **Skipping `-Cleanup` / `stratus cleanup`.** Leaves users, files, services, or cloud resources behind — a §5 cleanup violation and, in the cloud, an ongoing cost. *Fix:* cleanup is part of every technique's run, followed by a verification that the artifact is gone.
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

## Cross-references

- **`purple-team-engineer`** (`security/agents/purple-team-engineer.md`) — the orchestrator that runs this skill in its **Simulate** step and owns the scope-file gate this skill enforces; it pairs each simulation with the blue assertion.
- **`penetration-testing:detection-validation`** — the **blue half**, run immediately after each technique: it queries the log/alert store and asserts the detection fired for that ATT&CK id. Simulation without it is noise.
- **`security-governance:detection-engineering`** (`security/detection-engineering/`, `security-governance` plugin) — **authors** the Sigma rules/detections this lane validates. A technique with no authored detection is a coverage gap to route there; a not-detected technique whose rule exists is a broken rule to route there. Author there, validate here.
- **`penetration-tester`** (`security/agents/penetration-tester.md`) — the offensive sibling in the same plugin: it **exploits** to prove an attacker can chain findings into impact; this **simulates** known atomics to prove the guardrails *detect* them. Shared ATT&CK Enterprise spine and the same §5 authorization machinery; a chain `penetration-tester` completed undetected is the exact hypothesis for a new detection to simulate here.
- **`observability-engineer-*`** + **`be-<stack>:queries`** / **`be-<stack>:dashboards`** *(peers, named not loaded)* — own the telemetry substrate (Loki/Prometheus/Tempo, the log/alert pipeline) the blue half queries. A technique that fired but produced no log the SIEM could see is a **telemetry gap** routed to them, not a passing control.
- **`penetration-testing:reporting`** (`security/pentest-reporting/`) — where every simulated technique is written to the action log and where the cleanup-verification section is closed.
- **`infra-security-tester`** (`devops/`) — the posture sibling; its Cloud/Containers benchmark findings can scope which cloud techniques (Stratus) are worth simulating.
