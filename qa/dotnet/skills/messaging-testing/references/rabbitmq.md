# Messaging Testing — RabbitMQ / AMQP (.NET 8 / NUnit) — **canonical stack**

This is the **canonical** stack of the `qa/dotnet/skills/messaging-testing/` node, the **fourth and final
`messaging-testing` sibling** (service-bus → SQS → Kafka → **RabbitMQ**) — building it
**closes the family**. RabbitMQ's clients are **first-class across all three stacks** (there is no single
"native" runtime the way Kafka is JVM-native), so the canonical choice was a judgment call: **.NET leads
here** to keep the `messaging-testing` family **.NET-led for three of its four siblings** (`service-bus`/`sqs` also lead
in .NET), and because `RabbitMQ.Client` v7's fully **async** surface (`CreateChannelAsync` /
`BasicPublishAsync` / `BasicAckAsync` / `AsyncEventingBasicConsumer`) maps cleanly onto the global
**async-all-the-way** rule. The `java` (`com.rabbitmq:amqp-client`, with **Spring AMQP** noted for the
listener/DLX convention) and `typescript` (`amqplib`) siblings are **ported** from this file — all three
clients follow the same connection → channel → declare exchange/queue → publish / consume(ack) model, so
this is a true translate-the-concepts port, not a redesign.

This node **ports the service-bus structure** onto RabbitMQ: the **same two assertion patterns** and the
**same eventual-consistency condition-wait discipline**. Of the four siblings, RabbitMQ sits **closest to
`service-bus`/`sqs`** — it's a **queue broker with per-message manual ack** and a **broker-native dead-letter** path
(unlike Kafka's log + offsets + app-level DLT). What's distinctive is the **AMQP routing topology**:
producers publish to an **exchange** with a **routing key**, and **bindings** route the message to queues.

- **Producer-assert** — the SUT, when exercised, **produced** message X (published it to an exchange).
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has
> no synchronous return you can assert on the next line. The message is in flight; the consumer runs on its
> own schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the
> message (or its effect) to appear, with a bounded timeout — **never `Task.Delay` / `Thread.Sleep`**. This
> is the exact lineage of `qa-db-testing-client-dotnet`'s `WaitForAsync` poll helper and
> `references/service-bus.md`'s condition-wait. RabbitMQ's pull primitive,
> `BasicGetAsync(queue, autoAck)`, returns a message **or `null` immediately** — so the bounded **poll loop**
> around it (get until a message appears, or a deadline passes) *is* the condition-wait; a fixed sleep is not.

## The RabbitMQ model — exchange → binding → queue, manual ack, DLX (read this first)

RabbitMQ is an **AMQP 0-9-1 queue broker**. Its settlement model is close to Service Bus and SQS —
a queue you **consume-and-settle**, with a **broker-native dead-letter** path — but its **routing topology**
is unique and it's where most test mistakes happen:

- **Producers publish to an *exchange*, never directly to a queue.** A publish carries a **routing key**. The
  exchange uses its **bindings** to decide which queue(s) get a copy:
  - **direct** — deliver to queues whose binding key **equals** the routing key.
  - **topic** — binding keys are patterns (`order.*`, `order.#`); routing keys like `order.eu.placed` match.
  - **fanout** — every bound queue gets a copy; routing key ignored (the SNS-fan-out analogue).
  - **headers** — route on message headers instead of the routing key.
- **Routing happens at publish time.** A message published to an exchange with **no matching bound queue** is
  **dropped** (unless published `mandatory: true`, which returns it). **This is the sharpest contrast with
  Kafka's retained log** — RabbitMQ does **not** keep a message for a queue that didn't exist when it was
  published. **Consequence for tests:** to producer-assert, the test queue **must be declared and bound to the
  exchange *before* the SUT publishes**. (See the `RabbitProbe` and producer-assert pattern below.)
- **Manual ack — the consume-and-settle contract.** Consume with **`autoAck: false`**: the broker delivers the
  message and waits for you to settle it.
  - `BasicAckAsync(deliveryTag)` — processed, remove it (the Service Bus `Complete` / SQS `DeleteMessage`
    analogue).
  - `BasicNackAsync(deliveryTag, requeue: true)` / `BasicRejectAsync(deliveryTag, requeue: true)` — failed,
    **put it back** on the queue → redelivered (the peek-lock `Abandon` / SQS visibility-timeout analogue).
  - `BasicNackAsync(deliveryTag, requeue: false)` / `BasicRejectAsync(deliveryTag, requeue: false)` — failed,
    **don't requeue** → routed to the **dead-letter exchange** if one is configured, else discarded.
  - **Un-acked on channel/connection close → automatically requeued and redelivered** (the lock-expiry
    analogue). So an un-settled message is never silently lost — it comes back.
- **Dead-letter exchange (DLX) — broker-native, like `service-bus`/`sqs`'s DLQ, *unlike* Kafka's app-level DLT.** A queue
  declared with the argument **`x-dead-letter-exchange`** (and optionally `x-dead-letter-routing-key`) sends
  its dead-lettered messages — **rejected/nacked with `requeue: false`**, **TTL-expired**, or
  **max-length-dropped** — to that exchange, which routes them to a **dead-letter queue** you assert on. This
  is broker plumbing, not application code (the contrast to assert against Kafka's `<topic>.DLT`).
- **Prefetch / QoS.** `BasicQosAsync(prefetchCount: n)` caps how many un-acked messages the broker hands a
  consumer at once — back-pressure. Rarely the thing under assertion; declare it where the consumer's
  concurrency matters, and otherwise leave it.

## Stack

- .NET 8, C# (nullable reference types on), NUnit 4.x — **async all the way** (`CreateConnectionAsync`,
  `CreateChannelAsync`, `BasicPublishAsync`, `BasicGetAsync`, `BasicAckAsync`; never `.Result` / `.Wait()`)
- `RabbitMQ.Client` v7 (the AMQP client — `ConnectionFactory` / `IConnection` / `IChannel` /
  `AsyncEventingBasicConsumer`). v7 renamed `IModel` → `IChannel` and made the surface fully async; if you're
  on v6 the methods are the synchronous `IModel.BasicPublish` / `BasicAck` — prefer v7 for the async rule.
- `Testcontainers.RabbitMq` (`RabbitMqBuilder`) — boots a **local RabbitMQ broker** and surfaces an AMQP
  connection string
- The SUT's typed publisher/consumer is **constructor-injected** with the connection string (or an injected
  `IConnection`) — never a static connection string read inside a `[Test]`

```
IntegrationTests/
├── Fixtures/
│   └── RabbitMqFixture.cs          ← boots the broker, declares exchanges/queues/bindings, exposes the connection
├── Messaging/
│   ├── RabbitProbe.cs              ← test-side reader: bounded BasicGet poll over a bound test queue (the "drain")
│   └── WaitFor.cs                  ← bounded condition-wait for consumer side-effects
└── OrderPublishingTests.cs
```

## Local broker for tests — RabbitMQ via Testcontainers

There is no in-memory RabbitMQ. For deterministic local + CI tests, run a **real broker in a container** and
point the client at its connection string. The `Testcontainers.RabbitMq` module wires it up, waits for
readiness, and hands you the AMQP URI via `GetConnectionString()`. Reuse the fixture discipline (boot once per fixture; **never `Task.Delay` for readiness** — the module owns
the wait strategy). **Declare the topology — exchanges, queues, bindings — up front in the fixture** (RabbitMQ
auto-declares nothing, and routing happens at publish time, so the bindings must pre-exist).

```csharp
using NUnit.Framework;
using RabbitMQ.Client;
using Testcontainers.RabbitMq;

namespace IntegrationTests.Fixtures;

public abstract class RabbitMqFixture
{
    private RabbitMqContainer _broker = null!;

    // Intent, not the container handle. The connection string is surfaced, never logged.
    protected string ConnectionString { get; private set; } = null!;

    [OneTimeSetUp]
    public async Task StartBrokerAsync()
    {
        // The module declares its own readiness wait strategy. Pin the image tag, never `latest`.
        _broker = new RabbitMqBuilder()
            .WithImage("rabbitmq:3.13-management")
            .Build();
        await _broker.StartAsync();
        ConnectionString = _broker.GetConnectionString();   // amqp://guest:guest@host:port

        await DeclareTopologyAsync();
    }

    [OneTimeTearDown]
    public async Task StopBrokerAsync() => await _broker.DisposeAsync();

    // Declare the AMQP topology once: the order exchange, the consumer's queue (with a DLX), the
    // dead-letter exchange + queue, and the bindings. Routing is at publish time, so this must pre-exist.
    private async Task DeclareTopologyAsync()
    {
        var factory = new ConnectionFactory { Uri = new Uri(ConnectionString) };
        await using var conn = await factory.CreateConnectionAsync();
        await using var channel = await conn.CreateChannelAsync();

        await channel.ExchangeDeclareAsync("orders", ExchangeType.Topic, durable: false, autoDelete: false);
        await channel.ExchangeDeclareAsync("orders.dlx", ExchangeType.Fanout, durable: false, autoDelete: false);

        // The consumer's work queue dead-letters rejected/expired messages to orders.dlx.
        await channel.QueueDeclareAsync("orders.q", durable: false, exclusive: false, autoDelete: false,
            arguments: new Dictionary<string, object?> { ["x-dead-letter-exchange"] = "orders.dlx" });
        await channel.QueueBindAsync("orders.q", "orders", routingKey: "order.#");

        // The dead-letter queue you assert on.
        await channel.QueueDeclareAsync("orders.dlq", durable: false, exclusive: false, autoDelete: false);
        await channel.QueueBindAsync("orders.dlq", "orders.dlx", routingKey: "");   // fanout ignores the key
    }
}
```

> **Cloud / shared test broker alternative.** If your org runs against a real **test** RabbitMQ broker
> instead of a container, read the AMQP URI (and credentials) **from env, lazily** — never hard-code it,
> never log it (cross-link `qa-auth0-test-tokens-dotnet` for the secrets-from-env discipline). A container is
> the default for CI determinism; a shared broker makes tests order-dependent unless each uses a
> **uniquely named queue** (since a queue retains messages until they're consumed).

## The test-side reader — `RabbitProbe` (the "drain" analogue)

The test reads a queue by **polling `BasicGetAsync` in a bounded loop** until a message appears or a deadline
passes — that loop *is* the condition-wait. `BasicGetAsync` is a single synchronous pull (returns a message or
`null` immediately), so the loop, not the call, supplies the wait. The probe acks what it reads so the queue
empties cleanly.

```csharp
using RabbitMQ.Client;

namespace IntegrationTests.Messaging;

public sealed class RabbitProbe
{
    private readonly string _connectionString;

    public RabbitProbe(string connectionString) => _connectionString = connectionString;

    /// Pull one message from `queue` within `timeout`, polling on a bounded loop. Returns the body bytes,
    /// or null if nothing arrived in the window. Acks what it reads (a test probe drains, it doesn't requeue).
    public async Task<byte[]?> GetAsync(string queue, TimeSpan timeout)
    {
        var factory = new ConnectionFactory { Uri = new Uri(_connectionString) };
        await using var conn = await factory.CreateConnectionAsync();
        await using var channel = await conn.CreateChannelAsync();

        using var cts = new CancellationTokenSource(timeout);
        while (!cts.IsCancellationRequested)
        {
            BasicGetResult? result = await channel.BasicGetAsync(queue, autoAck: false);   // single pull
            if (result is not null)
            {
                await channel.BasicAckAsync(result.DeliveryTag, multiple: false);          // drain → ack
                return result.Body.ToArray();
            }
            await Task.Delay(TimeSpan.FromMilliseconds(100), cts.Token);   // poll cadence, not an assertion sleep
        }
        return null;   // nothing arrived in the window → a failed produce, asserted by the caller
    }
}
```

> `Task.Delay` appears **only** as the poll cadence *inside* the bounded loop, between `BasicGet` pulls — never
> as a bare `await Task.Delay(5000)` standing in for "the message probably arrived by now". The loop returns
> the instant a message is there and *fails the assert* (via `Is.Not.Null`) if the window passes empty; a bare
> sleep races the broker.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes to the **exchange**; the test reads the **bound queue** and asserts the body and properties.
Because RabbitMQ routes at publish time, the queue must be **declared and bound before the SUT publishes** —
the fixture's `DeclareTopologyAsync` did that. An empty result means "nothing routed here within the window" —
a failed produce, asserted deterministically.

```csharp
public class OrderPublishingTests : RabbitMqFixture
{
    private RabbitProbe _probe = null!;
    private IConnection _conn = null!;
    private OrderPublisher _sut = null!;   // production code, constructor-injected with the connection

    [SetUp]
    public async Task SetUp()
    {
        _probe = new RabbitProbe(ConnectionString);
        var factory = new ConnectionFactory { Uri = new Uri(ConnectionString) };
        _conn = await factory.CreateConnectionAsync();
        _sut = new OrderPublisher(_conn);   // constructor injection — no static connection
    }

    [TearDown]
    public async Task TearDown() => await _conn.DisposeAsync();

    [Test]
    public async Task Should_publish_OrderPlaced_When_an_order_is_submitted()
    {
        var order = Orders.Pending().WithTotal(1999).Build();   // builder (qa/dotnet/skills/test-data-builder)

        await _sut.SubmitAsync(order);                          // SUT publishes to the "orders" exchange

        // Read the bound test queue; the bounded BasicGet poll is the condition-wait. Never a fixed Task.Delay.
        var body = await _probe.GetAsync("orders.q", TimeSpan.FromSeconds(10));

        Assert.That(body, Is.Not.Null, "no message was routed to 'orders.q' within the wait window");
        var placed = JsonSerializer.Deserialize<OrderPlaced>(body!);
        Assert.That(placed!.OrderId, Is.EqualTo(order.Id));     // one logical assertion: the published fact
    }
}
```

> **Producer-assert with a dedicated probe queue.** If the SUT publishes to an exchange whose only bound queue
> is the *real* consumer's (so reading it would steal the consumer's work), declare an **exclusive,
> auto-delete test queue** bound to the same exchange + routing key in `[SetUp]`, and read *that* — a topic/
> direct exchange delivers a copy to every matching binding, so your probe queue and the real queue each get
> one. (This is the fanout-style "give me my own copy" trick; it only works because the binding pre-exists the
> publish.)

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **publishes an input message**, lets the consumer run, and waits for
the observable side-effect (a DB row, another message) — eventually consistent, so poll a **probe** on a
condition. This reuses `qa-db-testing-client-dotnet`'s `WaitForAsync` verbatim.

```csharp
[Test]
public async Task Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed()
{
    var orderId = Guid.NewGuid();

    // 1. Publish the input message to the exchange the consumer's queue is bound to.
    await using var channel = await _conn.CreateChannelAsync();
    var props = new BasicProperties { ContentType = "application/json", CorrelationId = orderId.ToString() };
    await channel.BasicPublishAsync(
        exchange: "orders", routingKey: "order.paid", mandatory: false,
        basicProperties: props, body: JsonSerializer.SerializeToUtf8Bytes(new OrderPaid(orderId)));

    // 2. The SUT (an AsyncEventingBasicConsumer-based consumer) is already running and picks it up.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
    var shipment = await WaitFor.Async(
        probe:     ct => _shipmentsProbe.GetByOrderId(orderId, ct),
        predicate: s  => s.Status == "Ready",
        timeout:   TimeSpan.FromSeconds(10),
        interval:  TimeSpan.FromMilliseconds(200));

    Assert.That(shipment.OrderId, Is.EqualTo(orderId));         // one logical assertion: the side-effect
}
```

The `WaitFor.Async` helper is the same bounded poll as `qa-db-testing-client-dotnet` — included here so the
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

## Manual ack / nack / reject — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs with
**`autoAck: false`** and explicitly settles each message. The settlement choice is what later DLX assertions
depend on, so model it the way production does:

| Outcome | Call | Effect |
|---------|------|--------|
| Processed OK | `BasicAckAsync(tag)` | Remove the message (the `Complete` / `DeleteMessage` analogue) |
| Transient failure, retry | `BasicNackAsync(tag, requeue: true)` | Put it back → redelivered (the `Abandon` / visibility-timeout analogue) |
| Permanent failure, dead-letter | `BasicNackAsync(tag, requeue: false)` | Don't requeue → routed to the DLX (or discarded if none) |
| Single-message reject | `BasicRejectAsync(tag, requeue: false)` | Like nack, but exactly one message |

```csharp
// Consumer settlement — manual ack on an AsyncEventingBasicConsumer:
await using var channel = await _conn.CreateChannelAsync();
await channel.BasicQosAsync(prefetchSize: 0, prefetchCount: 10, global: false);   // back-pressure (optional)

var consumer = new AsyncEventingBasicConsumer(channel);
consumer.ReceivedAsync += async (_, ea) =>
{
    if (CanProcess(ea.Body))
        await channel.BasicAckAsync(ea.DeliveryTag, multiple: false);             // done — remove it
    else
        await channel.BasicNackAsync(ea.DeliveryTag, multiple: false, requeue: false);  // → dead-letter exchange
};
await channel.BasicConsumeAsync("orders.q", autoAck: false, consumer);
```

> **Un-acked messages come back.** If a consumer reads with `autoAck: false` and the channel closes before it
> acks, the broker **requeues** the message — so a crashed consumer never silently loses work. In tests this
> means: ack (or nack) every message you consume, or you'll see it **redelivered** into the next test. The
> redelivery is also *assertable* — `ea.Redelivered` is `true` on a second delivery.

## Dead-letter-exchange assertions

A common, high-value assertion: **a message that failed processing landed in the dead-letter queue.** The
work queue was declared with `x-dead-letter-exchange = orders.dlx` (fixture topology), so a
`BasicNackAsync(..., requeue: false)` / `BasicRejectAsync(..., requeue: false)` — or a TTL expiry, or a
max-length drop — routes the message through the DLX to `orders.dlq`. Read **that** queue:

```csharp
[Test]
public async Task Should_dead_letter_the_message_When_the_order_payload_is_invalid()
{
    await using var channel = await _conn.CreateChannelAsync();
    var props = new BasicProperties { ContentType = "application/json" };
    await channel.BasicPublishAsync(
        exchange: "orders", routingKey: "order.paid", mandatory: false,
        basicProperties: props, body: Encoding.UTF8.GetBytes("{ not valid order json }"));

    // The consumer (SUT) rejects it with requeue:false → it routes through orders.dlx to orders.dlq.
    // Bounded BasicGet poll the DLQ — wait on the condition (a message lands), not a sleep.
    var dead = await _probe.GetAsync("orders.dlq", TimeSpan.FromSeconds(10));

    Assert.That(dead, Is.Not.Null, "expected the poison message in the dead-letter queue");
    Assert.That(Encoding.UTF8.GetString(dead!), Does.Contain("not valid order json"));   // the original payload
}
```

> RabbitMQ adds an `x-death` header (count, reason — `rejected` / `expired` / `maxlen` — original exchange and
> routing key) to a dead-lettered message. Assert on `x-death` when you need to prove **why** it was
> dead-lettered, not just that it landed.

## Exchanges, routing keys & bindings

The AMQP routing model is the distinctive part. Assert the **routing**, not just the publish — that a message
with routing key K reached the queues bound for K, and didn't reach the ones that weren't.

```csharp
[Test]
public async Task Should_route_only_eu_orders_to_the_eu_queue_When_publishing_by_region()
{
    await using var channel = await _conn.CreateChannelAsync();
    // Topic exchange "orders"; eu.q bound with "order.eu.*", us.q bound with "order.us.*" (in fixture setup).

    await channel.BasicPublishAsync("orders", routingKey: "order.eu.placed", mandatory: false,
        basicProperties: new BasicProperties(), body: JsonSerializer.SerializeToUtf8Bytes(new OrderPlaced(Guid.NewGuid())));

    var toEu = await _probe.GetAsync("orders.eu.q", TimeSpan.FromSeconds(10));
    var toUs = await _probe.GetAsync("orders.us.q", TimeSpan.FromSeconds(2));   // short window — expect nothing

    Assert.Multiple(() =>                                   // one behaviour: the topic routing
    {
        Assert.That(toEu, Is.Not.Null, "EU order did not reach the EU queue");
        Assert.That(toUs, Is.Null,     "EU order was wrongly routed to the US queue");
    });
}
```

A **fanout** exchange (routing key ignored) is the broadcast / SNS-fan-out analogue — every bound queue gets a
copy; assert each one received it. A **direct** exchange routes on an exact routing-key match.

## Receiving a batch / draining

To assert "exactly N messages were produced", pull in a bounded loop and count — the timeout stops it hanging
when fewer than N arrive. (Extend `RabbitProbe` with a `GetManyAsync(queue, max, timeout)` that loops
`BasicGetAsync` until `max` or the deadline; it acks each.)

```csharp
var batch = await _probe.GetManyAsync("orders.q", max: 10, timeout: TimeSpan.FromSeconds(5));
Assert.That(batch, Has.Count.EqualTo(3));                   // SUT produced exactly 3
```

## Anti-patterns

- **`await Task.Delay(5000)` before reading / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* the `RabbitProbe` bounded `BasicGetAsync` poll for the receive side, and the
  `WaitFor.Async` bounded poll for consumer side-effects — each returns the instant the condition holds and
  *fails* if it never does.
- **Publishing before the test queue is declared and bound.** RabbitMQ routes at publish time and **drops**
  a message with no matching bound queue — the probe then reads nothing and the assert flakes for the wrong
  reason. *Fix:* declare exchanges/queues/bindings in `[OneTimeSetUp]` (the fixture topology) **before** any
  publish; for a dedicated probe queue, bind it in `[SetUp]`.
- **Consuming with `autoAck: true` when testing settlement.** The broker removes the message on delivery, so
  you can't assert ack-vs-nack-vs-dead-letter or redelivery. *Fix:* `autoAck: false` and settle explicitly.
- **Leaving a consumed message un-acked across tests.** On channel close the broker **requeues** it, and the
  next test sees a "phantom" redelivery. *Fix:* ack (or nack) every message; the `RabbitProbe` acks what it
  drains.
- **Expecting an app-level DLT topic (the Kafka habit).** RabbitMQ dead-lettering is **broker-native** — a
  `x-dead-letter-exchange` queue argument, not application code. *Fix:* declare the DLX + DLQ in the topology
  and assert the **DLQ**; don't look for a `<topic>.DLT`.
- **Treating a `null` `BasicGet` result as success.** `null` means nothing was on the queue in the window —
  that's a failed produce, not a pass. *Fix:* `Assert.That(body, Is.Not.Null, ...)` before deserializing.
- **Sharing one queue across parallel test classes.** Competing consumers steal each other's messages; asserts
  go non-deterministic. *Fix:* a **uniquely named queue per fixture** (or `[Parallelizable(ParallelScope.None)]`
  on the messaging fixtures), and drain leftovers in `[SetUp]`.
- **Reading the connection string inside a `[Test]` / hard-coding it.** *Fix:* surface it from the fixture
  (container) or env (shared broker), inject it; never log it.

## Examples

**End-to-end: a consume → process → publish flow, asserted on the output queue, with the poison case routed to
the DLQ.**

```csharp
public class FulfilmentConsumerTests : RabbitMqFixture
{
    private RabbitProbe _probe = null!;
    private IConnection _conn = null!;

    [SetUp]
    public async Task SetUp()
    {
        _probe = new RabbitProbe(ConnectionString);
        var factory = new ConnectionFactory { Uri = new Uri(ConnectionString) };
        _conn = await factory.CreateConnectionAsync();
        await DrainAsync("orders.q");                 // independent tests — start from empty
        await DrainAsync("shipments.q");
    }

    [TearDown]
    public async Task TearDown() => await _conn.DisposeAsync();

    [Test]
    public async Task Should_publish_ShipmentReady_When_a_valid_OrderPaid_is_consumed()
    {
        var orderId = Guid.NewGuid();
        await using var channel = await _conn.CreateChannelAsync();
        var props = new BasicProperties { ContentType = "application/json", CorrelationId = orderId.ToString() };
        await channel.BasicPublishAsync("orders", "order.paid", mandatory: false,
            basicProperties: props, body: JsonSerializer.SerializeToUtf8Bytes(new OrderPaid(orderId)));

        // The SUT consumer processes "orders.q" and publishes onto the "shipments" exchange → "shipments.q".
        var ready = await _probe.GetAsync("shipments.q", TimeSpan.FromSeconds(10));

        Assert.That(ready, Is.Not.Null, "consumer did not publish a ShipmentReady message");
        var shipment = JsonSerializer.Deserialize<ShipmentReady>(ready!);
        Assert.That(shipment!.OrderId, Is.EqualTo(orderId));   // correlation preserved
    }

    private async Task DrainAsync(string queue)
    {
        while (await _probe.GetAsync(queue, TimeSpan.FromMilliseconds(300)) is not null) { }
    }
}
```

Lifecycle for this test:
1. `[OneTimeSetUp]` (in `RabbitMqFixture`) boots the broker once and declares the exchanges/queues/bindings;
   the connection string is surfaced.
2. `[SetUp]` opens a connection and drains the queues so the test starts from empty — tests stay independent
   and order-free.
3. The test publishes an input message; the running SUT consumer publishes onto the output exchange; the test
   **polls** the output queue (the condition-wait) and asserts correlation was preserved.
4. `[TearDown]` disposes the connection; `[OneTimeTearDown]` disposes the broker.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```csharp
public static class Orders
{
    public static OrderBuilder Pending() => new OrderBuilder().WithStatus("Pending");
}
// OrderBuilder.WithTotal(...).WithCurrency(...).WithCustomer(...).Build() — see qa/dotnet/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** The `RabbitProbe` bounded `BasicGetAsync`
  poll for the receive side; `WaitFor.Async` for consumer side-effects. **No bare `Task.Delay` /
  `Thread.Sleep`** as an assertion wait — `Task.Delay` only as the poll cadence inside the bounded helper.
- **Declare the topology before publishing.** Exchanges, queues, and bindings in `[OneTimeSetUp]` (or a probe
  queue in `[SetUp]`) — RabbitMQ routes at publish time and drops messages with no matching bound queue.
- The SUT's publisher/consumer is **constructor-injected** with the `IConnection` / connection string —
  never a static connection or a connection string read inside a `[Test]`.
- **Consume with `autoAck: false` and settle every message** (`BasicAck` / `BasicNack` / `BasicReject`).
  Never leave a message un-acked into the next test — it requeues and redelivers.
- **Dead-lettering is broker-native** — declare `x-dead-letter-exchange` + a DLX + a dead-letter queue and
  assert the **DLQ**; don't expect a Kafka-style app-level DLT.
- Assert the **fact**, not the absence: a `null` `BasicGet` result is a *failed* produce — assert
  `Is.Not.Null` before reading the body.
- **Async all the way** — `await` every RabbitMQ call; `await using` connections/channels; never `.Result` /
  `.Wait()`.
- **Independent tests:** a uniquely named queue per fixture **or** drain-to-empty in `[SetUp]`; integration
  fixtures `[Parallelizable(ParallelScope.None)]` unless verified isolated.
- Local broker = **RabbitMQ via Testcontainers** (pinned image); a shared test broker's AMQP URI/credentials
  come from **env, read lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code.

## Cross-references

- `qa-messaging-testing-java` — same skill, Java 21 / TestNG (`com.rabbitmq:amqp-client`:
  `ConnectionFactory().setUri(...)`, `conn.createChannel()`, `exchangeDeclare` / `queueDeclare(..., args)` /
  `queueBind`, `basicPublish`, `basicConsume(queue, false, callback)` + `basicAck`/`basicNack`/`basicReject`,
  `basicGet` polling, Awaitility for side-effects; **Spring AMQP** `RabbitTemplate` + `@RabbitListener` +
  `QueueBuilder.deadLetterExchange(...)` noted for the listener/DLX convention; `RabbitMQContainer`). Structure
  ported, not code.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`amqplib`: `amqp.connect(url)`,
  `conn.createChannel()`, `assertExchange` / `assertQueue(..., { arguments: { 'x-dead-letter-exchange' } })` /
  `bindQueue`, `channel.publish`, `channel.consume(q, cb, { noAck: false })` + `channel.ack`/`nack`/`reject`,
  `channel.get` polling, `expect.poll` for side-effects, `@testcontainers/rabbitmq` `RabbitMQContainer`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure Service
  Bus; **the `rabbitmq`-vs-`service-bus` parallel**: RabbitMQ's manual ack + broker-native DLX is the **closest** of the three
  siblings to Service Bus's peek-lock + DLQ sub-queue — same consume-and-settle shape, different routing model.
- `references/sqs.md` — AWS SQS; same parallel (delete-to-ack + redrive-policy DLQ ≈
  RabbitMQ's ack + DLX). Same condition-wait discipline, different broker.
- `references/kafka.md` (`kafka`, the immediately prior sibling) — **the `rabbitmq`-vs-`kafka` boundary**:
  Kafka log + offsets + app-level DLT vs RabbitMQ queue + manual ack + broker-native DLX.
- `qa-db-testing-client-dotnet` — the `WaitFor.Async` poll helper and the seeder/probe split reused for
  the consumer side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-auth0-test-tokens-dotnet` — when authing to a shared cloud broker with credentials from env; the
  secrets-from-env discipline.
- `qa-allure-reporting-dotnet` — attach the received message body / DLQ `x-death` reason to the Allure result.
- `qa-test-data-builder-dotnet` — builders/ObjectMother for message payloads with 4+ fields.
