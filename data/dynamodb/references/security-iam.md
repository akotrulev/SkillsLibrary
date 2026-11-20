# DynamoDB — security, IAM, backup and global tables

DynamoDB has no database users, roles, or `GRANT` — **IAM is the entire authorization surface**. Everything below is IAM policy plus a small amount of table configuration.

## Fine-grained (item- and attribute-level) access control

The headline capability: an IAM policy can restrict a principal to **only the items whose partition key matches the caller's identity**, and to **only a subset of attributes** — without any application code enforcing it. This is how you get real row-level multi-tenant isolation on a shared table.

- **`dynamodb:LeadingKeys`** (v2 alias **`FirstPartitionKeyValues`**) — restricts an operation to items whose **partition key** equals a value you bind to the caller's identity. Use with the **`ForAllValues:StringEquals`** set operator and a policy variable substituted from the identity (Cognito identity id, a SAML/OIDC claim, or a session tag).
- **`dynamodb:Attributes`** — whitelist the attributes a principal may read or write; pair with `dynamodb:Select = SPECIFIC_ATTRIBUTES` (reads) and `dynamodb:ReturnValues = NONE` (writes) so a caller can't exfiltrate columns by asking for `ALL_ATTRIBUTES`.

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:PutItem", "dynamodb:UpdateItem"],
  "Resource": "arn:aws:dynamodb:eu-west-1:111122223333:table/app",
  "Condition": {
    "ForAllValues:StringEquals": {
      "dynamodb:LeadingKeys": ["${cognito-identity.amazonaws.com:sub}"]
    },
    "StringEquals": { "dynamodb:Select": "SPECIFIC_ATTRIBUTES" },
    "ForAllValues:StringEquals": {
      "dynamodb:Attributes": ["PK", "SK", "name", "status", "totalMinor"]
    }
  }
}
```

The classic delivery vehicle is the **Token Vending Machine**: the client authenticates, a broker returns short-lived STS credentials scoped by `LeadingKeys` to that user/tenant, and the client talks to DynamoDB directly — the data plane enforces isolation even if the app query is sloppy. Because the guarantee lives in IAM, it is exactly the kind of control the `qa-security` peer's **BOLA/IDOR** access-control matrix should verify: prove tenant A's credentials cannot read tenant B's partition.

**Caveat:** `LeadingKeys` only constrains the **partition key**, and only on operations that carry it (`GetItem`, `Query`, `BatchGetItem`, `PutItem`, `UpdateItem`, `DeleteItem`). It cannot scope a `Scan`, and it cannot filter by sort key — model the tenant boundary into the partition key or don't rely on this.

## Action / resource scoping

- Grant **per-table and per-index** ARNs, never `dynamodb:*` on `*`. Index actions need the index ARN: `.../table/app/index/GSI1`.
- Separate read vs write policies; most services need `GetItem`/`Query`/`BatchGetItem` far more than `PutItem`/`UpdateItem`.
- Deny `dynamodb:DeleteTable`, `dynamodb:*Backup*`, and PITR-disabling actions on the runtime role — those belong to an ops/IaC role.
- If the app declares keys via attributes (see the .NET section of `connections.md`), it needs **no `dynamodb:DescribeTable`** grant.

## Encryption at rest — pick the key tier

At-rest encryption is **always enabled and cannot be turned off**; the only decision is who owns the key:

| Key tier | Use when | Notes |
|---|---|---|
| **AWS owned** (default) | No compliance requirement for key custody | Free, invisible, no CloudTrail on key use |
| **AWS managed** (`aws/dynamodb`) | You want key usage in CloudTrail with no key management | Free KMS key AWS rotates |
| **Customer managed (CMK)** | Compliance / audit / cross-account / "revoke by disabling the key" | You control rotation, grants, and CloudTrail; per-request KMS cost; **DynamoDB caches data keys** so it isn't per-item |

A CMK gives you the kill switch: disable the key and the table is instantly unreadable. Grant the runtime role `kms:Decrypt` (and `kms:GenerateDataKey` for writes) on that CMK. **In transit** is TLS by default — enforce it with an `aws:SecureTransport = true` condition and, in-VPC, a **gateway VPC endpoint** (`com.amazonaws.<region>.dynamodb`) so traffic never leaves the AWS network; scope the endpoint policy to the same table ARNs.

## Backup & recovery

- **PITR (point-in-time recovery)** — continuous backups, restore to any second in a rolling 35-day window. Turn it on for every table holding non-reconstructable data; it's the defense against a bad deploy or bulk delete. Restore creates a **new table** (you re-point the app), it never overwrites in place.
- **On-demand backups** — full snapshots you retain long-term (compliance holds) independent of the 35-day PITR window; via AWS Backup for cross-account/cross-region vaulting.

## Global tables (multi-region)

Global tables (current version `2019.11.21`) replicate a table across regions with **active-active, last-writer-wins** multi-region writes. They need PITR-grade discipline: identical IAM in each region, the CMK replicated per region (a CMK is regional — use a multi-region key or a per-region key), and app awareness that a write in one region is **eventually** visible in another. Reach for them only for genuine multi-region active-active or low-latency-global-reads requirements, not "for resilience" (a single-region table with PITR already survives an AZ loss).
