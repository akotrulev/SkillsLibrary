# Lab setup — GCPGoat in an owned project

Stand up, exercise, and tear down **GCPGoat** (`github.com/ine-labs/GCPGoat`), the owned-lab target this
skill practises against. **Deploy only into a new, disposable GCP project you control.** Never a
production project, never a shared-services project, never a project outside the committed cloud scope
file.

## What GCPGoat covers

A deliberately-vulnerable, Terraform-deployed GCP environment (INE Labs) covering OWASP Top 10 (2021) web
risks **plus** misconfiguration across **IAM, Cloud Storage buckets, Cloud Functions, and Compute
Engine**. Documented attack-path scenarios:

- **Compute Engine SSRF → metadata SA token theft** — a web-app SSRF reaches `169.254.169.254` and steals
  the VM's attached SA token (`../SKILL.md` Step 3, `T1552.005`).
- **Privilege escalation via a default/over-privileged SA** — a VM carrying the old default-Editor SA,
  pivoted to owner-level access (`references/gcp-privesc.md`).
- **Cloud Storage** — public/misconfigured bucket enumeration and data exposure
  (`references/gcp-bucket-brute.md`).
- **Cloud Functions** — a vulnerable function plus deploy/invoke-as-SA (`references/gcp-privesc.md`
  method 8/9).
- **Cloud SQL / data-store exposure** and further privilege escalation inside Compute Engine.

Complementary targets worth naming alongside GCPGoat for isolated-technique practice: **CNAPPgoat**
(multi-cloud, INE/Ermetic) for a lighter single-misconfiguration drill, and a thunder-ctf-style challenge
set for privesc-chain practice without the full web-app surface.

## Prerequisites

- A **dedicated, throwaway GCP project** inside an org you control — never an existing, shared, or
  production project. Create it specifically for this lab and plan to delete it after.
- Billing enabled on that project, with a **budget alert** configured before deploying anything.
- `gcloud` CLI and Terraform installed locally, authenticated against the throwaway project
  (`gcloud auth login` + `gcloud config set project LAB_PROJECT_ID`).
- Org Policy on the project allows the APIs GCPGoat needs (Compute Engine, Cloud Storage, Cloud
  Functions/Cloud Run functions, Cloud SQL, IAM) — check for an org-level constraint that blocks any of
  these before running `terraform apply`, so the deploy doesn't fail partway through.
- A committed **cloud scope file** naming the lab project id as the sole in-scope resource, with an
  **expiry date** on the authorization line — the same gate every live act in `../SKILL.md` requires,
  applied to the lab itself.

## Deploy

```bash
git clone https://github.com/ine-labs/GCPGoat
cd GCPGoat
# Set the project/region variables per the repo's own instructions (terraform.tfvars or equivalent).
terraform init
terraform plan                 # review every resource before creating anything
terraform apply
```

- Review the `terraform plan` output before applying — confirm nothing targets a resource outside the
  throwaway project.
- Once applied, **record every created resource and service account** (SA emails, bucket names, instance
  names) into the cloud scope file as the lab's known-good inventory — this is what makes later Cloud
  Audit Log / SCC review legible (Step 4 of `../SKILL.md`): you know what *should* be there, so anything
  else is signal.
- Enable **Admin Activity log review** (it is always-on by default, but confirm it is actually being read
  — a logged-but-unread event is a defender-coverage gap worth noting, per the posture↔exploitation
  handoff).

## Exercise

Work the lab in the same order as `../SKILL.md`'s steps: enumerate (`references/gcp-enum.md`), chain
privilege escalation (`references/gcp-privesc.md`), exploit the storage/metadata/function surface
(`references/gcp-bucket-brute.md` + Step 3), then review what landed in Cloud Audit Logs and Security
Command Center against what was actually done (Step 4) — the lab's value is confirming the detection
story closes, not just that the exploit chain works.

## Guardrails while the lab is live

- **Isolated project only** — never attach the lab's Terraform state, service accounts, or buckets to
  anything shared or production.
- **No DoS, ever**, even against a disposable lab — a destructive demo (deleting a resource, exhausting a
  quota) is skipped or reverted immediately, matching the production discipline so the habit doesn't
  diverge between lab and real engagement.
- Keep the **budget alert** active for the lab's lifetime; GCPGoat's Compute/Cloud SQL resources accrue
  cost even when idle.
- Snapshot the IAM policy state after deploy (`gcloud projects get-iam-policy LAB_PROJECT_ID`) so a
  post-exercise diff shows exactly what the exercise changed, separate from what GCPGoat's Terraform
  created.

## Teardown

```bash
terraform destroy
```

- **Delete any out-of-band SA keys minted during the exercise** that `terraform destroy` won't know
  about — a key created via `gcp-privesc.md`'s method 4 is not Terraform-managed state, and `destroy`
  will not revoke it; list and delete explicitly: `gcloud iam service-accounts keys list --iam-account=SA`
  then `gcloud iam service-accounts keys delete KEY_ID --iam-account=SA`.
- **Delete or disable the project** after the exercise — don't leave a vulnerable-by-design environment
  running past the exercise window, even inside a project nominally dedicated to it.
- **Revoke the scope file's authorization at its stated expiry** — the same `#volatile`, never-cached
  discipline as a live engagement.
- **Scrub any harvested-secret notes** down to blast-radius descriptions only — no recovered key, token,
  or secret value is retained past the exercise, in notes or anywhere else (§2.5 loot redaction applies
  to lab exercises exactly as it applies to a real engagement).
