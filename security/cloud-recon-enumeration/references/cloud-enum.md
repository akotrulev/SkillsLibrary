# cloud_enum — anonymous public-asset & storage discovery

**cloud_enum** (initstring, `initstring/cloud_enum`) permutes an organization's name against common affixes and queries each cloud's predictable storage/service DNS namespace **anonymously** — no credentials, no authentication, nothing attributable to a principal. It is the first tool run in any cloud recon pass, because it is the cheapest and quietest: it reads public DNS/HTTP responses, never the target's control-plane API.

## Invocation

```bash
# Keyword permutation against an org name (and known aliases) across AWS/Azure/GCP.
cloud_enum -k <orgname> -k <org-alias> -k <org-abbrev> \
  --disable-azure    # scope to the providers the engagement actually covers
# Narrow further with -m (mutations file) / -b (brute-force list) once the obvious affixes are exhausted.
```

- **Keyword choice matters more than tool flags.** Feed it every plausible org name variant (legal name, common abbreviation, product names) — the permutation engine does the affix work (`-dev`, `-backups`, `-assets`, `-logs`, `-prod`, etc.).
- **`--disable-<provider>`** scopes the run to only the clouds the cloud scope file actually names; running it against a provider the org has no footprint in is wasted noise, not a safety issue, but still worth scoping.
- Install via `pip install cloud_enum` or the pinned GitHub release; it ships in Kali.

## What it answers

For each permuted name, cloud_enum classifies the response as:

| Response | Meaning |
|---|---|
| 404 / NXDOMAIN | Doesn't exist |
| 403 / access-denied body | Exists, but protected (still a confirmed asset — worth recording even though it's not exploitable here) |
| 200 / listing body | **Exists and is public** — the recon hit |

Per-provider endpoint shapes it checks:

- **AWS S3** — `<bucket>.s3.amazonaws.com`, `<bucket>.s3.<region>.amazonaws.com`; a public bucket's listing returns XML `ListBucketResult`.
- **Azure Blob** — `<account>.blob.core.windows.net/<container>?restype=container&comp=list`, plus `file.`/`queue.`/`table.` endpoint siblings and `<app>.azurewebsites.net` app-service names.
- **GCP GCS** — `storage.googleapis.com/<bucket>`, `<bucket>.storage.googleapis.com`.

It also surfaces supporting public surface: open storage containers aside, certificate-transparency logs (crt.sh) and passive DNS enumerate subdomains that resolve to cloud front-ends (`*.cloudfront.net`, `*.azureedge.net`, GCP load-balancer IPs) — a provider footprint map even before a direct storage hit lands.

ATT&CK Cloud: **T1619 — Cloud Storage Object Discovery** (the anonymous half; the authenticated half is listing containers you already hold credentials for, covered in `enumerate-iam.md`'s permission map).

## How it feeds the exploitation skills

- **A public bucket/container (200/listing)** is a direct lead to the matching provider skill's storage-abuse section (`s3-attacks.md` for AWS, the Azure/GCP equivalents) — confirm what the listing contains, reported by category/count, never raw contents.
- **A protected-but-confirmed asset (403)** still narrows the org's resource-naming convention, feeding the next permutation round and ScoutSuite's targeted follow-up.
- **A subdomain resolving to a cloud front-end** maps the provider footprint for the engagement's later authenticated passes — which clouds actually matter here.

## Anti-patterns

- **Treating a 200/listing hit as implicit authorization to pull every object.** A public bucket is in scope only if the scope file's account/domain ownership covers it; report the exposure and its category of contents, not a bulk download.
- **Brute-forcing with an unbounded mutation list against a fragile/shared DNS resolver.** Keep keyword lists targeted; this is still network traffic, even if it's quiet.
- **Skipping the certificate-transparency / passive-DNS supporting pass.** It is free and frequently surfaces assets the direct storage-name permutation misses entirely.
