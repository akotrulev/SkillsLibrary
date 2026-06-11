---
name: qa-security-testing-secrets-scanning
description: Use when scanning a repo and its git history for committed secrets — Gitleaks as the fast PR gate, TruffleHog to verify whether leaked credentials are live — blocking new leaks via pre-commit + CI. Language-agnostic (CLI/Docker). Triggers: "scan for leaked secrets", "add Gitleaks to CI", "a key was committed to the repo".
---

# Security Testing — Secrets Scanning (Shared)

**Secrets scanning** answers one question no other layer does: **"did a credential get committed to the
repo?"** — an AWS access key, an Auth0 client secret, a DB connection string with a password, a private key,
a personal-access token. It reads your **source files and git history**, matches against credential
patterns (and, for TruffleHog, **live-verifies** them), and fails the build / blocks the commit when it
finds one. It's distinct from SAST (insecure *code patterns*) and SCA (vulnerable *dependencies*) — those
read your code structure and your dependency tree; this reads for *literal secrets that should never have
been committed*. Maps to **OWASP A02:2025 Security Misconfiguration** and **A07:2025 Authentication
Failures** (leaked credentials are a direct authn failure).

> **One architectural fact (per `qa-security-shared`).** Gitleaks and TruffleHog are **language-agnostic
> binaries** — they scan bytes and git objects, not a parsed AST or a package manager. A three-language
> split gains nothing, so this is a **single shared skill** under `qa/_shared/security-testing/`, invoked
> identically from any stack's pipeline. Don't triplicate a `docker run`. Load `qa-security-shared`
> alongside it for the OWASP map, the ticketed-triage discipline, and the SARIF → code-scanning spine — this
> skill carries only the secrets-specific tools, the git-history gotcha, and the rotate-not-delete rule.

## Decision matrix — which tool, where

| Need | Use | Why |
|------|-----|-----|
| **Block a secret before it's committed** (fast, local, every commit) | **Gitleaks** as a **pre-commit hook** | Sub-second regex on staged changes; catches the secret before it ever reaches the remote/history |
| **Sweep the full git history** for secrets committed in the past | **Gitleaks `detect`** (whole-repo) | Scans every commit object — finds the secret someone "deleted" but is still in history |
| **Low-noise CI gate** that only fails on **real, live** credentials | **TruffleHog `--results=verified`** | Live-auth check verifies the credential actually works → ~90% fewer false positives → the gate stays trusted |
| Scan **non-git surfaces** (Docker images, S3/GCS buckets, CI logs, a filesystem) | **TruffleHog** | Uniquely scans those sources; Gitleaks is git/filesystem only |
| **Accept the current state** of a legacy repo and gate only NEW secrets | **detect-secrets** (`--baseline`) — or Gitleaks `--baseline-path` | detect-secrets' baseline workflow is purpose-built for "audit once, gate deltas"; Gitleaks' `--baseline-path` does the same |

**2025/2026 recommendation — run both, plainly.** Use **Gitleaks as a fast pre-commit hook** (regex +
optional history sweep — catches the secret *before* it's committed) **and TruffleHog in CI with
`--results=verified`** for a low-noise gate that fails only on credentials proven live. They're
complementary, not redundant: Gitleaks is the cheap broad net at the developer's machine; TruffleHog's
verification is what keeps the CI gate from crying wolf. **Note on Gitleaks' trajectory:** Gitleaks moved to
**security-patch-only maintenance** in 2025 (the successor project is **Betterleaks**) — it's still an
excellent pre-commit default and the most widely deployed scanner, but track the successor. For a legacy
repo drowning in historical findings, **detect-secrets** has the strongest *accept-current-state* `--baseline`
workflow.

## Setup — binaries, Docker, actions

```bash
# Gitleaks — Go binary (Homebrew / Docker / GitHub releases)
brew install gitleaks
docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo

# TruffleHog — Go binary (install script / Docker)
brew install trufflehog
docker run --rm -v "$PWD:/repo" trufflesecurity/trufflehog:latest git file:///repo
```

Both ship official GitHub Actions (`gitleaks/gitleaks-action`, `trufflesecurity/trufflehog`) — wired below.
No secrets in the scanner config itself: a `GITLEAKS_LICENSE` (org-tier) or any auth token is read from env,
lazily, never committed (global rule).

## Running both — history sweep, verified CI gate, pre-commit

### Gitleaks — `detect` (history) vs `protect` (staged), and exit codes

```bash
# Scan the FULL git history of the repo — every commit, not just HEAD. THE important mode.
gitleaks detect --source=. --report-format sarif --report-path gitleaks.sarif

# Scan only STAGED changes (the pre-commit path — fast, pre-commit). Catches before the commit lands.
gitleaks protect --staged --source=.

# Customize the gate: exit non-zero ONLY when findings exist (default is already 1 on findings).
gitleaks detect --exit-code 2          # use any code your pipeline keys on
```

- **`gitleaks detect`** walks the **git log** — it scans every commit's diff, so it finds a secret that was
  committed and later "removed." This is the mode that catches the history gotcha below.
- **`gitleaks protect --staged`** scans only the staged working tree — fast enough for a pre-commit hook,
  and it stops the secret *before* it becomes a commit (so it never enters history at all).
- **Exit code is the gate:** Gitleaks exits **`1` when it finds leaks** (configurable via `--exit-code`),
  `0` when clean — the same process-exit gate the rest of the security family uses.
- **Report formats:** `--report-format json|csv|junit|sarif|template` (`--report-path <file>`). Emit
  **SARIF** for code-scanning + **junit/json** for Allure/CI.
- **Config:** `--config <file>` or `GITLEAKS_CONFIG` env points at a `.gitleaks.toml` (allowlist + custom
  rules; see triage). `--baseline-path baseline.json` ignores findings already recorded in a baseline so the
  gate fires only on **new** secrets.

### TruffleHog — the verified CI gate

```bash
# CI gate: scan git history but FAIL ONLY on credentials proven live by an auth check.
trufflehog git file://. --results=verified --fail        # --fail → non-zero exit when a verified secret is found

# Non-git surfaces TruffleHog uniquely reaches:
trufflehog docker --image=myorg/api:latest --results=verified
trufflehog s3 --bucket=my-bucket --results=verified
trufflehog filesystem ./build --results=verified
```

- **`--results=verified`** is the headline feature: for a candidate like an AWS key, TruffleHog makes a
  **live authentication call** to confirm the credential actually works — cutting false positives roughly
  **90%**. A verified finding is a real, exploitable, live credential. **This is what keeps the gate
  trusted.** (`--results=verified,unknown` widens it to include un-verifiable types — see the anti-pattern
  on ignoring unverified-but-real.)
- **`--fail`** makes the process exit non-zero on a (verified) finding — the CI gate.
- TruffleHog scans Docker images, S3/GCS, CI logs, a filesystem, and git — surfaces Gitleaks doesn't reach.

### Pre-commit hook (Gitleaks)

```yaml
# .pre-commit-config.yaml — runs gitleaks on `git commit`, blocks the commit on a finding
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks        # scans staged changes; non-zero exit aborts the commit
```

```bash
pre-commit install         # wire the hook once; now every `git commit` runs gitleaks first
```

The pre-commit hook is the **first and cheapest line** — it stops the secret on the developer's machine, so
it never reaches the remote, never enters history, never needs rotating. The CI gate is the backstop for
when someone commits with `--no-verify` or hasn't installed the hook.

## ⚠️ The git-history gotcha — rotate, do not delete

> **A secret committed and then "removed" is STILL in the git history — and must be ROTATED, not just
> deleted.** Scanning only HEAD (the current working tree) misses it entirely. Anyone with repo access — or
> anyone who cloned/forked before the "removal", or any automated scraper watching public pushes — already
> has the credential. Deleting the line in a follow-up commit changes *nothing* about the secret's exposure.

The only correct response to a **true-positive** secret:

1. **ROTATE the credential at its source** — revoke/regenerate the AWS key, Auth0 client secret, DB
   password, token. This is the actual fix; everything else is cleanup.
2. *Then* purge it from history if required (`git filter-repo` / BFG) — but **rotation comes first**, because
   history rewrites don't reach existing clones, forks, or scraper caches.
3. Add the (now-dead) value to the allowlist *only* with a ticket noting it's been rotated, so the dead
   string in history doesn't re-fail the gate forever.

This is exactly why **`gitleaks detect` (full history)** matters and a HEAD-only scan is a false comfort: the
secret you need to rotate is almost always one already buried in a past commit.

## Triage — ticketed allowlist + baseline (per `qa-security-shared`)

A real repo's first scan lights up — test fixtures with fake keys, example configs, already-rotated values
still in history. Gating on *every* finding mutes the gate; the discipline (identical to the SCA suppression
file and the axe baseline — defer to `qa-security-shared` for the full framing):

1. **Baseline the current state once** — `gitleaks detect --report-path baseline.json`, then run with
   `--baseline-path baseline.json` so existing findings are ignored and only **NEW** secrets fail. (Or
   detect-secrets' `--baseline` on a legacy repo.)
2. **Gate NEW findings hard** — anything not in the baseline fails the build.
3. **Every allowlist entry carries a ticket + reason.** A scoped `.gitleaks.toml` allowlist, never a blanket
   mute.

```toml
# .gitleaks.toml — extends the default ruleset; add SCOPED, ticketed allowlists
[extend]
useDefault = true

# Global allowlist (applies across rules) — scope tightly, ticket every entry.
[allowlist]
description = "JIRA-5120: known non-secrets — fake test fixtures + a rotated key still in history"
paths = [
  '''tests/fixtures/.*\.env\.example$''',   # example file: documented placeholder, not a real secret
]
regexes = [
  '''AKIAEXAMPLEKEYNOTREAL''',              # rotated 2026-05; dead string lingers in history (JIRA-5120)
]
commits = [
  "a1b2c3d4",                               # the commit that introduced the now-rotated key (JIRA-5120)
]

# Rule-level allowlist — narrows ONE rule, not the whole scan.
[[rules]]
id = "aws-access-key"
[rules.allowlist]
description = "JIRA-5121: AWS keys in the terraform examples dir are documented placeholders"
paths = ['''examples/terraform/.*''']
```

- Allowlist by **`paths`** (regex on file path), **`regexes`** (the literal value), **`commits`** (a
  specific SHA), **rule-level** (`[rules.allowlist]`) or **global** (`[allowlist]`). Scope to the narrowest
  that works — never a blanket path-glob that hides future real secrets.
- A **true-positive** is *not* an allowlist case — it's a **rotate** case (above). Only add the dead value
  to the allowlist *after* rotation, with the ticket that proves it.
- **Shrink the allowlist over time.** Never grow it to make a red build green — that's how a real leaked
  credential gets buried. Track allowlist size as a metric.

## Reporting — SARIF → code-scanning, JSON/junit → Allure

Standardize on **SARIF** for inline PR findings and a human report for the run (per the
`qa-security-shared` SARIF spine):

- **Gitleaks** → `--report-format sarif --report-path gitleaks.sarif` for code-scanning; `--report-format
  junit` (or `json`) to attach to **Allure** + as a CI artifact.
- **TruffleHog** → `--json` for a machine-readable artifact; the verified findings are the ones that gate.
- Upload SARIF via `github/codeql-action/upload-sarif` so each leak shows **inline on the PR diff**,
  de-duplicates run-over-run, and tracks fixed/new state (cross-link `qa-allure-reporting-{stack}`,
  `qa-ci-pipelines-{stack}`).

```yaml
# .github/workflows/secrets-scan.yml — cross-link qa-ci-pipelines-*
name: Secrets Scan
on: [pull_request]

jobs:
  # Fast regex + history net (official action). Exit 1 on findings → gate.
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }              # full history — NOT just HEAD (the git-history gotcha)
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}   # org-tier only; env, lazy, never committed
      - if: always()
        uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: results.sarif }

  # Low-noise verified gate — fails only on credentials proven LIVE.
  trufflehog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with: { fetch-depth: 0 }
      - uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --results=verified --fail   # live-auth check → ~90% fewer false positives
```

> **`fetch-depth: 0` is mandatory.** The default shallow clone gives the scanner only the tip commit — it
> would scan HEAD and miss every secret buried in history. Fetch the full history or the scan is theatre.

## Anti-patterns

- **Scanning only HEAD, not history.** A secret committed then "removed" is still in every clone/fork — a
  HEAD-only scan reports clean while the credential is live. *Fix:* `gitleaks detect` over the full repo +
  `fetch-depth: 0` in CI.
- **Deleting the line instead of rotating the credential.** Removing the secret in a follow-up commit
  changes nothing — it's still in history, already scraped. *Fix:* **rotate at the source** first; history
  purge is cleanup, not the fix.
- **Blanket-allowlisting** (a whole directory, a broad path regex, or `useDefault = false` to silence noise).
  Hides every future real secret in that scope. *Fix:* scope each allowlist entry to a specific
  path/regex/commit, ticketed.
- **No pre-commit hook, so secrets reach CI (or the remote) before they're caught.** By then it may already
  be in history and need rotating. *Fix:* `gitleaks protect --staged` as a pre-commit hook — stop it on the
  dev's machine.
- **Ignoring unverified-but-real findings.** `--results=verified` is great for a low-noise gate, but a
  high-entropy string for a credential type TruffleHog *can't* live-verify (a private internal token) is
  still a real leak. *Fix:* triage `unknown` results out-of-band (`--results=verified,unknown` in a
  scheduled/audit run); never assume "unverified" means "not a secret."
- **No verification → high false-positive noise mutes the gate.** A pure-regex CI gate that fires on every
  fixture key trains the team to ignore it. *Fix:* gate CI on TruffleHog `--results=verified`; keep the
  noisy broad regex at pre-commit where a human triages each hit live.
- **Committing the `.gitleaks.toml` allowlist as a dumping ground** — every red finding gets a line to go
  green. The file rots into a list of un-reviewed mutes that bury a real leak. *Fix:* ticket every entry,
  rotate true-positives (don't allowlist them live), shrink the file over time.
- **Hard-coding the scanner's own auth** (`GITLEAKS_LICENSE`, registry creds) in the workflow. *Fix:* env
  var / secret store, read lazily — never committed (global rule: no secrets in code).

## Rules (hard constraints)

- The gate is the **process exit code** — Gitleaks exits `1` on findings (`--exit-code` to customize);
  TruffleHog `--fail` exits non-zero on a verified finding. Gate **new** secrets hard.
- **Scan the full git history, not just HEAD** (`gitleaks detect` over the repo; `fetch-depth: 0` in CI). A
  HEAD-only scan misses the secrets that most need rotating.
- A **true-positive secret means ROTATE the credential** at its source — deleting the line is not enough
  (it's in history, possibly already scraped). History purge is cleanup *after* rotation.
- Run **both tools, by role:** Gitleaks as a **fast pre-commit hook** (+ history sweep), TruffleHog in **CI
  with `--results=verified`** for the low-noise gate. Note Gitleaks is security-patch-only maintenance
  (successor: Betterleaks).
- Triage with a **ticketed `.gitleaks.toml` allowlist + `--baseline-path`**: scope each entry narrowly,
  ticket it, **gate new findings**, shrink the file over time. Never blanket-allowlist; never allowlist a
  live true-positive instead of rotating it.
- Emit **SARIF** → code-scanning (inline PR findings) + **JSON/junit** → Allure + CI artifact.
- **No secrets in the scanner config** (license, registry auth) — env vars, read lazily, never committed.
- Map findings to **OWASP A02:2025 / A07:2025**; a clean secrets scan ≠ "secure" — run the other layers
  (SAST, SCA, DAST) too (per `qa-security-shared`).

## Cross-references

- `qa-security-shared` — **load alongside this skill**: the OWASP map (A02/A07), the ticketed-triage
  discipline, the SARIF → code-scanning consolidation, and the layer map this skill plugs into (secrets =
  one layer; a clean scan says nothing about the others).
- `qa-security-testing-sast` — the **insecure-code-patterns / taint-flow** sibling (reads your source
  structure; secrets scanning reads for literal credentials — orthogonal).
- `qa-security-testing-dependency-scanning-{java,dotnet,typescript}` — the **SCA** sibling (reads your
  **build graph** for vulnerable deps; secrets scanning reads your **source + history** for credentials).
- `qa-ci-pipelines-{stack}` (+ `qa/_shared/ci-conventions`) — the gate step, full-history
  checkout, SARIF + artifact upload.
- `qa-allure-reporting-{stack}` — attach the junit/JSON report to the run.
- `qa/manual/bug-report-writer` — write up a confirmed leaked-credential finding (with the rotation step as
  the fix, not "delete the line").
- `qa/_shared/agents/qa-security` — the phased orchestrator that loads `qa-security-shared` + this tool skill
  in the per-PR static-gate phase.
