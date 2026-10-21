# enumerate-iam — authenticated permission brute-force + principal/trust enumeration

Once a credential is in hand — from a leaked key, a lab-provided test identity, or a confirmed metadata-service chain — the next question is always the same: **"I have these keys — what can they actually do?"** Direct policy reads (`iam:GetPolicy`, role listings) are frequently denied to a deliberately-scoped test principal, so the answer comes from a **non-destructive permission brute-force**: firing read-only `Get*`/`List*`/`Describe*` calls and recording which succeed versus return `AccessDenied`. The success set **is** the permission map, inferred without ever reading a policy document. ATT&CK Cloud: **T1087.004 — Account Discovery: Cloud Account.**

## Invocation

```bash
# enumerate-iam (A. Riancho) — AWS, non-destructive get/list probing against a held credential.
python enumerate-iam.py --access-key <id> --secret-key <key> [--session-token <token>]

# Always confirm the principal first, independent of the tool.
aws sts get-caller-identity
```

- **`enumerate-iam`'s technique generalizes** across clouds: GCP's `testIamPermissions` API answers the same question directly (ask "can this principal do X" for a list of permissions, in one authenticated call, rather than brute-forcing); Azure's equivalent is reading role assignments for the signed-in principal (`az role assignment list --assignee <id>`). `cliam` (securisec) is a cross-cloud alternative to `enumerate-iam` worth naming if a single tool across AWS/Azure/GCP is preferred.
- **Non-destructive by construction.** Every call in the brute-force set is a `Get*`/`List*`/`Describe*` read — never a mutating call. This is what keeps the technique inside the "recon, not exploitation" fence even though it is authenticated and active.
- **Maintenance note:** `enumerate-iam`'s internal API-call map is generated from the AWS SDK and goes stale as AWS ships new API calls — regenerate it against the current `aws-sdk-js` roughly quarterly, or its "success set" undercounts what the credential can actually do.

## Whoami — always the first call

Every authenticated pass opens with the provider's identity check, before anything else:

```bash
aws sts get-caller-identity
az account show          # or: az ad signed-in-user show
gcloud auth list && gcloud config list
```

This confirms which principal you are testing *as*, before attributing any subsequent finding to it — and every one of these calls is itself logged against that principal in the provider's audit trail (CloudTrail / Azure Activity Log + Entra sign-in logs / GCP Cloud Audit Logs). Enumeration is attributable by construction; that is the awareness point, not a reason to avoid testing under authorization.

## Principal / role / trust enumeration

Beyond "what can I do directly," enumerate what the principal can **become**:

- List roles and read their **trust policies** to find assumable roles (`sts:AssumeRole` for AWS, cross-account/cross-project trust for Azure/GCP) and flag over-broad `Principal: *` trust statements.
- Build the escalation graph this produces — which roles are reachable, by what trust edge — as leads for the provider skill's privilege-escalation-graph tooling (PMapper for AWS models this formally; cross-referenced, not duplicated here).
- **OIDC / workload-identity-federation trust** rides in this same lane: enumerate OIDC identity providers (AWS), federated identity credentials (Azure), and workload-identity-federation pools/providers (GCP), reading their trust conditions for wildcard or missing-scope subjects (the GitHub Actions `sub` claim shape, detailed in `SKILL.md`'s OIDC section). **Never validate a token exchange across a condition that could span tenants** — enumerate the condition as a config read only.

## What it answers

"Principal P can perform {these actions} on {these resources}, and can assume {these roles}" — a reachability map, scored by blast-radius, never a dump of policy JSON or secret values.

## How it feeds the provider skills

- The permission map and the assumable-role graph are the direct feedstock for each provider skill's **IAM privilege-escalation** section (`cloud-attack-aws`'s PMapper-graphed privesc paths, and the Azure/GCP equivalents).
- An over-broad OIDC/federation trust condition is handed to the provider skill as a federation-abuse lead, never exploited here.
- A principal with unexpectedly broad `Get*`/`List*` reach across services (e.g. discovering it can also enumerate a second service's resources) feeds `SKILL.md`'s Cloud Infrastructure/Service Discovery sections (`T1580`/`T1526`) as the resource-inventory half of the same pass.

## Anti-patterns

- **Running the brute-force against a principal outside the cloud scope file.** Every call is attributable; confirm the principal's account/subscription/project before the first call, not after.
- **Treating a stale `enumerate-iam` API map as authoritative.** An undercounted success set understates the credential's real reach. *Fix:* regenerate the map periodically; note its last-regenerated date in the engagement record.
- **Validating a cross-tenant OIDC token exchange "just to confirm."** This is the universal red line every provider's rules-of-engagement forbid outright. *Fix:* enumerate the trust condition only; never execute the exchange unless the subject is unambiguously the in-scope tenant's own.
- **Reporting the permission map as a raw success/failure call log.** *Fix:* synthesize it into the blast-radius statement ("P can do X on Y, and assume Z") the report format expects.
