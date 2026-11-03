---
paths:
  - "**/*.{tf,tfvars,bicep,bicepparam}"
  - "**/.terraform.lock.hcl"
---

<!-- devops rules v1 (2026-11-03): IaC. Installed by /devops:rules; edit the paths above to fit this project. -->

# Infrastructure-as-code standards (Terraform, Bicep)

Severity tags as in the core devops rules.

- Terraform state is remote and locked (Terraform Cloud, S3 with a lock, an Azure blob lease), one state per environment, and the backend authenticates by OIDC. Never local state, never state in git. *blocker*
- Small single-purpose modules, versioned; inputs typed and described, outputs documented. *minor*
- Resource names derive from a prefix variable; no hard-coded names. *minor*
- Every resource is tagged `env`, `service`, `owner`, `cost_center`. *major*
- `prevent_destroy`, a delete lock or deletion protection on every stateful or irreversible resource: databases, buckets and storage with content, Key Vaults, DNS zones. *major*
- `for_each` over a map keyed by a stable id, never a list whose reordering destroys and recreates. *major*
- No `null_resource` or `local-exec` doing what a resource can declare. *major*
- No public bucket or anonymous blob read; a static site is served through CloudFront with OAC or Front Door. *blocker*
- No `0.0.0.0/0` ingress to a workload; only the load balancer's security group or a named source reaches it, and workloads get no public IP. *major*
- Production runs at least two instances across zones. *major*
- Secrets live in Key Vault, Secrets Manager or Parameter Store, read by the workload's identity; never a plaintext app setting or task environment value. *blocker*
- One account or subscription, and one Key Vault, per environment. *major*
- A scanner suppression is `checkov:skip=<CHECK_ID>:<ticket and reason>` on the one resource, with a re-review date; the committed baseline only shrinks. *major*
