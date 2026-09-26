# Messaging Testing — Azure Service Bus (.NET 8 / NUnit) — **canonical stack**

This is the **canonical** stack of the `qa/dotnet/skills/messaging-testing/` node, and it **opens the
`messaging-testing` family** (service-bus → SQS → Kafka → RabbitMQ). **.NET leads here by
judgment** (the same "lead where the tool is most authentic" call WireMock and dependency-scan
made): Service Bus is **Azure-native** and the `Azure.Messaging.ServiceBus` SDK is its most first-class
client surface (sender/receiver/processor, sub-queue access, the richest settlement API). The `java`
(`com.azure:azure-messaging-servicebus`) and `typescript` (`@azure/service-bus`) siblings are **ported**
from this file — all three SDKs mirror the same client → sender/receiver model, so this is a true
translate-the-concepts port, not a redesign.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue or topic.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has
> no synchronous return you can assert on the next line. The message is in flight; the consumer runs on its
> own schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the
> message (or its effect) to appear, with a bounded timeout — **never `Task.Delay` / `Thread.Sleep`**. This
> is the exact lineage of `qa-db-connection-dotnet`'s `WaitForAsync` poll helper. Service Bus gives you a *better*
> primitive than polling for the receive side: `ReceiveMessageAsync(maxWaitTime)` **long-polls** — it
> blocks up to a bounded window for a message to arrive, then returns it or `null`. That bounded wait *is*
> the condition-wait; a fixed sleep is not.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** (`ReceiveMessageAsync`,
  `SendMessageAsync`, `CompleteMessageAsync`; never `.Result` / `.Wait()`)
- `Azure.Messaging.ServiceBus` (the data-plane SDK — client / sender / receiver / processor)
- `Azure.Messaging.ServiceBus.Administration` (`ServiceBusAdministrationClient`) only when a test must
  **create/clear entities** the emulator config didn't pre-declare (most tests don't — entities are declared
  in the emulator `Config.json`)
- `Testcontainers.ServiceBus` (`ServiceBusBuilder`) — boots the **Azure Service Bus emulator** plus its
  required **SQL Edge** sidecar and surfaces a ready connection string
- The SUT's typed publisher/consumer is **constructor-injected** with the connection string (or an injected
  `ServiceBusClient`) — never a static connection string read inside a `[Test]`

```
IntegrationTests/
├── Fixtures/
│   └── ServiceBusFixture.cs        ← boots the emulator (+SQL Edge), exposes the connection string
├── Messaging/
│   ├── ServiceBusProbe.cs          ← test-side receive/peek helpers (read messages + DLQ)
│   └── WaitFor.cs                  ← bounded condition-wait for consumer side-effects
├── Config.json                     ← declares the namespace + queues/topics the tests use
└── OrderPublishingTests.cs
```

## The Service Bus model — entities, settlement, sub-queues

- **Queue** — one log, competing consumers. Send with a **sender**, receive with a **receiver**.
- **Topic + subscription** — publish once to the topic; each **subscription** gets its own copy (filtered).
  You receive from a `CreateReceiver(topicName, subscriptionName)`.
- **Dead-letter queue (DLQ)** — every queue and subscription has a system **sub-queue** where messages that
  can't be processed (explicit dead-letter, max-delivery-count exceeded, TTL expiry) land. Reach it with
  `SubQueue.DeadLetter`.
- **Receive modes** (the settlement contract):
  - **Peek-lock** (`ServiceBusReceiveMode.PeekLock`, the **default**) — the broker hands you the message
    under an **exclusive lock** and waits for you to **settle** it: `CompleteMessageAsync` (done, remove),
    `AbandonMessageAsync` (release the lock, redeliver), `DeadLetterMessageAsync` (move to DLQ),
    `DeferMessageAsync` (set aside). If you do nothing, the lock expires and it redelivers. This is what
    production code uses and what DLQ assertions depend on.
  - **Receive-and-delete** (`ServiceBusReceiveMode.ReceiveAndDelete`) — the broker deletes on delivery; no
    settlement, no redelivery, no DLQ. **Convenient for test-side draining/assertion** (you just want to
    read what's there), but never for code that must not lose a message on a crash.

## Local broker for tests — the Azure Service Bus emulator

There is no in-memory Service Bus. For deterministic local + CI tests, run the **Azure Service Bus
emulator** (`mcr.microsoft.com/azure-service-bus/service-bus-emulator`), which **depends on a SQL Edge**
container (`mcr.microsoft.com/azure-sql-edge`) for its store. The emulator reads a **`Config.json`** that
declares the namespace, queues, topics and subscriptions up front (limits: **1 namespace, 50
queues/topics**). The connection string carries `UseDevelopmentEmulator=true`.

The cleanest path in .NET is the **`Testcontainers.ServiceBus`** module — it wires the emulator + SQL Edge
sidecar together, waits for readiness, and hands you a connection string. Reuse the fixture-base discipline (boot once per fixture; **never `Task.Delay` for readiness** — the
module owns the wait strategy).

```csharp
using NUnit.Framework;
using Testcontainers.ServiceBus;

namespace IntegrationTests.Fixtures;

public abstract class ServiceBusFixture
{
    private ServiceBusContainer _broker = null!;

    // Intent, not the container handle. Secrets (the emulator string) are surfaced, never logged.
    protected string ConnectionString { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartBrokerAsync()
    {
        // The module declares its own readiness wait strategy and pulls the SQL Edge dependency.
        // Entities come from Config.json (mounted by the module); pin the image tag, never `latest`.
        _broker = new ServiceBusBuilder()
            .WithImage("mcr.microsoft.com/azure-service-bus/service-bus-emulator:1.1.2")
            .WithAcceptLicenseAgreement(true)   // ACCEPT_EULA=Y — required by the emulator
            .Build();

        await _broker.StartAsync();
        ConnectionString = _broker.GetConnectionString();
    }

    [OneTimeTearDown]
    public async Task StopBrokerAsync() => await _broker.DisposeAsync();
}
```

`Config.json` (mounted by the module / `WithResourceMapping`) declares the entities the tests use:

```json
{
  "UserConfig": {
    "Namespaces": [{
      "Name": "sbemulatorns",
      "Queues": [
        { "Name": "orders", "Properties": { "MaxDeliveryCount": 5, "DeadLetteringOnMessageExpiration": true } }
      ],
      "Topics": [{
        "Name": "order-events",
        "Subscriptions": [
          { "Name": "fulfilment", "Properties": { "MaxDeliveryCount": 5 } },
          { "Name": "audit",      "Properties": { "MaxDeliveryCount": 5 } }
        ]
      }]
    }]
  }
}
```

> **Cloud test namespace alternative.** If your org runs against a real **test** Service Bus namespace
> instead of the emulator, read the connection string (or an Azure AD token via
> `DefaultAzureCredential` + the namespace FQDN) **from env, lazily** — never hard-code it, never log it
> (cross-link `qa-test-login-tokens-dotnet` for the token-acquisition discipline). The emulator is the
> default for CI determinism; a shared cloud namespace makes tests order-dependent unless each uses a
> unique queue/subscription.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes; the test **drains the queue with a bounded receive** and asserts the message body and
properties. `ReceiveMessageAsync(maxWaitTime)` long-polls — it *is* the condition-wait; a `null` return
means "nothing arrived within the window" and fails the assertion deterministically.

```csharp
public class OrderPublishingTests : ServiceBusFixture
{
    private ServiceBusClient _client = null!;
    private OrderPublisher _sut = null!;   // production code, constructor-injected with the client

    [SetUp]
    public void SetUp()
    {
        _client = new ServiceBusClient(ConnectionString);
        _sut = new OrderPublisher(_client);   // constructor injection — no static client
    }

    [TearDown]
    public async Task TearDown() => await _client.DisposeAsync();

    [Test]
    public async Task Should_publish_OrderPlaced_When_an_order_is_submitted()
    {
        var order = Orders.Pending().WithTotal(1999).Build();   // builder (qa/dotnet/skills/test-data-builder)

        await _sut.SubmitAsync(order);                          // SUT produces the message

        // Read-and-delete on the TEST side: we only want to see what was produced, no settlement needed.
        await using var receiver = _client.CreateReceiver(
            "orders", new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });

        // Bounded long-poll = the condition-wait. Never a fixed Task.Delay before receiving.
        var message = await receiver.ReceiveMessageAsync(maxWaitTime: TimeSpan.FromSeconds(10));

        Assert.That(message, Is.Not.Null, "no message was published to 'orders' within the wait window");
        var placed = message!.Body.ToObjectFromJson<OrderPlaced>();
        Assert.That(placed.OrderId, Is.EqualTo(order.Id));      // one logical assertion: the published fact
    }

    [Test]
    public async Task Should_stamp_correlation_metadata_When_publishing()
    {
        var order = Orders.Pending().Build();

        await _sut.SubmitAsync(order);

        await using var receiver = _client.CreateReceiver(
            "orders", new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });
        var message = await receiver.ReceiveMessageAsync(TimeSpan.FromSeconds(10));

        Assert.That(message, Is.Not.Null);
        Assert.Multiple(() =>                                   // one behaviour: the message envelope
        {
            Assert.That(message!.Subject, Is.EqualTo("OrderPlaced"));
            Assert.That(message.CorrelationId, Is.EqualTo(order.Id.ToString()));
            Assert.That(message.ContentType, Is.EqualTo("application/json"));
        });
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so poll a
**probe** on a condition. This reuses `qa-db-connection-dotnet`'s `WaitForAsync` verbatim.

```csharp
[Test]
public async Task Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed()
{
    var orderId = Guid.NewGuid();

    // 1. Seed the input message onto the queue the consumer listens to.
    await using var sender = _client.CreateSender("orders");
    await sender.SendMessageAsync(new ServiceBusMessage(BinaryData.FromObjectAsJson(new OrderPaid(orderId)))
    {
        Subject = "OrderPaid",
        ContentType = "application/json",
        CorrelationId = orderId.ToString(),
    });

    // 2. The SUT (a ServiceBusProcessor-based consumer) is already running and picks it up.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
    var shipment = await WaitFor.Async(
        probe:     ct => _shipmentsProbe.GetByOrderId(orderId, ct),
        predicate: s  => s.Status == "Ready",
        timeout:   TimeSpan.FromSeconds(10),
        interval:  TimeSpan.FromMilliseconds(200));

    Assert.That(shipment.OrderId, Is.EqualTo(orderId));        // one logical assertion: the side-effect
}
```

The `WaitFor.Async` helper is the same bounded poll as `qa-db-connection-dotnet` — included here so the
node is self-contained:

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
> `await Task.Delay(5000)` standing in for "the message probably arrived by now". The difference: the helper
> returns the instant the condition holds and *fails* if it never does; a bare sleep races the broker.

## Peek-lock vs receive-and-delete — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs in
**peek-lock** (production default) and explicitly settles. When the **test** drains a queue just to assert
what's there, **receive-and-delete** is simpler (no lock to manage). Pick by role:

| Side | Mode | Why |
|------|------|-----|
| Test asserting *what was produced* (drain + read) | `ReceiveAndDelete` | No settlement bookkeeping; you only want to see the message |
| Test exercising the *consumer's* settlement logic | `PeekLock` | Lets you assert Complete vs Abandon vs DeadLetter and redelivery |

```csharp
// Consumer settlement — peek-lock, explicit settle:
await using var receiver = _client.CreateReceiver("orders");   // PeekLock is the default
var msg = await receiver.ReceiveMessageAsync(TimeSpan.FromSeconds(10));

if (CanProcess(msg))
    await receiver.CompleteMessageAsync(msg);                  // remove it — processed
else
    await receiver.DeadLetterMessageAsync(msg,
        deadLetterReason: "ValidationFailed",
        deadLetterErrorDescription: "missing customerId");     // move to DLQ with a reason
```

## Dead-letter-queue assertions

A common, high-value assertion: **a message that failed processing landed in the DLQ** (either the consumer
explicitly dead-lettered it, or it exceeded `MaxDeliveryCount`). Receive from the **DLQ sub-queue**:

```csharp
[Test]
public async Task Should_dead_letter_the_message_When_the_order_payload_is_invalid()
{
    var bad = new ServiceBusMessage(BinaryData.FromString("{ not valid order json }"))
    {
        Subject = "OrderPaid", ContentType = "application/json",
    };
    await using var sender = _client.CreateSender("orders");
    await sender.SendMessageAsync(bad);

    // The consumer (SUT) rejects it and dead-letters it. Assert on the DLQ.
    await using var dlqReceiver = _client.CreateReceiver(
        "orders", new ServiceBusReceiverOptions { SubQueue = SubQueue.DeadLetter });

    // Bounded long-poll the DLQ — wait on the condition (a message lands), not a sleep.
    var dead = await dlqReceiver.ReceiveMessageAsync(maxWaitTime: TimeSpan.FromSeconds(10));

    Assert.That(dead, Is.Not.Null, "expected the poison message in the dead-letter queue");
    Assert.That(dead!.DeadLetterReason, Is.EqualTo("ValidationFailed"));   // the documented reason
}
```

For a **topic subscription's** DLQ, the sub-queue hangs off the subscription:
`_client.CreateReceiver("order-events", "fulfilment", new ServiceBusReceiverOptions { SubQueue = SubQueue.DeadLetter })`.

## Topics, subscriptions & filters

Publish to a **topic**; assert each **subscription** received the copy it should. Subscription **filters**
(SQL filters on properties, or correlation filters) mean not every subscription gets every message — assert
the routing, not just the publish.

```csharp
[Test]
public async Task Should_fan_out_to_fulfilment_and_audit_When_an_order_event_is_published()
{
    await using var sender = _client.CreateSender("order-events");
    await sender.SendMessageAsync(new ServiceBusMessage(BinaryData.FromObjectAsJson(new OrderPlaced(Guid.NewGuid())))
    {
        Subject = "OrderPlaced",
        ApplicationProperties = { ["region"] = "EU" },   // a SQL filter on the subscription can match this
    });

    // Each subscription gets its own copy — read from both.
    await using var fulfilment = _client.CreateReceiver("order-events", "fulfilment",
        new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });
    await using var audit = _client.CreateReceiver("order-events", "audit",
        new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });

    var toFulfilment = await fulfilment.ReceiveMessageAsync(TimeSpan.FromSeconds(10));
    var toAudit      = await audit.ReceiveMessageAsync(TimeSpan.FromSeconds(10));

    Assert.Multiple(() =>                                  // one behaviour: the fan-out routed to both
    {
        Assert.That(toFulfilment, Is.Not.Null, "fulfilment subscription got no copy");
        Assert.That(toAudit,      Is.Not.Null, "audit subscription got no copy");
    });
}
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain with `ReceiveMessagesAsync(maxMessages, maxWaitTime)`
and count — the bounded wait stops it hanging when fewer than N arrive:

```csharp
await using var receiver = _client.CreateReceiver(
    "orders", new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });
var batch = await receiver.ReceiveMessagesAsync(maxMessages: 10, maxWaitTime: TimeSpan.FromSeconds(5));
Assert.That(batch, Has.Count.EqualTo(3));                  // SUT produced exactly 3
```

## Anti-patterns

- **`await Task.Delay(5000)` before receiving / before asserting the side-effect.** Races the broker and
  the consumer; slow and flaky. *Fix:* `ReceiveMessageAsync(maxWaitTime)` for the receive side (it long-polls),
  and the `WaitFor.Async` bounded poll for consumer side-effects. The wait returns the instant the condition
  holds and *fails* if it never does.
- **Asserting on a peek-locked message but never settling it.** The lock expires, the message redelivers,
  and the next test sees a "phantom" message. *Fix:* `CompleteMessageAsync` (or dead-letter) every message
  you peek-lock, or drain with `ReceiveAndDelete` when you only need to read.
- **Sharing one queue across parallel test classes.** Competing receivers steal each other's messages;
  asserts go non-deterministic. *Fix:* a unique queue/subscription per fixture (or
  `[Parallelizable(ParallelScope.None)]` on the messaging fixtures), and drain leftovers in `[SetUp]`.
- **Not draining residual messages between tests.** A message left from a prior test makes the next
  `ReceiveMessageAsync` return the wrong one. *Fix:* drain-to-empty in `[SetUp]` (receive-and-delete in a
  loop until `null`), or use a fresh queue per test.
- **Reading the connection string inside a `[Test]` / hard-coding it.** *Fix:* surface it from the fixture
  (emulator) or env (cloud test namespace), inject it; never log it.
- **Treating `ReceiveMessageAsync` returning `null` as success.** `null` means nothing arrived in the
  window — that's a failed produce, not a pass. *Fix:* `Assert.That(message, Is.Not.Null, ...)` first.
- **Using `ReceiveAndDelete` to test the consumer's settlement logic.** You can't assert Complete vs
  Abandon vs DeadLetter if the broker already deleted it. *Fix:* peek-lock when settlement is under test.

## Examples

**End-to-end: a consume → process → republish flow, asserted on both the side-message and the DLQ for the
poison case.**

```csharp
public class FulfilmentConsumerTests : ServiceBusFixture
{
    private ServiceBusClient _client = null!;

    [SetUp]
    public async Task SetUp()
    {
        _client = new ServiceBusClient(ConnectionString);
        await DrainAsync("orders");                 // independent tests — start from empty
        await DrainAsync("shipments");
    }

    [TearDown]
    public async Task TearDown() => await _client.DisposeAsync();

    [Test]
    public async Task Should_publish_ShipmentReady_When_a_valid_OrderPaid_is_consumed()
    {
        var orderId = Guid.NewGuid();
        await using var sender = _client.CreateSender("orders");
        await sender.SendMessageAsync(new ServiceBusMessage(BinaryData.FromObjectAsJson(new OrderPaid(orderId)))
        {
            Subject = "OrderPaid", ContentType = "application/json", CorrelationId = orderId.ToString(),
        });

        // The SUT consumer processes "orders" and republishes onto "shipments".
        await using var shipments = _client.CreateReceiver(
            "shipments", new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });
        var ready = await shipments.ReceiveMessageAsync(maxWaitTime: TimeSpan.FromSeconds(10));

        Assert.That(ready, Is.Not.Null, "consumer did not republish a ShipmentReady message");
        Assert.That(ready!.CorrelationId, Is.EqualTo(orderId.ToString()));   // correlation preserved
    }

    private async Task DrainAsync(string queue)
    {
        await using var receiver = _client.CreateReceiver(
            queue, new ServiceBusReceiverOptions { ReceiveMode = ServiceBusReceiveMode.ReceiveAndDelete });
        while (await receiver.ReceiveMessageAsync(maxWaitTime: TimeSpan.FromMilliseconds(500)) is not null) { }
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` (in `ServiceBusFixture`) boots the emulator + SQL Edge once; the connection string is
   surfaced. Entities come from `Config.json`.
2. `[SetUp]` drains the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the
   output queue (the condition-wait) and asserts correlation was preserved.
4. `[TearDown]` disposes the client; `[OneTimeTearDown]` disposes the broker.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```csharp
public static class Orders
{
    public static OrderBuilder Pending() => new OrderBuilder().WithStatus("Pending");
}
// OrderBuilder.WithTotal(...).WithCurrency(...).WithCustomer(...).Build() — see qa/dotnet/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `ReceiveMessageAsync(maxWaitTime)` for the
  receive side (bounded long-poll); `WaitFor.Async` for consumer side-effects. **No bare `Task.Delay` /
  `Thread.Sleep`** as an assertion wait — `Task.Delay` only as the poll cadence inside the bounded helper.
- The SUT's publisher/consumer is **constructor-injected** with the `ServiceBusClient` / connection string —
  never a static client or a connection string read inside a `[Test]`.
- **Settle every peek-locked message** (`Complete` / `Abandon` / `DeadLetter`), or use `ReceiveAndDelete`
  when the test only reads. Never leave a lock to expire and redeliver into the next test.
- **Independent tests:** unique queue/subscription per fixture **or** drain-to-empty in `[SetUp]`; integration
  fixtures `[Parallelizable(ParallelScope.None)]` unless verified isolated.
- Assert the **fact**, not the absence: `ReceiveMessageAsync` returning `null` is a *failed* produce — assert
  `Is.Not.Null` before reading the body.
- **Async all the way** — `await` every Service Bus call; `await using` clients/senders/receivers; never
  `.Result` / `.Wait()`.
- Local broker = the **emulator via Testcontainers** (pinned image + SQL Edge sidecar + `Config.json`); a
  cloud test namespace's connection string/token comes from **env, read lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `qa-messaging-testing-java` — same skill, Java 21 / TestNG (`com.azure:azure-messaging-servicebus`:
  `new ServiceBusClientBuilder().connectionString(...)`, `.receiver().queueName(...).receiveMode(PEEK_LOCK)`,
  `receiveMessages(maxMessages, maxWaitTime)`, `SubQueue.DEAD_LETTER`, Awaitility for side-effects,
  `Testcontainers` Service Bus emulator module). Structure ported, not code.
- `qa-messaging-testing-typescript` — same skill, Node 24 + TS (`@azure/service-bus`:
  `new ServiceBusClient(connStr)`, `createReceiver(queue, { receiveMode, subQueueType: "deadLetter" })`,
  `receiveMessages(maxCount, { maxWaitTimeInMs })`, `expect.poll` for side-effects, Testcontainers emulator).
- `references/sqs.md` (`sqs`, next in family) — AWS SQS/SNS on LocalStack; visibility timeout +
  redrive-policy DLQ — same condition-wait discipline, different broker. Then Kafka (`kafka`, offset-based) and
  RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-connection-dotnet` — the `WaitFor.Async` poll helper and the seeder/probe split reused for
  the consumer side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-login-tokens-dotnet` — when authing to a cloud test namespace with an Azure AD token
  (`DefaultAzureCredential`) instead of the emulator connection string; secrets-from-env discipline.
- `qa-test-reports-dotnet` — attach the received message body / DLQ reason to the Allure result.
- `qa-test-data-builder-dotnet` — builders/ObjectMother for message payloads with 4+ fields.
