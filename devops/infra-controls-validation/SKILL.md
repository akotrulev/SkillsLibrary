---
name: controls-validation
description: Use when proving an infrastructure security control actually works, not just that it is configured. Triggers "verify TLS is actually enforced". Not for CSPM sweeps (cloud-posture).
disable-model-invocation: true
---

# DevOps — Infrastructure Controls Validation

Every other scanner in this domain answers *"is the control there?"* — a field set in a manifest, a resource
present in the account, a benchmark row green. This skill answers the question that actually decides whether
an incident happens: **"and does it work?"** A Key Vault the service never reads, an HTTPS listener sitting
beside an open port 80, a CloudWatch alarm wired to a deleted SNS topic, and a workflow that declares
`id-token: write` while still authenticating with a 2019 access key are all **present** controls and all
**ineffective** ones. Each of them passes a configuration review and fails a live check.

So the unit of work here is a **check**: a scripted, exit-coded assertion that a named control is effective,
carrying its own evidence line and re-runnable by id.
One `./controls/check-secrets.sh` run before the fix and after it, diffed by check id, is the deliverable.

> **Present vs effective.** `devops-auditor` reads the manifest, `devops:iac-security` the template,
> `devops:cloud-posture` the account's declared configuration: all three can be green while the running
> system leaks. A check that only re-reads the config file the static lane already read does not belong here.

## The control-family matrix

Read each row left to right: the third column is what this skill adds over the second.

| # | Control | "Present" means | **"Effective" means** | How to validate | Owner of the *authoring* half |
|---|---------|-----------------|-----------------------|-----------------|-------------------------------|
| **1** | **Secrets management** | A secret store exists and the app is wired to it | The **running** workload resolves secrets *from the store*, and no secret-shaped value sits in its env / config file / IaC var / pipeline variable / state file | Dump the live task/pod/function env and diff it against the store's inventory; assert the workload identity is a role, not a key | `devops:environment-config` |
| **1b** | **Rotation** | A rotation policy is attached | The last rotation actually **happened** within the window, and a rotated value is **picked up** by the app without a manual redeploy | `describe-secret` / `rotation-policy show` for `LastRotatedDate`; then rotate in a lower env and re-probe the app's `/health` | `devops:environment-config` |
| **2** | **Encryption in transit** | A TLS listener / cert exists | The plaintext path is **closed or redirected**, HSTS is served, and internal service-to-service hops are TLS/mTLS too — not just the public edge | `curl -sI http://…` for a 301, `nc -z :80`, listener `SslPolicy`, mesh `PeerAuthentication STRICT` | `devops:{aws,azure}-deployment` · `devops:kubernetes` |
| **2b** | **TLS quality** | — | *(handshake, protocol, cipher, chain, expiry)* | **Not here** — `qa-<stack>:certificate-scan` (sslyze / testssl.sh) | `qa-<stack>:certificate-scan` |
| **3** | **Monitoring & audit logging** | Audit logging is enabled; alert rules exist | A **synthetic event actually reaches** the log store, and the alert rule it should match **actually fires** and reaches a live notification channel | Emit a canary event → query Loki/CloudWatch/Log Analytics for it → force the alarm state / fire the rule → assert the notification landed | `observability-engineer-{dotnet,java,node}` |
| **4** | **CI/CD hardening** | A pipeline exists and deploys | It authenticates by **OIDC/WIF with no long-lived key anywhere**, actions are **SHA-pinned**, job `permissions:` are least-privilege, untrusted input never reaches a `run:` block, and prod is behind a protected branch + reviewed environment | Static parse of the workflow files **plus** an API read of the repo's secrets, rulesets, and environments — the config and the platform state must agree | `devops:{github-actions,gitlab-ci,azure-pipelines}` |

## Authorization — two tiers, and they are not the same

| Tier | What it reads | Gate |
|------|---------------|------|
| **Static** — workflow YAML, manifests, Terraform, `.tfvars`, chart values, committed state | files in the repo | **Safe anywhere.** No authorization line needed; run it on a laptop, in a PR gate, on someone else's fork |
| **Live** — `kubectl`, `aws`/`az`/`gcloud` reads, `curl` against a deployed host, an alarm forced into ALARM, a rotation triggered in staging | the running system | **Owned infrastructure only**, with a recorded, **expiring** authorization line naming the target scope, who authorized, and when it lapses. `#volatile` — never cached in `docs/agent-context/` |

Two live acts **change state**: forcing an alarm (`set-alarm-state`) pages whoever is on call, and triggering a
rotation invalidates a credential in use. Run them in a non-production environment by default, announce
them, log them in the run's action list, and authorize each act separately. Every other live check is a read.

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
  not applicable) reports `SKIP` **with the reason**, and skips are counted in the summary.
- **Evidence is the value observed, not the rule restated.** `LastRotatedDate=2026-07-29`, not "rotation is
  recent". A reader must be able to disagree with the verdict from the line alone.
- **Exit non-zero on any FAIL** so the same script is a report *and* a deploy-pipeline gate.
- **Redact.** A check proves a secret is *in the wrong place*; it prints the **key** and its location, never the value.
  Nothing sensitive is committed under `docs/`.

## Family 1 — Secrets management

**Read the env of the thing that is actually running.**

```bash
# K8s — literal env values on a running pod. A hit here is SEC-01, regardless of what the chart says.
kubectl get pod "$POD" -n "$NS" \
  -o jsonpath='{range .spec.containers[*].env[?(@.value)]}{.name}{"\n"}{end}' \
  | grep -Ei 'secret|token|key|password|passwd|pwd|conn|credential'

# ECS — the task definition distinguishes them for you: .environment is plaintext, .secrets is a store ref.
aws ecs describe-task-definition --task-definition "$TD" \
  --query 'taskDefinition.containerDefinitions[].environment[].name' --output text
```

Per-platform commands, etcd encryption-at-rest, Terraform state leakage, rotation proof and the
workload-identity assertion: **`references/secrets-and-encryption.md`**.

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

> **The fence with `qa-<stack>:certificate-scan`.** That skill owns **TLS quality** (protocol, cipher, chain,
> expiry); this skill owns **TLS enforcement**: TLS is *wired to every path* and the plaintext path is closed.
> An A+ grade on `https://` is worthless while `http://` serves 200. Run both, and hand the endpoint list
> to the cert scan rather than re-deriving it.

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

Audit-log-enabled probes, alert-rule inventory vs firing state, the notification-channel delivery proof and
the deliberate `SKIP` when there is no telemetry backend: **`references/monitoring-and-pipeline.md`**.

> **Prerequisite.** A target with no log/alert store has nothing to assert against: report
> `MON-* SKIP — no detection surface` and hand off to `observability-engineer-{dotnet,java,node}`.

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

Least-privilege `permissions:`, script-injection-shaped triggers, branch protection and rulesets,
environments with required reviewers, the GitLab and Azure Pipelines equivalents, and the linters
(`zizmor`, `actionlint`, OpenSSF Scorecard): **`references/monitoring-and-pipeline.md`**.

## The retest workflow

`infra-security-tester` finds; **`devops-engineer` fixes**; this skill **re-runs and verdicts** and edits no infrastructure.

1. **Baseline.** Run all four family scripts, capture stdout to
   `docs/audits/<NNN>-infra-controls-r1.txt`, and file each `FAIL` as a finding carrying its check id,
   evidence line, OWASP/ATT&CK ids (`references/finding-mapping.md`), and the owning skill from the matrix.
2. **Hand off.** `devops-engineer` remediates against the finding ids.
3. **Retest by id.** Re-run the *same script* (never a hand-check of the specific instance — a fix that
   patched one workflow and missed three siblings must show up), and prefix each result
   **Resolved / Resolved (differently) / Still open / Still open (regressed) / New**, per
   `engineering/standards-audit-engine`'s Mode B vocabulary. Save round N beside round 1; **never overwrite**.
4. **Only re-reading the control proves resolution.** A merged PR, a green deploy and a closed ticket are
   leads; a `PASS` line produced *this round* is evidence.
5. **Promote the passing checks into the deploy pipeline** so the fix cannot silently regress — the
   validation suite's end state is a gate, not a report.

## CI wiring

Before adding the checks to a deploy pipeline, read `references/ci-wiring.md`: the post-deploy gate job, and the split between static families on every PR and live families after each deploy. These gates live in `devops/{github-actions,gitlab-ci,azure-pipelines}`, never in the `qa/cicd/*` test lane.

## Rules (hard constraints)

The harness, authorization and retest sections above are the hard constraints: effectiveness over presence, `SKIP` ≠ `PASS`, redacted evidence, find and retest but never fix. Two more:

- **Pin every tool version** the suite uses, and every action in the gate workflow by **full commit SHA**: the suite holds itself to family 4's own rule.
- **A green controls run ≠ "secure"**: it means these four families' effective halves passed. Run the rest of the infra lane (`k8s-security`, `iac-security`, `cloud-posture`, `container-runtime-security`, `supply-chain-security`) and the app-layer lane (`qa-security`).

## Cross-references

- `devops/agents/infra-security-tester.md` — the owner; this skill is its **Step 5, Controls validation & retest**.
- **`devops:cloud-posture`** — the boundary partner: **broad CSPM benchmark sweeps** (whole account, hundreds of checks). This skill runs **a small targeted set proving four controls effective** and re-runs it after a fix. A posture finding ("CloudTrail disabled in eu-west-2") is an **input** to a family-3 check; do not re-implement CSPM here.
- `devops-auditor` — the **static conformance** sibling. Its sections G, H and I declare the rules this skill *proves*; a pure static misconfig stays with the auditor, a finding that needs a live probe is this skill's.
- `devops:environment-config` — the **authoring half of family 1**: it writes the control, this validates it. Its rule files `config.md` and `devops.md` are this skill's `SEC-*` check list.
- `qa-<stack>:secrets-scan` — secrets *committed* to the repo and its history; this finds a secret *live in a running workload's environment*.
- `qa-<stack>:certificate-scan` — **TLS quality** (protocol, cipher, chain, expiry); this skill hands it the endpoint list family 2 enumerates.
- `observability-engineer-{dotnet,java,node}` + `observability/{logs-traces-setup,metrics-setup,queries}` — the telemetry backend family 3 asserts against, and the owner of the fix when there is no detection surface; `queries` owns the LogQL/PromQL the canary runs.
- `devops-engineer` applies every fix; `devops:{github-actions,gitlab-ci,azure-pipelines}` own the pipeline this skill hardens and the deploy pipeline the gate runs in.
- `devops:iac-security` · `devops:kubernetes-security` · `devops:container-runtime-security` · `devops:supply-chain-security` · `devops:threat-modeling` — the infra-security siblings; threat-modeling supplies *which* controls matter, supply-chain owns signing and provenance (family 4's pinning checks stop at the reference, not the attestation).
- `engineering/standards-audit-engine` — the Mode A/B round vocabulary the retest workflow borrows.
