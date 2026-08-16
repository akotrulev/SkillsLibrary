# Cloud Posture — AWS (Prowler / ScoutSuite)

AWS is Prowler's strongest and oldest coverage — hundreds of checks across IAM, S3, EC2, RDS, KMS, CloudTrail, GuardDuty, Config, and more. Start here.

> **Authorization-first.** Everything below reads a live AWS account. Record `Authorization: <account/org scope + who authorized + expiry>` before running, treat it as `#volatile`, and use an account you own. The identity is **read-only** — a posture scan never writes.

## The read-only identity

Prowler and ScoutSuite need read across the account. The AWS-managed pair covers most of it; a small supplementary policy fills the gaps Prowler's checks reach that `SecurityAudit`/`ViewOnlyAccess` miss (e.g. `account:Get*`, `apigateway:GET`, some `*:List*`/`*:Describe*`).

- **`SecurityAudit`** (AWS managed) — the primary read policy for security posture.
- **`ViewOnlyAccess`** (AWS managed) — broad describe/list read.
- **Supplementary read policy** — Prowler ships the exact JSON (the `prowler-additions`/`ProwlerScan` policy in the repo's `permissions/`); attach it for full check coverage.

Never grant more than read. If a check reports "access denied," add the specific read action — never a wildcard write.

## Authenticating

Prowler uses the standard AWS SDK credential chain — a named profile, env vars, an assumed role, or an instance/OIDC role.

```bash
# Named profile (local).
prowler aws --profile security-audit

# Assume a dedicated read-only role (preferred — the role carries SecurityAudit + supplementary).
prowler aws --role arn:aws:iam::123456789012:role/prowler-security-audit

# Scope to regions / services when you don't need the whole account.
prowler aws --profile security-audit --regions eu-west-1 eu-west-2 --services s3 iam cloudtrail kms
```

**In CI: OIDC only.** Assume the read-only role via `aws-actions/configure-aws-credentials@v4` with `permissions: id-token: write` — no `AWS_ACCESS_KEY_ID`. A long-lived key is a blocker finding (the library's no-static-cloud-credentials invariant).

## Org-wide scanning (all accounts)

For an AWS Organization, assume a role that exists in every member account, plus the Organizations management role for account metadata:

```bash
prowler aws \
  -R arn:aws:iam::<member-account>:role/prowler-security-audit \
  -O arn:aws:iam::<mgmt-account>:role/prowler-organizations-reader
```

- `-R`/`--role` — the member-account role to assume (deploy the same role name to every account).
- `-O`/`--organizations-role` — the role in the Organizations management account (pulls account names/tags so the report reads by account, not id).

Loop the active-account list from Organizations and run per account (parallelizable), or drive it from the management account. This is the scheduled nightly shape for a multi-account estate.

## The scan — headline checks

```bash
# Full account, CIS 3.0 AWS, HTML for humans + OCSF for machines.
prowler aws --compliance cis_3.0_aws --output-formats html json-ocsf --output-directory "reports/$(date +%F)"

# The gate — Critical/High failures only.
prowler aws --severity critical high --status FAIL --compliance cis_3.0_aws --output-formats json-ocsf
```

What the headline AWS checks catch (map each to a CIS control + an ATT&CK Cloud technique per the SKILL's two-spine rule):

- **IAM** — root account MFA/access keys (`iam_root_mfa_enabled`, `iam_no_root_access_key`), unused credentials, password policy, over-permissive policies (`*:*`), access-key rotation → T1078.004 / T1098.
- **S3** — public buckets/ACLs (`s3_bucket_public_access`), bucket encryption, block-public-access, secure-transport policy → T1530 (public storage), A02.
- **Encryption at rest** — EBS/RDS/S3/KMS default encryption, KMS key rotation → CIS crypto controls.
- **Encryption in transit** — ELB/CloudFront TLS policy, S3 `aws:SecureTransport` → pairs with `qa-security-certificate-scan` for the endpoint TLS.
- **Logging/audit** — CloudTrail enabled in all regions + log-file validation + KMS-encrypted (`cloudtrail_multi_region_enabled`), Config recorder on, VPC flow logs → T1562.008 / A09.
- **Network exposure** — security groups open to `0.0.0.0/0` on sensitive ports, public RDS/EC2, default-VPC use → T1580.

## ScoutSuite on AWS

```bash
scout aws --profile security-audit --report-dir "reports/scout/$(date +%F)"
# Scope services / regions if the account is large.
scout aws --profile security-audit --services s3 iam ec2 rds --regions eu-west-1
```

Produces `scoutsuite-report/` — one offline HTML file, browse by service, colour-coded by rule severity. Hand it to the auditor; gate with Prowler.

## Commercial tools (references only — a licensed team already has these)

- **AWS Security Hub + Config + GuardDuty** — AWS-native continuous posture + threat detection; Security Hub aggregates CIS/AWS-FSBP findings. If the account already runs Security Hub, Prowler complements it (Prowler can even push findings to Security Hub via ASFF) rather than replacing it.
- **Wiz / Prisma Cloud (Palo Alto)** — agentless graph-based CNAPP; posture + workload + identity in one, with attack-path analysis. Where present, they are the primary CSPM and Prowler is the OSS second opinion / CI gate.
- **Prowler Pro / Prowler App** — the hosted SaaS of the same engine (scheduled scans, dashboards, ticketing integrations) for teams that want the OSS checks with a managed control plane.

The OSS path (`prowler`/`scout`) runs with nothing but the read-only role — nothing in this skill depends on a paid license.
