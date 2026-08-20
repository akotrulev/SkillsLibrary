---
name: secgov-detection-engineering
description: Use to author and test security detections as code — Sigma rules and alert-as-code that catch attacker BEHAVIOR in logs at runtime, mapped to MITRE ATT&CK, version-controlled, and unit-tested against true/false log samples before deploy. Language-agnostic, blue-team. Triggers "write a Sigma rule for this technique", "detection-as-code pipeline", "author an alert for lateral movement", "turn this pentest finding into a detection", "what detections cover our ATT&CK gaps". Not for scanning code/config for vulns (`qa-security`), running the attack that a detection should catch (`penetration-tester`), validating a detection actually fires (`purple-team-engineer`), or app-health dashboards (`observability`).
---

# Security Governance — Detection Engineering (Sigma · alert-as-code · ATT&CK-mapped)

Detection engineering is the standing blue-team counterpart to the offensive lanes: where `penetration-tester` proves an attacker can chain findings into impact and `qa-security` finds the vulnerable code, this skill authors the **detections that catch the attacker's behavior in your logs at runtime** — and proves each one fires on a true event and stays quiet on a benign one. It is **detection-as-code**: rules live in Git, are reviewed in pull requests, unit-tested against log samples, converted to your SIEM's query language, and promoted through a pipeline — never click-authored in a console where no one can review or roll them back.

This skill is **language-agnostic** (Sigma is vendor-neutral YAML; sigma-cli/pySigma are Python; the backends are your SIEM) and homes in the **`security-governance`** plugin, loaded by the **`security-architect`** agent (Stage 5). The **`purple-team-engineer`** agent (Stage 4, `penetration-testing` plugin) does not load this skill — it **consumes the detections authored here** as feedstock: its `purpleteam-detection-validation` reads these Sigma rule files, converts them with `sigma-cli`, and asserts each fires. This skill **authors** detections; it does not run the attacks (`penetration-tester`) or assert the detection fired against a live simulation (`purple-team-engineer`).

> **This is defensive authoring — no gate, but no telemetry means no detection.** Writing and converting Sigma rules touches no live target, so this skill carries no authorization gate (unlike the offensive lanes). Its one hard prerequisite is a **telemetry source**: a detection that queries a log field your stack never emits is a **gap, not a passing control**. Confirm the data source exists before claiming coverage.

## Two spines, stated per detection

- **MITRE ATT&CK — the primary spine.** Every detection names the **technique id(s)** it covers (`T1021.001` RDP lateral movement, `T1003.001` LSASS dumping, `T1078` valid accounts). **Pin the ATT&CK version in the rule/repo** — technique ids move between versions: **v18** (2025-10-28) replaced the free-text `Detections` field with structured **Detection Strategies · Analytics · Data Components** (author your detections to a Data Component so you know what telemetry each needs), and **v19** (2026-04-28 — Enterprise: 15 tactics · 222 techniques · 475 sub-techniques) **retired `Defense Evasion` and split it in two: `Stealth` keeps the old id `TA0005`, and `Defense Impairment` is the new `TA0112`** — so a rule tagged to the old `defense-evasion` tactic is now mis-mapped. **v19.2** (2026-08-06) is the current release; pin the exact release including the minor, and track the version you author against.
- **OWASP — where the detection targets a web/API attack class.** A detection for SQLi attempts against an endpoint carries **A05:2025 Injection**; a detection over WAF blocks or missing-header findings carries **A02:2025 Security Misconfiguration**; a detection for a known-vulnerable dependency being exercised carries **A03:2025 Software Supply Chain Failures**. A *missing or broken* detection is itself **A09:2025 Security Logging and Alerting Failures** — the category this whole lane exists to close. **Use the 2025 numbering** (Injection moved A03→A05 in the 2025 edition); the `qa-security` scanners already do. OWASP is secondary here (this lane watches behavior in logs, not code).

Severity of a *missing* or *broken* detection is scored on the library's **blocker/major/minor/nit** table (this is defensive authoring, not an offensive finding — no CVSS divergence). Detection **efficacy** is tracked separately as coverage (true-positive fired · false-positive rate · ATT&CK techniques covered vs in the threat model).

## Setup — pinned tool versions (2026-08)

```bash
# sigma-cli 3.1.0 — the official CLI (pySigma-based; the deprecated `sigmac` is gone). Needs Python >= 3.10.
pipx install sigma-cli                       # or: pip install sigma-cli==3.1.0

# Install the backend + pipeline for YOUR SIEM (40+ targets: Splunk SPL, Elastic ES|QL/DSL, Sentinel KQL,
# QRadar AQL, Chronicle YARA-L, …). One plugin per target.
sigma plugin list
sigma plugin install splunk                  # or: elasticsearch · microsoft365defender (Defender/Sentinel) · …

# Convert a rule to the target query language, applying a field-mapping pipeline.
sigma convert -t splunk -p splunk_windows rules/lateral_movement_rdp.yml
sigma check rules/                           # lint: schema, required fields, ATT&CK tags — run in CI
```

> **Renames / gotchas to state honestly.** `sigmac` (the legacy converter) is **dead** — use `sigma-cli` (pySigma). The **SigmaHQ community ruleset** (3,000+ ATT&CK-mapped rules) is a **baseline to extend, not a set to enable wholesale** — importing all of it produces alert fatigue, not coverage. A backend converts syntax; it does **not** guarantee your logs carry the fields the rule references — that is what the field-mapping **pipeline** (`-p`) and a telemetry check are for.

## The Sigma rule — anatomy and the fields that matter

```yaml
title: Suspicious RDP Logon From New Source (Lateral Movement)
id: 6f3b9c2a-1d4e-4a7b-9c8f-0e1a2b3c4d5e     # stable UUID — never reused, never regenerated on edit
status: experimental                          # experimental → test → stable (promotion tracks maturity)
description: Detects an interactive RDP logon (type 10) to a host from a source not seen before, a common
  lateral-movement step after credential theft.
references:
  - https://attack.mitre.org/techniques/T1021/001/
author: security-architect
date: 2026-08-20
tags:
  - attack.lateral-movement                   # tactic (ATT&CK v19 — verify the tactic slug for your version)
  - attack.t1021.001                           # technique — the primary spine
logsource:
  product: windows
  service: security                            # THE telemetry contract — this log must actually be collected
detection:
  selection:
    EventID: 4624
    LogonType: 10
  condition: selection
falsepositives:
  - Jump hosts and admin bastions with legitimate broad RDP access — tune with an allowlist of known sources
level: high                                    # informational | low | medium | high | critical
```

- **`id`** is a permanent UUID — edits keep it, so tuning history and SIEM deployment state track one rule.
- **`logsource`** is the **telemetry contract**: it names the log that must be collected for the rule to fire. If your stack does not ship `windows/security` (or the equivalent), the rule is a documented gap, not a control.
- **`tags`** carry the ATT&CK mapping — the spine. `sigma check` fails a rule missing them.
- **`falsepositives`** is not optional prose — it is the tuning contract the reviewer holds you to. A rule with no stated false-positive is either trivially noisy or not thought through.
- **`level`** feeds the SIEM's alert severity; keep it honest so triage priority is real.

## Sigma Correlations — multi-event detections

A single log line rarely proves an attack; a **rate**, a **sequence**, or a **join** does. Sigma **Correlations** (native since the pySigma era) express these without dropping to backend-specific SPL/KQL:

- **`event_count`** — N failed logons (`T1110` brute force) within a window → then a success.
- **`value_count`** — one source touching N distinct hosts in a window (spray / lateral scan).
- **`temporal` / `temporal_ordered`** — technique A then technique B within a window (the chain a single rule can't see — e.g. LSASS access `T1003.001` followed by outbound to a new host `T1021`).

Author the base rules, then a correlation that references them by `id`. Not every backend compiles every correlation type — `sigma convert` tells you; where it can't, the rule documents the SIEM-native equivalent rather than silently dropping the logic.

## Detection-as-code — the pipeline (the whole discipline)

Detections are software artifacts. The lifecycle, in a Git repo with CI (GitHub Actions / GitLab CI):

1. **Hypothesis** — a detection starts from a *source*: an ATT&CK technique in the threat model (`devops-threat-modeling`), a `penetration-tester` finding ("we reached domain admin and nothing alerted"), an incident, or a new CVE's exploitation behavior. Name the source in the rule's `references`.
2. **Author** the Sigma rule (or alert-as-code — below), `status: experimental`.
3. **Lint** — `sigma check rules/` in CI: schema, required fields, ATT&CK tags present, UUID unique.
4. **Unit-test the detection** — this is the step teams skip and it is the point of the lane. Run the rule against a **known-true** log sample (it must fire) *and* a **known-benign** sample (it must stay quiet). A rule that fires on both is a false-positive machine; a rule that fires on neither is dead. Store the samples beside the rule (`tests/`), redacted of any real secret/PII.
5. **Convert** — `sigma convert` to the target backend(s) in CI.
6. **Deploy to staging → promote to prod** — through the pipeline, `status: experimental → test → stable` as it earns confidence, with **rollback** (revert the commit, re-deploy) always available.
7. **Validate** — hand to **`purple-team-engineer`** (the purple-team lane): its `atomic-simulation` runs the ATT&CK technique on an authorized env and `detection-validation` asserts *this* rule fired. A detection is not "done" until something has proven it fires against a real technique — authoring is half the loop.
8. **Tune** — false positives from production feed back into `falsepositives` and the selection logic. An untuned noisy rule that analysts mute is worse than no rule (it hides the signal and erodes trust).

**Alert-as-code beyond Sigma.** Where a detection can't be expressed in Sigma (a SIEM-native ML job, a Sentinel Analytics rule, an Elastic detection-engine rule with an exception list), keep it *as code* anyway: Elastic detection rules via the Detections API in Git, Sentinel Analytics rules as Bicep/ARM, Splunk `savedsearches.conf` in a version-controlled app. The medium changes; the discipline (reviewed, tested, promotable, rollback-able, ATT&CK-tagged) does not.

## Anti-patterns

- **Enabling the whole SigmaHQ ruleset.** 3,000 rules firing at once is alert fatigue, not coverage — analysts mute the channel and miss the real one. *Fix:* start from your threat model's techniques; import the matching community rules, tune them, and grow deliberately.
- **A detection with no telemetry source.** The rule converts cleanly and never fires because the log field it queries is never collected. *Fix:* verify the `logsource` is actually shipped (name `observability-engineer-*` / `queries` to confirm the pipeline) before claiming the technique covered.
- **Authoring in the SIEM console.** A rule clicked into Splunk/Sentinel has no review, no test, no version history, no rollback. *Fix:* author as Sigma/alert-as-code in Git; the console is a deploy target, not the source of truth.
- **Mapping to a stale ATT&CK version.** A rule tagged `attack.defense-evasion` is mis-mapped after v19's Stealth/Defense-Impairment split. *Fix:* pin the ATT&CK version in the repo; re-map on upgrade.
- **Shipping a rule with no false-positive test.** It looks like coverage and pages the analyst at 3am on a backup job. *Fix:* the true-AND-false sample test is a merge gate, not a nicety.
- **Claiming coverage without validation.** "We have a rule for T1003" ≠ "we detect T1003." *Fix:* the rule is a hypothesis until `purple-team-engineer` proves it fires; state which techniques are *authored* vs *validated*.
- **A real secret/host in a test log sample.** Detection test fixtures often come from real incident logs. *Fix:* redact per the loot rule; nothing sensitive committed.

## Hard rules

- **Every detection maps to ≥1 ATT&CK technique**, and the **ATT&CK version is pinned** in the repo (v19 current; re-map on upgrade — technique/tactic ids move).
- **No detection without a telemetry source** — confirm the log is collected; green ≠ covered. A missing source is a documented gap routed to `observability-engineer-*`.
- **Unit-test every rule against a true-AND-benign sample before deploy** — fire on the attack, stay quiet on the benign; this is a merge gate.
- **Detection-as-code, not click-ops** — versioned, PR-reviewed, tested, promotable, rollback-able; the SIEM console is a deploy target only.
- **Authored ≠ validated** — state which techniques are authored vs proven-firing; validation is `purple-team-engineer`'s. Detection engineering is half of a two-half loop.
- **Tune for precision** — a stated false-positive per rule; an untuned noisy rule that gets muted is worse than none.
- **Redaction** — test log samples carry no real secret/PII; pin tool versions (sigma-cli 3.1.0; the 1.x line it superseded is two majors behind); the community ruleset is a baseline to extend, never enabled wholesale.

## Cross-references

- **`security-architect`** (`security/agents/security-architect.md`) — the roll-up agent that loads this skill: an ATT&CK coverage gap in the posture picture becomes a detection to author here.
- **`purple-team-engineer`** (`security/agents/purple-team-engineer.md`, `penetration-testing` plugin) — the **validation** half: `atomic-simulation` runs the technique, `detection-validation` asserts this rule fired. You author; it proves. Shared ATT&CK spine.
- **`penetration-tester`** (`security/agents/penetration-tester.md`) — offensive **input**: a chain that reached impact undetected is the exact hypothesis for a new detection ("author the rule that would have caught the LSASS dump → lateral hop").
- **`devops-threat-modeling`** (`devops/threat-modeling/`) — the threat register scopes *which* techniques to write detections for first; it routes threats to the lanes that test them, this authors the standing detections.
- **`observability-engineer-*`** + **`observability-queries`** *(peers, named not loaded)* — own the telemetry substrate (Loki/Prometheus/Tempo, the log/metric pipeline) your detections query, and the query-language mechanics. A missing `logsource` is a handoff to them. This lane authors the **security** analytics; they own the app-health RED/USE dashboards.
- **`qa-security`** (`qa/_shared/agents/qa-security.md`) — the fence partner: it detects the *vulnerability in the code/config*; this detects the *attacker behavior in the logs at runtime*. A SAST finding is a fix; a detection is a tripwire for when the fix is missed.
- **`secgov-security-hardening`** / **`secgov-secrets-hardening`** — the other defensive-engineering siblings in this plugin: hardening *prevents*, detection *catches what prevention missed* — defense in depth, authored together.
