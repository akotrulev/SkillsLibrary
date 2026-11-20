---
name: passive-scan
description: Use when adding an OWASP ZAP baseline (passive) DAST scan as a CI gate for a TypeScript pipeline. Triggers "add a DAST gate to CI". Not for active injection scans (active-scan).
disable-model-invocation: true
---

# Security Testing — OWASP ZAP Baseline Scan (TypeScript)

OWASP **ZAP** (Zed Attack Proxy) is the de-facto open-source DAST (dynamic application security testing)
scanner. The **baseline scan** (`passive-scan.py`, shipped in the `ghcr.io/zaproxy/zaproxy` Docker image)
spiders a **running** app for a short bounded time, runs ZAP's **passive** scan rules — it reads the
traffic it generates, it does **not** fire attack payloads — and reports alerts by risk level, exiting
**non-zero to fail the build** when alerts cross a threshold. This is the canonical *shift-left DAST gate
in the pipeline*: fast, safe to run against a deployed/ephemeral env, and CI-native.

> **⚠️ Baseline (passive) vs full scan (active) — the line you must not cross in CI-against-a-shared-env.**
> `passive-scan.py` runs **passive** rules only: it observes the spidered/proxied traffic and flags
> issues it can *see* (missing `Content-Security-Policy`, `Set-Cookie` without `Secure`/`HttpOnly`,
> verbose `Server` headers, info leaks). It sends **no attack payloads**, so it is **safe and fast**
> (~1–few minutes) and the right gate for every PR. `zap-full-scan.py` adds the **active** scanner, which
> *injects* SQLi/XSS/traversal payloads — it finds far more but **mutates state and must never run against
> production or a shared environment**. This skill is the **baseline** gate. Reach for the full scan only
> against a throwaway environment you own, on a slower cadence.

> **Tool-invoked-via-Docker, not a library — the shape of this node.** ZAP's baseline scan is a **Docker
> invocation**, language-agnostic. There is **no in-process ZAP SDK** you embed. TypeScript is the
> **canonical** stack here only because it's the house default — the scan itself is `docker run … 
> passive-scan.py`. So this node is **CLI/Docker-driven** (the same port shape as lighthouse-ci): the
> three stacks differ only in how they (a) stand up the target app, (b) invoke the `zaproxy` image, and
> (c) parse the JSON report and assert. The `.NET`/`Java` siblings re-express the *same Docker
> choreography* with `Process`/`ProcessBuilder` + their JSON parser. See them for that.

## Decision matrix — where ZAP baseline fits

| Need | Use | Why |
|------|-----|-----|
| Passive DAST gate on a **running** app in every PR (headers, cookie flags, info leaks) | **this skill** | Safe (no payloads), fast, CI-native; exits non-zero to fail the build |
| Deep active attack testing (SQLi/XSS/traversal payloads) on a throwaway env | `zap-full-scan.py` (out of scope here) | Active scanner mutates state — never prod/shared; slower cadence |
| **Dependency / library** CVEs (vulnerable npm packages, transitive CVEs) | dependency-scan | SCA reads your lockfile; ZAP scans running HTTP — orthogonal layers |
| Per-component **accessibility** rule assertions | axe-playwright | Different concern; same *ticketed-baseline triage* discipline applies |

**Rule of thumb:** ZAP baseline is your **passive DAST PR gate** against a running app. It complements —
does not replace — SCA dependency scanning: they are different layers (running-app HTTP surface vs
your dependency tree). Run both; together they close Step 2's `security-testing` family.

## Setup — no SDK, just Docker (and optionally the GitHub Action)

There is nothing to `npm install` for the scan itself — you need **Docker** on the runner and the ZAP
image:

```bash
docker pull ghcr.io/zaproxy/zaproxy:stable      # the image carrying passive-scan.py
```

For the programmatic (test-driven) path you only need a JSON parse + your test runner, both already
present in a TS shop (`node:child_process`, `node:fs`, Vitest). For the CI-first path you need **no local
install at all** — the `zaproxy/action-baseline` GitHub Action wraps the image.

## The baseline scan model — spider, passive-scan, report, exit-code

`passive-scan.py -t <targetUrl>` does three things against an **already-running** app:

1. **Spider** the target for `-m <minutes>` (default **1**) to discover URLs — optionally `-j` to add the
   **Ajax spider** for JS-heavy SPAs.
2. **Passive-scan** the discovered traffic (no attack payloads) and collect **alerts** by risk:
   **High / Medium / Low / Informational**.
3. **Report** (`-J`/`-r`/`-x`/`-w`) and **exit with a code that gates the build**.

The key flags:

| Flag | Meaning |
|------|---------|
| `-t <url>` | **Target** URL (required) — the running app to scan |
| `-m <min>` | Spider duration in minutes (default `1`) |
| `-j` | Also run the **Ajax spider** (for SPA/JS-rendered routes) |
| `-c <file>` | **Rules config** file — flip rule-ids to `IGNORE`/`WARN`/`FAIL` (the triage gate; see below) |
| `-l <level>` | Minimum alert level to **report**: `PASS`/`IGNORE`/`INFO`/`WARN`/`FAIL` |
| `-J/-r/-x/-w` | Write **JSON / HTML / XML / Markdown** report |
| `-a` | Include **alpha** passive rules (more coverage, more noise) |
| `-I` | Do **not** fail (exit 0) on warnings — only `FAIL`-level alerts fail |
| `-n <ctx>` | ZAP **context** file (authenticated scans — see below) |
| `-z <opts>` | Pass-through ZAP command-line options |
| `-T <min>` | Max minutes to wait for ZAP startup |

### Exit codes are the gate

`passive-scan.py` maps alerts to a process exit code — **this is the build-fail mechanism**, identical
across all three stacks:

| Exit | Meaning | Build |
|------|---------|-------|
| `0` | Success — no alerts at or above the gate | ✅ pass |
| `1` | At least one **`FAIL`**-level alert | ❌ **fail** |
| `2` | At least one **`WARN`** and no `FAIL`s | ⚠️ pass-or-fail (your policy) |
| `3` | Other failure (couldn't start, target unreachable) | ❌ fail (infra) |

By default ZAP reports **every** alert as `WARN`, so an unconfigured run exits **2**. You make the gate
meaningful with the **rules config** (`-c`): promote the rules you care about to `FAIL` (→ exit 1, fail
the build) and demote known/accepted ones to `IGNORE`. Treat exit `2` per your policy — many teams pass
on `2` (warnings tracked, not blocking) and hard-fail only on `1`.

## The triage gate — `-c rules.tsv` (front and center, like `axe-playwright`'s ticketed baseline)

A real app's first ZAP run lights up with WARNs. Gating on *every* alert trains the team to ignore the
gate. The disciplined approach is the **ticketed rules config**: a tab-separated file that sets each ZAP
rule-id to `IGNORE`, `WARN`, or `FAIL`, with **every `IGNORE` carrying a ticket + reason** — the exact
same allow-list discipline as `qa-typescript:accessibility-testing`, ported to ZAP.

```tsv
# .zap/rules.tsv — tab-separated: <rule-id>	<IGNORE|WARN|FAIL>	(reason)
# Promote the rules we will not regress on → FAIL (exit 1, fails the build):
10038	FAIL	(Content Security Policy header missing — must ship)
10054	FAIL	(Cookie without SameSite attribute)
# Demote documented, ticketed accepted-risk / false-positives → IGNORE:
10015	IGNORE	(No Cache-control header on public marketing pages — JIRA-3101, accepted)
10096	IGNORE	(Timestamp disclosure false-positive on static asset hashes — JIRA-3102)
# Scope out a third-party widget URL we don't own (rule-id OUTOFSCOPE <regex>):
10027	OUTOFSCOPE	https://widget\.thirdparty\.com/.*
```

- Columns are **tab-separated**: `<rule-id>` ⇥ `<IGNORE|WARN|FAIL>` ⇥ `(reason)`.
- `IGNORE` → not reported. `WARN` → reported, doesn't fail (exit 2). `FAIL` → reported and **fails the
  build** (exit 1). Use `*` as the rule-id to apply to all rules.
- `OUTOFSCOPE` with a **regex** excludes URLs (third-party embeds you can't fix).
- **Discipline (reuse `axe-playwright`'s framing):** gate **new** findings — promote the rules you've fixed to `FAIL`
  so they can never regress; every `IGNORE` is a *documented, ticketed* accepted risk, not a silent
  suppression. Shrink the IGNORE list over time; never grow it to make a real failure go away.

## Running the scan — the CI-first path (`zaproxy/action-baseline`)

The natural home is CI. The official Action wraps the image, runs the baseline, uploads the report
artifact, and (optionally) opens a tracking GitHub issue (cross-link
`qa-typescript:ci-pipelines`):

```yaml
# .github/workflows/passive-scan.yml
name: ZAP Baseline DAST
on: [pull_request]

jobs:
  zap_baseline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5          # needed so the Action can read .zap/rules.tsv

      # Stand up the target app first.
      - name: Start the app
        run: docker compose up -d --wait    # --wait blocks on healthchecks, NOT a sleep

      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.15.0
        with:
          target: 'http://localhost:3000'
          rules_file_name: '.zap/rules.tsv'   # the ticketed triage gate above
          cmd_options: '-a -j'                # alpha rules + Ajax spider for the SPA
          fail_action: true                   # fail the job on alerts (else relies on rules→FAIL)
          allow_issue_writing: true           # open/update a tracking issue (default true)
          artifact_name: zap_baseline_report  # the uploaded report artifact
          token: ${{ secrets.GITHUB_TOKEN }}
```

Action inputs that matter:

- **`target`** (required) — the running app URL.
- **`rules_file_name`** — path to the `-c` rules config (checkout the repo first so it's readable).
- **`cmd_options`** — extra `passive-scan.py` flags (`-a` alpha rules, `-j` Ajax spider, `-m 3`…).
- **`fail_action`** — `true` fails the job if ZAP reports **any** alert; default `false` (then only your
  `FAIL`-promoted rules fail, via the exit-code). Pick one model and be explicit.
- **`allow_issue_writing`** (default `true`) — opens/updates a GitHub issue with the findings.
- **`docker_name`** — defaults to `ghcr.io/zaproxy/zaproxy:stable`; point at `:weekly` for newer rules.
- **`artifact_name`** (default `zap_scan`) — the report artifact name.

> **Wait on a condition, never a sleep.** The app must be **ready** before the scan or you get
> false-clean/exit-3 results. Use `docker compose up --wait` (blocks on healthchecks) or a Testcontainers
> wait strategy — never `sleep 30` / `waitForTimeout`. Global rule: no fixed waits.

## Running the scan — the programmatic path

To drive the scan from a test (assert on parsed counts, attach to Allure) → read `references/programmatic.md`: the one-shot Docker client, its `ZapResult` and the `ZapAlert` shape that the Allure attachment below reads.

## Authenticated scans (keep it light — the headline is the unauthenticated gate)

The baseline gate's sweet spot is the **unauthenticated** surface (headers, cookies, public pages). For
behind-login pages, baseline can take a ZAP **context** file (`-n context.context`) defining auth, or
pass session/auth options through `-z`. Full authenticated flows are really the **full scan's** job — keep
the baseline gate focused. If you do auth, inject any credentials via **env vars read lazily**, never in
the committed context file or `cmd_options` (global rule: no secrets in code).

## Reporting the gate — ZAP report into Allure + CI artifact

`passive-scan.py` writes `report.json` / `report.html` / `report.xml` to the mounted work dir; the Action
uploads them as an artifact and (optionally) opens a tracking issue. Surface the gate in Allure too, so a
failing run names the alerts without re-scanning (cross-link `qa-typescript:test-reports`):

```ts
// support/zap-report.ts
import { allure } from 'allure-js-commons';
import { readFileSync } from 'node:fs';
import type { ZapResult } from './passive-scan';

/** Attach the ZAP HTML + a readable alert summary to Allure so a failure carries the report. */
export function attachZapReport(result: ZapResult): void {
  allure.attachment('zap-report.html', readFileSync(result.reportHtmlPath), 'text/html');
  const summary = result.alerts
    .map((a) => `[${a.riskdesc}] ${a.alert} (rule ${a.pluginid}) ×${a.count}`)
    .join('\n');
  allure.attachment('zap-alerts.txt', summary || 'no alerts', 'text/plain');
}
```

- **Allure** — attach the HTML + a readable alert summary (rule id, risk, count).
- **CI artifact** — the Action's `artifact_name` upload, or upload the work dir yourself (cross-link
  `qa-typescript:ci-pipelines`).
- **Tracking issue** — `allow_issue_writing: true` opens/updates a GitHub issue with the WARN/FAIL set.

## Anti-patterns

- **Running `zap-full-scan.py` (active) against prod or a shared env.** It injects attack payloads and
  mutates state. *Fix:* use the **baseline** (passive) gate here; reserve the full scan for a throwaway
  env you own.
- **Scanning before the app is ready** (`sleep 30` then scan). Races startup → false-clean or exit 3.
  *Fix:* `docker compose up --wait` / a Testcontainers wait strategy on a healthcheck — never a fixed
  sleep (`waitForTimeout`/`Thread.sleep`).
- **Container can't reach the target.** A `localhost` target from inside the ZAP container points at the
  *container*, not your app. *Fix:* `--network host` on Linux CI, or `http://host.docker.internal:<port>`
  on Mac/Windows, or put the SUT and ZAP on a shared Docker network and use the service name.
- **Gating on every alert with no rules config.** Every run exits 2; the team mutes the gate. *Fix:* a
  ticketed `-c rules.tsv` — promote what matters to `FAIL`, `IGNORE` documented accepted risks.
- **Blanket-`IGNORE`ing to make it green.** That hides real findings. *Fix:* `IGNORE` only with a ticket +
  reason in the file; shrink the list over time (the `axe-playwright` discipline).
- **Treating a clean baseline as "secure."** Passive scanning sees only what's on the wire — no business
  logic, no injection. *Fix:* pair with SCA, the full active scan on a safe env, and manual pentest.
- **Committing auth credentials in the context file / `cmd_options`.** *Fix:* env vars, read lazily.
- **`numberOfRuns`-style flakiness ignored — spider time too short for a SPA.** A 1-minute spider may miss
  JS routes. *Fix:* `-j` (Ajax spider) and bump `-m` for SPAs; still bounded, still passive.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **Examples**.
