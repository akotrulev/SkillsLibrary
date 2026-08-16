# Monitoring effectiveness & CI/CD hardening — present-AND-effective checks

Families 3 and 4 of the controls harness. Both fail on *effectiveness*: a log pipeline that ingests but never
alerts; a pipeline that "uses OIDC" while a stale static key still sits in repo secrets. Every check returns a
boolean for `controls/lib.sh` and reruns after remediation. Tags: `[STATIC]` file read (safe), `[LIVE]` reads
owned infra (authorization-gated).

## Family 3 — Monitoring & telemetry effectiveness

The control is not "logging is on" but "a security-relevant event **reaches the store** and **raises the alert
it should**." The only honest way to prove that is a synthetic event, end to end. This is the one family with
a hard external dependency: **it needs a telemetry backend to assert against** — the Loki/Prometheus/Tempo
stack the `observability/` domain owns. With no backend, the correct result is a deliberate `SKIP` reporting
"no detection surface to assert against," never a silent pass.

### The three-step effectiveness probe

`[LIVE]` **1. Emit a uniquely-tagged synthetic event** from inside the workload so it travels the real path:

```bash
PROBE="controls-probe-$(git rev-parse --short HEAD)-$RANDOM"
kubectl exec -n NS POD -- logger -t security-audit "AUDIT synthetic denied-access marker=$PROBE"
# or hit an endpoint that emits an auditable event: a failed login, a forbidden access, a role change.
```

`[LIVE]` **2. Assert it reached the log store** within the SLO window:

```bash
# Loki (the library default). CloudWatch Logs Insights / Azure Log Analytics KQL are the managed equivalents.
sleep 30
COUNT=$(logcli query --limit=5 --since=2m '{app="svc"} |= "'"$PROBE"'"' 2>/dev/null | grep -c "$PROBE")
test "$COUNT" -ge 1 && echo "PASS ingest" || echo "FAIL: probe never reached the log store"
```

`[LIVE]` **3. Assert the ALERT fired** — the step that separates "we have logs" from "we detect." A rule that
exists but never fires is a detection gap, not a pass:

```bash
# Trigger the condition the rule watches for (e.g. N failed logins), then query the alert store.
# Prometheus/Alertmanager:
curl -s http://alertmanager:9093/api/v2/alerts | jq -e --arg p "$PROBE" \
  '[.[] | select(.labels.probe==$p or (.annotations.description // "" | test($p)))] | length >= 1' \
  && echo "PASS alert fired" || echo "FAIL: condition met, no alert"
```

`[LIVE]` The presence half (cheap, run first — a disabled trail makes the effectiveness probe moot):

```bash
aws cloudtrail get-trail-status --name TRAIL --query IsLogging               # true
aws cloudtrail describe-trails --query 'trailList[].{name:Name,multiRegion:IsMultiRegionTrail}'
az monitor diagnostic-settings list --resource RESOURCE_ID --query '[].logs[?enabled]'
```

Map a gap to **OWASP A09 Security Logging & Alerting Failures**; a disabled/short-retention cloud trail is
also ATT&CK `T1562.008` (Impair Defenses: Cloud Logs). The effectiveness assertion hands off to
`observability-engineer-*` (who own the backend and the rule) and, at continuous scale, to the forthcoming
`detection-validation` purple-team lane — this lane proves a *specific* control fires, that lane runs it on a
schedule.

## Family 4 — CI/CD pipeline hardening

The two library invariants live here: **no static cloud credentials** and **pin everything**. Both are
blocker-class by default.

`[STATIC]` **CICD-01 — no static keys anywhere in the workflows** (the first invariant):

```bash
grep -rEn 'A(KIA|SIA)[0-9A-Z]{16}|AZURE_CLIENT_SECRET|-----BEGIN [A-Z ]*PRIVATE KEY' \
  .github/workflows .gitlab-ci.yml azure-pipelines.yml 2>/dev/null && echo FAIL || echo PASS
```

`[LIVE]` **CICD-02 — the platform half:** no long-lived credential still sitting as a repo/org secret, even if
the workflow uses OIDC. A dormant key is still a key:

```bash
gh secret list --repo myorg/api                       # look for AWS_ACCESS_KEY_ID, AZURE_CREDENTIALS, etc.
gh api /repos/myorg/api/actions/secrets --jq '.secrets[].name'
```

`[STATIC]` **CICD-03 — OIDC is actually wired** (the effective half of "no static keys" — the workflow must
request the token and assume a role, not just avoid a stored key):

```bash
grep -rEn 'id-token:\s*write' .github/workflows/ && echo "PASS oidc requested" || echo "FAIL: no OIDC token"
# and the cloud side: a role trust policy scoped to the repo AND ref, not a wildcard.
aws iam get-role --role-name CI_ROLE --query 'Role.AssumeRolePolicyDocument' | \
  jq -e '.Statement[] | select(.Principal.Federated? // "" | test("token.actions.githubusercontent"))
         | .Condition.StringLike["token.actions.githubusercontent.com:sub"] // .Condition.StringEquals'
```

`[STATIC]` **CICD-04 — least-privilege job permissions** — a top-level `permissions: write-all` (or the
default token with no `permissions:` block) is a finding:

```bash
for f in .github/workflows/*.y*ml; do
  grep -q '^permissions:' "$f" || echo "FAIL $f: no permissions block (defaults to broad token)"
  grep -qE 'permissions:\s*(write-all|.*: write)$' "$f" && echo "REVIEW $f: broad permissions"
done
```

`[STATIC]` **CICD-05 — every third-party action pinned to a full 40-char commit SHA** (the second invariant —
a mutable tag runs attacker code with your secrets; the KICS Action compromise of March 2026 is the case):

```bash
grep -rhoE 'uses:\s*[^@]+@[^ ]+' .github/workflows/ | grep -vE '@[0-9a-f]{40}( |$)' \
  && echo "FAIL: actions pinned by tag, not SHA" || echo PASS
```

`[STATIC]` **CICD-06 — no injection-shaped triggers**: `pull_request_target` combined with a checkout of the
PR head, or `${{ github.event.* }}` interpolated straight into a `run:` shell:

```bash
grep -rlE 'pull_request_target' .github/workflows/ && echo "REVIEW: pull_request_target present"
grep -rnE 'run:.*\$\{\{\s*github\.event\.(issue|pull_request|comment|head_ref)' .github/workflows/ \
  && echo "FAIL: untrusted event data in a run step (script injection)"
```

`[STATIC]` **CICD-07 — prod behind an approval gate**: a protected environment with required reviewers, not a
push-to-main auto-deploy:

```bash
gh api /repos/myorg/api/environments --jq '.environments[] | select(.name=="production")
  | {name, reviewers:(.protection_rules[]? | select(.type=="required_reviewers"))}'
```

Static analyzers worth wiring as the automated form of CICD-04/05/06: **`zizmor`** (GitHub Actions security
audit), **`actionlint`** (workflow correctness + shellcheck of `run:` blocks), and **OpenSSF Scorecard**'s
`Dangerous-Workflow` / `Token-Permissions` / `Pinned-Dependencies` checks.

## The retest loop

Every check is idempotent and exit-coded, so after `devops-engineer` remediates a finding the same script
reruns and flips it from FAIL to PASS — that transition, captured in the round-over-round report, is the proof
the fix worked. A control that can't be re-asserted the same way twice isn't validated.

## Cross-references

- `../SKILL.md` — the harness and the control-family matrix; this reference is Families 3 and 4 in depth.
- `secrets-and-encryption.md` — Families 1 and 2.
- `observability-engineer-{dotnet,java,node}` + the `queries`/`dashboards` skills — own the telemetry backend
  and rules Family 3 asserts against; a `SKIP` when no backend exists routes here.
- `detection-validation` (forthcoming purple-team lane) — continuous, scheduled detection assertion; this lane
  proves a specific control fires on demand.
- `devops/{github-actions,gitlab-ci,azure-pipelines}` — own the pipeline authoring Family 4 hardens; findings
  route to `devops-engineer`, then this lane retests.
- The two invariants (`no static cloud credentials`, `pin everything`) are the same ones `devops-auditor`
  sections G and I check statically; this lane validates they hold **effectively** and retests.
