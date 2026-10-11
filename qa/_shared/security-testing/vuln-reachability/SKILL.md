---
name: vuln-reachability
description: Use to de-noise an existing SCA/SAST gate so it fires on EXPLOITABLE-AND-REACHABLE, not raw CVSS — a post-processing stage that joins scanner output on CVE id against CISA KEV + EPSS + VEX, then rewrites the verdict. Read-only, no re-scan, safe every PR. Language-agnostic. Triggers "our CVE gate is too noisy", "gate on exploitability not CVSS", "add EPSS/KEV weighting". Do NOT use to run a scan (`dependency-scan`/`image-infra-scan`/`code-scan`) or to exploit a CVE (`exploit-validation`).
---

# Security Testing — Vulnerability Reachability & Exploitability Weighting

A raw CVE gate blocks on **CVSS**, and CVSS answers the wrong question: it scores *how bad the flaw is in the
abstract*, not *whether this deployment can be attacked through it*. The result is a gate that reds the build
on a CVSS-9.8 nobody can reach while a CVSS-6 that is **actively exploited in the wild** slips through as a
warning — so teams mute it. This skill is the fix: a **post-processing enrichment stage** that takes the
scanner's output unchanged and re-decides each finding against three cheap, authoritative signals —
**is it exploited (KEV), how likely is exploitation (EPSS), is the vulnerable code reachable (VEX)** — and
gates on the enriched verdict.

It is **not a scanner** and **re-scans nothing.** `dependency-scan`, `image-infra-scan`, and `code-scan` keep
running unchanged and stay authoritative on *"is the vulnerable component present."* This skill is a **pure
function of their output + cached public feeds** — it joins on the CVE id, so it works identically for Trivy,
Grype, `npm audit`, OWASP Dependency-Check, and `dotnet list --vulnerable`. It is **read-only and safe on
every PR** — it reads public feeds and local scanner JSON, sends no payloads, and needs no authorization gate
(the one exploit-weighting skill that doesn't). It pairs with `qa-<stack>:security-foundations` (the OWASP backbone,
esp. **A03:2025 Software Supply Chain Failures**) — load that alongside.

## The single most important rule: never multiply EPSS by CVSS

FIRST states it outright — *"Do not multiply an EPSS score by an ordinal (such as CVSS). The product has no
interpretable meaning."* Combine the signals with **boolean predicates only**, in a fixed precedence:

```
ACT     if CVE ∈ KEV                                → block + page   (exploited in the wild — ground truth)
DEFER   if VEX not_affected (reachability)          → suppress, keep the record   (evaluated AFTER KEV)
ATTEND  if CVSS >= 7.0 AND EPSS >= 0.10             → block          (tighten: AND Automatable==yes AND internet_facing)
TRACK   otherwise                                    → ticket, no block
```

Three design invariants, each load-bearing:

1. **KEV is evaluated first and unconditionally.** A KEV CVE is ACT *regardless of EPSS, CVSS, or
   reachability* — it is known-exploited, which is ground truth that outranks every prediction. Measured
   against today's feeds, a pure `EPSS>=0.1` gate **misses 24% of KEV** (395 known-exploited CVEs, one at
   EPSS 0.0025). So **KEV must be an independent OR-branch, never folded into the EPSS threshold.**
2. **Reachability suppresses, never promotes.** A VEX `not_affected` demotes a finding; an *unreachable* KEV
   CVE is **still ACT**, because reachability analysis has false negatives and KEV is ground truth. VEX runs
   **after** the KEV check — never before, or a `not_affected` statement could silently suppress a
   known-exploited CVE.
3. **A de-noised gate demotes, it never deletes.** Every suppressed finding stays in the report
   (`--show-suppressed` / `ignoredMatches`), with the feed versions that produced the verdict recorded — a
   gate that *deletes* findings is an audit failure, not a de-noised gate.

## Decision matrix — which signal, from where

| Signal | Source | Feed / tool | `references/` | What it answers |
|---|---|---|---|---|
| **Exploited in the wild** | CISA KEV | `known_exploited_vulnerabilities.json` (1.6 MB, load once into a set) | `epss-kev.md` | is it *actually* being exploited — ground truth |
| **Exploitation likelihood** | EPSS v5 | daily CSV feed (preferred) or the JSON API | `epss-kev.md` | 30-day exploitation probability, 0–1 |
| **Automatable / Technical Impact** | CISA Vulnrichment | `cisagov/vulnrichment` (free, per-CVE, SSVC ADP) | `epss-kev.md` | the two best gate inputs CVSS base score isn't |
| **Reachability** | VEX (OpenVEX/CSAF) | govulncheck / osv-scanner / dep-scan → a VEX file | `vex-reachability.md` | is the vulnerable *function* on the execute path |
| **The verdict** | the join | a ~60-line enrichment stage over scanner JSON | `enrichment-gate.md` | ACT / ATTEND / DEFER / TRACK + exit code |

**Rule of thumb:** KEV + EPSS enrichment is the **immediate** win — two cached files, a CVE-id join, no
tooling change, and it de-noises *any* existing gate. Reachability (VEX) is the **second** layer — it needs a
call-graph tool per language and mostly demotes; add it once the KEV+EPSS gate is trusted.

## The framework: SSVC, and why not CVSS

The gate's shape copies **SSVC** (Stakeholder-Specific Vulnerability Categorization, CMU-SEI + CISA) — a
decision tree, not a score. CISA's **BOD 26-04** (June 2026, superseding the revoked BOD 22-01) prioritizes on
four variables — **Asset Exposure · KEV Status · Exploit Automation · Technical Impact** — and **CVSS base
score is deliberately not one of them.** That is the whole thesis: gate on exploitability and reachability,
use CVSS only as the impact input inside the ATTEND branch.

**CISA Vulnrichment** publishes the SSVC inputs *free, per-CVE, machine-readable* into the CVE record's ADP
container (`Exploitation` none/poc/active · `Automatable` yes/no · `Technical Impact` partial/total). This is
the most under-used feed in the whole design — `Automatable` and `Technical Impact` are better gate inputs
than a CVSS base score and cost nothing.

## Setup — pinned versions & feeds (2026-08)

```bash
# The two feeds — fetch ONCE per pipeline into a date-keyed cache, read locally (avoids the API traps).
curl -sO https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json   # KEV (note /feeds/)
curl -sL -o epss.csv.gz https://epss.empiricalsecurity.com/epss_scores-current.csv.gz          # EPSS v5 CSV

# EPSS API (single lookups / small batches ≤100 — prefer the CSV for a CI gate).
curl -s "https://api.first.org/data/v1/epss?cve=CVE-2021-44228"

# Reachability → VEX (OSS, per language). OpenVEX is the interop format.
go install golang.org/x/vuln/cmd/govulncheck@v1.7.0        # Go, symbol-level; -format openvex
# osv-scanner v2.5.0 (--call-analysis), OWASP dep-scan 6.3.0 (multi-lang), Grype v0.117.0 (consumes VEX).

# VEX consumers already in the library: Trivy v0.74.0 (--vex, --show-suppressed).
```

> **EPSS is v5** (released 2026-06-15; the machine-readable `model_version` is **`v2026.06.15`**, on line 1
> of every CSV). It is governed by the **FIRST EPSS SIG but generated by Empirical Security** — the CSV host
> is `epss.empiricalsecurity.com` (the old `epss.cyentia.com` 301-redirects there). **KEV is now driven by
> BOD 26-04, not the revoked BOD 22-01** — say so; the live feed's `requiredAction` text proves it. Pin no
> tool to `:latest` — record `model_version` + KEV `catalogVersion` in every report so a verdict reproduces.

## The enrichment procedure

1. **Cache the feeds once** per pipeline (date-keyed): KEV JSON → a `set` of `cveID`; EPSS CSV → a
   `dict[cve] → (epss, percentile)`. Record `catalogVersion` and `model_version`. Local reads make the gate
   deterministic, offline-reproducible, and free of the API's batching traps.
2. **Parse the scanner output** (Trivy/Grype/npm-audit/OWASP-DC/dotnet JSON or SARIF) into `(cve, cvss,
   pkg)` rows. The scanner stays authoritative on presence.
3. **Join and decide** per the precedence above: KEV → VEX-suppress → CVSS+EPSS → TRACK. A CVE missing from
   EPSS is `None`, **never `0`** (absence ≠ safe).
4. **Emit the verdict** on one of three paths (`enrichment-gate.md`): an **exit code** (`ACT|ATTEND` ⇒ 1);
   **enriched SARIF** (write the exploitability into `security-severity` + `tags:["KEV","ACT"]` so
   code-scanning sorts on exploitability, not CVSS); or a **Trivy `--ignore-policy` Rego allowlist** of the
   below-gate CVEs so the scanner's own exit code comes out de-noised.
5. **Keep every suppression visible** and stamped with the feed versions; a demoted finding is a ticket, not
   a deletion.

A concrete run (real feeds, `catalogVersion=2026.08.14`): three CRITICALs in, three different verdicts out —
`CVE-2021-44228` (in KEV) → **ACT/page**; `CVE-2024-3094` (EPSS 0.86) → **ATTEND/block**; `CVE-2023-45853`
(zlib, CVSS 9.8 but EPSS 0.032) → **TRACK/ticket**. The zlib case is the whole point: the highest-CVSS
finding, correctly demoted. Add a VEX `not_affected / vulnerable_code_not_in_execute_path` for it → **DEFER**.

## Reachability myth-busters (state these honestly)

- **Grype has no reachability** — it *consumes* OpenVEX. Reachability comes from an upstream call-graph tool
  (govulncheck) that *emits* the VEX Grype then reads.
- **Falco and Tetragon are not SCA de-noisers.** Both are eBPF *threat detection* with no SBOM to filter a
  CVE list against. Tetragon's file-access tracing is the right *primitive* (Kubescape's runtime relevancy
  rests on it) but ships no de-noising product. Don't wire them in for this.
- **Semgrep Supply Chain is proprietary** (not the LGPL CE engine) and does **no reachability on transitive
  dependencies** — the layer where most CVEs live. **Snyk's Runtime Sensor is discontinued** (archived
  2026-05). The only OSS runtime-reachability product is **Kubescape/ARMO** (eBPF node-agent → filtered
  SBOM). Commercial static-reachability tools (Endor, Backslash — which claims 80–90% actionable-noise
  reduction, Checkmarx Exploitable-Path) are name-only references; their language coverage is always far
  narrower than plain SCA, and **Go support is the sharpest discriminator.**

## Anti-patterns

- **Multiplying EPSS × CVSS** for a "risk score." The product is meaningless (FIRST). *Fix:* boolean
  predicates in the fixed precedence.
- **Folding KEV into the EPSS threshold** ("EPSS ≥ 0.1 covers the exploited ones"). It misses 24% of KEV.
  *Fix:* KEV is an independent, first, unconditional OR-branch.
- **Running VEX suppression before the KEV check.** A `not_affected` statement then silently suppresses a
  known-exploited CVE. *Fix:* KEV first, VEX after.
- **Treating a missing EPSS score as 0.** Absence ≠ safe. *Fix:* `None`, and let KEV/CVSS still decide it.
- **Per-CVE HTTP to the feeds in CI**, or an EPSS batch > ~100. The KEV catalog is one file (load once); the
  EPSS API **silently returns HTTP 200 with `total:0`** on an oversized batch and **silently drops unknown
  CVEs**. *Fix:* cache both feeds locally; if you must hit the API, batch ≤100 and assert the returned row
  count.
- **A de-noised gate that deletes findings.** Then a re-prioritization is indistinguishable from a coverage
  gap. *Fix:* demote, keep visible (`--show-suppressed`/`ignoredMatches`), stamp the feed versions.
- **`osv-scanner --call-analysis=rust` in CI unaware it compiles the project** (runs `build.rs` — arbitrary
  code execution). *Fix:* only on trusted code; know Go is default-on and wraps govulncheck.

## Rules (hard constraints)

- **Never multiply EPSS by an ordinal.** Combine KEV / EPSS / CVSS / reachability with **boolean predicates**
  in the fixed precedence: **KEV(ACT) → VEX-suppress(DEFER) → CVSS≥7 ∧ EPSS≥0.1(ATTEND) → TRACK.**
- **KEV first and unconditional; reachability suppresses but never promotes; VEX after KEV.** A missing EPSS
  score is `None`, never `0`.
- **Post-process, don't re-scan.** The existing gates stay authoritative on presence; this is a pure function
  of their output + cached feeds, joined on CVE id — works for Trivy, Grype, npm-audit, OWASP-DC, dotnet.
- **Cache both feeds once per pipeline, date-keyed;** record `catalogVersion` + EPSS `model_version` so a
  verdict reproduces (the same CVE legitimately changes verdict day to day).
- **Demote, never delete** — every suppression stays in the report and is ticketed. `knownRansomwareCampaignUse
  == "Known"` (a string), never truthiness.
- **Map to A03:2025** (Software Supply Chain Failures); the enriched severity, not CVSS, drives the gate and
  the code-scanning sort (`security-severity`).
- **Honest tooling:** Grype consumes VEX (doesn't compute reachability); Falco/Tetragon are not de-noisers;
  Semgrep SC is proprietary + no transitive reachability; Kubescape is the only OSS runtime option. No secrets
  in feed/config; the feeds need no auth.

## Cross-references

- `qa-<stack>:security-foundations` — the OWASP backbone (**A03:2025 Software Supply Chain**), the triage discipline
  (ticketed suppressions, gate NEW) this skill sharpens. **Load alongside.**
- `qa/<stack>/skills/security-testing/dependency-scan` (npm audit · OWASP DC · `dotnet list --vulnerable`) ·
  `qa-<stack>:image-infra-scan` (Trivy) · `qa-<stack>:code-scan` (Opengrep/Semgrep) — the **detection
  gates** whose output this skill enriches. It re-scans none of them; it re-decides their verdicts. This is
  the single biggest quality-of-life win for those gates.
- `qa-<stack>:exploit-validation` — the sibling that *proves* a reachable CVE is exploitable. Reachability
  says "the code is on the execute path"; exploit-validation fires the payload. This skill prioritizes what
  that one then proves.
- `qa/manual/bug-report-writer` — an ACT/ATTEND verdict on a real CVE is written up with its KEV/EPSS/VEX
  evidence and feed versions.
- `qa/_shared/agents/qa-security.md` — the orchestrator; this skill runs as the **reachability-weighting
  step inside Step 2** (static gates), reprioritizing SCA/SAST output before the gate decision.
- Deep dives: **`references/epss-kev.md`** (both feeds, the API traps, thresholds, Vulnrichment/SSVC) ·
  **`references/vex-reachability.md`** (OpenVEX + govulncheck/osv-scanner/dep-scan/Grype/Kubescape, the
  myth-busters) · **`references/enrichment-gate.md`** (the join, the decide function, the three output paths,
  ordering & caching, the Dependency-Track server alternative).
