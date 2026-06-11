---
name: qa-file-storage-testing-java
description: Use when tests must assert object-storage side-effects — AWS S3 via LocalStack or Azure Blob via Azurite: uploads, downloads, presigned/SAS URLs, multipart/block staging, storage-triggered events. Triggers: "assert the export landed in the bucket", "test the presigned-URL flow", "verify blob metadata/tier". Pick the store in the decision matrix, then read its reference file.
---

# QA — File Storage Testing (Java 21)

One registered skill, 2 tools — a project uses exactly one. Identify the project's tool
(dependencies, docker-compose, infra config; ask one question if ambiguous), then **read the matching
`references/<tool>.md` end-to-end before writing any code** — it carries the full model, patterns,
templates, anti-patterns, and hard rules for that tool. This file only routes and holds the rules
shared by every tool in the family.

## Tools in this family

| Read | Use when |
|------|----------|
| `references/s3.md` | AWS S3 via LocalStack — buckets/keys, multipart, presigned URLs, versioning, S3→SQS events |
| `references/azure-blob.md` | Azure Blob via Azurite — containers, block staging, SAS tokens, tiers, snapshots |

## Decision matrix — pick the tool

| Need | Use | Why |
|------|-----|-----|
| Assert against **AWS S3** (buckets/keys, multipart, presigned URLs, versioning, lifecycle, S3→SQS events) | **`references/s3.md`** | AWS-native object store; `software.amazon.awssdk:s3` is the first-class JVM client; LocalStack runs it locally |
| Assert against **Azure Blob Storage** (containers/blobs, SAS tokens, blob tiers, Event Grid → Storage Queue) | `references/azure-blob.md` | Azure-native; container/blob not bucket/key, SAS not presigned, Azurite not LocalStack |
| Assert a **message** was produced/consumed, no object store in the flow | `qa-messaging-testing-java` | Pure queue assertion; here SQS appears only as the *downstream* of an S3 event |
| Assert a **DB row** was written, no object store | `qa-db-testing-client-java` | Pure DB verification; reuse its Awaitility wait for the eventual side here |
| Mock a downstream **HTTP** dependency the SUT calls | `qa-api-mocking-java` | Not storage — a synchronous request/response fake |

**Rule of thumb:** *AWS bucket + keys, presigned URLs, S3 events?* → S3. *Azure container + blobs, SAS?* →
azure-blob. *A queue with no object?* → messaging. *A row with no object?* → db-testing.

> **The `s3`-vs-`azure-blob` boundary in one line.** S3 is **buckets + keys**, addressed path-style against **LocalStack**,
> with **presigned URLs**, a `putBucketNotificationConfiguration` → SQS/SNS event bridge, and `forcePathStyle`.
> Azure Blob is **containers + blobs** against **Azurite**, with **SAS tokens** (the presigned-URL analogue),
> **Event Grid → Storage Queue** notifications, and blob **access tiers**. Same two assertion shapes, different
> store.

## Shared rules (every tool in this family)

- Local emulator (LocalStack / Azurite) via Testcontainers — never a real cloud bucket in tests.
- Unique bucket/container or key prefix per test, plus cleanup.
- Condition-wait for async object processing; assert content and metadata, not listing timing.

## Cross-references

Each `references/<tool>.md` carries its own cross-references to sibling skills (DB verification,
test environments, CI, chaos). Route there after picking the tool.
