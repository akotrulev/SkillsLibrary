# File-Storage Testing — Azure Blob Storage (Node 24 + TypeScript / Vitest)

This is the **TypeScript sibling** of the `qa/typescript/skills/file-storage-testing/` node, **ported** from the
canonical .NET stack (`qa-dotnet:file-storage-testing`, **.NET-led by the user's choice** — Azure
Blob is Azure-native, the most authentic lead; the Azure SDK is first-class everywhere, so TS is the house
default language but not the canonical stack for this node). It **closes the `qa/typescript/skills/file-storage-testing/` family**
(s3 → azure-blob) in this stack. It is the sibling **ported from the `s3` node's structure** onto
Azure Blob — **same two assertion shapes, same eventual-consistency condition-wait discipline**; only the store
SDK and its primitives change. Where S3 has buckets/keys, presigned URLs, multipart upload, and LocalStack,
Azure Blob has containers/blobs, SAS tokens, block-blob staging, and Azurite. It reuses the same
verification-inside-tests lineage: the standard Testcontainers fixture discipline
and the **eventual-consistency condition-wait** (`expect.poll`) from `qa-typescript:db-connection`
(`db-testing/connection`). All three Azure SDKs mirror the same upload / download / exists / get-properties / list / delete + SAS +
block-staging model, so this is a true translate-the-concepts port, not a redesign.

File-storage tests assert one of two things about a blob flow:

- **Upload-assert** — the SUT, when exercised, **uploaded** blob X (it now exists in the container at the
  expected name, with the expected content, content-type, and metadata).
- **Process-assert** — the SUT **consumed/processed** a blob and produced an observable **side-effect Y**
  (a row written, a *derived* blob — a thumbnail, a transcoded file — or a notification sent).

> **The boundary that shapes this skill — eventual consistency.** Azure Blob is strongly read-after-write
> consistent for a single upload/download, but the things tests usually assert are *not* synchronous: a worker
> that processes an uploaded blob runs on its own schedule, a **Blob → Event Grid → Storage Queue** notification
> lands "soon", a derived blob appears after the worker finishes. So the core discipline matches `db-testing/connection` / `s3`:
> **wait on a condition** for the effect to appear, with a bounded timeout — **never `setTimeout` /
> `waitForTimeout`**. Use Vitest's `expect.poll`. (Listing is the one place to stay alert to lag —
> `listBlobsFlat` can momentarily lag a just-written blob; assert the blob via `exists`/`getProperties` rather
> than scanning a list when you can.)

## Stack

- Node 24, TypeScript (`strict: true`), Vitest — async all the way (`await` every blob call)
- `@azure/storage-blob` — `BlobServiceClient` (account-level), `ContainerClient` (container-level), `BlobClient`
  (per-blob download + properties + SAS + snapshots + tier), `BlockBlobClient` (uploads + block staging).
  `@azure/storage-queue` `QueueClient` only for the Event-Grid → Storage-Queue notification bridge (cross-link
  `service-bus`).
- `@testcontainers/azurite` (`AzuriteContainer`) — boots **Azurite** (the local Azure Storage emulator) and
  surfaces the **well-known `devstoreaccount1` connection string** the `BlobServiceClient` is built from
- Vitest's `expect.poll` — the bounded condition-wait for processing side-effects
- The SUT's storage gateway takes the `BlobServiceClient` / `ContainerClient` (or a typed wrapper) and the
  container name via its **constructor** — never a module-level client or a connection string read inside an
  `it()`

```
test/integration/
├── fixtures/
│   └── blob-fixture.ts          ← boots Azurite, creates the container(s), exposes the container client
└── invoice-upload.test.ts
```

## The Azure Blob model — containers/blobs, staging, SAS, tiers, snapshots, lifecycle, events

- **Container + blob** — blobs live in a flat keyspace inside a container; the `/`-delimited "folders" are a
  listing convention (a `prefix`), not real directories. `BlockBlobClient.uploadData` writes; `BlobClient.download`
  / `downloadToBuffer` reads the body; **`getProperties` is the HEAD analogue** (existence + metadata +
  content-type + size + content-MD5 + access-tier + ETag, no body — the cheap "does it exist with the right
  shape" probe); **`exists`** is the bare existence check; `ContainerClient.listBlobsFlat({ prefix })` lists by
  prefix; `BlobClient.delete` / `deleteIfExists` removes.
- **Content-type + metadata** — set `blobHTTPHeaders.blobContentType` on the upload (Azure does *not* infer it
  from the blob name extension — a common bug to assert against); user metadata goes in `metadata` (round-tripped
  verbatim, no prefix mangling). The **`contentMD5`** is the blob's **content-MD5** — Azure exposes it more
  directly than S3's opaque ETag. **It is auto-computed for a single-shot `uploadData`**, but **not** for a
  **block-staged** (large) blob unless you set it explicitly — so don't assert `contentMD5` on a staged blob
  (assert size instead), the Azure analogue of "multipart ETags ≠ MD5".
- **Large-blob upload (block staging)** — `BlockBlobClient.uploadData(buffer, { blockSize, concurrency })` chunks
  automatically for large buffers. The explicit **block-staging** API is the multipart analogue:
  `stageBlock(base64BlockId, data, length)` uploads each block, then `commitBlockList(blockIds)` assembles them
  server-side into one blob. The assertion is the same: the assembled blob exists with the expected size/content.
- **SAS tokens (the presigned-URL analogue)** — `BlobClient.generateSasUrl({ permissions, expiresOn })` mints a
  time-limited, signed URL that embeds the auth, so a client with **no Azure credentials** can `GET`/`PUT`
  directly. The test generates one and exercises it with `fetch` to prove it works — and asserts an *expired*
  one is rejected (403). `generateSasUrl` needs the client's shared key, which it has when built from the Azurite
  connection string.
- **Access tiers (the tiering control)** — `BlobClient.setAccessTier("Hot"/"Cool"/"Cold"/"Archive")` moves a
  blob between storage tiers; assert via `(await getProperties()).accessTier`. This is the **data-plane**,
  test-fast tier control (works in Azurite). Lifecycle-management *policies* are a separate **management-plane**
  config — see the lifecycle section.
- **Versioning / snapshots** — a **snapshot** (`createSnapshot`) captures a read-only point-in-time copy of a
  blob, addressed by its snapshot timestamp (`withSnapshot(snapshot)`); overwrite the base and the snapshot
  still serves the older content. (Account-level *blob versioning* is the management-plane analogue; snapshots
  are the data-plane, Azurite-supported one this skill uses.)
- **Lifecycle policies** — auto-tiering/expiration rules are a **management-plane** config
  (`@azure/arm-storage`), **not** a data-plane blob operation, and **Azurite does not implement them**. As with
  `s3`'s lifecycle: **execution runs on a ~daily cadence — far too slow to assert in a test** — so you assert the
  **policy config round-trips** (against a real account) and never wait for a blob to expire. The data-plane,
  test-fast equivalent is the **access tier** above.
- **Event Grid → Storage Queue notifications** — a blob write fires a `Microsoft.Storage.BlobCreated` Event Grid
  event; routed to a **Storage Queue**, an upload produces a downstream queue message the test asserts (the
  bridge — the Azure parallel to `s3`'s S3 → SQS, cross-link `qa-typescript:messaging-testing` `service-bus`).
  **The headline `azure-blob` divergence: Azurite does NOT emit Event Grid events** — so this test runs against a real
  Azure test account, or locally asserts the **subscription wiring config** only. Flagged honestly below.

## Local store for tests — Azurite (well-known connection string)

There is no in-memory Azure Blob. For deterministic local + CI tests, run **Azurite**
(`mcr.microsoft.com/azure-storage/azurite`) — the Azure Storage emulator (the **LocalStack analogue**) — which
serves Blob (and Queue/Table) storage. Build the `BlobServiceClient` from the **well-known Azurite
`devstoreaccount1` connection string** the Testcontainers module surfaces. Unlike S3 against LocalStack there is
**no force-path-style gotcha** — the connection string already carries the path-style emulator endpoint. The
`@testcontainers/azurite` module boots the container, owns the readiness wait, and surfaces the connection
string. Reuse the standard Testcontainers fixture discipline (boot once per suite; **never
`setTimeout` for readiness**). **Create the container in fixture setup** through the SDK.

```typescript
import { AzuriteContainer, StartedAzuriteContainer } from "@testcontainers/azurite";
import { BlobServiceClient, ContainerClient } from "@azure/storage-blob";
import { randomUUID } from "node:crypto";

export interface BlobFixture {
  service: BlobServiceClient;
  container: ContainerClient;
  containerName: string;
  emptyContainer: () => Promise<void>;
  stop: () => Promise<void>;
}

export async function startBlobFixture(): Promise<BlobFixture> {
  // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
  const started: StartedAzuriteContainer = await new AzuriteContainer(
    "mcr.microsoft.com/azure-storage/azurite:3.31.0",
  ).start();

  // The module surfaces the well-known devstoreaccount1 connection string (dev key included — never logged).
  const service = BlobServiceClient.fromConnectionString(started.getConnectionString());

  // Uniquely named container per suite → independent, parallel-safe.
  const containerName = `orders-${randomUUID().replace(/-/g, "")}`;
  const container = service.getContainerClient(containerName);
  await container.createIfNotExists();

  // Independent tests: empty the container (blobs + snapshots) so each starts clean.
  const emptyContainer = async (): Promise<void> => {
    for await (const blob of container.listBlobsFlat({ includeSnapshots: true })) {
      await container.getBlobClient(blob.name).deleteIfExists({ deleteSnapshots: "include" });
    }
  };

  return { service, container, containerName, emptyContainer, stop: async () => { await started.stop(); } };
}
```

> **Cloud test account alternative.** If your org runs against a real **test** Azure storage account instead of
> Azurite, drop the connection string and build the client from the account endpoint + **`DefaultAzureCredential`**
> (`new BlobServiceClient("https://<acct>.blob.core.windows.net", new DefaultAzureCredential())`); read the
> account name/endpoint from `process.env`, never hard-code a key, never log it (cross-link
> `qa-typescript:test-login-tokens`). Azurite is the default for CI determinism; a shared cloud account makes
> tests order-dependent unless each uses a **uniquely named container** or empties it in `beforeEach`. (Note:
> `generateSasUrl` with a shared key needs the connection-string client; with `DefaultAzureCredential` mint a
> **user-delegation SAS** via `getUserDelegationKey` instead.)

## Core pattern 1 — upload-assert (the SUT uploaded blob X)

The SUT uploads; the test asserts the blob **exists** at the expected name with the right content-type and
metadata (HEAD via `getProperties`), then reads the body to assert content. `getProperties` rejects with a
`RestError` whose `statusCode === 404` when the blob is absent — so a clean "does it exist" check is `exists()`
or a `getProperties` that doesn't reject.

```typescript
import { describe, it, expect, beforeAll, beforeEach, afterAll } from "vitest";

describe("invoice upload", () => {
  let fx: BlobFixture;
  let sut: InvoiceStore;

  beforeAll(async () => { fx = await startBlobFixture(); });
  afterAll(async () => { await fx.stop(); });
  beforeEach(async () => {
    await fx.emptyContainer();                     // independent tests — start from empty
    sut = new InvoiceStore(fx.container);          // constructor injection — no module-level client
  });

  it("should store the invoice pdf when an invoice is finalised", async () => {
    const invoice = invoices.finalised().withNumber("INV-1001").build(); // builder (qa/typescript/skills/test-data-builder)

    await sut.save(invoice);                                             // SUT uploads the blob

    // HEAD = the cheap existence + shape probe.
    const props = await fx.container.getBlobClient("invoices/INV-1001.pdf").getProperties();
    expect(props.contentType).toBe("application/pdf");                   // Azure does NOT infer this
    expect(props.metadata?.invoiceNumber).toBe("INV-1001");
  });

  it("should write the exact pdf bytes when storing", async () => {
    const invoice = invoices.finalised().withNumber("INV-1002").build();

    await sut.save(invoice);

    const buffer = await fx.container.getBlobClient("invoices/INV-1002.pdf").downloadToBuffer();
    expect(buffer).toEqual(invoice.renderedPdf);                        // one logical assertion: the stored bytes
  });
});
```

## Core pattern 2 — process-assert (the SUT processed a blob → side-effect Y)

Here the SUT is a **worker**: it watches a container (or is driven by a blob event), processes an uploaded blob,
and produces an observable side-effect — a DB row, a *derived* blob (a thumbnail), or a notification. The
side-effect is eventually consistent, so **seed the input blob, then wait on a condition with `expect.poll`**.
This reuses `qa-typescript:db-connection`'s discipline.

```typescript
import type { BlobGetPropertiesResponse } from "@azure/storage-blob";

it("should produce a thumbnail blob when an image is uploaded", async () => {
  // 1. Seed the input blob the worker watches.
  await fx.container.getBlockBlobClient("uploads/cat.png").uploadData(sampleImages.png1024, {
    blobHTTPHeaders: { blobContentType: "image/png" },
  });

  // 2. The SUT worker picks it up and writes a derived blob.

  // 3. Wait on the SIDE-EFFECT, not on a clock. expect.poll re-runs until the derived blob exists (or times out).
  await expect
    .poll(() => propertiesOrNull(fx, "thumbnails/cat.png").then((p) => p?.contentLength ?? 0), {
      timeout: 10_000,
      interval: 200,
    })
    .toBeGreaterThan(0);

  const thumb = await fx.container.getBlobClient("thumbnails/cat.png").getProperties();
  expect(thumb.contentType).toBe("image/png");   // one logical assertion: the derived blob
});

// HEAD-or-null probe: resolves to the properties if the blob exists, null otherwise (so expect.poll keeps waiting).
async function propertiesOrNull(fx: BlobFixture, name: string): Promise<BlobGetPropertiesResponse | null> {
  try {
    return await fx.container.getBlobClient(name).getProperties();
  } catch (e) {
    if (typeof e === "object" && e !== null && "statusCode" in e && e.statusCode === 404) return null;
    throw e;
  }
}
```

> `expect.poll` re-evaluates *until the matcher passes*, then returns; it **fails** if the matcher never passes
> inside the timeout. That is the difference from a bare `await new Promise((r) => setTimeout(r, 5000))`, which
> races the worker and is slow even when the work finished early. **No `setTimeout` / `waitForTimeout` as an
> assertion wait — ever.**

## Large-blob upload (block staging) — `BlockBlobClient`

For large blobs, `BlockBlobClient.uploadData(buffer, { blockSize, concurrency })` already chunks automatically.
The explicit **block-staging** API (the multipart analogue) stages numbered blocks then commits them into one
blob — useful when the SUT assembles a blob from parts. The assertion is unchanged: the assembled blob exists
with the expected size.

```typescript
it("should upload a large blob in blocks when staging and committing", async () => {
  const bytes = largePayloads.ofSize(12 * 1024 * 1024); // 12 MB → multiple blocks
  const blockBlob = fx.container.getBlockBlobClient("backups/db-2026-06.dump");

  const blockIds: string[] = [];
  const blockSize = 4 * 1024 * 1024; // 4 MB blocks
  for (let offset = 0; offset < bytes.length; offset += blockSize) {
    // Block IDs must be equal-length base64 strings.
    const id = Buffer.from(randomUUID()).toString("base64");
    const chunk = bytes.subarray(offset, Math.min(offset + blockSize, bytes.length));
    await blockBlob.stageBlock(id, chunk, chunk.length);
    blockIds.push(id);
  }
  await blockBlob.commitBlockList(blockIds, {
    blobHTTPHeaders: { blobContentType: "application/octet-stream" },
  });

  const props = await blockBlob.getProperties();
  expect(props.contentLength).toBe(bytes.length); // assembled blob is the full size
  // NB: don't assert contentMD5 === md5(bytes) on a staged blob — it isn't auto-computed for block commits.
});
```

> For the common "just upload a big buffer" case, `uploadData(buffer, { blockSize, concurrency })` stages +
> commits for you. Hand-drive `stageBlock`/`commitBlockList` only when the SUT itself does.

## SAS tokens — mint one, prove a credential-less client can use it

`generateSasUrl` builds a time-limited, signed URL. The test mints one and exercises it with `fetch` (no Azure
creds) to prove the round-trip — then asserts an **expired** one is rejected.

```typescript
import { BlobSASPermissions } from "@azure/storage-blob";

it("should let a client download via a sas url", async () => {
  const blob = fx.container.getBlockBlobClient("reports/q2.csv");
  await blob.uploadData(Buffer.from("id,total\n1,1999"), { blobHTTPHeaders: { blobContentType: "text/csv" } });

  const url = await blob.generateSasUrl({
    permissions: BlobSASPermissions.parse("r"),
    expiresOn: new Date(Date.now() + 5 * 60_000),
  });

  const res = await fetch(url);          // credential-less client uses the signed URL
  expect(await res.text()).toContain("1,1999");
});

it("should reject an expired sas url", async () => {
  const blob = fx.container.getBlockBlobClient("reports/q2.csv");
  await blob.uploadData(Buffer.from("x"));

  const url = await blob.generateSasUrl({
    permissions: BlobSASPermissions.parse("r"),
    expiresOn: new Date(Date.now() - 1000), // already expired
  });

  const res = await fetch(url);
  expect(res.status).toBe(403);          // signature expired
});
```

## Snapshots — assert the older content survives an overwrite

Snapshot a blob, overwrite the base, and assert the snapshot still serves the older content (the data-plane
analogue of S3 versioning that Azurite supports).

```typescript
it("should keep the older content when a snapshotted blob is overwritten", async () => {
  const blob = fx.container.getBlockBlobClient("config/app.json");
  await blob.uploadData(Buffer.from('{"v":1}'));

  const { snapshot } = await blob.createSnapshot(); // point-in-time copy of v1

  await blob.uploadData(Buffer.from('{"v":2}'));    // base now v2

  // The base serves the new content; the snapshot still serves the old.
  const current = (await fx.container.getBlobClient("config/app.json").downloadToBuffer()).toString();
  const oldCopy = (await fx.container.getBlobClient("config/app.json").withSnapshot(snapshot!).downloadToBuffer())
    .toString();
  expect(current).toBe('{"v":2}');
  expect(oldCopy).toBe('{"v":1}'); // snapshot retained the older version
});
```

## Access tiers — set and assert (the data-plane tier control)

`setAccessTier` moves a blob between Hot/Cool/Cold/Archive; assert via `(await getProperties()).accessTier`. This
is the **test-fast** tier control. Lifecycle-management *policies* are a **management-plane** config Azurite
doesn't implement and whose execution runs ~daily — too slow to assert; if you need to test the policy, assert
its **config round-trips** against a real account (the `s3` lifecycle discipline), never wait for a blob to
transition.

```typescript
it("should move a blob to the cool tier", async () => {
  const blob = fx.container.getBlockBlobClient("archive/2025-report.csv");
  await blob.uploadData(Buffer.from("id,total\n1,1999"));

  await blob.setAccessTier("Cool");

  const props = await fx.container.getBlobClient("archive/2025-report.csv").getProperties();
  expect(props.accessTier).toBe("Cool"); // tier round-trips
  // Do NOT try to assert a lifecycle policy actually tiered/expired a blob — that runs daily; out of a test's reach.
});
```

## Event Grid → Storage Queue notifications (the bridge to `service-bus`) — and the Azurite limitation

A blob write fires a `Microsoft.Storage.BlobCreated` Event Grid event; routed to a **Storage Queue**, the test
asserts the downstream queue message — the Azure parallel to `s3`'s S3 → SQS bridge.

> **⚠️ The headline `azure-blob` divergence — Azurite does NOT emit Event Grid events.** There is no local Event Grid in
> the emulator, so this end-to-end test **cannot run against Azurite**. Two honest options:
> 1. **Run it against a real Azure test account** with a blob event subscription routing to a Storage Queue
>    (the code below) — receive the queue message and assert it names the blob.
> 2. **Locally, assert the wiring config only** (the event-subscription / queue binding exists and points at the
>    right queue) and assert the SUT's downstream effect directly via the process-assert pattern above.
>
> Cross-link the s3 sibling's S3 → SQS section as the conceptual parallel, and
> `qa-typescript:messaging-testing` for the Azure-native messaging downstream.

```typescript
import { QueueClient } from "@azure/storage-queue";

// Against a REAL Azure test account (NOT Azurite): a BlobCreated event is routed to a Storage Queue.
it.runIf(process.env.REAL_AZURE_ACCOUNT)("should fire a storage queue message when a blob is created", async () => {
  // The blob event subscription → Storage Queue is provisioned out-of-band (IaC). Here we just receive.
  const queue = new QueueClient(process.env.REAL_AZURE_ACCOUNT!, "blob-events");

  await fx.container.getBlockBlobClient("incoming/order.json").uploadData(Buffer.from("{}"));

  // Poll the queue on a CONDITION (the message arriving), not a sleep — Event Grid delivery is eventual.
  const message = await vi.waitFor(
    async () => {
      const { receivedMessageItems } = await queue.receiveMessages({ numberOfMessages: 1 });
      if (receivedMessageItems.length === 0) throw new Error("no message yet");
      return receivedMessageItems[0];
    },
    { timeout: 30_000, interval: 1000 },
  );

  expect(Buffer.from(message.messageText, "base64").toString()).toContain("incoming/order.json");
  await queue.deleteMessage(message.messageId, message.popReceipt);
});
```

## Anti-patterns

- **`await new Promise((r) => setTimeout(r, 5000))` (or `page.waitForTimeout`) before asserting a
  processed/derived blob or a blob event.** Races the worker and the event delivery; slow and flaky. *Fix:*
  `expect.poll` on the HEAD/probe for the side-effect; poll the queue for the blob event. Never a bare sleep.
- **Asserting content-type without setting it.** Azure stores whatever `blobHTTPHeaders.blobContentType` you sent
  and does **not** infer it from the `.pdf`/`.png` blob name; a missing one defaults to
  `application/octet-stream`. *Fix:* set the content-type on the upload, assert it on `getProperties`.
- **Asserting `contentMD5 === md5(bytes)` on a block-staged blob.** Like S3 multipart ETags, a committed
  block-blob's content-MD5 is **not** auto-computed. *Fix:* assert `contentLength` and/or download-and-compare
  bytes; only a single-shot `uploadData` auto-sets `contentMD5`.
- **Expecting Azurite to fire Event Grid events.** Azurite has **no Event Grid** — the blob-event → queue test
  won't trigger locally. *Fix:* run that test against a real test account (`it.runIf(process.env.REAL_AZURE_ACCOUNT)`,
  excluded from the Azurite CI run), or assert the wiring config + the SUT effect directly.
- **Trying to assert lifecycle-policy *execution*.** Auto-tier/expire runs on a ~daily management-plane cadence;
  a test can't wait for it (and Azurite doesn't implement it). *Fix:* assert the **access tier** directly
  (`setAccessTier` → `getProperties`) for the data-plane control; round-trip the **policy config** against a
  real account if you must test it.
- **Sharing one container across parallel test files.** Cross-talk: one file's blobs/deletes leak into another's
  listings and asserts. *Fix:* a **uniquely named container per fixture** (as in `startBlobFixture`) or
  `emptyContainer()` in `beforeEach`.
- **Deleting a blob without including snapshots.** `delete` on a blob that has snapshots fails unless you pass
  `{ deleteSnapshots: "include" }`. *Fix:* `emptyContainer()` deletes with `deleteSnapshots: "include"`.
- **Scanning `listBlobsFlat` to check a single blob exists.** A list can momentarily lag a just-written blob and
  it's O(container). *Fix:* `exists()` / `getProperties()` — strongly consistent for the blob, cheap, rejects
  with a 404 `RestError` cleanly when absent.
- **Hard-coding the connection string / an account key in an `it()`.** *Fix:* surface the Azurite connection
  string from the fixture; for a cloud test account use `DefaultAzureCredential` + endpoint from env; never log
  secrets.
- **Reaching for Azure Blob when the store is AWS S3.** *Fix:* `references/s3.md`.

## Examples

**End-to-end: an upload → process → derived-blob flow.**

```typescript
describe("image processing worker", () => {
  let fx: BlobFixture;

  beforeAll(async () => { fx = await startBlobFixture(); });
  afterAll(async () => { await fx.stop(); });
  beforeEach(async () => { await fx.emptyContainer(); }); // independent tests — start from empty

  it("should write a thumbnail when an image is uploaded", async () => {
    // The SUT worker is wired: BlobCreated → worker → writes thumbnails/<name>.
    await fx.container.getBlockBlobClient("uploads/photo.png").uploadData(sampleImages.png1024, {
      blobHTTPHeaders: { blobContentType: "image/png" },
    });

    // Wait on the derived blob (the condition-wait) — the worker runs async.
    await expect
      .poll(() => propertiesOrNull(fx, "thumbnails/photo.png").then((p) => p?.contentLength ?? 0), {
        timeout: 15_000,
        interval: 250,
      })
      .toBeGreaterThan(0);

    const thumb = await fx.container.getBlobClient("thumbnails/photo.png").getProperties();
    expect(thumb.contentType).toBe("image/png"); // derived blob produced
  });
});
```

Lifecycle for this test:
1. `beforeAll` (`startBlobFixture`) boots Azurite once and creates a **uniquely named container**; the container
   client is surfaced.
2. `beforeEach` empties the container so the test starts clean — tests stay independent and order-free.
3. The test seeds an input blob; the running SUT worker produces a derived blob; the test **polls the HEAD of
   the derived blob with `expect.poll`** and asserts it exists with the right content-type.
4. `afterAll` stops the container.

**Test-data builder for blob payloads (4+ fields → builder, per the global rules).**

```typescript
export const invoices = {
  finalised: () => new InvoiceBuilder().withStatus("Finalised"),
};
// InvoiceBuilder.withNumber(...).withTotal(...).withCustomer(...).withRenderedPdf(...).build()
// — see qa/typescript/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `expect.poll` on a HEAD/DB probe for
  processed/derived blobs; poll the queue for blob events. **No `setTimeout` / `waitForTimeout`** as an assertion
  wait.
- The SUT's storage gateway takes the `BlobServiceClient` / `ContainerClient` + container name via its
  **constructor** — never a module-level client or a connection string read inside an `it()`.
- **Azurite is built from the well-known connection string** the module surfaces (no force-path-style gotcha —
  unlike S3). A cloud test account uses **`DefaultAzureCredential` + endpoint from env**, read lazily, never
  logged; mint a **user-delegation SAS** there (shared-key `generateSasUrl` needs the connection-string client).
- **Set `blobContentType` explicitly** on uploads (Azure doesn't infer it); assert it on `getProperties`. Don't
  assert `contentMD5 === md5` on block-staged blobs.
- **Independent tests:** a **uniquely named container per fixture** (or `emptyContainer()` in `beforeEach`);
  delete blobs **with `{ deleteSnapshots: "include" }`**.
- **Assert the access tier directly; assert lifecycle-policy *config* (not execution)** and only against a real
  account — Azurite doesn't implement lifecycle policies.
- **Azurite emits no Event Grid events** — run the blob-event → queue test against a real account
  (`it.runIf(process.env.REAL_AZURE_ACCOUNT)`), or assert wiring + SUT effect locally.
- Prefer `exists()` / `getProperties()` over scanning `listBlobsFlat` for single-blob existence.
- **Async all the way** — `await` every blob/queue call; consume download buffers.
- Test names describe behavior (`should …`); one logical assertion per test; builders for 4+-field payloads;
  structured logging; no secrets in code; `strict: true`.

## Cross-references

- `qa-dotnet:file-storage-testing` — the **canonical** stack this is ported from (.NET 8 / NUnit,
  `Azure.Storage.Blobs` `BlobServiceClient`/`BlobClient`/`BlockBlobClient`, `BlobSasBuilder` + `GenerateSasUri`,
  `Testcontainers.Azurite` `AzuriteBuilder`, `WaitFor.Async`). Structure ported, not code.
- `qa-java:file-storage-testing` — same skill, Java 21 / TestNG (`com.azure:azure-storage-blob`
  `BlobServiceClient`/`BlobClient`/`BlockBlobClient`, `BlobServiceSasSignatureValues` + `generateSas`,
  Awaitility, `org.testcontainers:azure` `AzuriteContainer`).
- `references/s3.md` — **the node whose structure this is ported from** AND the
  **`s3`-vs-`azure-blob` boundary**: buckets/keys + presigned URLs + multipart (`@aws-sdk/lib-storage` `Upload`) +
  LocalStack + `forcePathStyle` vs containers/blobs + SAS tokens + block-staging + Azurite + Event Grid→Storage
  Queue.
- `qa-typescript:db-connection` — the `expect.poll` wait and the seeder/probe split reused for the
  processed-blob side-effect assertions; the **eventual-consistency lineage** this skill leans on.
- `qa-typescript:messaging-testing` — Azure-native messaging, the natural downstream for the
  Event Grid → Storage Queue bridge (the Azure parallel to `s3`'s S3 → SQS).
- `qa-typescript:test-login-tokens` — when running against a cloud test account; the
  `DefaultAzureCredential` / secrets-from-env discipline.
- `qa-typescript:test-reports` — attach the uploaded/derived blob's name + metadata (or the queue-message
  body) to the Allure result.
- `qa-typescript:test-data-builder` — builders/ObjectMother for blob payloads with 4+ fields.
