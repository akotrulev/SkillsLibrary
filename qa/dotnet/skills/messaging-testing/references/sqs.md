# Messaging Testing — AWS SQS / SNS (.NET 8 / NUnit)

Ported from the **canonical** Azure Service Bus stack of the `qa/dotnet/skills/messaging-testing/` family (`service-bus`, where .NET
also led), and **.NET leads this `sqs` node too — by the user's choice** (the house default would have been
TypeScript; .NET was picked for this node, the same kind of judgment call Service Bus and WireMock
stated explicitly). This file is the **canonical** `sqs` stack; the `java` (`software.amazon.awssdk:sqs`/`sns`)
and `typescript` (`@aws-sdk/client-sqs`/`client-sns`) siblings are **ported** from it — all three AWS SDKs
mirror the same send / receive / delete model, so this is a true translate-the-concepts port, not a redesign.

This is the **second `messaging-testing` sibling** (service-bus → **SQS** → Kafka → RabbitMQ).
It keeps the **exact same two assertion patterns and the same eventual-consistency condition-wait discipline**
as `service-bus` — only the broker SDK and its settlement semantics change.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The message is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the message
> (or its effect) to appear, with a bounded timeout — **never `Task.Delay` / `Thread.Sleep`**. This is the
> exact lineage of `qa-db-testing-client-dotnet`'s `WaitForAsync` poll and `references/service-bus.md`'s
> condition-wait. SQS gives you the **`WaitTimeSeconds` long-poll** as a better primitive than spin-polling for
> the receive side: `ReceiveMessageAsync` with `WaitTimeSeconds` blocks up to a bounded window (max **20s**)
> for a message to arrive, then returns it or an empty `Messages` list. That bounded wait *is* the
> condition-wait; a fixed sleep is not.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** (`SendMessageAsync`,
  `ReceiveMessageAsync`, `DeleteMessageAsync`; never `.Result` / `.Wait()`)
- `AWSSDK.SQS` (`AmazonSQSClient` — send / receive / delete / queue attributes) and
  `AWSSDK.SimpleNotificationService` (`AmazonSimpleNotificationServiceClient`) for SNS→SQS fan-out
- `Testcontainers.LocalStack` (`LocalStackBuilder`) — boots **LocalStack** (the local AWS emulator) and
  surfaces an endpoint URL the SDK clients point at via `ServiceURL`
- The SUT's typed publisher/consumer is **constructor-injected** with the `IAmazonSQS` client (or the
  resolved queue URL) — never a static client or an endpoint read inside a `[Test]`

```
IntegrationTests/
├── Fixtures/
│   └── SqsFixture.cs          ← boots LocalStack, creates the queues (+DLQ via redrive), exposes the SQS client + URLs
├── Messaging/
│   └── WaitFor.cs             ← bounded condition-wait for consumer side-effects (reused from qa-db-testing)
└── OrderPublishingTests.cs
```

## The SQS model — visibility timeout, redrive → DLQ, FIFO, SNS fan-out

SQS has **no peek-lock and no per-message ack**. The whole settlement model is:

- **Queue** — competing consumers; one `ReceiveMessage` returns up to 10 messages and **hides** each one for
  its **visibility timeout** instead of removing it. You then call **`DeleteMessage`** (with the message's
  **`ReceiptHandle`**) to remove it — that delete *is* the "I processed it" ack. If you don't delete before
  the visibility timeout elapses, the message becomes visible again and is **redelivered**. There is no
  "receive-and-delete" mode — every receive is followed by an explicit delete when you're done.
- **Visibility timeout** — the SQS analogue of Service Bus's peek-lock: a received message is *invisible*, not
  gone, until you delete it (or the timeout expires → redelivery). `ChangeMessageVisibilityAsync` lets a test
  shorten it to force fast redelivery.
- **Redrive policy → dead-letter queue (DLQ)** — a queue's `RedrivePolicy` attribute names a separate DLQ and
  a `maxReceiveCount`. After a message has been **received** `maxReceiveCount` times **without being deleted**,
  SQS moves it to the DLQ. The DLQ is just another SQS queue — you receive from it to assert. *(This is the
  redrive-policy analogue of Service Bus's `MaxDeliveryCount` → DLQ sub-queue.)*
- **Standard vs FIFO** — a **FIFO** queue's name ends `.fifo` (`FifoQueue=true`); every send needs a
  **`MessageGroupId`** (ordering scope) and a **`MessageDeduplicationId`** (or `ContentBasedDeduplication=true`
  to derive it from the body). Standard queues are best-effort-ordered and at-least-once; FIFO is
  exactly-once-per-dedup-window and ordered within a group.
- **SNS→SQS fan-out** — the topics/subscriptions analogue. Publish once to an **SNS topic**; each **SQS queue
  subscribed** to it gets a copy. Set `RawMessageDelivery=true` on the subscription or the SNS envelope wraps
  your payload in JSON. The subscribed queue also needs an access policy allowing the topic to send to it
  (LocalStack sets this for you when SNS creates the subscription).

## Local broker for tests — LocalStack

There is no in-memory SQS. For deterministic local + CI tests, run **LocalStack** (`localstack/localstack`),
which emulates SQS + SNS on a single endpoint (default `:4566`). Point every SDK client at that endpoint via
`ServiceURL`; LocalStack accepts any credentials (`test`/`test` by convention) and the account id is
`000000000000`. The cleanest path in .NET is the **`Testcontainers.LocalStack`** module — it boots the
container, owns the readiness wait, and surfaces the endpoint. Reuse the fixture discipline (boot once per fixture; **never `Task.Delay` for readiness** — the module owns
the wait strategy). **Create the queues in fixture setup** (there is no `Config.json` equivalent — you declare
them through the SDK).

```csharp
using Amazon.Runtime;
using Amazon.SQS;
using Amazon.SQS.Model;
using NUnit.Framework;
using Testcontainers.LocalStack;

namespace IntegrationTests.Fixtures;

public abstract class SqsFixture
{
    private LocalStackContainer _localstack = null!;

    protected IAmazonSQS Sqs { get; private set; } = null!;
    protected string OrdersUrl { get; private set; } = null!;
    protected string OrdersDlqUrl { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartBrokerAsync()
    {
        // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
        _localstack = new LocalStackBuilder()
            .WithImage("localstack/localstack:3.5")
            .Build();
        await _localstack.StartAsync();

        var endpoint = _localstack.GetConnectionString();   // e.g. http://127.0.0.1:<mappedPort>
        // LocalStack accepts any creds; surfaced for the client, never logged.
        Sqs = new AmazonSQSClient(
            new BasicAWSCredentials("test", "test"),
            new AmazonSQSConfig { ServiceURL = endpoint, AuthenticationRegion = "us-east-1" });

        // Declare the queues the tests use: DLQ first, then the source queue wired to it by a redrive policy.
        OrdersDlqUrl = (await Sqs.CreateQueueAsync("orders-dlq")).QueueUrl;
        var dlqArn = (await Sqs.GetQueueAttributesAsync(
            new GetQueueAttributesRequest { QueueUrl = OrdersDlqUrl, AttributeNames = ["QueueArn"] })).QueueARN;

        OrdersUrl = (await Sqs.CreateQueueAsync(new CreateQueueRequest
        {
            QueueName = "orders",
            Attributes = new Dictionary<string, string>
            {
                ["VisibilityTimeout"] = "1",   // short, so redelivery is fast in tests (default is 30s)
                ["RedrivePolicy"] = $$"""{"deadLetterTargetArn":"{{dlqArn}}","maxReceiveCount":"3"}""",
            },
        })).QueueUrl;
    }

    [OneTimeTearDown]
    public async Task StopBrokerAsync()
    {
        Sqs?.Dispose();
        await _localstack.DisposeAsync();
    }

    // Independent tests: purge the queues so each starts from empty.
    protected async Task PurgeAsync(string queueUrl) => await Sqs.PurgeQueueAsync(queueUrl);
}
```

> **Cloud test queue alternative.** If your org runs against a real **test** AWS account instead of LocalStack,
> drop the `ServiceURL` override and let the SDK resolve the real endpoint; read the region from env and the
> credentials from the **default AWS credential chain** (instance role / SSO / env vars) — never hard-code an
> access key, never log it (cross-link `qa-auth0-test-tokens-dotnet` for the secrets-from-env discipline).
> LocalStack is the default for CI determinism; a shared cloud queue makes tests order-dependent unless each
> uses a uniquely named queue.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT sends; the test **receives with a bounded long-poll** and asserts the message body and attributes.
`ReceiveMessageAsync` with `WaitTimeSeconds` long-polls — it *is* the condition-wait; an empty `Messages`
list means "nothing arrived within the window" and fails the assertion deterministically. Delete what you
read so it doesn't leak into the next test.

```csharp
public class OrderPublishingTests : SqsFixture
{
    private OrderPublisher _sut = null!;   // production code, constructor-injected with the SQS client + URL

    [SetUp]
    public async Task SetUp()
    {
        await PurgeAsync(OrdersUrl);                  // independent tests — start from empty
        _sut = new OrderPublisher(Sqs, OrdersUrl);    // constructor injection — no static client
    }

    [Test]
    public async Task Should_send_OrderPlaced_When_an_order_is_submitted()
    {
        var order = Orders.Pending().WithTotal(1999).Build();   // builder (qa/dotnet/skills/test-data-builder)

        await _sut.SubmitAsync(order);                          // SUT produces the message

        // Bounded long-poll = the condition-wait. Never a fixed Task.Delay before receiving.
        var received = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        {
            QueueUrl = OrdersUrl,
            WaitTimeSeconds = 10,        // long-poll up to 10s for the message to land
            MaxNumberOfMessages = 1,
            MessageAttributeNames = ["All"],
        });

        Assert.That(received.Messages, Is.Not.Empty, "no message was sent to 'orders' within the wait window");
        var placed = JsonSerializer.Deserialize<OrderPlaced>(received.Messages[0].Body)!;
        Assert.That(placed.OrderId, Is.EqualTo(order.Id));      // one logical assertion: the published fact

        await Sqs.DeleteMessageAsync(OrdersUrl, received.Messages[0].ReceiptHandle);   // ack/clean up
    }

    [Test]
    public async Task Should_stamp_event_type_attribute_When_publishing()
    {
        var order = Orders.Pending().Build();

        await _sut.SubmitAsync(order);

        var received = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        {
            QueueUrl = OrdersUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1, MessageAttributeNames = ["All"],
        });

        Assert.That(received.Messages, Is.Not.Empty);
        var message = received.Messages[0];
        Assert.Multiple(() =>                                   // one behaviour: the message envelope
        {
            Assert.That(message.MessageAttributes["eventType"].StringValue, Is.EqualTo("OrderPlaced"));
            Assert.That(message.MessageAttributes["correlationId"].StringValue, Is.EqualTo(order.Id.ToString()));
        });
        await Sqs.DeleteMessageAsync(OrdersUrl, message.ReceiptHandle);
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so poll a
**probe** on a condition. This reuses `qa-db-testing-client-dotnet`'s `WaitForAsync` verbatim.

```csharp
[Test]
public async Task Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed()
{
    var orderId = Guid.NewGuid();

    // 1. Seed the input message onto the queue the consumer polls.
    await Sqs.SendMessageAsync(new SendMessageRequest
    {
        QueueUrl = OrdersUrl,
        MessageBody = JsonSerializer.Serialize(new OrderPaid(orderId)),
        MessageAttributes = new Dictionary<string, MessageAttributeValue>
        {
            ["eventType"] = new() { DataType = "String", StringValue = "OrderPaid" },
        },
    });

    // 2. The SUT (an SQS-polling consumer) is already running and picks it up.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
    var shipment = await WaitFor.Async(
        probe:     ct => _shipmentsProbe.GetByOrderId(orderId, ct),
        predicate: s  => s.Status == "Ready",
        timeout:   TimeSpan.FromSeconds(10),
        interval:  TimeSpan.FromMilliseconds(200));

    Assert.That(shipment.OrderId, Is.EqualTo(orderId));        // one logical assertion: the side-effect
}
```

The `WaitFor.Async` helper is the same bounded poll as `qa-db-testing-client-dotnet` and ``service-bus`` Service Bus —
included so the node is self-contained:

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

## Visibility timeout — received-but-not-deleted → redelivery (the peek-lock analogue)

A received message is **invisible**, not gone, for its visibility timeout. If the consumer doesn't
`DeleteMessage` before that window elapses, the message becomes visible again and is **redelivered**. This is
SQS's settlement primitive — there's no `Complete`/`Abandon`. To assert redelivery deterministically, shorten
the visibility window (we set the queue's `VisibilityTimeout=1` in the fixture, or call
`ChangeMessageVisibilityAsync(..., 0)` to make it immediately visible again).

```csharp
[Test]
public async Task Should_redeliver_the_message_When_it_is_received_but_not_deleted()
{
    await Sqs.SendMessageAsync(OrdersUrl, """{"orderId":"abc"}""");

    // First receive — DON'T delete. The message is now invisible for the visibility timeout.
    var first = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
    {
        QueueUrl = OrdersUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1,
        AttributeNames = ["ApproximateReceiveCount"],
    });
    Assert.That(first.Messages, Is.Not.Empty);

    // Make it visible again immediately (instead of sleeping for the timeout) → forces redelivery.
    await Sqs.ChangeMessageVisibilityAsync(OrdersUrl, first.Messages[0].ReceiptHandle, 0);

    // Second receive long-polls until the redelivered copy reappears — the condition-wait, not a sleep.
    var second = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
    {
        QueueUrl = OrdersUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1,
        AttributeNames = ["ApproximateReceiveCount"],
    });

    Assert.That(second.Messages, Is.Not.Empty, "the un-deleted message was not redelivered");
    Assert.That(int.Parse(second.Messages[0].Attributes["ApproximateReceiveCount"]),
        Is.GreaterThanOrEqualTo(2));            // delivered at least twice — proof of redelivery
}
```

## Redrive-policy DLQ assertions

The high-value assertion: **a message that kept failing landed in the DLQ**. With `maxReceiveCount=3` (set in
the fixture's redrive policy), a message received 3 times without a delete is moved to the DLQ on the **next**
receive attempt (a documented SQS/LocalStack behaviour — the move is triggered by a receive, so do one more
receive than `maxReceiveCount` to trigger it). Then receive from the **DLQ** to assert.

```csharp
[Test]
public async Task Should_redrive_to_the_dlq_When_max_receive_count_is_exceeded()
{
    await Sqs.SendMessageAsync(OrdersUrl, """{ not valid order json }""");

    // Receive-without-delete maxReceiveCount+1 times, resetting visibility to 0 each time to force fast
    // redelivery. The bounded long-poll is the condition-wait; no Task.Delay anywhere.
    for (var attempt = 0; attempt < 4; attempt++)   // 4 = maxReceiveCount(3) + 1 to trigger the move
    {
        var poll = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        {
            QueueUrl = OrdersUrl, WaitTimeSeconds = 5, MaxNumberOfMessages = 1,
        });
        if (poll.Messages.Count > 0)
            await Sqs.ChangeMessageVisibilityAsync(OrdersUrl, poll.Messages[0].ReceiptHandle, 0);
    }

    // Assert on the DLQ — long-poll the condition (the message lands), not a sleep.
    var dead = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
    {
        QueueUrl = OrdersDlqUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1,
    });

    Assert.That(dead.Messages, Is.Not.Empty, "expected the poison message in the dead-letter queue");
    Assert.That(dead.Messages[0].Body, Does.Contain("not valid order json"));   // the original payload
    await Sqs.DeleteMessageAsync(OrdersDlqUrl, dead.Messages[0].ReceiptHandle);
}
```

> When the **SUT consumer** owns the failing/deleting, you don't drive the receive loop yourself — you seed the
> poison message, let the consumer fail it `maxReceiveCount` times, and `WaitFor.Async`-poll the DLQ for the
> moved message. The manual loop above is for when the *test* is exercising the redrive wiring directly.

## Standard vs FIFO queues

A **FIFO** queue (`.fifo` suffix, `FifoQueue=true`) guarantees ordering within a `MessageGroupId` and
deduplicates within a 5-minute window. Each send must carry a `MessageGroupId`, and a
`MessageDeduplicationId` unless the queue has `ContentBasedDeduplication=true`.

```csharp
var fifoUrl = (await Sqs.CreateQueueAsync(new CreateQueueRequest
{
    QueueName = "orders.fifo",
    Attributes = new Dictionary<string, string>
    {
        ["FifoQueue"] = "true",
        ["ContentBasedDeduplication"] = "true",   // dedup id derived from the body
    },
})).QueueUrl;

[Test]
public async Task Should_deduplicate_When_the_same_message_is_sent_twice_within_the_window()
{
    var body = """{"orderId":"dup-1"}""";
    var send = (string b) => Sqs.SendMessageAsync(new SendMessageRequest
    {
        QueueUrl = fifoUrl, MessageBody = b, MessageGroupId = "orders",
    });

    await send(body);
    await send(body);   // identical body within the dedup window → collapsed to one

    var received = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
    {
        QueueUrl = fifoUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 10,
    });

    Assert.That(received.Messages, Has.Count.EqualTo(1));   // dedup collapsed the duplicate
}
```

## SNS→SQS fan-out

Publish once to an **SNS topic**; assert each **subscribed SQS queue** received its copy — the topics/
subscriptions analogue. Use `RawMessageDelivery=true` so the queue gets your raw payload, not the SNS JSON
envelope.

```csharp
[Test]
public async Task Should_fan_out_to_both_queues_When_an_order_event_is_published()
{
    var sns = new AmazonSimpleNotificationServiceClient(
        new BasicAWSCredentials("test", "test"),
        new AmazonSimpleNotificationServiceConfig { ServiceURL = _endpoint, AuthenticationRegion = "us-east-1" });

    var topicArn = (await sns.CreateTopicAsync("order-events")).TopicArn;
    foreach (var queueUrl in new[] { _fulfilmentUrl, _auditUrl })
    {
        var arn = (await Sqs.GetQueueAttributesAsync(
            new GetQueueAttributesRequest { QueueUrl = queueUrl, AttributeNames = ["QueueArn"] })).QueueARN;
        await sns.SubscribeAsync(new SubscribeRequest
        {
            TopicArn = topicArn, Protocol = "sqs", Endpoint = arn,
            Attributes = new Dictionary<string, string> { ["RawMessageDelivery"] = "true" },
        });
    }

    await sns.PublishAsync(topicArn, JsonSerializer.Serialize(new OrderPlaced(Guid.NewGuid())));

    // Each subscribed queue gets its own copy — long-poll both (the condition-wait).
    var toFulfilment = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        { QueueUrl = _fulfilmentUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1 });
    var toAudit = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        { QueueUrl = _auditUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1 });

    Assert.Multiple(() =>                                   // one behaviour: the fan-out reached both
    {
        Assert.That(toFulfilment.Messages, Is.Not.Empty, "fulfilment queue got no copy");
        Assert.That(toAudit.Messages,      Is.Not.Empty, "audit queue got no copy");
    });
}
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain in a loop with `WaitTimeSeconds` and count — the bounded
long-poll stops it hanging when fewer than N arrive. SQS returns **at most 10** per receive, so loop:

```csharp
var drained = new List<Message>();
while (true)
{
    var page = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
    {
        QueueUrl = OrdersUrl, WaitTimeSeconds = 2, MaxNumberOfMessages = 10,
    });
    if (page.Messages.Count == 0) break;       // bounded wait returned empty → drained
    drained.AddRange(page.Messages);
    foreach (var m in page.Messages)
        await Sqs.DeleteMessageAsync(OrdersUrl, m.ReceiptHandle);
}
Assert.That(drained, Has.Count.EqualTo(3));    // SUT produced exactly 3
```

## Anti-patterns

- **`await Task.Delay(5000)` before receiving / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* `ReceiveMessageAsync` with `WaitTimeSeconds` for the receive side (it
  long-polls, max 20s), and the `WaitFor.Async` bounded poll for consumer side-effects.
- **`WaitTimeSeconds = 0` (short-polling) in a test.** Short-poll returns immediately, usually empty even when
  a message is in flight, so it races the produce. *Fix:* always set `WaitTimeSeconds` (long-poll) — that *is*
  the condition-wait.
- **Receiving but never deleting.** The message stays invisible for the visibility timeout, then redelivers
  into the next test as a "phantom". *Fix:* `DeleteMessageAsync(url, ReceiptHandle)` every message you've
  finished with — that's the SQS ack — or `PurgeQueueAsync` in `[SetUp]`.
- **Treating an empty `Messages` list as success.** Empty means nothing arrived in the window — a failed
  produce, not a pass. *Fix:* `Assert.That(received.Messages, Is.Not.Empty, ...)` first.
- **Expecting the DLQ move after exactly `maxReceiveCount` receives.** SQS moves the message on the *next*
  receive after the count is exceeded. *Fix:* receive `maxReceiveCount + 1` times (resetting visibility to 0),
  then assert on the DLQ — or let the SUT consumer fail it and `WaitFor.Async`-poll the DLQ.
- **Sharing one queue across parallel test classes.** Competing receivers steal each other's messages; asserts
  go non-deterministic. *Fix:* a uniquely named queue per fixture, `PurgeQueueAsync` in `[SetUp]`, and
  `[Parallelizable(ParallelScope.None)]` on the messaging fixtures.
- **FIFO send without a `MessageGroupId`.** The send is rejected. *Fix:* every FIFO send carries a
  `MessageGroupId`; supply a `MessageDeduplicationId` unless `ContentBasedDeduplication=true`.
- **Hard-coding the endpoint / an AWS access key in a `[Test]`.** *Fix:* surface the LocalStack endpoint from
  the fixture; for a cloud test account use the default credential chain + region from env; never log secrets.

## Examples

**End-to-end: a consume → process → republish flow, asserted on the side-message, with the poison case going
to the DLQ.**

```csharp
public class FulfilmentConsumerTests : SqsFixture
{
    [SetUp]
    public async Task SetUp()
    {
        await PurgeAsync(OrdersUrl);          // independent tests — start from empty
        await PurgeAsync(ShipmentsUrl);
    }

    [Test]
    public async Task Should_send_ShipmentReady_When_a_valid_OrderPaid_is_consumed()
    {
        var orderId = Guid.NewGuid();
        await Sqs.SendMessageAsync(new SendMessageRequest
        {
            QueueUrl = OrdersUrl,
            MessageBody = JsonSerializer.Serialize(new OrderPaid(orderId)),
            MessageAttributes = new Dictionary<string, MessageAttributeValue>
            {
                ["eventType"]     = new() { DataType = "String", StringValue = "OrderPaid" },
                ["correlationId"] = new() { DataType = "String", StringValue = orderId.ToString() },
            },
        });

        // The SUT consumer polls "orders" and republishes onto "shipments".
        var ready = await Sqs.ReceiveMessageAsync(new ReceiveMessageRequest
        {
            QueueUrl = ShipmentsUrl, WaitTimeSeconds = 10, MaxNumberOfMessages = 1, MessageAttributeNames = ["All"],
        });

        Assert.That(ready.Messages, Is.Not.Empty, "consumer did not republish a ShipmentReady message");
        Assert.That(ready.Messages[0].MessageAttributes["correlationId"].StringValue,
            Is.EqualTo(orderId.ToString()));      // correlation preserved
        await Sqs.DeleteMessageAsync(ShipmentsUrl, ready.Messages[0].ReceiptHandle);
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` (in `SqsFixture`) boots LocalStack once and creates the queues (DLQ + source wired by a
   redrive policy); the SQS client + URLs are surfaced.
2. `[SetUp]` purges the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the output
   queue (the condition-wait) and asserts correlation was preserved, then deletes what it read.
4. `[OneTimeTearDown]` disposes the client and the container.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```csharp
public static class Orders
{
    public static OrderBuilder Pending() => new OrderBuilder().WithStatus("Pending");
}
// OrderBuilder.WithTotal(...).WithCurrency(...).WithCustomer(...).Build() — see qa/dotnet/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `ReceiveMessageAsync` with `WaitTimeSeconds`
  for the receive side (bounded long-poll, max 20s); `WaitFor.Async` for consumer side-effects. **No bare
  `Task.Delay` / `Thread.Sleep`** as an assertion wait — `Task.Delay` only as the poll cadence inside the
  bounded helper. Never short-poll (`WaitTimeSeconds = 0`) in a test.
- The SUT's publisher/consumer is **constructor-injected** with the `IAmazonSQS` client / queue URL — never a
  static client or an endpoint read inside a `[Test]`.
- **Delete (ack) every message you've finished processing** with its `ReceiptHandle`, or `PurgeQueueAsync` in
  `[SetUp]`. Never leave an un-deleted message to redeliver into the next test.
- **Independent tests:** uniquely named queue per fixture **or** `PurgeQueueAsync` in `[SetUp]`; integration
  fixtures `[Parallelizable(ParallelScope.None)]` unless verified isolated.
- Assert the **fact**, not the absence: an empty `Messages` list is a *failed* produce — assert `Is.Not.Empty`
  before reading the body.
- **DLQ via redrive policy:** receive `maxReceiveCount + 1` times (visibility reset to 0) to trigger the move,
  then assert on the DLQ — or let the SUT fail it and `WaitFor.Async`-poll the DLQ.
- **Async all the way** — `await` every SQS/SNS call; `Dispose` clients; never `.Result` / `.Wait()`.
- Local broker = **LocalStack via Testcontainers** (pinned image; queues created in fixture setup); a cloud
  test account uses the **default credential chain + region from env**, read lazily, never logged.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `qa-messaging-testing-java` — same skill, Java 21 / TestNG (`software.amazon.awssdk:sqs`/`sns`:
  `SqsClient.builder().endpointOverride(...)`, `receiveMessage(b -> b.waitTimeSeconds(10)...)`,
  `RedrivePolicy` attribute, Awaitility for side-effects, `org.testcontainers:localstack`
  `LocalStackContainer`). Structure ported, not code.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`@aws-sdk/client-sqs`/`client-sns`:
  `new SQSClient({ endpoint })`, `ReceiveMessageCommand({ WaitTimeSeconds: 10 })`, `expect.poll` for
  side-effects, `@testcontainers/localstack`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure Service
  Bus on the emulator; **the `service-bus`-vs-`sqs` boundary**: Service Bus peek-lock + DLQ *sub-queue* vs SQS
  visibility-timeout + redrive-policy *DLQ queue* — same condition-wait discipline, different settlement.
  Kafka (`kafka`, offset-based) and RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-testing-client-dotnet` — the `WaitFor.Async` poll helper and the seeder/probe split reused for
  the consumer side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-auth0-test-tokens-dotnet` — when running against a cloud test account; the default-credential-chain
  + secrets-from-env discipline.
- `qa-allure-reporting-dotnet` — attach the received message body / DLQ payload to the Allure result.
- `qa-test-data-builder-dotnet` — builders/ObjectMother for message payloads with 4+ fields.
