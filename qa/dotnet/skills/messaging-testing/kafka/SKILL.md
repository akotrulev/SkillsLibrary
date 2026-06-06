---
name: qa-messaging-testing-kafka-dotnet
description: >-
  Async messaging assertions against Apache Kafka in .NET 8 (NUnit) with `Confluent.Kafka`: prove the
  system-under-test **produced** record X onto a topic, or **consumed** one and produced side-effect Y, where
  the result is **eventually consistent** — so you wait on a condition for the record to arrive, never
  `Task.Delay`. `new ProducerBuilder<string,string>(config).Build()` / `ProduceAsync(topic, new Message<...>{
  Key, Value })`, `new ConsumerBuilder<string,string>(config).Build()` / `Subscribe(topic)` / `Consume(TimeSpan)`
  poll, **offsets + consumer groups + partitions** (you read from an offset, you don't ack/delete per record;
  `AutoOffsetReset.Earliest`, `EnableAutoCommit=false` + `Commit()`), **key → partition routing** (ordering
  within a partition), and an **app-level dead-letter topic** (`<topic>.DLT` — a convention, not a broker
  feature), with a **local broker for tests** via Testcontainers (`Testcontainers.Kafka` `KafkaContainer`).
  Triggers: "assert our service produced an OrderPlaced record to the topic", "verify the consumer wrote the
  row after the record arrived", "the record that failed processing landed on the DLT topic", "records with the
  same key kept their order", "read from the start of the topic with a fresh consumer group", "wait for the
  record without a sleep", "stand up a local Kafka for these tests". Do NOT use for: in-process mocking of a
  downstream HTTP dependency (use qa-api-mocking-wiremock-dotnet), DB-only assertions with no broker (use
  qa-db-testing-client-dotnet), the Java stack (use qa-messaging-testing-kafka-java), the TypeScript stack (use
  qa-messaging-testing-kafka-typescript), or a different broker — Azure Service Bus
  (qa-messaging-testing-service-bus-*), AWS SQS (qa-messaging-testing-sqs-*), RabbitMQ
  (qa-messaging-testing-rabbitmq-*).
---

# Messaging Testing — Apache Kafka (.NET 8 / NUnit)

Ported from the **canonical** `java` stack of the `qa/dotnet/skills/messaging-testing/kafka/` node (Java leads this node by
judgment — Kafka is JVM-native and `org.apache.kafka:kafka-clients` is its most first-class client; this file
re-expresses the same model in .NET idioms — `Confluent.Kafka`, NUnit, a bounded `Consume` poll loop,
Testcontainers). This is the **third `messaging-testing` sibling** (#28 service-bus → #29 SQS → **#30 Kafka** →
#31 RabbitMQ); it keeps the **same two assertion patterns and the same eventual-consistency condition-wait
discipline** as #28 — only the broker model changes, and Kafka's is the **biggest departure in the family**, so
read the model section before the code. Translate-the-concepts, not redesign — `Confluent.Kafka` mirrors the
same produce / subscribe / poll model.

- **Producer-assert** — the SUT, when exercised, **produced** record X onto a topic.
- **Consumer-assert** — the SUT **consumed** a record and produced an observable **side-effect Y** (a row
  written, an email sent, another record produced).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The record is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the record
> (or its effect) to appear, with a bounded timeout — **never `Task.Delay` / `Thread.Sleep`**. This is the
> exact lineage of `qa-db-testing-client-dotnet`'s `WaitForAsync` poll and
> `qa-messaging-testing-service-bus-dotnet`'s condition-wait. Kafka gives you **`consumer.Consume(TimeSpan)`**
> as the receive-side primitive: it blocks up to a bounded window for a record, then returns it or `null`. A
> **bounded poll loop** (consume until you have the records you expect, or a deadline passes) *is* the
> condition-wait; a fixed sleep is not.

## The Kafka model — a LOG, not a queue (read this first)

Kafka is **not a queue**. It's an append-only, partitioned **commit log**, and that changes every settlement
assumption SQS (#29) and Service Bus (#28) baked in:

- **Topics + partitions.** A topic is split into **partitions**; each partition is an ordered, immutable log.
  Ordering is guaranteed **only within a partition**, not across a topic.
- **You read from an offset; you do NOT ack/delete per record.** Consuming a record does **not** remove it —
  it stays in the log until the topic's **retention** window expires. There is no per-message ack, no
  visibility timeout, no "complete/abandon". Instead each **consumer group** tracks an **offset** per
  partition: "I've read up to here". `Commit()` persists that position. So the SQS "delete = ack" and Service
  Bus "complete = ack" have **no analogue** — the closest thing is *committing an offset*, and it marks a
  position, it doesn't consume-and-destroy.
- **Consumer groups.** Records are delivered to **each consumer group** independently. Two groups reading the
  same topic each get every record (fan-out is built in — no SNS/topic-subscription wiring needed). Within a
  group, partitions are divided among members (competing consumers, per partition).
- **`AutoOffsetReset.Earliest`** decides where a group with **no committed offset** starts: `Earliest` = the
  beginning of the log, `Latest` = only new records. **Test-side reads use a fresh group id + `Earliest`** so
  they read the whole topic from the start — that's the "drain the queue" analogue, except the log isn't
  drained, just re-read.
- **Keys → partition routing.** A record's **key** is hashed to pick a partition, so all records with the same
  key land on the same partition and keep their relative order. This is the ordering primitive (the rough
  analogue of SQS FIFO's `MessageGroupId`).
- **No broker-native DLQ.** Kafka has **no dead-letter queue**. A "DLT" (dead-letter topic) is an
  **application-level convention**: on a processing failure the consumer's error handler **produces the record
  to a separate `<topic>.DLT` topic**. A `Confluent.Kafka` consumer does this in a `catch` block (the .NET
  analogue of Spring Kafka's `DeadLetterPublishingRecoverer`). This is the sharpest contrast with #28 (broker
  DLQ *sub-queue*) and #29 (redrive-policy DLQ *queue*) — same job, **app code** instead of a broker feature.
- **Log compaction** (mention): a compacted topic keeps only the **latest** value per key. Rarely what a test
  asserts on directly; just don't expect every historical record on a compacted topic.

## Decision matrix — Kafka vs the rest of the `messaging-testing` family

| Need | Use | Why |
|------|-----|-----|
| Assert against **Apache Kafka** (offsets, consumer groups, partitions, key routing, app-level DLT, compaction) | **Kafka (this skill)** | Log-based, not a queue; `Confluent.Kafka` is the first-class .NET client; Kafka/Redpanda Testcontainers run locally |
| Assert against an **Azure Service Bus** queue/topic (peek-lock, DLQ sub-queue, sessions, SQL filters) | `qa-messaging-testing-service-bus-dotnet` (#28) | Azure-native queue/topic; explicit peek-lock settlement + DLQ sub-queue — not offsets |
| Assert against **AWS SQS / SNS** (visibility timeout, redrive-policy DLQ, FIFO dedup, SNS fan-out) | `qa-messaging-testing-sqs-dotnet` (#29) | AWS-native queue; delete-to-ack + visibility timeout — not a log you re-read |
| Assert against **RabbitMQ** (exchanges, routing keys, manual ack/nack, DLX) | `qa-messaging-testing-rabbitmq-dotnet` (#31) | AMQP broker; exchange/binding topology + per-message ack |
| Mock a downstream **HTTP** dependency the SUT calls | `qa-api-mocking-wiremock-dotnet` (#22) | Not messaging — a synchronous request/response fake |
| Assert a row was written, with no broker in the flow | `qa-db-testing-client-dotnet` (#3) | Pure DB verification; reuse its `WaitForAsync` for the eventual-consistency side here |

**Rule of thumb:** *A partitioned log you read by offset, with consumer groups and an app-level DLT?* → Kafka.
*A different broker?* → the matching sibling. *No broker at all?* → DB/API-mocking. All four messaging
siblings share the **same eventual-consistency condition-wait discipline** — only the broker model differs.

> **The #30-vs-#28/#29 boundary in one line.** Service Bus and SQS are **queues**: you **consume-and-settle**
> (peek-lock complete / delete), a record leaves the queue, and the broker owns the **DLQ**. Kafka is a
> **log**: you **read at an offset and commit your position**, the record **stays** (other groups re-read it),
> there is **no per-message ack** and **no broker DLQ** — a DLT is something **your app produces to**. Same
> *condition-wait discipline*, **fundamentally different** broker model.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** for produces and side-effect
  waits (`ProduceAsync`; never `.Result` / `.Wait()`). Note `Consume(TimeSpan)` is **synchronous by design** in
  `Confluent.Kafka` (it wraps the native librdkafka poll) — that's the one place a blocking call is correct,
  bounded by the `TimeSpan` you pass.
- `Confluent.Kafka` (`ProducerBuilder` / `ConsumerBuilder` / `Message<,>` / `ConsumeResult<,>` / `AdminClient`)
- `Testcontainers.Kafka` (`KafkaBuilder` → `KafkaContainer`) — boots a **local broker** and surfaces
  `GetBootstrapAddress()` (cross-link `qa-test-environments-dotnet`). A Redpanda image (Kafka-API-compatible,
  ~2× faster start) is a drop-in alternative when you boot a fresh broker per suite.
- The SUT's typed producer/consumer is **constructor-injected** with the bootstrap servers (or an injected
  `IProducer`/`IConsumer`) — never a static client or a bootstrap string read inside a `[Test]`

```
IntegrationTests/
├── Fixtures/
│   └── KafkaFixture.cs       ← boots the Kafka container, creates topics, exposes bootstrap servers + a producer factory
├── Messaging/
│   ├── KafkaProbe.cs         ← test-side reader: fresh consumer group at Earliest, bounded consume-until-N (the "drain" analogue)
│   └── WaitFor.cs            ← bounded condition-wait for consumer side-effects (reused from qa-db-testing)
└── OrderPublishingTests.cs
```

## Local broker for tests — Kafka / Redpanda via Testcontainers

There is no in-memory Kafka. For deterministic local + CI tests, run a **real broker in a container** and point
the clients at `GetBootstrapAddress()`. The cleanest path in .NET is the **`Testcontainers.Kafka`** module
(`confluentinc/cp-kafka`); a Redpanda image is the lighter, faster-starting Kafka-API-compatible alternative.
Reuse the fixture discipline from `qa-test-environments-dotnet` (boot once per fixture; **never `Task.Delay`
for readiness** — the module owns the wait strategy). **Create topics up front** with a known partition count
(via `AdminClient`) so partition assertions are deterministic.

```csharp
using Confluent.Kafka;
using Confluent.Kafka.Admin;
using NUnit.Framework;
using Testcontainers.Kafka;

namespace IntegrationTests.Fixtures;

public abstract class KafkaFixture
{
    private KafkaContainer _broker = null!;

    protected string BootstrapServers { get; private set; } = null!;
    protected KafkaProbe Probe { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartBrokerAsync()
    {
        // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
        _broker = new KafkaBuilder().WithImage("confluentinc/cp-kafka:7.6.1").Build();
        await _broker.StartAsync();
        BootstrapServers = _broker.GetBootstrapAddress();
        Probe = new KafkaProbe(BootstrapServers);

        // Create the topics with a known partition count so partition/ordering assertions are deterministic.
        using var admin = new AdminClientBuilder(
            new AdminClientConfig { BootstrapServers = BootstrapServers }).Build();
        await admin.CreateTopicsAsync(new[]
        {
            new TopicSpecification { Name = "orders",     NumPartitions = 3, ReplicationFactor = 1 },
            new TopicSpecification { Name = "orders.DLT", NumPartitions = 1, ReplicationFactor = 1 },
            new TopicSpecification { Name = "shipments",  NumPartitions = 1, ReplicationFactor = 1 },
        });
    }

    [OneTimeTearDown]
    public async Task StopBrokerAsync() => await _broker.DisposeAsync();

    // A short-lived producer for seeding input records. Await the produce so the record is flushed
    // before the test moves on — that's a confirm, not a sleep.
    protected IProducer<string, string> NewProducer() =>
        new ProducerBuilder<string, string>(
            new ProducerConfig { BootstrapServers = BootstrapServers, Acks = Acks.All }).Build();
}
```

> **Cloud / shared test cluster alternative.** If your org runs against a real **test** Kafka cluster instead
> of a container, read `BootstrapServers` and the SASL/SSL credentials **from env, lazily** — never hard-code
> them, never log them (cross-link `qa-auth0-test-tokens-dotnet` for the secrets-from-env discipline). A
> container is the default for CI determinism; a shared cluster makes tests order-dependent unless each uses a
> **uniquely named topic** and a **fresh consumer group** (because the log isn't drained between tests).

## The test-side reader — `KafkaProbe` (the "drain" analogue)

Because consuming doesn't remove records, the test-side reader subscribes a **fresh consumer group** at
`Earliest` and **consumes until it has the records it expects or a deadline passes**. The bounded loop is the
condition-wait — `Consume(TimeSpan)` long-polls each iteration; no `Task.Delay` anywhere.

```csharp
using Confluent.Kafka;

namespace IntegrationTests.Messaging;

public sealed class KafkaProbe
{
    private readonly string _bootstrapServers;

    public KafkaProbe(string bootstrapServers) => _bootstrapServers = bootstrapServers;

    /// Read up to `count` records from `topic`, from the start, within `timeout`. Fresh group → reads the
    /// whole log; the bounded consume loop IS the condition-wait. Returns what arrived (possibly fewer).
    public IReadOnlyList<ConsumeResult<string, string>> Records(string topic, int count, TimeSpan timeout)
    {
        var config = new ConsumerConfig
        {
            BootstrapServers = _bootstrapServers,
            GroupId = $"probe-{Guid.NewGuid()}",          // fresh group → reads from the start
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = false,                     // a probe commits nothing
        };

        var collected = new List<ConsumeResult<string, string>>();
        using var consumer = new ConsumerBuilder<string, string>(config).Build();
        consumer.Subscribe(topic);

        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline && collected.Count < count)
        {
            var result = consumer.Consume(TimeSpan.FromMilliseconds(500));   // long-poll = the wait
            if (result is not null) collected.Add(result);
        }
        consumer.Close();    // leave the group cleanly
        return collected;
    }
}
```

> `Consume(TimeSpan)` blocks up to that window for a record and returns the instant one arrives — it does
> **not** sleep the full duration when records are present. The loop ends as soon as `count` records are in, or
> fails the test (via the assertion below) if the deadline passes empty. That is the condition-wait; a bare
> `Task.Delay(5000)` "until the record probably arrived" races the broker and is banned.

## Core pattern 1 — producer-assert (the SUT produced record X)

The SUT produces; the test reads with the probe and asserts the record's key, value and headers. An **empty**
result means "nothing arrived within the window" — a failed produce, asserted deterministically.

```csharp
public class OrderPublishingTests : KafkaFixture
{
    private OrderPublisher _sut = null!;   // production code, constructor-injected with the bootstrap servers

    [SetUp]
    public void SetUp() => _sut = new OrderPublisher(BootstrapServers, "orders");   // constructor injection

    [Test]
    public async Task Should_produce_OrderPlaced_When_an_order_is_submitted()
    {
        var order = Orders.Pending().WithTotal(1999).Build();   // builder (qa/dotnet/skills/test-data-builder)

        await _sut.SubmitAsync(order);                          // SUT produces the record

        // Fresh-group read from the start, bounded consume = the condition-wait. Never a fixed Task.Delay.
        var records = Probe.Records("orders", count: 1, timeout: TimeSpan.FromSeconds(10));

        Assert.That(records, Is.Not.Empty, "no record produced to 'orders' within the poll window");
        var placed = JsonSerializer.Deserialize<OrderPlaced>(records[0].Message.Value)!;
        Assert.That(placed.OrderId, Is.EqualTo(order.Id));      // one logical assertion: the produced fact
    }

    [Test]
    public async Task Should_stamp_the_key_and_eventType_header_When_producing()
    {
        var order = Orders.Pending().Build();

        await _sut.SubmitAsync(order);

        var records = Probe.Records("orders", count: 1, timeout: TimeSpan.FromSeconds(10));

        Assert.That(records, Is.Not.Empty);
        var message = records[0].Message;
        Assert.Multiple(() =>                                   // one behaviour: the record envelope
        {
            Assert.That(message.Key, Is.EqualTo(order.Id.ToString()));   // key drives partition routing
            Assert.That(Encoding.UTF8.GetString(message.Headers.GetLastBytes("eventType")),
                Is.EqualTo("OrderPlaced"));
        });
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **produces an input record**, lets the consumer run, and waits for the
observable side-effect — eventually consistent, so poll a probe on a condition. This reuses
`qa-db-testing-client-dotnet`'s `WaitForAsync` verbatim.

```csharp
[Test]
public async Task Should_write_a_shipment_row_When_an_OrderPaid_record_is_consumed()
{
    var orderId = Guid.NewGuid();

    // 1. Produce the input record onto the topic the consumer subscribes to. Await → flushed.
    using (var producer = NewProducer())
    {
        await producer.ProduceAsync("orders", new Message<string, string>
        {
            Key = orderId.ToString(),
            Value = JsonSerializer.Serialize(new OrderPaid(orderId)),
        });
    }

    // 2. The SUT consumer is already running and picks it up.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
    var shipment = await WaitFor.Async(
        probe:     ct => _shipmentsProbe.GetByOrderId(orderId, ct),
        predicate: s  => s.Status == "Ready",
        timeout:   TimeSpan.FromSeconds(10),
        interval:  TimeSpan.FromMilliseconds(200));

    Assert.That(shipment.OrderId, Is.EqualTo(orderId));        // one logical assertion: the side-effect
}
```

The `WaitFor.Async` helper is the same bounded poll as `qa-db-testing-client-dotnet` and #28/#29 — included so
the node is self-contained:

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
> `await Task.Delay(5000)` standing in for "the record probably arrived by now". The difference: the helper
> returns the instant the condition holds and *fails* if it never does; a bare sleep races the broker.

## Offsets, consumer groups & commit semantics

The defining Kafka behaviour: **consuming doesn't remove the record; committing an offset only marks your
group's position.** A *different* group, or the same group reset to `Earliest`, re-reads the whole log. Tests
exploit this — the probe always uses a **fresh group**, so it sees every record regardless of what the SUT's
group has committed.

```csharp
[Test]
public async Task Should_let_a_fresh_group_reread_the_whole_log_When_a_prior_group_already_consumed()
{
    using (var producer = NewProducer())
        await producer.ProduceAsync("orders",
            new Message<string, string> { Key = "k1", Value = """{"orderId":"a"}""" });

    // Group A reads — the record is NOT deleted.
    var groupA = Probe.Records("orders", count: 1, timeout: TimeSpan.FromSeconds(10));
    Assert.That(groupA, Has.Count.EqualTo(1));

    // A brand-new group at Earliest still sees the same record — the log was never drained.
    var groupB = Probe.Records("orders", count: 1, timeout: TimeSpan.FromSeconds(10));
    Assert.That(groupB, Has.Count.EqualTo(1));   // proof: Kafka is a re-readable log, not a consume-and-destroy queue
}
```

When the **SUT consumer** commits manually (`EnableAutoCommit=false` + `Commit(result)` after processing), the
behaviour you assert is the *side-effect* (pattern 2), not the offset — offsets are the consumer's bookkeeping,
the row/record is the contract.

## Keys → partition routing & per-key ordering

A record's **key** is hashed to a partition, so same-key records share a partition and keep their order. This
is the ordering primitive — assert it directly.

```csharp
private record Seq(int Seq);

[Test]
public async Task Should_keep_per_key_ordering_When_records_share_a_key()
{
    using (var producer = NewProducer())
        for (var i = 1; i <= 3; i++)
            await producer.ProduceAsync("orders",
                new Message<string, string> { Key = "cust-42", Value = $$"""{"seq":{{i}}}""" });

    var records = Probe.Records("orders", count: 3, timeout: TimeSpan.FromSeconds(10));

    Assert.That(records, Has.Count.EqualTo(3));
    Assert.Multiple(() =>
    {
        Assert.That(records.Select(r => r.Partition.Value).Distinct().Count(),
            Is.EqualTo(1));                                  // same key → same partition
        Assert.That(records.Select(r => JsonSerializer.Deserialize<Seq>(r.Message.Value)!.Seq),
            Is.EqualTo(new[] { 1, 2, 3 }));                  // order preserved within the partition
    });
}
```

> Records with **different** keys may land on different partitions and arrive **interleaved** — never assert a
> total order across a multi-partition topic. Order is a *per-partition* (per-key) guarantee only.

## App-level dead-letter topic (DLT) — a convention, not a broker feature

Kafka has **no broker DLQ**. When the SUT consumer can't process a record, its **error handler produces the
record to a separate `<topic>.DLT` topic**. The test seeds a poison record and asserts it lands on the DLT —
exactly the same shape as #28/#29's DLQ assertion, but the dead-lettering is **app code**, not the broker.

```csharp
[Test]
public async Task Should_route_the_poison_record_to_the_DLT_When_processing_fails()
{
    using (var producer = NewProducer())
        await producer.ProduceAsync("orders",
            new Message<string, string> { Key = "bad", Value = "{ not valid order json }" });

    // The SUT consumer fails to deserialize/process; its error handler (a catch → ProduceAsync, the .NET
    // analogue of Spring Kafka's DeadLetterPublishingRecoverer) republishes onto the DLT topic.
    var dead = Probe.Records("orders.DLT", count: 1, timeout: TimeSpan.FromSeconds(10));

    Assert.That(dead, Is.Not.Empty, "expected the poison record on the DLT topic");
    Assert.That(dead[0].Message.Value, Does.Contain("not valid order json"));   // the original payload
}
```

> **DLT naming.** The convention is `<topic>.DLT` (Spring Kafka's `DeadLetterPublishingRecoverer` default) or
> `<topic>-dlt` (Spring Kafka `@RetryableTopic` + retry topics). In .NET you pick the destination topic name in
> your error handler — assert on whatever your app produces to. The topic is just another topic you read.

## Receiving a batch / draining

To assert "exactly N records were produced", read with a count and bounded timeout — the probe's consume loop
stops as soon as N arrive (or the deadline passes):

```csharp
var drained = Probe.Records("orders", count: 3, timeout: TimeSpan.FromSeconds(5));
Assert.That(drained, Has.Count.EqualTo(3));      // SUT produced exactly 3
```

(There's no delete step — the records stay in the log; a fresh group re-reads them. Isolation comes from a
**unique topic per fixture**, not from draining.)

## Anti-patterns

- **`await Task.Delay(5000)` before reading / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* the `KafkaProbe` bounded consume loop (`Consume(TimeSpan)`) for the receive
  side, and the `WaitFor.Async` bounded poll for consumer side-effects.
- **A test-side consumer with `AutoOffsetReset.Latest` (or a reused group id).** It starts **after** the
  records the SUT already produced and reads **nothing**, so the assert flakes or fails for the wrong reason.
  *Fix:* a **fresh group id** + **`Earliest`** for every probe read (the `KafkaProbe` does this).
- **Treating an empty consume result as success.** Empty means nothing arrived in the window — a failed
  produce, not a pass. *Fix:* `Assert.That(records, Is.Not.Empty)` (or `Has.Count.EqualTo(n)`) before reading
  values.
- **Asserting a total order across a multi-partition topic.** Different keys → different partitions → records
  interleave. *Fix:* assert order **within a key/partition** only; pin records to one partition with a shared
  key when order is under test.
- **Expecting a broker DLQ.** Kafka has none — an un-handled poison record just sits in the log and the
  consumer may spin on it. *Fix:* assert the **app-level DLT** topic the consumer's error handler produces to.
- **Sharing one topic across parallel test classes.** Because the log isn't drained, leftovers from another
  class show up in your fresh-group read. *Fix:* a **uniquely named topic per fixture** (or per test), and
  `[Parallelizable(ParallelScope.None)]` on the messaging fixtures unless verified isolated.
- **Forgetting to flush the producer.** A fire-and-forget produce may not have reached the broker before the
  assert. *Fix:* `await ProduceAsync(...)` (or `producer.Flush(timeout)`) — a confirm, not a sleep.
- **Hard-coding `BootstrapServers` / SASL creds in a `[Test]`.** *Fix:* surface bootstrap servers from the
  fixture (container) or env (shared cluster); never log secrets.
- **Reaching for Kafka when the dependency is an HTTP call.** *Fix:* `qa-api-mocking-wiremock-dotnet` —
  messaging is for async topics, not request/response fakes.

## Examples

**End-to-end: a consume → process → produce flow, asserted on the output topic, with the poison case routed to
the DLT.**

```csharp
public class FulfilmentConsumerTests : KafkaFixture
{
    [Test]
    public async Task Should_produce_ShipmentReady_When_a_valid_OrderPaid_is_consumed()
    {
        var orderId = Guid.NewGuid();
        using (var producer = NewProducer())
            await producer.ProduceAsync("orders", new Message<string, string>
            {
                Key = orderId.ToString(),
                Value = JsonSerializer.Serialize(new OrderPaid(orderId)),
            });

        // The SUT consumer subscribes to "orders" and produces onto "shipments".
        var ready = Probe.Records("shipments", count: 1, timeout: TimeSpan.FromSeconds(10));

        Assert.That(ready, Is.Not.Empty, "consumer did not produce a ShipmentReady record");
        Assert.That(ready[0].Message.Key, Is.EqualTo(orderId.ToString()));   // correlation key preserved
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` (in `KafkaFixture`) boots the Kafka container once and creates the topics with a known
   partition count; bootstrap servers + the `KafkaProbe` are surfaced.
2. The test produces an input record (awaiting the produce → flushed); the running SUT consumer produces onto
   the output topic.
3. The test reads the output topic with a **fresh-group** probe (the condition-wait) and asserts the
   correlation key was preserved.
4. `[OneTimeTearDown]` disposes the container. (No per-test drain — isolation is by unique topic, since the
   log isn't consumed-and-destroyed.)

**Test-data builder for record payloads (4+ fields → builder, per the global rules).**

```csharp
public static class Orders
{
    public static OrderBuilder Pending() => new OrderBuilder().WithStatus("Pending");
}
// OrderBuilder.WithTotal(...).WithCurrency(...).WithCustomer(...).Build() — see qa/dotnet/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** The `KafkaProbe` bounded consume loop
  (`Consume(TimeSpan)`) for the receive side; `WaitFor.Async` for consumer side-effects. **No bare
  `Task.Delay` / `Thread.Sleep`** as an assertion wait — `Task.Delay` only as the poll cadence inside the
  bounded helper. (`Consume(TimeSpan)` is correctly blocking and bounded — that's the one allowed block.)
- **Every test-side read uses a fresh consumer group + `AutoOffsetReset.Earliest`** so it reads the topic from
  the start (the log isn't drained — `Latest` or a reused group would miss already-produced records).
- The SUT's producer/consumer is **constructor-injected** with the bootstrap servers / client — never a static
  client or a bootstrap string read inside a `[Test]`.
- Assert the **fact**, not the absence: an empty consume result is a *failed* produce — `Is.Not.Empty` /
  `Has.Count.EqualTo(n)` before reading values.
- **Order is a per-partition (per-key) guarantee** — never assert a total order across a multi-partition topic.
- **No broker DLQ** — assert the **app-level DLT** topic (`<topic>.DLT` / `<topic>-dlt`) the consumer's error
  handler produces to.
- **Independent tests:** a **uniquely named topic per fixture** (the log isn't consumed-and-destroyed, so a
  shared topic leaks records); `[Parallelizable(ParallelScope.None)]` on messaging fixtures unless isolated.
- **Flush/confirm produces** (`await ProduceAsync(...)` or `Flush`); **dispose** every producer/consumer
  (`Close()` the consumer to leave the group cleanly).
- Local broker = **Kafka/Redpanda via Testcontainers** (pinned image; topics created in `[OneTimeSetUp]`); a
  shared test cluster reads `BootstrapServers` + SASL creds from **env, lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `qa-messaging-testing-kafka-java` — the **canonical** stack, Java 21 / TestNG (`org.apache.kafka:kafka-clients`:
  `KafkaProducer`/`KafkaConsumer`, `consumer.poll(Duration)`, `auto.offset.reset=earliest`, `commitSync`,
  Awaitility for side-effects, `ConfluentKafkaContainer`/`RedpandaContainer`). This file is ported from it.
- `qa-messaging-testing-kafka-typescript` — same skill, Node 20 + TS (`kafkajs`: `consumer.subscribe({
  fromBeginning: true })` + `consumer.run({ eachMessage })` collecting into a buffer, `expect.poll`,
  `@testcontainers/kafka`). Note: kafkajs has **no synchronous poll** — a buffer + `expect.poll` is the port
  of this file's bounded consume loop.
- `qa-messaging-testing-service-bus-dotnet` (#28, the **structure this node is ported from**) — Azure Service
  Bus; **the #30-vs-#28 boundary**: queue + peek-lock settlement + broker DLQ sub-queue vs Kafka log + offsets
  + app-level DLT.
- `qa-messaging-testing-sqs-dotnet` (#29, the immediately prior sibling) — AWS SQS; **the #30-vs-#29 boundary**:
  delete-to-ack + visibility timeout + redrive-policy DLQ vs Kafka commit-offset + re-readable log + app-level
  DLT. Same condition-wait discipline, different broker model.
- `qa-db-testing-client-dotnet` (#3) — the `WaitFor.Async` poll helper and the seeder/probe split reused for
  the consumer side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-environments-dotnet` (#14) — booting the Kafka container; the per-fixture lifecycle and
  readiness-wait discipline (never `Task.Delay`) mirrored here.
- `qa-auth0-test-tokens-dotnet` (#16) — when running against a shared cloud cluster with SASL/OAuth creds; the
  secrets-from-env discipline.
- `qa-api-mocking-wiremock-dotnet` (#22) — the *synchronous* counterpart: fake an HTTP dependency the SUT
  calls. The boundary: WireMock = request/response fake; Kafka = async topic assertions.
- `qa-allure-reporting-dotnet` — attach the consumed record value / DLT payload to the Allure result.
- `qa-test-data-builder-dotnet` — builders/ObjectMother for record payloads with 4+ fields.
