# Identity abuse & token theft (`T1552.005` → `T1078.004`, `T1098.001`)

Feeds Step 2 of `../SKILL.md`. Three identity-abuse paths, highest-value first.

## Managed-identity IMDS token theft (`T1552.005` → `T1078.004`) — the highest-value path

The Instance Metadata Service at **`169.254.169.254`** issues OAuth bearer tokens for the MI attached to
the host; the only gate is the **`Metadata: true`** header — a minimal anti-SSRF measure, not an auth
control:

```
GET http://169.254.169.254/metadata/identity/oauth2/token
      ?api-version=2018-02-01&resource=https://management.azure.com/   # or ...vault.azure.net / ...graph.microsoft.com
Header: Metadata: true
```

For a **user-assigned** MI add `&client_id=<miClientId>`; App Service/Functions use `IDENTITY_ENDPOINT` +
`IDENTITY_HEADER` instead of the link-local IP. Two ways to reach it: code execution on the host, or an
**SSRF** in an app on the host (the `Metadata: true` header blocks naive URL-fetch SSRF but not SSRF that
sets custom headers, follows redirects, or proxies; IP-encoding and DNS-rebinding bypasses are documented
leads). **Impact = the MI's RBAC roles** — report as blast-radius ("MI held Contributor on RG x → could
read all storage keys / run commands on all VMs"), never the token value.

## Service-principal credential abuse (`T1078.004`, `T1552.001`)

Loot SP client secrets/certs from source control, pipeline variables, `.azure`/`.env` files, App Service
config, ARM/Terraform state, or Key Vault; authenticate non-interactively
(`az login --service-principal -u <appId> -p <secret|cert> --tenant <tid>`) to act as the SP with its
often-broad roles. SP sign-ins frequently **bypass MFA** (no interactive user) — a reason they are prized.

## Consent & app abuse / credential addition (`T1098.001`/`.003`, `T1528`)

Adding a client secret or certificate to an app/SP you can write to grants durable non-interactive access
(persistence + privesc); illicit OAuth consent to Graph scopes retains delegated access that survives
password resets. Note these as persistence mechanisms; never run phishing against third parties.

## Device-code & PRT (awareness only)

Device-code phishing (RFC 8628; Storm-2372 active since Aug 2024) and Primary-Refresh-Token abuse via the
Microsoft Authentication Broker client (`29d9ed98-a469-4536-ade2-f981bc1d605e`) are taught for
**recognition and detection**, not execution against live users — the skill teaches what these trip, and
that defenders block device-code flow via Conditional Access.

## What this feeds

A confirmed MI/SP token theft or credential addition is a headline finding for
`penetration-testing:reporting` (CVSS + ATT&CK Cloud id). The recovered token's reach (Key Vault, storage,
RBAC roles) chains into Step 3/4.
