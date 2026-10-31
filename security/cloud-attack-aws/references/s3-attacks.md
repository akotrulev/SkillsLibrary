# S3 abuse & object exfil — public exposure, policy/ACL abuse, snapshot seams

Feeds Step 3 (service exploitation) of `../SKILL.md`. S3 is the classic AWS data-exposure and exfil
target. Maps to **`T1619` Cloud Storage Object Discovery** and **`T1530` Data from Cloud Storage**; the
snapshot-restore seam that lands credential-bearing filesystems maps to **`T1537` Transfer Data to Cloud
Account** / **`T1578.001`/`.002`**. Only in-scope buckets/accounts from the cloud scope file; a recovered
object is reported as *what category it holds and what it unlocks*, never its content.

## The access model, in attack terms

- **Bucket names are a global namespace** — predictable/brute-forceable (`<company>-backups`, `-logs`,
  `-dev`, `-assets`, `-prod`). A response distinguishes **doesn't-exist** (404) from **exists-but-protected**
  (403) from **exists-and-public** (200/XML `ListBucketResult`) — that three-way split is the whole
  anonymous-discovery technique, shared with `cloud-recon-enumeration`'s storage discovery.
- **Access is gated by** bucket ACLs (legacy), bucket policies, the account+bucket **Block Public Access**
  toggles, and object ownership. Misconfig = public read/write/list, or a bucket policy trusting `*` or the
  wrong account.

## Anonymous / public exposure (`T1619`, `T1530`)

```bash
aws s3 ls s3://<bucket> --no-sign-request                     # unauthenticated list of a public bucket
aws s3 cp s3://<bucket>/<key> - --no-sign-request             # unauthenticated object read
curl https://<bucket>.s3.amazonaws.com/                       # XML ListBucketResult if public
```

- Anonymous `ListBucket`/`GetObject` needs no credentials. Read the grant with `s3:GetBucketPolicy` /
  `s3:GetBucketAcl` to characterize *why* it is exposed.

## Authenticated abuse — policy/ACL and object discovery

```bash
aws s3api get-bucket-policy --bucket <b>                      # read the grant
aws s3api put-bucket-policy --bucket <b> --policy file://...  # grant self/* access (mutation — lab + scoped only)
aws s3 ls s3://<b> --recursive                                # object discovery (T1619)
aws s3 cp s3://<b>/<key> ./                                   # GetObject on interesting keys: .env, tfstate, DB dumps
aws s3api put-object --bucket <b> --key app.js --body ...     # plant/overwrite served content (lab + scoped only)
```

- `s3:PutBucketPolicy`/`PutBucketAcl` to grant yourself or `*` access, and `PutObject` to overwrite a
  config/JS asset served to users, are **mutations** — exercise only against a scoped lab bucket and record
  for cleanup.
- Object discovery then targeted `GetObject` on backups, `.env`, `tfstate`, and DB dumps is the data-exfil
  path — report the **category and blast-radius** of what a readable key holds, never its content.

## The snapshot seam (`T1537`, `T1578`)

EBS/RDS snapshots are the data-exfil seam that bypasses bucket controls entirely: `CreateSnapshot` →
`ModifySnapshotAttribute createVolumePermission=all` (or share to a specific account) → restore a volume
under attacker control and read its filesystem for credentials/keys. Same pattern for RDS
(`ModifyDBSnapshotAttribute`/`ModifyDBClusterSnapshotAttribute` with `all`) and for shared/public AMIs.
Read-only exfil of **your own lab** volumes; **unshare and delete** the snapshot in cleanup.

## Detection footprint (awareness, not evasion — D5)

- **Object-level `GetObject`/`PutObject` are CloudTrail data events — off by default.** Check
  `aws cloudtrail get-event-selectors` to know whether object reads are logged; report "object reads
  unlogged" as a **defender-coverage gap**, never use it as a stealth path.
- **Bucket-level actions** (`PutBucketPolicy`, `PutBucketAcl`) are **management events, always logged**, and
  a bucket just made public tends to trip GuardDuty `Policy:S3/BucketPublicAccessGranted` /
  `BucketAnonymousAccessGranted`; anomalous bulk reads trip `Exfiltration:S3/AnomalousBehavior` (S3
  protection). Name the `eventName` + finding per technique.

## What this feeds

A confirmed public bucket, writable policy, or snapshot-exfil path is reported (CVSS + ATT&CK Cloud id) via
`penetration-testing:reporting`, and is the lead `security/cloud-incident-response` keys its S3/data-exfil
runbook on.
