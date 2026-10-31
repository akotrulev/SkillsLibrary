# Lab setup — AzureGoat in an owned tenant

Stand up, exercise, and tear down the owned-lab target this skill practises against. **Deploy only into a
new, disposable Azure subscription you control** — never a production subscription, never a shared-services
subscription, never a subscription outside the committed cloud scope file. The lab is named in the scope
file as an in-scope resource, with an **expiry** on the authorization line, the same `#volatile` gate every
live act in `../SKILL.md` requires.

**AzureGoat** (`github.com/ine-labs/AzureGoat`) — INE's intentionally-vulnerable Azure environment,
deployed by **Terraform into your own subscription**. Black-box by design, with escalation paths to
full-infrastructure takeover.

| Surface it exercises | Maps to `../SKILL.md` |
|---|---|
| Serverless vulnerable blog on **Azure Functions** → OWASP Top 10 web flaws | foothold (feeds `initial-access`) |
| **SSRF** on the Function env → reach **IMDS** → steal the Function's **managed-identity** token | Step 2 (MI IMDS theft, `T1552.005`→`T1078.004`) |
| **Storage Account** misconfigurations (public/over-permissive access, key exposure) | Step 4 (storage-key theft, `T1552`) |
| **Cosmos DB** backing store | Step 3/4 (data access) |
| **Azure Automation** (runbooks) in the chain | Step 4 (runbook/Hybrid-Worker code exec) |
| **Identities / RBAC** misconfigurations enabling privesc | Step 4 (role-assignment abuse) |

## Prerequisites

- A **dedicated, throwaway Azure subscription** (not shared/corp) you control, with a scoped SP or user
  holding **Contributor on a dedicated throwaway resource group** to apply.
- **`az` CLI** (owned login) and **Terraform** installed locally.
- A **budget alert** configured on the subscription before deploying anything — AzureGoat creates live,
  cost-accruing resources (Functions, Storage, Cosmos DB, Automation).
- A committed **cloud scope file** naming the lab subscription id (and region) as the sole in-scope
  resource, with an **expiry date** on the authorization line.

## Deploy

```bash
git clone https://github.com/ine-labs/AzureGoat && cd AzureGoat
az login                       # owned account
terraform init
terraform plan                 # review every resource before creating anything
terraform apply                # creates the vulnerable Functions app + storage + cosmos + automation
# capture the output app URL and resource IDs into the engagement notes / scope file inventory
```

- **Module/scenario layout grows** — check the repo README at deploy time rather than trusting a pinned
  layout here; AzureGoat has had multiple module versions.
- Record the deployed resource IDs into the scope file as the lab's known-good inventory, so later Entra
  sign-in / Azure Activity / Key Vault log review is legible against what you created.

## Guardrails while the lab is live

- **Isolated subscription only** — no production peering; never attach the lab's Terraform state, identities,
  keys, or storage to anything shared or production.
- **Tag all resources** `purpose=lab` so teardown and billing review are unambiguous.
- **No DoS, ever**, even against a disposable lab — password spray, load-testing, or a destructive demo
  (deleting a resource, exhausting a quota) is skipped or reverted immediately, matching production
  discipline so the habit doesn't diverge.
- Keep the **budget alert** active for the lab's lifetime; the resources accrue cost even when idle.

## Teardown

```bash
terraform destroy              # ALWAYS — these are live, vulnerable-by-design resources
```

- **Delete out-of-band artifacts `destroy` won't know about** — an SP credential or role assignment minted
  via a Step-4 privesc path, a SAS token, a runbook or Custom Script Extension, the GA elevate-access toggle
  (turn it back off) — these are not Terraform-managed state: revoke/remove them explicitly.
- Verify the resource group is deleted; rotate/remove the lab SP; confirm no orphaned public IPs, storage
  accounts, or Cosmos instances remain.
- **Revoke the scope file's authorization at its stated expiry** — the same `#volatile`, never-cached
  discipline as a live engagement; note teardown time against the authorization expiry.
- **Scrub harvested-secret notes** down to blast-radius descriptions only — no recovered token, SP secret,
  storage key, or Key Vault value is retained past the exercise, in notes or anywhere else (§2.5 loot
  redaction applies to lab exercises exactly as to a real engagement).

## Optional second range

PurpleCloud or an Entra-focused CTF range for directory-heavy drills — keep each in **its own subscription**,
under its own scope-file entry and expiry.
