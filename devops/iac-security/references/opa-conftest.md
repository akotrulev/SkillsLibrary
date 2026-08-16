# OPA / Conftest — policy-as-code deep dive

**Conftest** (CNCF, part of the Open Policy Agent project, single Go binary) runs **Rego** policies against
structured configuration: Terraform HCL and plan JSON, Kubernetes manifests, Helm output, Dockerfiles, YAML,
JSON, TOML, INI, XML, and ~20 other formats. Read this when the rule you need is **org-specific**, spans
arbitrary config, needs real logic, or must be **shared** with an admission controller.

## Checkov custom policy vs Rego — pick once

| | Checkov custom policy | OPA / Conftest |
|---|---|---|
| Rule shape | One resource type's attributes; a graph connection | Arbitrary structure, cross-document, set/aggregate logic |
| Language | YAML (declarative) or Python | Rego |
| Report | Same run, same baseline, same SARIF as built-ins | Separate run and exit code |
| Reuse | Checkov only | **The same Rego runs in Conftest, OPA Gatekeeper, Terraform Cloud/Enterprise, and Kyverno-adjacent tooling** |
| Best at | "Every RDS cluster retains 30 days" | "The set of resources in this plan must not exceed 3 public endpoints, and only in the DMZ account" |

Reuse is usually the deciding factor: a Rego rule written once gates the PR (Conftest) **and** blocks the
apply at admission time (Gatekeeper). That is a guardrail; a PR-only check is a suggestion.

## Rule kinds and exit codes

Conftest looks for three rule names in each policy package: **`deny`**, **`violation`**, and **`warn`**.

| Rule | Effect |
|---|---|
| `deny` / `violation` | Failure. Exit code `1` |
| `warn` | Warning. Exit `0` by default; exit `1` with `--fail-on-warn` |

`violation` differs from `deny` only in that it can return a structured object (`{"msg": ..., "details": ...}`)
rather than a plain string. Use `warn` as the **informational lane** — the direct analogue of Checkov's
`--soft-fail` pass: a new rule ships as `warn`, the backlog gets cleared, then it is promoted to `deny`.

Suffixed names work too (`deny_missing_tags`), which is what makes unit tests readable — you assert *that
rule* fired rather than string-matching a message.

## Running it

```bash
# Kubernetes manifests — the default: policies in ./policy, package main.
conftest test deploy/*.yaml

# Explicit policy dir, repeatable.
conftest test tfplan.json --policy ./infra/policies/opa

# Terraform HCL directly (no plan) — force the parser.
conftest test infra/environments/prod/main.tf --parser hcl2

# Helm → policy: render first, read from stdin.
helm template ./charts/api | conftest test - --policy ./policy/k8s

# Cross-document rules: --combine merges every input into one array so a policy
# can reason about the SET (e.g. "every Deployment has a matching PDB").
conftest test deploy/*.yaml --combine --policy ./policy/k8s

# Non-default namespaces (packages other than `main`).
conftest test tfplan.json --namespace org.network --namespace org.tagging
conftest test tfplan.json --all-namespaces
```

| Flag | Effect |
|---|---|
| `-p, --policy` | Policy directory. Default `./policy`. Repeatable |
| `-n, --namespace` / `--all-namespaces` | Which Rego package(s) to evaluate. Default `main` |
| `-d, --data` | JSON/YAML data files the policies `import data.…` — the allow-lists live here |
| `--combine` | Merge all inputs into one document so rules can reason across files |
| `--parser` | Force a parser (`hcl2`, `dockerfile`, `yaml`, `json`, `toml`, `ini`, `edn`, `xml`) |
| `--ignore` | Regex path exclusion |
| `--fail-on-warn` | `warn` becomes exit `1` (exit `2` reserved for failures) |
| `--no-fail` | Always exit `0` — the informational pass |
| `-o, --output` | `stdout`, `json`, `tap`, `table`, `junit`, `github`, `azuredevops`, **`sarif`** |
| `--trace` | Print the Rego evaluation trace — the debugging tool when a rule silently never fires |
| `-c, --config-file` | `conftest.toml`, so local and CI agree |

Config precedence: **CLI flags → `CONFTEST_*` env vars → `conftest.toml`**.

## Writing policies

```rego
# infra/policies/opa/tags.rego
package main

import rego.v1

required_tags := {"env", "service", "owner", "cost_center"}

deny contains msg if {
	change := input.resource_changes[_]
	not is_delete(change)
	missing := required_tags - {t | change.change.after.tags[t]}
	count(missing) > 0
	msg := sprintf("%s is missing mandatory tags: %v", [change.address, missing])
}

is_delete(change) if {
	count(change.change.actions) == 1
	change.change.actions[0] == "delete"
}
```

```rego
# infra/policies/opa/network.rego — an org rule no vendor catalogue ships.
package main

import rego.v1

dmz_accounts := {"1234567890", "0987654321"}

deny contains msg if {
	change := input.resource_changes[_]
	change.type == "aws_security_group_rule"
	change.change.after.type == "ingress"
	"0.0.0.0/0" in change.change.after.cidr_blocks
	not input.variables.account_id.value in dmz_accounts
	msg := sprintf("%s opens ingress to 0.0.0.0/0 outside a DMZ account", [change.address])
}
```

Notes that matter in practice:

- **`import rego.v1`** — OPA v1 syntax (`if`, `contains`, keyword-required rule bodies). New policies should
  use it; older `deny[msg] { … }` bodies still parse but will not survive an OPA major.
- The **plan JSON shape** is the contract: `input.resource_changes[]` with `.address`, `.type`,
  `.change.actions[]`, `.change.before`, `.change.after`, plus `input.variables`, `input.planned_values`, and
  `input.configuration`. **Skip deletes** — asserting tags on a resource being destroyed is noise.
- For **Kubernetes**, `input` is one manifest document (`input.kind`, `input.metadata`, `input.spec`), or the
  merged array under `--combine`.
- Put allow-lists (accounts, regions, approved AMIs, instance types) in a **`--data` file**, not in the
  policy — then updating the list is a data change, reviewable on its own.

## Testing policies — non-negotiable

An untested policy is green forever, which is worse than no policy: it manufactures confidence. Conftest ships
the test runner.

```rego
# infra/policies/opa/tags_test.rego
package main

import rego.v1

test_denies_when_tags_missing if {
	deny with input as {"resource_changes": [{
		"address": "aws_s3_bucket.logs",
		"change": {"actions": ["create"], "after": {"tags": {"env": "prod"}}},
	}]}
}

test_allows_when_all_tags_present if {
	count(deny) == 0 with input as {"resource_changes": [{
		"address": "aws_s3_bucket.logs",
		"change": {"actions": ["create"], "after": {"tags": {
			"env": "prod", "service": "orders", "owner": "platform", "cost_center": "cc-42",
		}}},
	}]}
}
```

```bash
conftest verify --policy ./infra/policies/opa    # runs every *_test.rego
```

Assert **both directions** — that the rule fires on a violation *and* stays quiet on a compliant input. A
test that only checks the failing case passes even when the rule matches everything.

## Sharing policies

```bash
# Publish the policy bundle as an OCI artifact and consume it from every repo.
conftest push ghcr.io/myorg/iac-policies:1.4.0 ./infra/policies/opa
conftest pull ghcr.io/myorg/iac-policies:1.4.0
conftest test tfplan.json --policy ./policy
```

- **Version and pin the bundle** (`:1.4.0`, never `:latest`) — a policy bundle is a build input, and the
  plugin's pinning invariant applies to it exactly as it does to actions and base images.
- The same Rego installed in **OPA Gatekeeper** as a `ConstraintTemplate` turns the PR check into an
  admission-time guardrail. Author once, enforce twice — a manifest that never went through CI still cannot
  land. Cross-link `devops-kubernetes` for the Gatekeeper install and `devops-k8s-security` for validating
  that admission actually blocks.

## Anti-patterns specific to this lane

- **A policy directory nobody runs `conftest verify` against.** Green forever, proves nothing. Add `verify` to
  CI next to `test`.
- **Rules that only look at `input.resource_changes[].change.after` without filtering deletes.** Every
  destroy fails the gate and the team learns to ignore it.
- **Hard-coding account IDs, regions, and AMI owners inside the Rego.** Put them in `--data`; a list change
  should not be a policy review.
- **Shipping a new rule straight as `deny`.** Land it as `warn`, clear the backlog, then promote — the same
  ratchet as Checkov's baseline.
- **String-matching messages in tests.** Name the rule (`deny_missing_tags`) and assert the rule, so
  rewording a message does not break the suite.
