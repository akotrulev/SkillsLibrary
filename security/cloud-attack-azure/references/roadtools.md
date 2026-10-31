# ROADtools / ROADrecon (+ GraphRunner) — Entra ID directory enumeration from a token

Feeds Step 1 (Entra enumeration) of `../SKILL.md`. **ROADtools** (Dirk-jan Mollema) is the canonical
offline Entra ID enumeration framework: authenticate once, dump the directory, then query it locally.
**GraphRunner** (Black Hills) is the Microsoft-Graph post-exploitation companion. Both touch only in-scope
tenants named in the cloud scope file; every call is logged in the Entra sign-in and audit logs.

> **Currency caveat — ROADrecon `gather` is broken (2025).** The classic `roadrecon gather` ran against
> the **legacy Azure AD Graph** (`graph.windows.net`), which Microsoft has **retired** — so the stock
> `gather` fails. The working path is a **Microsoft-Graph community fork** (the upstream `msgraph` branch
> has been stale since Apr 2025). Confirm the fork and its branch at engagement time rather than trusting a
> pinned name here, and verify against the repo README before teaching the exact invocation.

## ROADrecon — authenticate, gather, explore

```bash
pipx install roadrecon            # install the working msgraph community fork, not the stale upstream gather
roadrecon auth -u user@tenant -p '<password>'     # or device-code / token-based auth
roadrecon gather                  # dump the directory (MS Graph fork) into roadrecon.db (SQLite)
roadrecon gui                     # local web UI over the offline DB — no further tenant calls
```

- The offline DB answers **"what does this token see?"** — users, groups (incl. dynamic-group rules), app
  registrations, service principals and their API permissions/credentials/owners, directory roles &
  assignments, and Conditional Access policies (enumerated for **awareness** of which controls exist, never
  to bulid a bypass — D5).
- `gather` is a **burst of Graph reads** — the aiohttp client is **detectable** (Elastic ships a prebuilt
  "ROADrecon aiohttp enumeration" rule). Recon is not invisible; report the footprint, do not try to hide it.
- Once the directory is mapped, the high-value leads for Step 2 are: **app/SP owners** (an owner can add a
  credential → impersonate), **SPs with broad API permissions**, and **dynamic-group rules** whose
  membership an attacker-controlled attribute satisfies.

## GraphRunner — Microsoft Graph post-exploitation (awareness-bounded)

```powershell
Import-Module .\GraphRunner.ps1
Get-GraphTokens                   # interactive device-code token acquisition
Invoke-GraphRecon                 # CA policies, app registrations, consent grants, directory roles
```

- Covers recon (CA/apps/consent), data pull (mail/SharePoint/OneDrive/Teams), and persistence (malicious
  OAuth app, group clone). In this lane the **recon** verbs are the authorized use; the data-pull and
  persistence modules are run **only against an owned lab tenant**, demonstrated-then-reverted, and reported
  as blast-radius (`T1098.001` illicit consent, `T1136.003` backdoor account) — never run against a third
  party, never phishing a real user.

## Detection footprint (awareness, not evasion — D5)

- Every `auth`/`gather`/Graph call writes an **Entra sign-in log** entry carrying the **client app id** used
  — the broker client `29d9ed98-a469-4536-ade2-f981bc1d605e` flags device-code/PRT flows. A directory dump
  is a high-signal burst; the aiohttp client matches a prebuilt Elastic rule.
- Directory **mutations** (adding an app credential, a consent grant, a role assignment) write **Entra audit
  log** entries — the `T1098` trail. Report the log each action writes so the defender knows what should have
  fired; never teach suppressing it.

## Cleanup

Any OAuth app, group clone, SP credential, or account created to prove a path is **deleted in cleanup**;
the offline `roadrecon.db` is directory loot — segregate it per the scope file's data-handling, report
blast-radius not contents, and never commit it.

## What this feeds

The directory map is the feedstock for Step 2 (identity abuse) and for **AzureHound → BloodHound**
(`azurehound.md`), which turns the same relationships into shortest-path-to-Global-Admin/Owner queries.
Confirmed findings carry their ATT&CK Cloud id to `penetration-testing:reporting`.
