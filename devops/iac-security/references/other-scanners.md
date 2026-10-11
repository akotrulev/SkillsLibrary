# Other IaC scanners — tfsec, Terrascan, KICS, and the commercial lane

Read this when someone proposes adopting a scanner other than Checkov / Conftest / Trivy, or when you inherit
a repo that already runs one. **Two of the four names in the classic "IaC scanner" list are dead**, which is
the single most useful fact in this file.

## Status table (August 2026)

| Tool | Status | Verdict |
|---|---|---|
| **tfsec** (Aqua) | **Merged into Trivy.** Last release `v1.28.14`, 2 May 2025; repo self-describes as "now part of Trivy" | **Do not adopt.** Its entire check library lives in `trivy config` — `qa-<stack>:image-infra-scan` already runs it. Migrate an inherited tfsec job to Trivy |
| **Terrascan** (Tenable) | **Archived** 20 Nov 2025. No maintenance, no new provider coverage, no CVE fixes | **Do not adopt.** Migrate to Checkov (its OPA-based policies map onto Rego, so an existing custom policy set ports to Conftest with modest effort) |
| **KICS** (Checkmarx) | Active. 2,400+ queries across 20+ IaC formats. **Its GitHub Action was compromised 23 Mar 2026** | **Niche adopt** — breadth, not depth. See the caveats below |
| **Checkov** (Palo Alto) | Active, weekly releases | **Primary.** `references/checkov.md` |
| **Conftest / OPA** (CNCF) | Active | **The org-rules layer.** `references/opa-conftest.md` |
| **Trivy** (Aqua) | Active | The lightweight built-in gate — **owned by `qa-<stack>:image-infra-scan`**, not this skill |

> **Why the two deaths matter for this skill's design.** The original tool list for this skill named
> `Checkov · tfsec · Terrascan · KICS · OPA/Conftest` as the tool family. Research collapsed it: tfsec's value
> is now reachable only through Trivy (which a sibling skill already owns), and Terrascan is unsafe to build a
> gate on. The family this skill actually routes is **Checkov + OPA/Conftest**, with KICS as a breadth
> fallback and the two dead tools documented so nobody re-adopts them.

## tfsec — for inherited repos only

```bash
# What an inherited job looks like:
tfsec ./infra --minimum-severity HIGH

# The migration — same checks, maintained engine, and the sibling skill already owns the invocation:
trivy config ./infra --severity HIGH,CRITICAL --exit-code 1
```

Check IDs carried over: tfsec's `aws-s3-enable-bucket-encryption` is Trivy's `AVD-AWS-0088`. Existing
`#tfsec:ignore:<id>` comments **are still honoured by Trivy's misconfig scanner**, so the migration does not
force a suppression rewrite — but new suppressions should use `.trivyignore.yaml` with `expired_at`, per
`qa-<stack>:image-infra-scan`.

## Terrascan — migrate off

Terrascan's differentiator was OPA-based policies, which is the good news for migration: the concepts port to
Conftest directly. Its `terrascan scan -i terraform -p ./policies` maps to
`conftest test <plan.json> --policy ./policies`, though the Rego needs rewriting against the plan-JSON input
shape rather than Terrascan's normalized resource model (`references/opa-conftest.md` has the shape).

An archived scanner in a pipeline is worse than no scanner: it reports green on provider resources and
attributes released after November 2025, which is a **false negative that looks like coverage**. Remove it in
the same PR that adds Checkov, never leave both.

## KICS — breadth, with caveats

**When it earns a place:** the repo uses an IaC format Checkov and Trivy do not cover well — Pulumi, Ansible
at depth, CDK/CDKTF synthesized output, Crossplane, Google Deployment Manager, OpenAPI at scale. KICS's
2,400+ queries span more formats than either.

```bash
docker run --rm -v "$PWD:/path" checkmarx/kics:v2.1.11 scan \
  -p /path/infra \
  --exclude-severities info,low \
  --report-formats sarif \
  -o /path/results
```

`scan -p <path>` · `-t/--type` restricts platform (`Terraform`, `Kubernetes`, `Ansible`, `Pulumi`, …) ·
`--exclude-severities` · `--fail-on high,medium` controls the exit code · `--report-formats`
(`json`, `sarif`, `html`, `junit`) · `--libraries-path` / `--queries-path` for custom Rego queries.

**Three caveats before adopting it:**

1. **Its GitHub Action was compromised on 23 March 2026.** Use the **Docker image pinned by digest**, not the
   marketplace action, and treat this as the concrete case for the plugin's pin-everything invariant — an
   unpinned `@master` scanner action is arbitrary code execution in a job that, for plan scanning, holds
   cloud credentials.
2. **Query overlap with Checkov is heavy.** Adopting both without scoping means the same misconfig fails twice
   — the double-gating anti-pattern the SKILL.md fence is entirely about. If KICS goes in, scope it with
   `-t` to the formats Checkov does **not** cover, and let Checkov keep the Terraform/K8s gate.
3. **Custom queries are Rego but not portable.** KICS Rego is written against its own normalized document
   model, so a query does not move to Conftest or Gatekeeper. If org rules are the driver, write Conftest
   policies instead — they run in three places.

## The commercial lane

The library's rule (plan §8 decision 2): **OSS is the default runnable path — nothing depends on a paid
license to run a lane.** Commercial tools are named so a licensed team knows where they fit, never assumed.

| Tool | Where it fits | What it adds over the OSS path |
|---|---|---|
| **Prisma Cloud** (Palo Alto) | The commercial platform **behind Checkov** | Central policy management, cross-repo baselines, severity metadata for every check, drift correlation between the IaC finding and the running resource. `checkov --bc-api-key` connects an OSS run to it |
| **Wiz** | CSPM + IaC-to-cloud correlation | Traces a template finding to the running resource and its actual internet exposure — the "is this reachable" question a static scan cannot answer. Sits mostly in `devops:cloud-posture`'s lane |
| **Snyk IaC** | PR-native IaC scanning | Developer-workflow polish and inline PR fixes; overlaps Checkov's catalogue closely |
| **Microsoft Defender for Cloud (DevOps security)** | Azure DevOps / GitHub | Rolls IaC findings into the same posture view as the Azure runtime posture — relevant given the library's Azure DevOps default |
| **HashiCorp Sentinel** | Terraform Cloud/Enterprise policy | The commercial peer of OPA/Conftest, enforced at the **apply** gate rather than the PR. Rego does not port to it |

If a licensed tool is already the org's gate, **do not add a second one** — apply the same one-owner-per-class
rule from the SKILL.md fence, and use this skill for the layer the licensed tool does not cover (usually the
org-specific policy-as-code half, which most platforms charge extra for or express less flexibly).

## Cross-references

- `references/checkov.md` — the primary scanner.
- `references/opa-conftest.md` — the org-rules layer, and the migration target for Terrascan policies.
- `qa-<stack>:image-infra-scan` — **owns Trivy**, including the absorbed tfsec check library. Migrate
  inherited tfsec jobs there, not here.
- `devops:cloud-posture` — where the "is the finding reachable in the running account" question actually
  belongs (Prowler / ScoutSuite, and the commercial CSPM lane).
