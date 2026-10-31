# CloudFox & ScoutSuite — read-only AWS situational awareness

Feeds Step 1 (enumeration) of `../SKILL.md`. Both tools are **read-only** (Describe/List/Get) — they
*find* leads, they do not exploit. **CloudFox** (`BishopFox/cloudfox`) is the offensive-recon tool that
surfaces leads plus ready-made follow-up commands; **ScoutSuite** (`nccgroup/ScoutSuite`) is the
whole-account misconfig snapshot, the same engine `devops:cloud-posture` runs defensively — run here to
seed exploitation leads rather than to benchmark posture. Only in-scope accounts/regions from the cloud
scope file.

## CloudFox — "what's here, what's reachable, where are the secrets, where's the privesc"

```bash
cloudfox aws --profile <in-scope-profile> all-checks          # the fastest single-command inventory
cloudfox aws --profile <p> instances                          # EC2 + attached instance profiles
cloudfox aws --profile <p> endpoints                          # internet-reachable endpoints
cloudfox aws --profile <p> secrets                            # Secrets Manager + SSM parameter names
cloudfox aws --profile <p> permissions                        # per-principal action map
cloudfox aws --profile <p> cape                               # cross-account privesc paths (needs PMapper data)
```

- **`all-checks`** runs the full set: `inventory`, `endpoints`, `instances`, `permissions`, `principals`,
  `role-trusts`, `access-keys`, `secrets`, `buckets`, `databases` (RDS connection strings), `env-vars`
  (Lambda), `route53`, `ecr`, `lambda`. It writes CSV/TXT plus **loot files** containing ready-to-run
  follow-up commands — the direct bridge into Steps 2–3.
- **`secrets`** surfaces *names and locations*, not values — report the blast-radius a readable secret
  implies, never its content (§2.5).
- **`cape`** computes cross-account privilege-escalation paths; it needs PMapper graph data (see
  `pmapper.md`) to resolve the edges.
- The loot files may name a recovered connection string or key — treat those as **blast-radius evidence**,
  never paste the value into a finding.

## ScoutSuite — whole-account misconfig snapshot as exploitation leads

```bash
scout aws --profile <in-scope-profile>          # multi-service audit → browsable HTML report
```

- Produces a browsable HTML report of account-wide misconfig: public S3, open security groups, weak IAM,
  missing encryption. Here it is a **lead generator**, not a posture benchmark — each red item is a
  candidate to *prove reachable* in Steps 2–3.
- This is the **posture↔exploitation handoff** named in `../SKILL.md`: a `devops:cloud-posture` ScoutSuite
  finding is a lead; confirming it is reachable here is reported back as validated posture.

## Detection footprint (awareness, not evasion — D5)

Every CloudFox/ScoutSuite call is a `Describe`/`List`/`Get` **management event**, logged against the
principal in CloudTrail; a high-volume sweep can itself trip `*:AnomalousBehavior`. Recon is attributable —
confirm the account is in-scope before the first sweep.

## What this feeds

CloudFox `permissions`/`cape` and ScoutSuite IAM findings seed PMapper + Pacu `iam__privesc_scan`
(Step 2); `secrets`/`buckets`/`databases` seed service exploitation (Step 3, `s3-attacks.md`). Confirmed
findings are reported (CVSS + ATT&CK Cloud id) via `penetration-testing:reporting`.
