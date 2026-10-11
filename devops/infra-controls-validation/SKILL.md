---
name: controls-validation
description: Use when proving an infrastructure security control is not just CONFIGURED but actually WORKING. Static-config checks run anywhere; live-probe checks need read access to OWNED infra plus a recorded, expiring authorization line. Triggers "prove our secrets aren't in env vars", "verify TLS is actually enforced", "retest the remediated findings". Not for CSPM sweeps (`devops:cloud-posture`), cert quality (`qa-<stack>:certificate-scan`), or git-history secrets (`qa-<stack>:secrets-scan`).
---

# DevOps — Infrastructure Controls Validation

Every other scanner in this domain answers *"is the control there?"* — a field set in a manifest, a resource
present in the account, a benchmark row green. This skill answers the question that actually decides whether
an incident happens: **"and does it work?"** A Key Vault the service never reads, an HTTPS listener sitting
beside an open port 80, a CloudWatch alarm wired to a deleted SNS topic, and a workflow that declares
`id-token: write` while still authenticating with a 2019 access key are all **present** controls and all
**ineffective** ones. Each of them passes a configuration review and fails a live check.

So the unit of work here is a **check**: a scripted, exit-coded assertion that a named control is effective,
carrying its own evidence line and re-runnable by id. That last property is the point — the JD phrase is
*"retest remediated findings"*, and a control validated by a paragraph of prose cannot be retested. One
`./controls/check-secrets.sh` run before the fix and after it, diffed by check id, is the deliverable.

> **⚠️ Present vs effective — the whole reason this skill exists.** A control has **two independent
> failure modes**: it can be *absent* (nobody configured it) or *inert* (configured and bypassed,
> unreachable, mis-wired, or overridden). Static scanning finds the first and is structurally blind to the
> second, because the intended state and the running state are different objects. `devops-auditor` reads
> the manifest, `devops:iac-security` reads the template, `devops:cloud-posture` reads the account's
> declared configuration — all three can be green while the running system leaks. **Every check in this
> skill asserts the effective half**, and the family matrix below states, per control, exactly what
> "present" means, what "effective" means, and the gap between them. If a check only re-reads the config
> file the static lane already read, it does not belong here.

## The control-family matrix

Four families, from the infra-security-tester JD. Read the row left to right: the third column is what this
skill adds over the fourth.

| # | Control | "Present" means | **"Effective" means** | How to validate | Owner of the *authoring* half |
|---|---------|-----------------|-----------------------|-----------------|-------------------------------|
| **1** | **Secrets management** | A secret store exists and the app is wired to it | The **running** workload resolves secrets *from the store*, and no secret-shaped value sits in its env / config file / IaC var / pipeline variable / state file | Dump the live task/pod/function env and diff it against the store's inventory; assert the workload identity is a role, not a key | `devops:environment-config` |
| **1b** | **Rotation** | A rotation policy is attached | The last rotation actually **happened** within the window, and a rotated value is **picked up** by the app without a manual redeploy | `describe-secret` / `rotation-policy show` for `LastRotatedDate`; then rotate in a lower env and re-probe the app's `/health` | `devops:environment-config` |
| **2** | **Encryption in transit** | A TLS listener / cert exists | The plaintext path is **closed or redirected**, HSTS is served, and internal service-to-service hops are TLS/mTLS too — not just the public edge | `curl -sI http://…` for a 301, `nc -z :80`, listener `SslPolicy`, mesh `PeerAuthentication STRICT` | `devops:{aws,azure}-deployment` · `devops:kubernetes` |
| **2b** | **TLS quality** | — | *(handshake, protocol, cipher, chain, expiry)* | **Not here** — `qa-<stack>:certificate-scan` (sslyze / testssl.sh) | `qa-<stack>:certificate-scan` |
| **3** | **Monitoring & audit logging** | Audit logging is enabled; alert rules exist | A **synthetic event actually reaches** the log store, and the alert rule it should match **actually fires** and reaches a live notification channel | Emit a canary event → query Loki/CloudWatch/Log Analytics for it → force the alarm state / fire the rule → assert the notification landed | `observability-engineer-{dotnet,java,node}` |
| **4** | **CI/CD hardening** | A pipeline exists and deploys | It authenticates by **OIDC/WIF with no long-lived key anywhere**, actions are **SHA-pinned**, job `permissions:` are least-privilege, untrusted input never reaches a `run:` block, and prod is behind a protected branch + reviewed environment | Static parse of the workflow files **plus** an API read of the repo's secrets, rulesets, and environments — the config and the platform state must agree | `devops:{github-actions,gitlab-ci,azure-pipelines}` |

**Two spines, per finding.** Control gaps map to **OWASP Top 10:2025** — **A02 Security Misconfiguration**
(families 2, 4), **A04 Insecure Design** (a control with no rotation or no enforcement path was designed
inert), **A09 Logging & Alerting Failures** (family 3), **A03 Software Supply Chain Failures** (family 4
pinning), **A07 Identification & Authentication Failures** (a static cloud key). Where a control's absence is
the *mitigation* for a technique, name the **MITRE ATT&CK** id too — Cloud/Containers matrices, not
Enterprise: `T1552.001/.007` Unsecured Credentials in files and cloud config (family 1), `T1557` /
`T1040` adversary-in-the-middle and sniffing (family 2), `T1562.008` Impair Defenses — Disable Cloud Logs
(family 3), `T1195.002` Compromise Software Supply Chain and `T1078.004` Valid Accounts — Cloud (family 4).
CIS Benchmarks supply the numbered row where one exists; cite it rather than re-deriving the rule.

## Authorization — two tiers, and they are not the same

| Tier | What it reads | Gate |
|------|---------------|------|
| **Static** — workflow YAML, manifests, Terraform, `.tfvars`, chart values, committed state | files in the repo | **Safe anywhere.** No authorization line needed; run it on a laptop, in a PR gate, on someone else's fork |
| **Live** — `kubectl`, `aws`/`az`/`gcloud` reads, `curl` against a deployed host, an alarm forced into ALARM, a rotation triggered in staging | the running system | **Owned infrastructure only**, with a recorded, **expiring** authorization line naming the target scope, who authorized, and when it lapses. `#volatile` — never cached in `docs/agent-context/` |

Two live acts are louder than the rest and get their own confirmation, because they **change state**:
forcing an alarm (`set-alarm-state`) pages whoever is on call, and triggering a rotation invalidates a
credential in use. **Default them to a non-production environment**, announce them before running, and log
them in the run's action list. Every other live check is a read.

## The check harness — one line per control, exit-coded, retestable

Checks are shaped so a report row and a rerun are the same artifact. One function per control, one line of
output, an id that never changes:

```bash
#!/usr/bin/env bash
# controls/lib.sh — the shared harness every family script sources.
set -uo pipefail            # NOT -e: a failing check must be recorded, not abort the run
FAILED=0

check() {                   # check <ID> <PASS|FAIL|SKIP> <evidence>
  local id=$1 verdict=$2; shift 2
  printf '%-10s %-4s %s\n' "$id" "$verdict" "$*"
  [[ $verdict == FAIL ]] && FAILED=1
  return 0
}

finish() { exit "$FAILED"; }  # non-zero if ANY check failed — this is the gate
```

```text
SEC-01     FAIL  container 'api' env contains secret-shaped key API_KEY (literal value, not secretRef)
SEC-04     PASS  secret 'orders/prod' LastRotatedDate=2026-07-29 (< 90d)
TLS-02     FAIL  http://api.example.com returned 200, expected 301 to https
MON-03     SKIP  no Alertmanager endpoint configured — cannot assert notification delivery
CICD-05    FAIL  4 actions referenced by tag, not SHA: actions/checkout@v5, …
```

- **The id is the contract.** `SEC-01` means the same assertion in every run forever, so "12 open at r1 → 3
  at r2" is a real trend and a retest is `./check-secrets.sh | grep SEC-01`. Never renumber; append.
- **`SKIP` is not `PASS`.** A check that could not run (no cluster credentials, no alert backend, control
  not applicable to this workload shape) reports `SKIP` **with the reason**. Collapsing an unrunnable check
  into a pass is how a validation suite becomes decoration — the honest report says "no detection surface to
  assert against."
- **Evidence is the value observed, not the rule restated.** `LastRotatedDate=2026-07-29`, not "rotation is
  recent". A reader must be able to disagree with the verdict from the line alone.
- **Exit non-zero on any FAIL** so the same script is a report *and* a deploy-pipeline gate.
- **Redact.** A check proves a secret is *in the wrong place*; it never prints the secret. Match on key
  name + shape + entropy and print the **key**, never the value (§ the loot rule).

## Family 1 — Secrets management

The one check that finds what every static reviewer misses: **read the env of the thing that is actually
running.**

```bash
# K8s — literal env values on a running pod. A hit here is SEC-01, regardless of what the chart says.
kubectl get pod "$POD" -n "$NS" \
  -o jsonpath='{range .spec.containers[*].env[?(@.value)]}{.name}{"\n"}{end}' \
  | grep -Ei 'secret|token|key|password|passwd|pwd|conn|credential'

# ECS — the task definition distinguishes them for you: .environment is plaintext, .secrets is a store ref.
aws ecs describe-task-definition --task-definition "$TD" \
  --query 'taskDefinition.containerDefinitions[].environment[].name' --output text
```

Full per-platform command set (K8s + CSI/External Secrets, ECS, Lambda, Container Apps, App Service),
etcd encryption-at-rest, Terraform state leakage, rotation proof, and the workload-identity assertion:
**`references/secrets-and-encryption.md`**.

## Family 2 — Encryption in transit

TLS being *available* proves nothing; the check is whether the **plaintext path still works**.

```bash
# TLS-02 — the plaintext path must redirect, not serve.
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://$HOST/")
[[ $code == 30[178] ]] || echo "FAIL http://$HOST returned $code"

# TLS-03 — HSTS present on the HTTPS response (and the redirect target is https, not a same-host loop).
curl -sI "https://$HOST/" | grep -i '^strict-transport-security:'
```

Internal hops, mesh mTLS (`PeerAuthentication` STRICT, `istioctl`/`linkerd` verification), load-balancer
minimum-TLS policy, Ingress TLS blocks, and the at-rest quick checks: **`references/secrets-and-encryption.md`**.

> **The fence with `qa-<stack>:certificate-scan`.** That skill owns **TLS quality** — protocol versions,
> cipher suites, forward secrecy, chain, expiry, Mozilla-policy grading, via sslyze/testssl.sh. This skill
> owns **TLS enforcement** — that TLS is *wired to every path* and the plaintext path is closed. A perfect
> A+ grade on `https://` is worthless while `http://` serves 200. Run both; they are orthogonal, and this
> skill's family-2 checks should *hand the endpoint list* to the cert scan rather than re-deriving it.

## Family 3 — Monitoring & telemetry effectiveness

"Logging is enabled" is a checkbox; **"an event I injected one minute ago is queryable, and the rule that
should have matched it fired"** is a control. The pattern is a three-hop canary:

```bash
# 1. Emit a uniquely-tagged synthetic event from inside the workload.
CANARY="controls-canary-$(date -u +%s)"
kubectl exec -n "$NS" "$POD" -- sh -c "echo '{\"level\":\"error\",\"msg\":\"$CANARY\"}' >&2"

# 2. Assert it reached the log store within the SLO (Loki here; CloudWatch/Log Analytics in the reference).
sleep 30
logcli query --limit=5 --since=5m "{namespace=\"$NS\"} |= \`$CANARY\`" | grep -q "$CANARY" \
  && echo "MON-01 PASS canary $CANARY visible in Loki within 30s"

# 3. Assert the ALERT the event should raise actually fired — not just that a rule exists.
amtool alert query --alertmanager.url="$AM" 'alertname="AppErrorRateHigh"'
```

Audit-log-enabled probes (CloudTrail status + log-file validation + multi-region, K8s audit policy, Azure
diagnostic settings), alert-rule inventory vs firing state, the notification-channel delivery proof, and the
deliberate `SKIP` when there is no telemetry backend: **`references/monitoring-and-pipeline.md`**.

> **Hard prerequisite, stated honestly.** A target with no log/alert store has **nothing to assert against**.
> Report `MON-* SKIP — no detection surface`, hand off to `observability-engineer-{dotnet,java,node}` to
> stand one up, and never let the absence of a backend read as a pass.

## Family 4 — CI/CD pipeline hardening

Two halves that must **agree**: the workflow files say what the pipeline intends, the platform API says what
it is allowed to do. A workflow declaring OIDC while a decade-old `AWS_SECRET_ACCESS_KEY` still sits in repo
secrets is the finding.

```bash
# CICD-01 — static keys anywhere in the workflows (the plugin's first invariant).
grep -rn 'aws-access-key-id\|AZURE_CLIENT_SECRET\|ARM_CLIENT_SECRET' .github/workflows/ && echo FAIL

# CICD-02 — the platform half: long-lived credential names still present as repo secrets.
gh api "/repos/$ORG/$REPO/actions/secrets" --jq '.secrets[].name' \
  | grep -E 'AWS_(SECRET_)?ACCESS_KEY|AZURE_CLIENT_SECRET|GCP_SA_KEY' && echo FAIL

# CICD-05 — every third-party action pinned to a full 40-char commit SHA (second invariant).
grep -rhoE 'uses:\s*[^ ]+' .github/workflows/ | grep -vE '@[0-9a-f]{40}\b' | grep -v '^uses: \./'
```

Least-privilege `permissions:` (workflow, job, and the repo-wide `default_workflow_permissions`),
script-injection-shaped triggers (`pull_request_target` / `issue_comment` / `workflow_run` interpolating
untrusted text into `run:`), branch protection and rulesets, environments with required reviewers, the
GitLab `id_tokens` and Azure Pipelines workload-identity equivalents, and the linters that automate most of
this (`zizmor`, `actionlint`, OpenSSF Scorecard): **`references/monitoring-and-pipeline.md`**.

## The retest workflow

The reason the checks are scripted at all. `infra-security-tester` finds; **`devops-engineer` fixes**; this
skill **re-runs and verdicts**, and nothing else in the loop edits infrastructure.

1. **Baseline.** Run all four family scripts, capture stdout to
   `docs/audits/<NNN>-infra-controls-r1.txt`, and file each `FAIL` as a finding carrying its check id,
   evidence line, OWASP/ATT&CK id, and the owning skill from the matrix.
2. **Hand off.** `devops-engineer` remediates against the finding ids. The tester does **not** apply the fix
   — same auditor↔engineer split as `devops-auditor` ↔ `devops-engineer`.
3. **Retest by id.** Re-run the *same script* (never a hand-check of the specific instance — a fix that
   patched one workflow and missed three siblings must show up), and prefix each result
   **Resolved / Resolved (differently) / Still open / Still open (regressed) / New**, per
   `engineering-practices/standards-audit-engine`'s Mode B vocabulary. Save round N beside round 1; **never overwrite**.
4. **Only re-reading the control proves resolution.** A merged PR, a green deploy, and a closed ticket are
   leads. A `PASS` line produced *this round* is evidence.
5. **Promote the passing checks into the deploy pipeline** so the fix cannot silently regress — the
   validation suite's end state is a gate, not a report.

## CI wiring — the deploy pipeline, not the test lane

These checks gate **the deployment**, so they live in `devops/{github-actions,gitlab-ci,azure-pipelines}`
alongside the deploy job — **not** in `qa/cicd/*`, which owns the test-suite lane (shard matrix, Allure,
perf gate, flake quarantine). The split is the library's standing fence; state it in the PR that adds them.

```yaml
# .github/workflows/deploy.yml — a post-deploy controls gate. Cross-link devops:github-actions.
  controls-validation:
    needs: deploy
    runs-on: ubuntu-latest
    environment: staging                     # the reviewed environment, so live reads are scoped
    permissions:
      id-token: write                        # OIDC only — no static key reaches this job
      contents: read
    steps:
      - uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8   # v5.0.0 — SHA-pinned
      - uses: aws-actions/configure-aws-credentials@v5
        with:
          role-to-assume: arn:aws:iam::123456789012:role/controls-validation-readonly
          aws-region: eu-west-1
      # Static families first — they need no credentials and fail fast.
      - run: ./controls/check-pipeline.sh
      # Live families next, scoped to the deployed staging endpoints.
      - run: ./controls/check-secrets.sh && ./controls/check-tls.sh && ./controls/check-monitoring.sh
        env: { TARGET_HOST: staging.example.com }
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: controls-report, path: controls-*.txt }
```

Run the **static** families (pipeline hardening, committed-secret shapes, IaC vars) on **every PR** — they
are free and need no credentials. Run the **live** families **post-deploy per environment**, because they
assert something about a running system that only exists after the deploy.

## Anti-patterns

- **Asserting the config file instead of the running system.** `grep secretRef values-prod.yaml` re-reads
  what `devops-auditor` already read and proves nothing about the pod that is up. *Fix:* read the live
  object — `kubectl get pod`, `describe-task-definition`, `get-function-configuration`.
- **"TLS is configured" with port 80 still serving.** The listener exists, the cert is valid, the grade is
  A+, and every legacy client is still speaking cleartext. *Fix:* TLS-02/03 — assert the redirect, the
  HSTS header, and that the plaintext port is closed or redirecting.
- **Treating a green cert scan as encryption-in-transit coverage.** `certificate-scan` grades the **public
  edge**. Service-to-service hops inside the cluster are usually where the plaintext is. *Fix:* check the
  internal hops and the mesh's `PeerAuthentication` mode too.
- **"Logging is enabled" as the monitoring check.** Logs landing in a bucket nobody queries, with an alert
  rule whose receiver was deleted, satisfies every static scanner. *Fix:* the canary — inject, query, and
  assert the alert fired and the notification was delivered (A09).
- **A `SKIP` reported as a `PASS`.** No cluster credentials, no alert backend, no rotation policy to read —
  and the suite comes back green. This is the single most damaging defect in a validation suite, because it
  inverts the artifact's meaning. *Fix:* `SKIP` with the reason, and count skips in the summary.
- **Checking the workflow YAML but not the platform state.** `permissions:` is least-privilege in every file
  while the repo default is `read-write`, or OIDC is wired while three long-lived keys remain in repo
  secrets. *Fix:* pair every static parse with the API read (`gh api .../actions/permissions/workflow`,
  `.../actions/secrets`, `.../environments`).
- **Printing the secret you found.** A report proving `API_KEY` sits in a task definition, quoting its
  value, has moved the secret into `docs/` and git history. *Fix:* print the **key name + location**; state
  blast radius; never the value.
- **Re-checking only the instance that was fixed.** The engineer patched the one workflow named in the
  finding; four siblings still fail. *Fix:* retest by **re-running the script**, never by spot-checking.
- **Forcing an alarm or triggering a rotation in production without saying so.** `set-alarm-state` pages a
  human; a rotation invalidates a live credential. *Fix:* non-production by default, announced, logged,
  authorized per act.
- **Running a broad CIS/CSPM sweep from here.** That is `devops:cloud-posture`'s job and it does it better.
  *Fix:* keep this suite to the four families, targeted and retestable; consume the posture report's
  findings as *input* to a validation check, not as a substitute for one.

## Rules (hard constraints)

- **Validate effectiveness, never presence.** Every check asserts something about the **running** system or
  the **platform's** state. A check that only re-reads a file the static lane already read belongs to
  `devops-auditor` / `devops:iac-security`, not here.
- **Checks are scripted, id-stable, and exit-coded** — one line per control (`ID VERDICT evidence`),
  non-zero exit on any `FAIL`. Ids never change or get reused; the suite is the retest.
- **`SKIP` ≠ `PASS`.** An unrunnable check reports `SKIP` **with the reason**, and skips are counted in the
  summary. Never report a missing detection surface, missing credentials, or an unrunnable probe as a pass.
- **Evidence is the observed value**, not the restated rule — and it is **redacted**: key names, locations,
  and blast radius, never a secret's contents. Nothing sensitive is committed under `docs/`.
- **Two authorization tiers.** Static-config checks are safe anywhere and need no gate. Any check that
  reads or touches live infrastructure requires **owned infrastructure** plus a recorded, **expiring**
  authorization line (`#volatile` — never cached). **State-changing acts** — forcing an alarm, triggering a
  rotation — are non-production by default, announced, and separately authorized per act.
- **Map every finding to both spines** — OWASP Top 10:2025 (A02 / A04 / A09 / A03 / A07) and, where the
  missing control mitigates a technique, the **MITRE ATT&CK Cloud or Containers** id. Cite the CIS row
  where one exists rather than re-deriving the rule.
- **Find and retest; never fix.** Remediation belongs to `devops-engineer`. Retest by **re-running the
  script**, prefix each result with the Mode-B vocabulary, save round N beside round 1, never overwrite.
  *Resolved* is claimed only from a `PASS` produced **this round**.
- **Own the boundary:** this skill = **targeted effectiveness validation + retest** of four named control
  families. Broad CIS/CSPM benchmark sweeps = `devops:cloud-posture`. TLS protocol/cipher/cert quality =
  `qa-<stack>:certificate-scan`. Committed secrets in git history = `qa-<stack>:secrets-scan`. Static
  conformance against the plugin's rules = `devops-auditor`.
- **These gates run in the deploy pipeline** (`devops/{github-actions,gitlab-ci,azure-pipelines}`), never in
  the `qa/cicd/*` test lane. Static families on every PR; live families post-deploy, per environment.
- **Pin every tool version** used by the suite (CLI, action, linter) and every action in the gate workflow
  by **full commit SHA** — the suite must hold itself to family 4's own rule.
- A green controls run ≠ "secure" — it means **these four families' effective halves passed**. Run the rest
  of the infra lane (`k8s-security`, `iac-security`, `cloud-posture`, `container-runtime-security`,
  `supply-chain-security`) and the app-layer lane (`qa-security`).

## Cross-references

- `devops/agents/infra-security-tester.md` — the step-by-step owner; this skill is its **Step 5, Controls
  validation & retest**, and the retest loop above is that step's contract.
- **`devops:cloud-posture`** — the boundary partner and the real overlap. Cloud-posture runs **broad CSPM
  benchmark sweeps** (Prowler / ScoutSuite across CIS + framework rows, hundreds of checks, whole account);
  this skill runs **a small targeted set proving four specific controls are effective**, and re-runs it
  after a fix. A posture finding ("CloudTrail disabled in eu-west-2") is a first-class **input** to a
  family-3 check ("and does an event reach the store"). Do not re-implement CSPM here.
- `devops-auditor` — the **static conformance** sibling. Its sections G (identity & credentials), H (config
  & secrets), and I (pinning & reproducibility) declare the same rules this skill *proves*. Where a finding
  is pure static misconfig it stays with the auditor; where it needs a live probe it is this skill's.
- `devops:environment-config` — the **authoring half of family 1**: the three-layer model, secret stores,
  Managed Identity / IAM Role binding, startup validation, rotation strategy. It writes the control; this
  validates it. Its "What NOT to do" list is literally this skill's `SEC-*` check list.
- `qa-<stack>:secrets-scan` — Gitleaks / TruffleHog over the **repo and its git history**. Orthogonal:
  that finds a secret that was *committed*; this finds a secret that is *live in a running workload's
  environment*. A repo can be clean while every pod leaks.
- `qa-<stack>:certificate-scan` — **TLS quality** (protocol, cipher, chain, expiry) via sslyze / testssl.sh.
  This skill validates TLS is **wired and enforced**; that one validates the handshake is **good**. Hand it
  the endpoint list family 2 enumerates.
- `observability-engineer-{dotnet,java,node}` + `observability/{logs-traces-setup,metrics-setup,queries}` —
  the telemetry backend family 3 asserts against, and the owner of the fix when there is no detection
  surface. `queries` owns the LogQL/PromQL the canary check runs.
- `devops-engineer` — **applies every fix**; this skill retests. `devops:{github-actions,gitlab-ci,azure-pipelines}`
  own the pipeline this skill hardens *and* the deploy pipeline the gate runs in.
- `devops:iac-security` · `devops:kubernetes-security` · `devops:container-runtime-security` ·
  `devops:supply-chain-security` · `devops:threat-modeling` — the infra-security siblings. Threat-modeling supplies
  *which* controls matter for this platform; supply-chain owns artifact signing/provenance (family 4's
  pinning checks stop at the reference, not the attestation).
- `engineering-practices/standards-audit-engine` — the Mode A/B round vocabulary, evidence rules, and severity semantics the
  retest workflow borrows.
