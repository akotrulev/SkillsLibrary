# File-Storage Testing — Azure Blob Storage (.NET 8 / NUnit)

This **closes the `qa/dotnet/skills/file-storage-testing/` family** (s3 → azure-blob). It is the **sibling ported
from the canonical `s3` stack** (`references/s3.md`, `s3`) — **same two assertion shapes, same
eventual-consistency condition-wait discipline**; only the store SDK and its primitives change. Where S3 has
buckets/keys, presigned URLs, multipart upload, and LocalStack, Azure Blob has containers/blobs, SAS tokens,
block-blob staging, and Azurite. It reuses the same verification-inside-tests lineage: the
standard Testcontainers fixture discipline and the **eventual-consistency
condition-wait** (`WaitFor.Async`) from `qa-db-connection-dotnet`.

**.NET leads this node by the user's choice.** The Azure SDK is first-class across all three stacks (no single
"native" runtime), so the house default would have been TypeScript; .NET was picked — and it is an especially
natural canonical for an **Azure-native** store (the "lead where the tool is most authentic" reasoning `service-bus`
service-bus used), keeping the recent Step-3 nodes .NET-led. This file is the **canonical** `azure-blob`
stack; the `java` (`com.azure:azure-storage-blob`) and `typescript` (`@azure/storage-blob`) siblings are
**ported** from it — all three SDKs mirror the same upload / download / exists / get-properties / list /
delete + SAS + block-staging model, so this is a true translate-the-concepts port, not a redesign.

File-storage tests assert one of two things about a blob flow:

- **Upload-assert** — the SUT, when exercised, **uploaded** blob X (it now exists in the container at the
  expected name, with the expected content, content-type, and metadata).
- **Process-assert** — the SUT **consumed/processed** a blob and produced an observable **side-effect Y**
  (a row written, a *derived* blob — a thumbnail, a transcoded file — or a notification sent).

> **The boundary that shapes this skill — eventual consistency.** Azure Blob is strongly read-after-write
> consistent for a single upload/download of a blob, but the things tests usually assert are *not* synchronous:
> a worker that processes an uploaded blob runs on its own schedule, a **Blob → Event Grid → Storage Queue**
> notification lands "soon", a derived blob appears after the worker finishes. So the core discipline matches
> `db-testing/client` / `s3`: **wait on a condition** for the effect to appear, with a bounded timeout — **never `Task.Delay` /
> `Thread.Sleep`**. Reuse `qa-db-connection-dotnet`'s `WaitFor.Async` poll. (Listing is the one place to
> stay alert to lag — `GetBlobs` can momentarily lag a just-written blob on some backends; assert the blob via
> `ExistsAsync`/`GetPropertiesAsync` rather than scanning a list when you can.)

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** (`UploadAsync`,
  `DownloadContentAsync`, `GetPropertiesAsync`, `ExistsAsync`, `DeleteAsync`; never `.Result` / `.Wait()`)
- `Azure.Storage.Blobs` — `BlobServiceClient` (account-level: list/create containers), `BlobContainerClient`
  (container-level: list/delete blobs), `BlobClient` (per-blob CRUD + properties + SAS + snapshots + tier),
  `BlockBlobClient` (block staging for large blobs). `Azure.Storage.Sas` `BlobSasBuilder` for SAS.
  `Azure.Storage.Queues` only for the Event-Grid → Storage-Queue notification bridge (cross-link `service-bus`).
- `Testcontainers.Azurite` (`AzuriteBuilder`) — boots **Azurite** (the local Azure Storage emulator) and
  surfaces the **well-known `devstoreaccount1` connection string** the `BlobServiceClient` is built from
- The SUT's storage gateway is **constructor-injected** with the `BlobServiceClient` (or a `BlobContainerClient`
  / typed wrapper) and the container name — never a static client or a connection string read inside a `[Test]`

```
IntegrationTests/
├── Fixtures/
│   └── BlobFixture.cs           ← boots Azurite, creates the container(s), exposes the container client
├── Storage/
│   └── WaitFor.cs               ← bounded condition-wait for processing side-effects (reused from qa-db-testing)
└── InvoiceUploadTests.cs
```

## The Azure Blob model — containers/blobs, staging, SAS, tiers, snapshots, lifecycle, events

- **Container + blob** — blobs live in a flat keyspace inside a container; the `/`-delimited "folders" are a
  listing convention (a `prefix`), not real directories. `BlobClient.UploadAsync` writes; `DownloadContentAsync`
  reads the body; **`GetPropertiesAsync` is the HEAD analogue** (existence + metadata + content-type + size +
  content-MD5 + access-tier + ETag, no body — the cheap "does it exist with the right shape" probe);
  **`ExistsAsync`** is the bare existence check; `BlobContainerClient.GetBlobsAsync(prefix:)` lists by prefix;
  `BlobClient.DeleteAsync` / `DeleteIfExistsAsync` removes.
- **Content-type + metadata** — set `ContentType` via `BlobHttpHeaders` on the upload (Azure does *not* infer it
  from the blob name extension — a common bug to assert against); user metadata goes in the `Metadata`
  dictionary (round-tripped verbatim, no prefix mangling). The **`ContentHash`** is the blob's **content-MD5** —
  Azure exposes it more directly than S3's opaque ETag. **It is auto-computed for a single-shot `UploadAsync`**,
  but **not** for a **block-staged** (large) blob unless you set it explicitly — so don't assert `ContentHash`
  on a staged blob (assert size instead), the Azure analogue of "multipart ETags ≠ MD5".
- **Large-blob upload (block staging)** — `BlobClient.UploadAsync(stream)` chunks automatically for large
  streams via `StorageTransferOptions`. The explicit **block-blob staging** API is the multipart analogue:
  `BlockBlobClient.StageBlockAsync(base64BlockId, stream)` uploads each block, then
  `CommitBlockListAsync(blockIds)` assembles them server-side into one blob. The assertion is the same: the
  assembled blob exists with the expected size/content.
- **SAS tokens (the presigned-URL analogue)** — `BlobSasBuilder` + `BlobClient.GenerateSasUri(...)` mints a
  time-limited, signed URL that embeds the auth, so a client with **no Azure credentials** can `GET`/`PUT`
  directly. The test generates one (permissions, `ExpiresOn`) and exercises it with a plain `HttpClient` to
  prove it works — and asserts an *expired* one is rejected (403). `GenerateSasUri` needs the client's shared
  key, which it has when built from the Azurite connection string.
- **Access tiers (the tiering control)** — `BlobClient.SetAccessTierAsync(AccessTier.Hot/Cool/Cold/Archive)`
  moves a blob between storage tiers; assert via `GetPropertiesAsync().Value.AccessTier`. This is the
  **data-plane**, test-fast tier control (works in Azurite). Lifecycle-management *policies* (auto-tier/expire
  after N days) are a separate **management-plane** config — see the lifecycle section.
- **Versioning / snapshots** — a **snapshot** (`CreateSnapshotAsync`) captures a read-only point-in-time copy of
  a blob, addressed by its snapshot timestamp (`BlobClient.WithSnapshot(snapshot)`); overwrite the base blob and
  the snapshot still serves the older content. (Account-level *blob versioning* — automatic versions on every
  write — is the management-plane analogue; snapshots are the data-plane, Azurite-supported one this skill uses.)
- **Lifecycle policies** — auto-tiering/expiration rules are a **management-plane** config
  (`Azure.ResourceManager.Storage`), **not** a data-plane blob operation, and **Azurite does not implement
  them**. As with `s3`'s lifecycle: **execution runs on a ~daily cadence — far too slow to assert in a test** —
  so you assert the **policy config round-trips** (against a real test account) and never wait for a blob to
  expire. The data-plane, test-fast equivalent is the **access tier** above.
- **Event Grid → Storage Queue notifications** — a blob write fires a `Microsoft.Storage.BlobCreated` Event
  Grid event; routed to a **Storage Queue**, an upload produces a downstream queue message the test asserts (the
  bridge — the Azure parallel to `s3`'s S3 → SQS, cross-link `qa-messaging-testing-dotnet` `service-bus`).
  **The headline `azure-blob` divergence: Azurite does NOT emit Event Grid events** — so this test runs against a real
  Azure test account, or locally asserts the **subscription wiring config** only. Flagged honestly below.

## Local store for tests — Azurite (well-known connection string)

There is no in-memory Azure Blob. For deterministic local + CI tests, run **Azurite**
(`mcr.microsoft.com/azure-storage/azurite`) — the Azure Storage emulator (the **LocalStack analogue**) — which
serves Blob (and Queue/Table) storage. Build the `BlobServiceClient` from the **well-known Azurite
`devstoreaccount1` connection string** the Testcontainers module surfaces (account name + dev key + the
container-mapped blob endpoint). Unlike S3 against LocalStack there is **no force-path-style gotcha** — the
emulator's endpoint is already path-style; the connection string carries it. The `Testcontainers.Azurite`
module boots the container, owns the readiness wait, and surfaces the connection string. Reuse the fixture
discipline (boot once per fixture; **never `Task.Delay` for readiness** — the
module owns the wait). **Create the container in fixture setup** through the SDK.

```csharp
using Azure.Storage.Blobs;
using NUnit.Framework;
using Testcontainers.Azurite;

namespace IntegrationTests.Fixtures;

public abstract class BlobFixture
{
    private AzuriteContainer _azurite = null!;

    protected BlobServiceClient Service { get; private set; } = null!;
    protected BlobContainerClient Container { get; private set; } = null!;
    protected string ContainerName { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartStoreAsync()
    {
        // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
        _azurite = new AzuriteBuilder()
            .WithImage("mcr.microsoft.com/azure-storage/azurite:3.31.0")
            .Build();
        await _azurite.StartAsync();

        // The module surfaces the well-known devstoreaccount1 connection string (dev key included — never logged).
        Service = new BlobServiceClient(_azurite.GetConnectionString());

        // Uniquely named container per fixture → independent, parallel-safe (no cross-talk between suites).
        ContainerName = $"orders-{Guid.NewGuid():N}";
        Container = Service.GetBlobContainerClient(ContainerName);
        await Container.CreateIfNotExistsAsync();
    }

    [OneTimeTearDown]
    public async Task StopStoreAsync() => await _azurite.DisposeAsync();

    // Independent tests: empty the container (blobs + snapshots) so each starts clean.
    protected async Task EmptyContainerAsync()
    {
        await foreach (var item in Container.GetBlobsAsync(states: BlobStates.Snapshots | BlobStates.Version))
        {
            await Container.GetBlobClient(item.Name)
                .DeleteIfExistsAsync(snapshotsOption: DeleteSnapshotsOption.IncludeSnapshots);
        }
    }
}
```

> **Cloud test account alternative.** If your org runs against a real **test** Azure storage account instead of
> Azurite, drop the connection string and build the client from the account endpoint + **`DefaultAzureCredential`**
> (`new BlobServiceClient(new Uri("https://<acct>.blob.core.windows.net"), new DefaultAzureCredential())`);
> read the account name/endpoint from env, never hard-code a key, never log it (cross-link
> `qa-test-login-tokens-dotnet` for the secrets-from-env discipline). Azurite is the default for CI determinism;
> a shared cloud account makes tests order-dependent unless each uses a **uniquely named container** (as above)
> or empties it in `[SetUp]`. (Note: `GenerateSasUri` with a shared key needs the connection-string client; with
> `DefaultAzureCredential` mint a **user-delegation SAS** via `GetUserDelegationKeyAsync` instead.)

## Core pattern 1 — upload-assert (the SUT uploaded blob X)

The SUT uploads; the test asserts the blob **exists** at the expected name with the right content-type and
metadata (HEAD via `GetPropertiesAsync`), then reads the body to assert content. `GetPropertiesAsync` throws
`RequestFailedException` with `Status == 404` when the blob is absent — so a clean "does it exist" check is
either `ExistsAsync` or a `GetPropertiesAsync` that doesn't throw.

```csharp
public class InvoiceUploadTests : BlobFixture
{
    private InvoiceStore _sut = null!;   // production code, constructor-injected with the container client

    [SetUp]
    public async Task SetUp()
    {
        await EmptyContainerAsync();             // independent tests — start from empty
        _sut = new InvoiceStore(Container);      // constructor injection — no static client
    }

    [Test]
    public async Task Should_store_the_invoice_pdf_When_an_invoice_is_finalised()
    {
        var invoice = Invoices.Finalised().WithNumber("INV-1001").Build();   // builder (qa/dotnet/skills/test-data-builder)

        await _sut.SaveAsync(invoice);                                       // SUT uploads the blob

        // HEAD = the cheap existence + shape probe. Asserts name, content-type, and user metadata in one behaviour.
        var props = (await Container.GetBlobClient("invoices/INV-1001.pdf").GetPropertiesAsync()).Value;
        Assert.Multiple(() =>
        {
            Assert.That(props.ContentType, Is.EqualTo("application/pdf"));    // Azure does NOT infer this
            Assert.That(props.Metadata["invoiceNumber"], Is.EqualTo("INV-1001"));
        });
    }

    [Test]
    public async Task Should_write_the_exact_pdf_bytes_When_storing()
    {
        var invoice = Invoices.Finalised().WithNumber("INV-1002").Build();

        await _sut.SaveAsync(invoice);

        var download = await Container.GetBlobClient("invoices/INV-1002.pdf").DownloadContentAsync();
        Assert.That(download.Value.Content.ToArray(), Is.EqualTo(invoice.RenderedPdf));   // the stored bytes
    }
}
```

## Core pattern 2 — process-assert (the SUT processed a blob → side-effect Y)

Here the SUT is a **worker**: it watches a container (or is driven by a blob event), processes an uploaded blob,
and produces an observable side-effect — a DB row, a *derived* blob (a thumbnail), or a notification. The
side-effect is eventually consistent, so **seed the input blob, then poll a probe on a condition**. This reuses
`qa-db-connection-dotnet`'s `WaitFor.Async` verbatim.

```csharp
[Test]
public async Task Should_produce_a_thumbnail_blob_When_an_image_is_uploaded()
{
    // 1. Seed the input blob the worker watches.
    await Container.GetBlobClient("uploads/cat.png").UploadAsync(
        BinaryData.FromBytes(SampleImages.Png1024),
        new BlobUploadOptions { HttpHeaders = new BlobHttpHeaders { ContentType = "image/png" } });

    // 2. The SUT worker picks it up and writes a derived blob.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the HEAD of the derived blob until it exists (or time out).
    var thumb = await WaitFor.Async(
        probe:     async ct => await TryGetPropertiesAsync("thumbnails/cat.png", ct),
        predicate: p  => p.ContentLength > 0,
        timeout:   TimeSpan.FromSeconds(10),
        interval:  TimeSpan.FromMilliseconds(200));

    Assert.That(thumb.ContentType, Is.EqualTo("image/png"));   // one logical assertion: the derived blob
}

// HEAD-or-null probe: returns the properties if the blob exists, null otherwise (so the poll keeps waiting).
private async Task<BlobProperties?> TryGetPropertiesAsync(string name, CancellationToken ct)
{
    try { return (await Container.GetBlobClient(name).GetPropertiesAsync(cancellationToken: ct)).Value; }
    catch (RequestFailedException e) when (e.Status == 404) { return null; }
}
```

The `WaitFor.Async` helper is the same bounded poll as `qa-db-connection-dotnet`, ``service-bus`` Service Bus, and
``s3`` S3 — included so the node is self-contained:

```csharp
public static class WaitFor
{
    public static async Task<T> Async<T>(
        Func<CancellationToken, Task<T?>> probe,
        Func<T, bool>                     predicate,
        TimeSpan                          timeout,
        TimeSpan                          interval,
        CancellationToken                 ct = default) where T : class
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeout);
        while (!cts.IsCancellationRequested)
        {
            var value = await probe(cts.Token);
            if (value is not null && predicate(value)) return value;
            await Task.Delay(interval, cts.Token);   // poll cadence INSIDE the helper, not an assertion sleep
        }
        throw new TimeoutException($"Side-effect did not satisfy the predicate within {timeout}.");
    }
}
```

> `Task.Delay` appears **only** as the poll cadence *inside* the bounded helper — never as a bare
> `await Task.Delay(5000)` standing in for "the worker probably finished by now". The helper returns the
> instant the condition holds and *fails* if it never does; a bare sleep races the worker.

## Large-blob upload (block staging) — `BlockBlobClient`

For large blobs, `BlobClient.UploadAsync(stream, ...)` already chunks automatically via `StorageTransferOptions`.
The explicit **block-staging** API (the multipart analogue) stages numbered blocks then commits them into one
blob — useful when the SUT assembles a blob from parts. The assertion is unchanged: the assembled blob exists
with the expected size.

```csharp
[Test]
public async Task Should_upload_a_large_blob_in_blocks_When_staging_and_committing()
{
    var bytes = LargePayloads.OfSize(12 * 1024 * 1024);   // 12 MB → multiple blocks
    var blockBlob = Container.GetBlockBlobClient("backups/db-2026-06.dump");

    var blockIds = new List<string>();
    const int blockSize = 4 * 1024 * 1024;                // 4 MB blocks
    for (var offset = 0; offset < bytes.Length; offset += blockSize)
    {
        var id = Convert.ToBase64String(Guid.NewGuid().ToByteArray());   // block IDs must be equal-length base64
        var len = Math.Min(blockSize, bytes.Length - offset);
        using var chunk = new MemoryStream(bytes, offset, len);
        await blockBlob.StageBlockAsync(id, chunk);
        blockIds.Add(id);
    }
    await blockBlob.CommitBlockListAsync(blockIds,
        new CommitBlockListOptions { HttpHeaders = new BlobHttpHeaders { ContentType = "application/octet-stream" } });

    var props = (await blockBlob.GetPropertiesAsync()).Value;
    Assert.That(props.ContentLength, Is.EqualTo(bytes.Length));   // assembled blob is the full size
    // NB: don't assert ContentHash == MD5(bytes) on a staged blob — it isn't auto-computed for block commits.
}
```

> For the common "just upload a big stream" case, prefer `Container.GetBlobClient(name).UploadAsync(stream, new
> BlobUploadOptions { TransferOptions = new StorageTransferOptions { MaximumTransferSize = 4*1024*1024 } })` —
> the SDK stages + commits for you. Hand-drive `StageBlock`/`CommitBlockList` only when the SUT itself does.

## SAS tokens — mint one, prove a credential-less client can use it

`BlobSasBuilder` + `GenerateSasUri` build a time-limited, signed URL. The test mints one and exercises it with a
**plain `HttpClient`** (no Azure creds) to prove the round-trip — then asserts an **expired** one is rejected.

```csharp
using Azure.Storage.Sas;

[Test]
public async Task Should_let_a_client_download_via_a_sas_url()
{
    var blob = Container.GetBlobClient("reports/q2.csv");
    await blob.UploadAsync(BinaryData.FromString("id,total\n1,1999"),
        new BlobUploadOptions { HttpHeaders = new BlobHttpHeaders { ContentType = "text/csv" } });

    var sas = blob.GenerateSasUri(new BlobSasBuilder(BlobSasPermissions.Read, DateTimeOffset.UtcNow.AddMinutes(5))
    {
        BlobContainerName = ContainerName,
        BlobName          = blob.Name,
        Resource          = "b",
    });

    using var http = new HttpClient();
    var body = await http.GetStringAsync(sas);            // credential-less client uses the signed URL
    Assert.That(body, Does.Contain("1,1999"));
}

[Test]
public async Task Should_reject_an_expired_sas_url()
{
    var blob = Container.GetBlobClient("reports/q2.csv");
    await blob.UploadAsync(BinaryData.FromString("x"), overwrite: true);

    var sas = blob.GenerateSasUri(new BlobSasBuilder(BlobSasPermissions.Read, DateTimeOffset.UtcNow.AddSeconds(-1))
    {
        BlobContainerName = ContainerName, BlobName = blob.Name, Resource = "b",
    });

    using var http = new HttpClient();
    var response = await http.GetAsync(sas);
    Assert.That(response.StatusCode, Is.EqualTo(System.Net.HttpStatusCode.Forbidden));   // signature expired
}
```

## Snapshots — assert the older content survives an overwrite

Snapshot a blob, overwrite the base, and assert the snapshot still serves the older content (the data-plane
analogue of S3 versioning that Azurite supports).

```csharp
[Test]
public async Task Should_keep_the_older_content_When_a_snapshotted_blob_is_overwritten()
{
    var blob = Container.GetBlobClient("config/app.json");
    await blob.UploadAsync(BinaryData.FromString("""{"v":1}"""), overwrite: true);

    var snapshot = (await blob.CreateSnapshotAsync()).Value.Snapshot;   // point-in-time copy of v1

    await blob.UploadAsync(BinaryData.FromString("""{"v":2}"""), overwrite: true);   // base now v2

    // The base serves the new content; the snapshot still serves the old.
    var current  = (await blob.DownloadContentAsync()).Value.Content.ToString();
    var oldCopy  = (await blob.WithSnapshot(snapshot).DownloadContentAsync()).Value.Content.ToString();
    Assert.Multiple(() =>
    {
        Assert.That(current, Is.EqualTo("""{"v":2}"""));
        Assert.That(oldCopy, Is.EqualTo("""{"v":1}"""));   // snapshot retained the older version
    });
}
```

## Access tiers — set and assert (the data-plane tier control)

`SetAccessTierAsync` moves a blob between Hot/Cool/Cold/Archive; assert via `GetPropertiesAsync().AccessTier`.
This is the **test-fast** tier control. Lifecycle-management *policies* (auto-tier/expire after N days) are a
**management-plane** config Azurite doesn't implement and whose execution runs ~daily — too slow to assert; if
you need to test the policy, assert its **config round-trips** against a real account (the `s3` lifecycle
discipline), never wait for a blob to transition.

```csharp
[Test]
public async Task Should_move_a_blob_to_the_cool_tier()
{
    var blob = Container.GetBlobClient("archive/2025-report.csv");
    await blob.UploadAsync(BinaryData.FromString("id,total\n1,1999"), overwrite: true);

    await blob.SetAccessTierAsync(AccessTier.Cool);

    var props = (await blob.GetPropertiesAsync()).Value;
    Assert.That(props.AccessTier, Is.EqualTo(AccessTier.Cool.ToString()));   // tier round-trips
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
> Cross-link the s3 sibling's S3 → SQS section as the conceptual parallel, and `qa-messaging-testing-dotnet`
> for the Azure-native messaging downstream.

```csharp
// Against a REAL Azure test account (NOT Azurite): a BlobCreated event is routed to a Storage Queue.
[Test]
[Category("RealAzureAccount")]   // excluded from the Azurite-only CI run
public async Task Should_fire_a_storage_queue_message_When_a_blob_is_created()
{
    // The blob event subscription → Storage Queue is provisioned out-of-band (IaC). Here we just receive.
    var queue = new QueueClient(RealAccountConnectionString, "blob-events");

    await Container.GetBlobClient("incoming/order.json").UploadAsync(BinaryData.FromString("{}"), overwrite: true);

    // Poll the queue on a CONDITION (the message arriving), not a sleep — Event Grid delivery is eventual.
    var message = await WaitFor.Async(
        probe:     async ct => (await queue.ReceiveMessageAsync(cancellationToken: ct)).Value,
        predicate: m  => m is not null,
        timeout:   TimeSpan.FromSeconds(30),
        interval:  TimeSpan.FromSeconds(1));

    Assert.That(message.MessageText, Does.Contain("incoming/order.json"));   // the event names the blob
    await queue.DeleteMessageAsync(message.MessageId, message.PopReceipt);
}
```

## Anti-patterns

- **`await Task.Delay(5000)` before asserting a processed/derived blob or a blob event.** Races the worker and
  the event delivery; slow and flaky. *Fix:* `WaitFor.Async` polling the HEAD/probe for the side-effect; poll
  the queue for the blob event. Never a bare sleep.
- **Asserting content-type without setting it.** Azure stores whatever `BlobHttpHeaders.ContentType` you sent
  and does **not** infer it from the `.pdf`/`.png` blob name. A missing one defaults to
  `application/octet-stream`. *Fix:* set `ContentType` on the upload, assert it on `GetPropertiesAsync`.
- **Asserting `ContentHash == MD5(bytes)` on a block-staged blob.** Like S3 multipart ETags, a committed
  block-blob's content-MD5 is **not** auto-computed. *Fix:* assert `ContentLength` and/or download-and-compare
  bytes; only a single-shot `UploadAsync` auto-sets `ContentHash`.
- **Expecting Azurite to fire Event Grid events.** Azurite has **no Event Grid** — the blob-event → queue test
  won't trigger locally. *Fix:* run that test against a real test account (`[Category("RealAzureAccount")]`,
  excluded from the Azurite CI run), or assert the wiring config + the SUT effect directly.
- **Trying to assert lifecycle-policy *execution*.** Auto-tier/expire runs on a ~daily management-plane cadence;
  a test can't wait for it (and Azurite doesn't implement it). *Fix:* assert the **access tier** directly
  (`SetAccessTierAsync` → `GetPropertiesAsync`) for the data-plane control; round-trip the **policy config**
  against a real account if you must test it.
- **Sharing one container across parallel test classes.** Cross-talk: one suite's blobs/deletes leak into
  another's listings and asserts. *Fix:* a **uniquely named container per fixture** (as in `BlobFixture`) or
  `EmptyContainerAsync` in `[SetUp]`; `[Parallelizable(ParallelScope.None)]` on the storage fixtures unless
  verified isolated.
- **Deleting a container/blob without including snapshots.** `DeleteAsync` on a blob that has snapshots fails
  unless you pass `DeleteSnapshotsOption.IncludeSnapshots`. *Fix:* `EmptyContainerAsync` enumerates with
  `BlobStates.Snapshots` and deletes with `IncludeSnapshots`.
- **Scanning `GetBlobs` to check a single blob exists.** A list can momentarily lag a just-written blob and it's
  O(container). *Fix:* `ExistsAsync` / `GetPropertiesAsync` — strongly consistent for the blob, cheap, and 404s
  cleanly when absent.
- **Hard-coding the connection string / an account key in a `[Test]`.** *Fix:* surface the Azurite connection
  string from the fixture; for a cloud test account use `DefaultAzureCredential` + endpoint from env; never log
  secrets.
- **Reaching for Azure Blob when the store is AWS S3.** *Fix:* `references/s3.md` — LocalStack,
  buckets/keys, presigned URLs, multipart, force-path-style; not Azurite/containers/SAS.

## Examples

**End-to-end: an upload → process → derived-blob flow.**

```csharp
public class ImageProcessingTests : BlobFixture
{
    [SetUp]
    public async Task SetUp() => await EmptyContainerAsync();   // independent tests — start from empty

    [Test]
    public async Task Should_write_a_thumbnail_When_an_image_is_uploaded()
    {
        // The SUT worker is wired: BlobCreated → worker → writes thumbnails/<name>.
        await Container.GetBlobClient("uploads/photo.png").UploadAsync(
            BinaryData.FromBytes(SampleImages.Png1024),
            new BlobUploadOptions { HttpHeaders = new BlobHttpHeaders { ContentType = "image/png" } });

        // Wait on the derived blob (the condition-wait) — the worker runs async.
        var thumb = await WaitFor.Async(
            probe:     ct => TryGetPropertiesAsync("thumbnails/photo.png", ct),
            predicate: p  => p.ContentLength > 0,
            timeout:   TimeSpan.FromSeconds(15),
            interval:  TimeSpan.FromMilliseconds(250));

        Assert.That(thumb.ContentType, Is.EqualTo("image/png"));   // derived blob produced
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` (in `BlobFixture`) boots Azurite once and creates a **uniquely named container**; the
   container client is surfaced.
2. `[SetUp]` empties the container so the test starts clean — tests stay independent and order-free.
3. The test seeds an input blob; the running SUT worker produces a derived blob; the test **polls the HEAD of
   the derived blob** (the condition-wait) and asserts it exists with the right content-type.
4. `[OneTimeTearDown]` disposes the container.

**Test-data builder for blob payloads (4+ fields → builder, per the global rules).**

```csharp
public static class Invoices
{
    public static InvoiceBuilder Finalised() => new InvoiceBuilder().WithStatus("Finalised");
}
// InvoiceBuilder.WithNumber(...).WithTotal(...).WithCustomer(...).WithRenderedPdf(...).Build()
// — see qa/dotnet/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `WaitFor.Async` polling a HEAD/DB probe for
  processed/derived blobs; poll the queue for blob events. **No bare `Task.Delay` / `Thread.Sleep`** as an
  assertion wait — `Task.Delay` only as the poll cadence inside the bounded helper.
- The SUT's storage gateway is **constructor-injected** with the `BlobServiceClient` / `BlobContainerClient` +
  container name — never a static client or a connection string read inside a `[Test]`.
- **Azurite is built from the well-known connection string** the module surfaces (no force-path-style gotcha —
  unlike S3). A cloud test account uses **`DefaultAzureCredential` + endpoint from env**, read lazily, never
  logged; mint a **user-delegation SAS** there (shared-key `GenerateSasUri` needs the connection-string client).
- **Set `ContentType` explicitly** on uploads (Azure doesn't infer it); assert it on `GetPropertiesAsync`. Don't
  assert `ContentHash == MD5` on block-staged blobs.
- **Independent tests:** a **uniquely named container per fixture** (or `EmptyContainerAsync` in `[SetUp]`);
  delete blobs **with `IncludeSnapshots`**; integration fixtures `[Parallelizable(ParallelScope.None)]` unless
  verified isolated.
- **Assert the access tier directly; assert lifecycle-policy *config* (not execution)** and only against a real
  account — Azurite doesn't implement lifecycle policies.
- **Azurite emits no Event Grid events** — run the blob-event → queue test against a real account
  (`[Category("RealAzureAccount")]`), or assert wiring + SUT effect locally.
- Prefer `ExistsAsync` / `GetPropertiesAsync` over scanning `GetBlobs` for single-blob existence.
- **Async all the way** — `await` every blob/queue call; never `.Result` / `.Wait()`.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `references/s3.md` — **the canonical stack this node is ported from** AND the
  **`s3`-vs-`azure-blob` boundary**: buckets/keys + presigned URLs + multipart (`TransferUtility`) + LocalStack +
  `ForcePathStyle` vs containers/blobs + SAS tokens + block-staging + Azurite + Event Grid→Storage Queue. Read
  it for the two assertion shapes and the eventual-consistency condition-wait this node mirrors.
- `qa-file-storage-testing-java` — same skill, Java 21 / TestNG (`com.azure:azure-storage-blob`:
  `BlobServiceClient`/`BlobContainerClient`/`BlobClient`, `upload`/`downloadContent`/`exists`/`getProperties`/
  `listBlobs`/`delete`, `BlockBlobClient.stageBlock`/`commitBlockList`, `generateSas` + `BlobServiceSasSignatureValues`,
  Awaitility for the side-effect wait, `org.testcontainers:azure` `AzuriteContainer`). Structure ported, not code.
- `qa-file-storage-testing-typescript` — same skill, Node 20 + TS (`@azure/storage-blob`:
  `BlobServiceClient.fromConnectionString`, `BlockBlobClient.uploadData`/`download`/`exists`/`getProperties`,
  `stageBlock`/`commitBlockList`, `generateSasUrl`, `expect.poll` for the side-effect wait,
  `@testcontainers/azurite`).
- `qa-db-connection-dotnet` — the `WaitFor.Async` poll helper and the seeder/probe split reused for the
  processed-blob side-effect assertions; the **eventual-consistency lineage** this skill leans on.
- `qa-messaging-testing-dotnet` — Azure-native messaging, the natural downstream for the Event
  Grid → Storage Queue bridge (the Azure parallel to `s3`'s S3 → SQS).
- `qa-test-login-tokens-dotnet` — when running against a cloud test account; the `DefaultAzureCredential`
  / secrets-from-env discipline.
- `qa-test-reports-dotnet` — attach the uploaded/derived blob's name + metadata (or the queue-message body)
  to the Allure result.
- `qa-test-data-builder-dotnet` — builders/ObjectMother for blob payloads with 4+ fields.
