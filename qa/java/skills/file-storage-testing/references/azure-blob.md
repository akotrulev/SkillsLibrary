# File-Storage Testing — Azure Blob Storage (Java 21 / TestNG)

This is the **Java sibling** of the `qa/java/skills/file-storage-testing/` node, **ported** from the canonical
.NET stack (`qa-file-storage-testing-dotnet`, **.NET-led by the user's choice** — Azure Blob is
Azure-native, the most authentic lead). It **closes the `qa/java/skills/file-storage-testing/` family** (s3 → `azure-blob`
azure-blob) in this stack. It is the sibling **ported from the `s3` node's structure** onto Azure Blob —
**same two assertion shapes, same eventual-consistency condition-wait discipline**; only the store SDK and its
primitives change. Where S3 has buckets/keys, presigned URLs, multipart upload, and LocalStack, Azure Blob has
containers/blobs, SAS tokens, block-blob staging, and Azurite. It reuses the same verification-inside-tests
lineage: the standard Testcontainers fixture discipline and the
**eventual-consistency condition-wait** (Awaitility) from `qa-db-testing-client-java`. All three Azure SDKs
mirror the same upload / download / exists / get-properties / list / delete + SAS + block-staging model, so this
is a true translate-the-concepts port, not a redesign.

File-storage tests assert one of two things about a blob flow:

- **Upload-assert** — the SUT, when exercised, **uploaded** blob X (it now exists in the container at the
  expected name, with the expected content, content-type, and metadata).
- **Process-assert** — the SUT **consumed/processed** a blob and produced an observable **side-effect Y**
  (a row written, a *derived* blob — a thumbnail, a transcoded file — or a notification sent).

> **The boundary that shapes this skill — eventual consistency.** Azure Blob is strongly read-after-write
> consistent for a single upload/download, but the things tests usually assert are *not* synchronous: a worker
> that processes an uploaded blob runs on its own schedule, a **Blob → Event Grid → Storage Queue** notification
> lands "soon", a derived blob appears after the worker finishes. So the core discipline matches `db-testing/client` / `s3`:
> **wait on a condition** for the effect to appear, with a bounded timeout — **never `Thread.sleep`**. Use
> **Awaitility**. (Listing is the one place to stay alert to lag — `listBlobs` can momentarily lag a
> just-written blob; assert the blob via `exists`/`getProperties` rather than scanning a list when you can.)

## Stack

- Java 21, TestNG — async work joined to a result; no busy-waiting beyond Awaitility
- `com.azure:azure-storage-blob` — `BlobServiceClient` (account-level), `BlobContainerClient` (container-level),
  `BlobClient` (per-blob CRUD + properties + SAS + snapshots + tier), `BlockBlobClient` (block staging for large
  blobs). `com.azure:azure-storage-queue` only for the Event-Grid → Storage-Queue notification bridge
  (cross-link `service-bus`).
- `org.testcontainers:azure` (`AzuriteContainer`) — boots **Azurite** (the local Azure Storage emulator) and
  surfaces the **well-known `devstoreaccount1` connection string** the `BlobServiceClient` is built from
- `org.awaitility:awaitility` — the bounded condition-wait for processing side-effects
- The SUT's storage gateway is **constructor-injected** with the `BlobServiceClient` (or a `BlobContainerClient`
  / typed wrapper) and the container name — never a static client or a connection string read inside a `@Test`

```
src/test/java/integration/
├── fixtures/
│   └── BlobFixture.java         ← boots Azurite, creates the container(s), exposes the container client
└── InvoiceUploadTest.java
```

## The Azure Blob model — containers/blobs, staging, SAS, tiers, snapshots, lifecycle, events

- **Container + blob** — blobs live in a flat keyspace inside a container; the `/`-delimited "folders" are a
  listing convention (a `prefix`), not real directories. `BlobClient.upload` writes; `downloadContent` reads the
  body; **`getProperties` is the HEAD analogue** (existence + metadata + content-type + size + content-MD5 +
  access-tier + ETag, no body — the cheap "does it exist with the right shape" probe); **`exists`** is the bare
  existence check; `BlobContainerClient.listBlobs(new ListBlobsOptions().setPrefix(...), null)` lists by prefix;
  `BlobClient.delete` / `deleteIfExists` removes.
- **Content-type + metadata** — set the content-type via `BlobHttpHeaders.setContentType(...)` on the upload
  (Azure does *not* infer it from the blob name extension — a common bug to assert against); user metadata goes
  in a `Map<String,String>` via `setMetadata(...)` (round-tripped verbatim, no prefix mangling). The
  **`getContentMd5()`** is the blob's **content-MD5** — Azure exposes it more directly than S3's opaque ETag.
  **It is auto-computed for a single-shot `upload`**, but **not** for a **block-staged** (large) blob unless you
  set it explicitly — so don't assert content-MD5 on a staged blob (assert size instead), the Azure analogue of
  "multipart ETags ≠ MD5".
- **Large-blob upload (block staging)** — `BlobClient.upload(...)` chunks automatically for large data via
  `ParallelTransferOptions`. The explicit **block-blob staging** API is the multipart analogue:
  `BlockBlobClient.stageBlock(base64BlockId, data, length)` uploads each block, then
  `commitBlockList(blockIds)` assembles them server-side into one blob. The assertion is the same: the assembled
  blob exists with the expected size/content.
- **SAS tokens (the presigned-URL analogue)** — `BlobServiceSasSignatureValues` + `BlobClient.generateSas(...)`
  produce a time-limited, signed query string; append it to `getBlobUrl()` for a URL a client with **no Azure
  credentials** can `GET`/`PUT` directly. The test generates one (permissions, `expiryTime`) and exercises it
  with the JDK `HttpClient` to prove it works — and asserts an *expired* one is rejected (403). `generateSas`
  needs the client's shared key, which it has when built from the Azurite connection string.
- **Access tiers (the tiering control)** — `BlobClient.setAccessTier(AccessTier.HOT/COOL/COLD/ARCHIVE)` moves a
  blob between storage tiers; assert via `getProperties().getAccessTier()`. This is the **data-plane**,
  test-fast tier control (works in Azurite). Lifecycle-management *policies* are a separate **management-plane**
  config — see the lifecycle section.
- **Versioning / snapshots** — a **snapshot** (`createSnapshot`) captures a read-only point-in-time copy of a
  blob, addressed by its snapshot timestamp (`getSnapshotClient(snapshot)`); overwrite the base and the snapshot
  still serves the older content. (Account-level *blob versioning* is the management-plane analogue; snapshots
  are the data-plane, Azurite-supported one this skill uses.)
- **Lifecycle policies** — auto-tiering/expiration rules are a **management-plane** config
  (`azure-resourcemanager-storage`), **not** a data-plane blob operation, and **Azurite does not implement
  them**. As with `s3`'s lifecycle: **execution runs on a ~daily cadence — far too slow to assert in a test** —
  so you assert the **policy config round-trips** (against a real account) and never wait for a blob to expire.
  The data-plane, test-fast equivalent is the **access tier** above.
- **Event Grid → Storage Queue notifications** — a blob write fires a `Microsoft.Storage.BlobCreated` Event
  Grid event; routed to a **Storage Queue**, an upload produces a downstream queue message the test asserts (the
  bridge — the Azure parallel to `s3`'s S3 → SQS, cross-link `qa-messaging-testing-java` `service-bus`).
  **The headline `azure-blob` divergence: Azurite does NOT emit Event Grid events** — so this test runs against a real
  Azure test account, or locally asserts the **subscription wiring config** only. Flagged honestly below.

## Local store for tests — Azurite (well-known connection string)

There is no in-memory Azure Blob. For deterministic local + CI tests, run **Azurite**
(`mcr.microsoft.com/azure-storage/azurite`) — the Azure Storage emulator (the **LocalStack analogue**) — which
serves Blob (and Queue/Table) storage. Build the `BlobServiceClient` from the **well-known Azurite
`devstoreaccount1` connection string** the Testcontainers module surfaces. Unlike S3 against LocalStack there is
**no force-path-style gotcha** — the connection string already carries the path-style emulator endpoint. The
`org.testcontainers:azure` module's `AzuriteContainer` boots the container, owns the readiness wait, and
surfaces the connection string. Reuse the standard Testcontainers fixture discipline (boot once per
fixture; **never `Thread.sleep` for readiness**). **Create the container in fixture setup** through the SDK.

```java
package integration.fixtures;

import com.azure.storage.blob.BlobContainerClient;
import com.azure.storage.blob.BlobServiceClient;
import com.azure.storage.blob.BlobServiceClientBuilder;
import com.azure.storage.blob.models.BlobItem;
import com.azure.storage.blob.models.DeleteSnapshotsOptionType;
import com.azure.storage.blob.models.ListBlobsOptions;
import org.testcontainers.azure.AzuriteContainer;
import org.testcontainers.utility.DockerImageName;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;

import java.util.UUID;

public abstract class BlobFixture {

    // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
    private final AzuriteContainer azurite = new AzuriteContainer(
            DockerImageName.parse("mcr.microsoft.com/azure-storage/azurite:3.31.0"));

    protected BlobServiceClient service;
    protected BlobContainerClient container;
    protected String containerName;

    @BeforeClass(alwaysRun = true)
    public void startStore() {
        azurite.start();

        // The module surfaces the well-known devstoreaccount1 connection string (dev key included — never logged).
        service = new BlobServiceClientBuilder()
                .connectionString(azurite.getConnectionString())
                .buildClient();

        // Uniquely named container per fixture → independent, parallel-safe.
        containerName = "orders-" + UUID.randomUUID().toString().replace("-", "");
        container = service.getBlobContainerClient(containerName);
        container.createIfNotExists();
    }

    @AfterClass(alwaysRun = true)
    public void stopStore() {
        azurite.stop();
    }

    // Independent tests: empty the container (blobs + snapshots) so each starts clean.
    protected void emptyContainer() {
        ListBlobsOptions opts = new ListBlobsOptions().setPrefix("");
        for (BlobItem item : container.listBlobs(opts, null)) {
            container.getBlobClient(item.getName())
                    .deleteIfExistsWithResponse(DeleteSnapshotsOptionType.INCLUDE, null, null, null);
        }
    }
}
```

> **Cloud test account alternative.** If your org runs against a real **test** Azure storage account instead of
> Azurite, drop the connection string and build the client from the account endpoint +
> **`DefaultAzureCredential`** (`new BlobServiceClientBuilder().endpoint("https://<acct>.blob.core.windows.net")
> .credential(new DefaultAzureCredentialBuilder().build()).buildClient()`); read the account name/endpoint from
> env, never hard-code a key, never log it (cross-link `qa-auth0-test-tokens-java`). Azurite is the default for
> CI determinism; a shared cloud account makes tests order-dependent unless each uses a **uniquely named
> container** or empties it in `@BeforeMethod`. (Note: `generateSas` with a shared key needs the
> connection-string client; with `DefaultAzureCredential` mint a **user-delegation SAS** via
> `getUserDelegationKey` instead.)

## Core pattern 1 — upload-assert (the SUT uploaded blob X)

The SUT uploads; the test asserts the blob **exists** at the expected name with the right content-type and
metadata (HEAD via `getProperties`), then reads the body to assert content. `getProperties` throws
`BlobStorageException` with `getStatusCode() == 404` when the blob is absent — so a clean "does it exist" check
is `exists()` or a `getProperties` that doesn't throw.

```java
public class InvoiceUploadTest extends BlobFixture {

    private InvoiceStore sut;   // production code, constructor-injected with the container client

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        emptyContainer();                       // independent tests — start from empty
        sut = new InvoiceStore(container);      // constructor injection — no static client
    }

    @Test
    public void Should_store_the_invoice_pdf_When_an_invoice_is_finalised() {
        Invoice invoice = Invoices.finalised().withNumber("INV-1001").build();   // builder (qa/java/skills/test-data-builder)

        sut.save(invoice);                                                       // SUT uploads the blob

        // HEAD = the cheap existence + shape probe.
        BlobProperties props = container.getBlobClient("invoices/INV-1001.pdf").getProperties();
        assertThat(props.getContentType()).isEqualTo("application/pdf");         // Azure does NOT infer this
        assertThat(props.getMetadata()).containsEntry("invoiceNumber", "INV-1001");
    }

    @Test
    public void Should_write_the_exact_pdf_bytes_When_storing() {
        Invoice invoice = Invoices.finalised().withNumber("INV-1002").build();

        sut.save(invoice);

        byte[] stored = container.getBlobClient("invoices/INV-1002.pdf").downloadContent().toBytes();
        assertThat(stored).isEqualTo(invoice.renderedPdf());   // one logical assertion: the stored bytes
    }
}
```

## Core pattern 2 — process-assert (the SUT processed a blob → side-effect Y)

Here the SUT is a **worker**: it watches a container (or is driven by a blob event), processes an uploaded blob,
and produces an observable side-effect — a DB row, a *derived* blob (a thumbnail), or a notification. The
side-effect is eventually consistent, so **seed the input blob, then wait on a condition with Awaitility**.
This reuses `qa-db-testing-client-java`'s discipline.

```java
@Test
public void Should_produce_a_thumbnail_blob_When_an_image_is_uploaded() {
    // 1. Seed the input blob the worker watches.
    container.getBlobClient("uploads/cat.png").uploadWithResponse(
            new BlobParallelUploadOptions(BinaryData.fromBytes(SampleImages.png1024()))
                    .setHeaders(new BlobHttpHeaders().setContentType("image/png")),
            null, null);

    // 2. The SUT worker picks it up and writes a derived blob.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Awaitility polls until the derived blob exists (or times out).
    await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
           .until(() -> propertiesOrNull("thumbnails/cat.png") != null);

    BlobProperties thumb = container.getBlobClient("thumbnails/cat.png").getProperties();
    assertThat(thumb.getContentType()).isEqualTo("image/png");   // one logical assertion: the derived blob
}

// HEAD-or-null probe: returns the properties if the blob exists, null otherwise (so Awaitility keeps waiting).
private BlobProperties propertiesOrNull(String name) {
    try { return container.getBlobClient(name).getProperties(); }
    catch (BlobStorageException e) { if (e.getStatusCode() == 404) return null; throw e; }
}
```

> `Awaitility` polls *until the condition holds*, then returns; it **fails** if the condition never holds inside
> the timeout. That is the difference from a bare `Thread.sleep(5000)`, which races the worker and is slow even
> when the work finished early. **No `Thread.sleep` as an assertion wait — ever.**

## Large-blob upload (block staging) — `BlockBlobClient`

For large blobs, `BlobClient.upload(...)` already chunks automatically via `ParallelTransferOptions`. The
explicit **block-staging** API (the multipart analogue) stages numbered blocks then commits them into one blob —
useful when the SUT assembles a blob from parts. The assertion is unchanged: the assembled blob exists with the
expected size.

```java
@Test
public void Should_upload_a_large_blob_in_blocks_When_staging_and_committing() {
    byte[] bytes = LargePayloads.ofSize(12 * 1024 * 1024);   // 12 MB → multiple blocks
    BlockBlobClient blockBlob = container.getBlobClient("backups/db-2026-06.dump").getBlockBlobClient();

    List<String> blockIds = new ArrayList<>();
    int blockSize = 4 * 1024 * 1024;                          // 4 MB blocks
    for (int offset = 0; offset < bytes.length; offset += blockSize) {
        // Block IDs must be equal-length base64 strings.
        String id = Base64.getEncoder().encodeToString(UUID.randomUUID().toString().getBytes());
        int len = Math.min(blockSize, bytes.length - offset);
        blockBlob.stageBlock(id, new ByteArrayInputStream(bytes, offset, len), len);
        blockIds.add(id);
    }
    blockBlob.commitBlockListWithResponse(new BlockBlobCommitBlockListOptions(blockIds)
            .setHeaders(new BlobHttpHeaders().setContentType("application/octet-stream")), null, null);

    BlobProperties props = blockBlob.getProperties();
    assertThat(props.getBlobSize()).isEqualTo((long) bytes.length);   // assembled blob is the full size
    // NB: don't assert getContentMd5() == MD5(bytes) on a staged blob — it isn't auto-computed for block commits.
}
```

> For the common "just upload a big stream" case, prefer `container.getBlobClient(name).upload(BinaryData, true)`
> with `ParallelTransferOptions` — the SDK stages + commits for you. Hand-drive `stageBlock`/`commitBlockList`
> only when the SUT itself does.

## SAS tokens — mint one, prove a credential-less client can use it

`BlobServiceSasSignatureValues` + `generateSas` build a time-limited, signed query string. The test mints one,
appends it to the blob URL, and exercises it with the JDK **`HttpClient`** (no Azure creds) to prove the
round-trip — then asserts an **expired** one is rejected.

```java
@Test
public void Should_let_a_client_download_via_a_sas_url() throws Exception {
    BlobClient blob = container.getBlobClient("reports/q2.csv");
    blob.uploadWithResponse(new BlobParallelUploadOptions(BinaryData.fromString("id,total\n1,1999"))
            .setHeaders(new BlobHttpHeaders().setContentType("text/csv")), null, null);

    String sas = blob.generateSas(new BlobServiceSasSignatureValues(
            OffsetDateTime.now().plusMinutes(5), new BlobSasPermission().setReadPermission(true)));

    HttpResponse<String> resp = HttpClient.newHttpClient().send(
            HttpRequest.newBuilder(URI.create(blob.getBlobUrl() + "?" + sas)).GET().build(),
            HttpResponse.BodyHandlers.ofString());
    assertThat(resp.body()).contains("1,1999");   // credential-less client used the signed URL
}

@Test
public void Should_reject_an_expired_sas_url() throws Exception {
    BlobClient blob = container.getBlobClient("reports/q2.csv");
    blob.upload(BinaryData.fromString("x"), true);

    String sas = blob.generateSas(new BlobServiceSasSignatureValues(
            OffsetDateTime.now().minusSeconds(1), new BlobSasPermission().setReadPermission(true)));   // expired

    // Awaitility waits past expiry on a CONDITION (a 403), not a fixed sleep.
    await().atMost(Duration.ofSeconds(5)).pollInterval(Duration.ofMillis(200)).until(() ->
            HttpClient.newHttpClient().send(
                    HttpRequest.newBuilder(URI.create(blob.getBlobUrl() + "?" + sas)).GET().build(),
                    HttpResponse.BodyHandlers.discarding()).statusCode() == 403);
}
```

## Snapshots — assert the older content survives an overwrite

Snapshot a blob, overwrite the base, and assert the snapshot still serves the older content (the data-plane
analogue of S3 versioning that Azurite supports).

```java
@Test
public void Should_keep_the_older_content_When_a_snapshotted_blob_is_overwritten() {
    BlobClient blob = container.getBlobClient("config/app.json");
    blob.upload(BinaryData.fromString("{\"v\":1}"), true);

    String snapshot = blob.createSnapshot().getSnapshotId();   // point-in-time copy of v1

    blob.upload(BinaryData.fromString("{\"v\":2}"), true);     // base now v2

    // The base serves the new content; the snapshot still serves the old.
    String current = blob.downloadContent().toString();
    String oldCopy = blob.getSnapshotClient(snapshot).downloadContent().toString();
    assertThat(current).isEqualTo("{\"v\":2}");
    assertThat(oldCopy).isEqualTo("{\"v\":1}");   // snapshot retained the older version
}
```

## Access tiers — set and assert (the data-plane tier control)

`setAccessTier` moves a blob between HOT/COOL/COLD/ARCHIVE; assert via `getProperties().getAccessTier()`. This
is the **test-fast** tier control. Lifecycle-management *policies* are a **management-plane** config Azurite
doesn't implement and whose execution runs ~daily — too slow to assert; if you need to test the policy, assert
its **config round-trips** against a real account (the `s3` lifecycle discipline), never wait for a blob to
transition.

```java
@Test
public void Should_move_a_blob_to_the_cool_tier() {
    BlobClient blob = container.getBlobClient("archive/2025-report.csv");
    blob.upload(BinaryData.fromString("id,total\n1,1999"), true);

    blob.setAccessTier(AccessTier.COOL);

    assertThat(container.getBlobClient("archive/2025-report.csv").getProperties().getAccessTier())
            .isEqualTo(AccessTier.COOL);   // tier round-trips
    // Do NOT try to assert a lifecycle policy actually tiered/expired a blob — that runs daily; out of a test's reach.
}
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
> Cross-link the s3 sibling's S3 → SQS section as the conceptual parallel, and `qa-messaging-testing-java`
> for the Azure-native messaging downstream.

```java
// Against a REAL Azure test account (NOT Azurite): a BlobCreated event is routed to a Storage Queue.
@Test(groups = "realAzureAccount")   // excluded from the Azurite-only CI run
public void Should_fire_a_storage_queue_message_When_a_blob_is_created() {
    // The blob event subscription → Storage Queue is provisioned out-of-band (IaC). Here we just receive.
    QueueClient queue = new QueueClientBuilder()
            .connectionString(realAccountConnectionString).queueName("blob-events").buildClient();

    container.getBlobClient("incoming/order.json").upload(BinaryData.fromString("{}"), true);

    // Poll the queue on a CONDITION (the message arriving), not a sleep — Event Grid delivery is eventual.
    await().atMost(Duration.ofSeconds(30)).pollInterval(Duration.ofSeconds(1)).untilAsserted(() -> {
        QueueMessageItem msg = queue.receiveMessage();
        assertThat(msg).isNotNull();
        assertThat(msg.getBody().toString()).contains("incoming/order.json");   // the event names the blob
        queue.deleteMessage(msg.getMessageId(), msg.getPopReceipt());
    });
}
```

## Anti-patterns

- **`Thread.sleep(5000)` before asserting a processed/derived blob or a blob event.** Races the worker and the
  event delivery; slow and flaky. *Fix:* Awaitility polling the HEAD/probe for the side-effect; poll the queue
  for the blob event. Never a bare sleep.
- **Asserting content-type without setting it.** Azure stores whatever `BlobHttpHeaders` content-type you sent
  and does **not** infer it from the `.pdf`/`.png` blob name; a missing one defaults to
  `application/octet-stream`. *Fix:* set the content-type on the upload, assert it on `getProperties`.
- **Asserting `getContentMd5() == MD5(bytes)` on a block-staged blob.** Like S3 multipart ETags, a committed
  block-blob's content-MD5 is **not** auto-computed. *Fix:* assert `getBlobSize()` and/or download-and-compare
  bytes; only a single-shot `upload` auto-sets content-MD5.
- **Expecting Azurite to fire Event Grid events.** Azurite has **no Event Grid** — the blob-event → queue test
  won't trigger locally. *Fix:* run that test against a real test account (`groups = "realAzureAccount"`,
  excluded from the Azurite CI run), or assert the wiring config + the SUT effect directly.
- **Trying to assert lifecycle-policy *execution*.** Auto-tier/expire runs on a ~daily management-plane cadence;
  a test can't wait for it (and Azurite doesn't implement it). *Fix:* assert the **access tier** directly
  (`setAccessTier` → `getProperties`) for the data-plane control; round-trip the **policy config** against a
  real account if you must test it.
- **Sharing one container across parallel test classes.** Cross-talk: one suite's blobs/deletes leak into
  another's listings and asserts. *Fix:* a **uniquely named container per fixture** (as in `BlobFixture`) or
  `emptyContainer()` in `@BeforeMethod`; keep the storage fixtures single-threaded unless verified isolated.
- **Deleting a blob without including snapshots.** `delete` on a blob that has snapshots fails unless you pass
  `DeleteSnapshotsOptionType.INCLUDE`. *Fix:* `emptyContainer()` deletes with `INCLUDE`.
- **Scanning `listBlobs` to check a single blob exists.** A list can momentarily lag a just-written blob and
  it's O(container). *Fix:* `exists()` / `getProperties()` — strongly consistent for the blob, cheap, throws
  `BlobStorageException` (404) cleanly when absent.
- **Hard-coding the connection string / an account key in a `@Test`.** *Fix:* surface the Azurite connection
  string from the fixture; for a cloud test account use `DefaultAzureCredential` + endpoint from env; never log
  secrets.
- **Reaching for Azure Blob when the store is AWS S3.** *Fix:* `references/s3.md` — LocalStack,
  buckets/keys, presigned URLs, multipart, force-path-style; not Azurite/containers/SAS.

## Examples

**End-to-end: an upload → process → derived-blob flow.**

```java
public class ImageProcessingTest extends BlobFixture {

    @BeforeMethod(alwaysRun = true)
    public void setUp() { emptyContainer(); }   // independent tests — start from empty

    @Test
    public void Should_write_a_thumbnail_When_an_image_is_uploaded() {
        // The SUT worker is wired: BlobCreated → worker → writes thumbnails/<name>.
        container.getBlobClient("uploads/photo.png").uploadWithResponse(
                new BlobParallelUploadOptions(BinaryData.fromBytes(SampleImages.png1024()))
                        .setHeaders(new BlobHttpHeaders().setContentType("image/png")),
                null, null);

        // Wait on the derived blob (the condition-wait) — the worker runs async.
        await().atMost(Duration.ofSeconds(15)).pollInterval(Duration.ofMillis(250))
               .until(() -> propertiesOrNull("thumbnails/photo.png") != null);

        BlobProperties thumb = container.getBlobClient("thumbnails/photo.png").getProperties();
        assertThat(thumb.getContentType()).isEqualTo("image/png");   // derived blob produced
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` (in `BlobFixture`) boots Azurite once and creates a **uniquely named container**; the
   container client is surfaced.
2. `@BeforeMethod` empties the container so the test starts clean — tests stay independent and order-free.
3. The test seeds an input blob; the running SUT worker produces a derived blob; the test **polls the HEAD of
   the derived blob with Awaitility** and asserts it exists with the right content-type.
4. `@AfterClass` stops the container.

**Test-data builder for blob payloads (4+ fields → builder, per the global rules).**

```java
public final class Invoices {
    public static InvoiceBuilder finalised() { return new InvoiceBuilder().withStatus("Finalised"); }
}
// InvoiceBuilder.withNumber(...).withTotal(...).withCustomer(...).withRenderedPdf(...).build()
// — see qa/java/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** Awaitility polling a HEAD/DB probe for
  processed/derived blobs; poll the queue for blob events. **No `Thread.sleep`** as an assertion wait.
- The SUT's storage gateway is **constructor-injected** with the `BlobServiceClient` / `BlobContainerClient` +
  container name — never a static client or a connection string read inside a `@Test`.
- **Azurite is built from the well-known connection string** the module surfaces (no force-path-style gotcha —
  unlike S3). A cloud test account uses **`DefaultAzureCredential` + endpoint from env**, read lazily, never
  logged; mint a **user-delegation SAS** there (shared-key `generateSas` needs the connection-string client).
- **Set the content-type explicitly** on uploads (Azure doesn't infer it); assert it on `getProperties`. Don't
  assert `getContentMd5() == MD5` on block-staged blobs.
- **Independent tests:** a **uniquely named container per fixture** (or `emptyContainer()` in `@BeforeMethod`);
  delete blobs **with `DeleteSnapshotsOptionType.INCLUDE`**; keep storage fixtures single-threaded unless
  verified isolated.
- **Assert the access tier directly; assert lifecycle-policy *config* (not execution)** and only against a real
  account — Azurite doesn't implement lifecycle policies.
- **Azurite emits no Event Grid events** — run the blob-event → queue test against a real account
  (`groups = "realAzureAccount"`), or assert wiring + SUT effect locally.
- Prefer `exists()` / `getProperties()` over scanning `listBlobs` for single-blob existence.
- Join async work to a result; `close()` what needs closing; no busy-waiting.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `qa-file-storage-testing-dotnet` — the **canonical** stack this is ported from (.NET 8 / NUnit,
  `Azure.Storage.Blobs` `BlobServiceClient`/`BlobClient`/`BlockBlobClient`, `BlobSasBuilder` + `GenerateSasUri`,
  `Testcontainers.Azurite` `AzuriteBuilder`, `WaitFor.Async`). Structure ported, not code.
- `qa-file-storage-testing-typescript` — same skill, Node 20 + TS (`@azure/storage-blob`:
  `BlobServiceClient.fromConnectionString`, `BlockBlobClient.uploadData`/`download`/`exists`/`getProperties`,
  `stageBlock`/`commitBlockList`, `generateSasUrl`, `expect.poll`, `@testcontainers/azurite`).
- `references/s3.md` — **the node whose structure this is ported from** AND the
  **`s3`-vs-`azure-blob` boundary**: buckets/keys + presigned URLs + multipart (`S3TransferManager`) + LocalStack +
  `forcePathStyle` vs containers/blobs + SAS tokens + block-staging + Azurite + Event Grid→Storage Queue.
- `qa-db-testing-client-java` — the Awaitility wait and the seeder/probe split reused for the
  processed-blob side-effect assertions; the **eventual-consistency lineage** this skill leans on.
- `qa-messaging-testing-java` — Azure-native messaging, the natural downstream for the Event
  Grid → Storage Queue bridge (the Azure parallel to `s3`'s S3 → SQS).
- `qa-auth0-test-tokens-java` — when running against a cloud test account; the `DefaultAzureCredential` /
  secrets-from-env discipline.
- `qa-allure-reporting-java` — attach the uploaded/derived blob's name + metadata (or the queue-message body) to
  the Allure result.
- `qa-test-data-builder-java` — builders/ObjectMother for blob payloads with 4+ fields.
