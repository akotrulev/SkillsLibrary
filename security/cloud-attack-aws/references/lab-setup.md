# Lab setup — CloudGoat, flaws.cloud, and IAM Vulnerable in owned accounts

Stand up, exercise, and tear down the owned-lab targets this skill practises against. **Deploy only into a
new, disposable AWS account you control** — never a production account, never a shared-services account,
never an account outside the committed cloud scope file. Each lab is named in the scope file as an
in-scope resource, with an **expiry** on the authorization line, the same `#volatile` gate every live act
in `../SKILL.md` requires.

Three complementary targets:

| Lab | Vehicle | Covers | Teardown |
|---|---|---|---|
| **CloudGoat** (`RhinoSecurityLabs/cloudgoat`) | Terraform, scenario-based | IAM privesc, EC2 SSRF→metadata, S3 breach, Lambda privesc, RCE, ECS, secrets | `./cloudgoat.py destroy <scenario>` |
| **IAM Vulnerable** (`BishopFox/iam-vulnerable`) | Terraform, IAM-only | 250+ IAM resources, ~31 privesc paths — the hands-on companion to the 21-method list + PMapper/Pacu | `terraform destroy` |
| **flaws.cloud** / **flaws2.cloud** (Scott Piper) | Hosted CTF, no deploy | S3 misconfig, IAM, EC2/ECS metadata, Cognito; flaws2 adds a defender track | none (hosted) |

## Prerequisites

- A **dedicated, throwaway AWS account** (or a clearly isolated sub-account) you control — never an
  existing, shared, or production account. For the Terraform labs you need `admin` on it to apply.
- **Terraform**, the **AWS CLI** with an owned profile, and **Python 3** installed locally.
- A **billing alert / budget** configured on the account before deploying anything — CloudGoat and IAM
  Vulnerable create live, cost-accruing resources.
- A committed **cloud scope file** naming the lab account id (and region) as the sole in-scope resource,
  with an **expiry date** on the authorization line.

## CloudGoat (scenario-based vulnerable infra)

```bash
git clone https://github.com/RhinoSecurityLabs/cloudgoat && cd cloudgoat
./cloudgoat.py config profile            # point at the owned profile
./cloudgoat.py create <scenario>         # emits start creds + start.txt
# ... work the scenario ...
./cloudgoat.py destroy <scenario>        # ALWAYS, to stop spend and remove exposure
```

- **Scenario roster grows** — list the repo's `scenarios/` directory at deploy time rather than trusting a
  pinned list. Representative scenarios mapping to `../SKILL.md`: `iam_privesc_by_rollback` (Step 2,
  `SetDefaultPolicyVersion`), `iam_privesc_by_attachment`, `iam_privesc_by_key_rotation`, `ec2_ssrf` (Step 3
  IMDS), `cloud_breach_s3` (Capital-One-style SSRF→metadata→S3 exfil), `lambda_privesc` (PassRole+Lambda).
  `detection_evasion` is a **lab-only** detection-understanding scenario — it exists to teach what trips
  CloudTrail/GuardDuty (Step 4, D5), never to build an evasion recipe for a real target.
- `create` emits the starting credentials and a `start.txt`; record them and the created resources into the
  scope file as the lab's known-good inventory so later CloudTrail/GuardDuty review is legible.

## IAM Vulnerable (IAM privesc lab)

```bash
git clone https://github.com/BishopFox/iam-vulnerable && cd iam-vulnerable
terraform init
terraform plan                            # review every resource before creating anything
terraform apply                           # creates 250+ IAM resources + a low-priv entry user
# exercise: assume the entry user, then
pmapper graph create ; pmapper query 'preset privesc *'
#   or: pacu → set_keys → run iam__privesc_scan ; walk each path by hand
terraform destroy                         # mandatory — these are live privesc paths
```

- **CloudFoxable** (Bishop Fox) is the CTF-style successor worth naming alongside it for guided practice.
- Snapshot the IAM state after apply (`aws iam get-account-authorization-details`) so a post-exercise diff
  shows exactly what the exercise changed versus what Terraform created.

## flaws.cloud / flaws2.cloud (hosted, no deploy)

- **flaws.cloud** — 6 levels on S3 misconfig, IAM, and instance-metadata key theft; hosted by the author,
  nothing to deploy or tear down. **flaws2.cloud** — an **attacker** track (container/ECS metadata, Cognito)
  and a **defender** track (log analysis), which directly feeds the detection-surface section (Step 4).
- **Prereqs:** AWS CLI + a browser. **Deploy / teardown:** none — read-only external targets the author
  authorizes for learning. Still work them under a scope file noting them as the in-scope targets.

## Guardrails while a lab is live

- **Isolated account only** — never attach a lab's Terraform state, IAM principals, keys, or buckets to
  anything shared or production.
- **No DoS, ever**, even against a disposable lab — a destructive demo (deleting a resource, exhausting a
  quota, an account-locking credential brute-force) is skipped or reverted immediately, matching production
  discipline so the habit doesn't diverge.
- Keep the **budget alert** active for the lab's lifetime; CloudGoat/IAM-Vulnerable resources accrue cost
  even when idle.

## Teardown

- Run the lab's own destroy (`./cloudgoat.py destroy <scenario>` / `terraform destroy`) — **always**.
- **Delete any out-of-band artifacts `destroy` won't know about** — an access key minted via a Step-2
  privesc path, a shared/public EBS or RDS snapshot, a planted S3 object — are not Terraform-managed state:
  revoke/unshare/delete them explicitly (`aws iam delete-access-key`, `aws ec2 reset-snapshot-attribute`,
  `aws rds modify-db-snapshot-attribute --values-to-remove all`).
- **Delete or close the account** after the exercise where feasible — don't leave vulnerable-by-design infra
  running past the window.
- **Revoke the scope file's authorization at its stated expiry** — the same `#volatile`, never-cached
  discipline as a live engagement.
- **Scrub harvested-secret notes** down to blast-radius descriptions only — no recovered key, token, STS
  credential, or secret value is retained past the exercise, in notes or anywhere else (§2.5 loot redaction
  applies to lab exercises exactly as to a real engagement).
