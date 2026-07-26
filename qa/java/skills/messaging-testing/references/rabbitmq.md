# Messaging Testing — RabbitMQ / AMQP (Java 21 / TestNG)

This is the **Java** sibling of the `qa/java/skills/messaging-testing/` node, the **fourth and final
`messaging-testing` sibling** (service-bus → SQS → Kafka → **RabbitMQ**) — building it
**closes the family**. The **canonical stack is .NET** (`qa-messaging-testing-dotnet`): RabbitMQ's
clients are first-class across all three stacks, so .NET was chosen to keep the family .NET-led for three of
its four siblings. This file is a **direct port** — same section order, same concepts, re-expressed in Java
21 / TestNG idioms with `com.rabbitmq:amqp-client` (and **Spring AMQP** noted for the listener/DLX
convention). Java's RabbitMQ client is itself the canonical/reference client, so the API maps one-to-one.

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
> message (or its effect) to appear, with a bounded timeout — **never `Thread.sleep`**. This is the exact
> lineage of `qa-db-connection-java`'s Awaitility usage and `references/service-bus.md`'s
> condition-wait. RabbitMQ's pull primitive, `channel.basicGet(queue, autoAck)`, returns a `GetResponse`
> **or `null` immediately** — so the bounded **poll loop** around it (get until a message appears, or a
> deadline passes) *is* the condition-wait; a fixed sleep is not.

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
  **dropped** (unless published `mandatory=true`, which returns it). **This is the sharpest contrast with
  Kafka's retained log** — RabbitMQ does **not** keep a message for a queue that didn't exist when it was
  published. **Consequence for tests:** to producer-assert, the test queue **must be declared and bound to the
  exchange *before* the SUT publishes**. (See the `RabbitProbe` and producer-assert pattern below.)
- **Manual ack — the consume-and-settle contract.** Consume with **`autoAck=false`**: the broker delivers the
  message and waits for you to settle it.
  - `basicAck(deliveryTag, multiple)` — processed, remove it (the Service Bus `complete` / SQS `deleteMessage`
    analogue).
  - `basicNack(deliveryTag, multiple, requeue=true)` / `basicReject(deliveryTag, requeue=true)` — failed,
    **put it back** on the queue → redelivered (the peek-lock `abandon` / SQS visibility-timeout analogue).
  - `basicNack(deliveryTag, multiple, requeue=false)` / `basicReject(deliveryTag, requeue=false)` — failed,
    **don't requeue** → routed to the **dead-letter exchange** if one is configured, else discarded.
  - **Un-acked on channel/connection close → automatically requeued and redelivered** (the lock-expiry
    analogue). So an un-settled message is never silently lost — it comes back.
- **Dead-letter exchange (DLX) — broker-native, like `service-bus`/`sqs`'s DLQ, *unlike* Kafka's app-level DLT.** A queue
  declared with the argument **`x-dead-letter-exchange`** (and optionally `x-dead-letter-routing-key`) sends
  its dead-lettered messages — **rejected/nacked with `requeue=false`**, **TTL-expired**, or
  **max-length-dropped** — to that exchange, which routes them to a **dead-letter queue** you assert on. This
  is broker plumbing, not application code (the contrast to assert against Kafka's `<topic>.DLT`).
- **Prefetch / QoS.** `basicQos(prefetchCount)` caps how many un-acked messages the broker hands a consumer at
  once — back-pressure. Rarely the thing under assertion; declare it where the consumer's concurrency matters,
  and otherwise leave it.

## Stack

- Java 21 + TestNG + AssertJ (`org.testng:testng`, `org.assertj:assertj-core`) + Awaitility
  (`org.awaitility:awaitility`)
- `com.rabbitmq:amqp-client` (the AMQP client — `ConnectionFactory` / `Connection` / `Channel` /
  `DeliverCallback`). This is the canonical/reference RabbitMQ client; **Spring AMQP**
  (`org.springframework.amqp:spring-rabbit`) is noted **only** for the listener/DLX convention
  (`RabbitTemplate`, `@RabbitListener`, `QueueBuilder.deadLetterExchange(...)`) — the assertion code stays on
  plain `amqp-client`.
- `org.testcontainers:rabbitmq` (`RabbitMQContainer`) — boots a **local RabbitMQ broker** and surfaces
  `getAmqpUrl()`
- The SUT's typed publisher/consumer is **constructor-injected** with the AMQP URL (or an injected
  `Connection`) — never a static URL read inside an `@Test`

```
src/test/java/.../messaging/
├── RabbitMqTestBase.java   ← boots the broker, declares exchanges/queues/bindings, exposes the AMQP URL + a probe
├── RabbitProbe.java        ← test-side reader: bounded basicGet poll over a bound test queue (the "drain")
└── OrderPublishingTest.java
```

## Local broker for tests — RabbitMQ via Testcontainers

There is no in-memory RabbitMQ. For deterministic local + CI tests, run a **real broker in a container** and
point the client at `getAmqpUrl()`. The `org.testcontainers:rabbitmq` module wires it up, waits for readiness,
and exposes the AMQP URL. Reuse the standard Testcontainers fixture discipline (boot once per class;
**never `Thread.sleep` for readiness** — the container owns the wait strategy). **Declare the topology —
exchanges, queues, bindings — up front** (RabbitMQ auto-declares nothing, and routing happens at publish time,
so the bindings must pre-exist).

```java
import com.rabbitmq.client.*;
import org.testcontainers.containers.RabbitMQContainer;
import org.testcontainers.utility.DockerImageName;
import org.testng.annotations.*;

import java.util.Map;

public abstract class RabbitMqTestBase {

    // Pin the image tag, never `latest`. The container declares its own readiness wait strategy.
    private final RabbitMQContainer broker =
            new RabbitMQContainer(DockerImageName.parse("rabbitmq:3.13-management"));

    protected String amqpUrl;
    protected RabbitProbe probe;

    @BeforeClass(alwaysRun = true)
    public void startBroker() throws Exception {
        broker.start();
        amqpUrl = broker.getAmqpUrl();   // amqp://guest:guest@host:port
        probe = new RabbitProbe(amqpUrl);
        declareTopology();
    }

    @AfterClass(alwaysRun = true)
    public void stopBroker() { broker.stop(); }

    // Declare the AMQP topology once: the order exchange, the consumer's queue (with a DLX), the
    // dead-letter exchange + queue, and the bindings. Routing is at publish time, so this must pre-exist.
    private void declareTopology() throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setUri(amqpUrl);
        try (Connection conn = factory.newConnection(); Channel channel = conn.createChannel()) {
            channel.exchangeDeclare("orders", BuiltinExchangeType.TOPIC, false);
            channel.exchangeDeclare("orders.dlx", BuiltinExchangeType.FANOUT, false);

            // The consumer's work queue dead-letters rejected/expired messages to orders.dlx.
            channel.queueDeclare("orders.q", false, false, false,
                    Map.of("x-dead-letter-exchange", "orders.dlx"));
            channel.queueBind("orders.q", "orders", "order.#");

            // The dead-letter queue you assert on.
            channel.queueDeclare("orders.dlq", false, false, false, null);
            channel.queueBind("orders.dlq", "orders.dlx", "");   // fanout ignores the routing key
        }
    }

    protected Connection newConnection() throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setUri(amqpUrl);
        return factory.newConnection();
    }
}
```

> **Cloud / shared test broker alternative.** If your org runs against a real **test** RabbitMQ broker instead
> of a container, read the AMQP URI (and credentials) **from env, lazily** — never hard-code it, never log it
> (cross-link `qa-test-login-tokens-java` for the secrets-from-env discipline). A container is the default for
> CI determinism; a shared broker makes tests order-dependent unless each uses a **uniquely named queue**
> (since a queue retains messages until they're consumed).

## The test-side reader — `RabbitProbe` (the "drain" analogue)

The test reads a queue by **polling `basicGet` in a bounded loop** until a message appears or a deadline
passes — that loop *is* the condition-wait. `basicGet` is a single synchronous pull (returns a `GetResponse`
or `null` immediately), so the loop, not the call, supplies the wait. The probe acks what it reads so the
queue empties cleanly.

```java
import com.rabbitmq.client.*;

import java.time.*;

public final class RabbitProbe {

    private final String amqpUrl;

    public RabbitProbe(String amqpUrl) { this.amqpUrl = amqpUrl; }

    /** Pull one message from `queue` within `timeout`, polling on a bounded loop. Returns the body bytes,
     *  or null if nothing arrived in the window. Acks what it reads (a test probe drains, it doesn't requeue). */
    public byte[] get(String queue, Duration timeout) throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setUri(amqpUrl);
        try (Connection conn = factory.newConnection(); Channel channel = conn.createChannel()) {
            Instant deadline = Instant.now().plus(timeout);
            while (Instant.now().isBefore(deadline)) {
                GetResponse response = channel.basicGet(queue, false);   // single pull, autoAck=false
                if (response != null) {
                    channel.basicAck(response.getEnvelope().getDeliveryTag(), false);   // drain → ack
                    return response.getBody();
                }
                Thread.sleep(100);   // poll cadence, not an assertion sleep (the only Thread.sleep allowed)
            }
        }
        return null;   // nothing arrived in the window → a failed produce, asserted by the caller
    }
}
```

> The `Thread.sleep(100)` is the **poll cadence between pulls inside a bounded loop** — never a bare
> `Thread.sleep(5000)` standing in for "the message probably arrived by now". The loop returns the instant a
> message is there and *fails the assert* (via `isNotNull()`) if the window passes empty; a bare sleep races
> the broker. (If you prefer no `Thread.sleep` at all, drive the loop with Awaitility's `await().until(...)`.)

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes to the **exchange**; the test reads the **bound queue** and asserts the body and properties.
Because RabbitMQ routes at publish time, the queue must be **declared and bound before the SUT publishes** —
the base class's `declareTopology` did that. An empty result means "nothing routed here within the window" — a
failed produce, asserted deterministically.

```java
import static org.assertj.core.api.Assertions.assertThat;

public class OrderPublishingTest extends RabbitMqTestBase {

    private Connection conn;
    private OrderPublisher sut;     // production code, constructor-injected with the connection

    @BeforeMethod(alwaysRun = true)
    public void setUp() throws Exception {
        conn = newConnection();
        sut = new OrderPublisher(conn);   // constructor injection — no static connection
    }

    @AfterMethod(alwaysRun = true)
    public void tearDown() throws Exception { conn.close(); }

    @Test
    public void Should_publish_OrderPlaced_When_an_order_is_submitted() throws Exception {
        Order order = Orders.pending().withTotal(1999).build();   // builder (qa/java/skills/test-data-builder)

        sut.submit(order);                                        // SUT publishes to the "orders" exchange

        // Read the bound test queue; the bounded basicGet poll is the condition-wait. Never a fixed sleep.
        byte[] body = probe.get("orders.q", Duration.ofSeconds(10));

        assertThat(body).as("a message routed to 'orders.q' within the wait window").isNotNull();
        OrderPlaced placed = Json.parse(body, OrderPlaced.class);
        assertThat(placed.orderId()).isEqualTo(order.id());       // one logical assertion: the published fact
    }
}
```

> **Producer-assert with a dedicated probe queue.** If the SUT publishes to an exchange whose only bound queue
> is the *real* consumer's (so reading it would steal the consumer's work), declare an **exclusive,
> auto-delete test queue** bound to the same exchange + routing key in `@BeforeMethod`, and read *that* — a
> topic/direct exchange delivers a copy to every matching binding, so your probe queue and the real queue each
> get one. (This is the fanout-style "give me my own copy" trick; it only works because the binding pre-exists
> the publish.)

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer** (a `DeliverCallback` loop or a Spring `@RabbitListener`). The test **publishes
an input message**, lets the consumer run, and waits for the observable side-effect (a DB row, another
message) — eventually consistent, so use **Awaitility** to poll a probe on a condition. This reuses
`qa-db-connection-java`'s discipline verbatim.

```java
import static org.awaitility.Awaitility.await;

@Test
public void Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed() throws Exception {
    UUID orderId = UUID.randomUUID();

    // 1. Publish the input message to the exchange the consumer's queue is bound to.
    try (Channel channel = conn.createChannel()) {
        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                .contentType("application/json").correlationId(orderId.toString()).build();
        channel.basicPublish("orders", "order.paid", props, Json.write(new OrderPaid(orderId)));
    }

    // 2. The SUT consumer is already running and picks it up.

    // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
    await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(200))
            .untilAsserted(() -> {
                Shipment shipment = shipmentsProbe.getByOrderId(orderId);
                assertThat(shipment).isNotNull();
                assertThat(shipment.status()).isEqualTo("Ready");   // one logical assertion: the side-effect
            });
}
```

> Awaitility polls the probe and returns the instant the condition holds, failing if it never does. That is
> the condition-wait — **never** a bare `Thread.sleep(5000)` standing in for "the message probably arrived by
> now", which races the broker.

## Manual ack / nack / reject — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs with
**`autoAck=false`** and explicitly settles each message. The settlement choice is what later DLX assertions
depend on, so model it the way production does:

| Outcome | Call | Effect |
|---------|------|--------|
| Processed OK | `basicAck(tag, false)` | Remove the message (the `complete` / `deleteMessage` analogue) |
| Transient failure, retry | `basicNack(tag, false, true)` | Put it back → redelivered (the `abandon` / visibility-timeout analogue) |
| Permanent failure, dead-letter | `basicNack(tag, false, false)` | Don't requeue → routed to the DLX (or discarded if none) |
| Single-message reject | `basicReject(tag, false)` | Like nack, but exactly one message |

```java
// Consumer settlement — manual ack via a DeliverCallback:
Channel channel = conn.createChannel();
channel.basicQos(10);   // prefetch — back-pressure (optional)

DeliverCallback onDeliver = (consumerTag, delivery) -> {
    long tag = delivery.getEnvelope().getDeliveryTag();
    if (canProcess(delivery.getBody()))
        channel.basicAck(tag, false);                       // done — remove it
    else
        channel.basicNack(tag, false, false);               // → dead-letter exchange
};
channel.basicConsume("orders.q", false, onDeliver, consumerTag -> { });   // autoAck=false
```

> **Un-acked messages come back.** If a consumer reads with `autoAck=false` and the channel closes before it
> acks, the broker **requeues** the message — so a crashed consumer never silently loses work. In tests this
> means: ack (or nack) every message you consume, or you'll see it **redelivered** into the next test. The
> redelivery is also *assertable* — `delivery.getEnvelope().isRedeliver()` is `true` on a second delivery.

## Dead-letter-exchange assertions

A common, high-value assertion: **a message that failed processing landed in the dead-letter queue.** The work
queue was declared with `x-dead-letter-exchange = orders.dlx` (base-class topology), so a
`basicNack(..., false)` / `basicReject(..., false)` — or a TTL expiry, or a max-length drop — routes the
message through the DLX to `orders.dlq`. Read **that** queue:

```java
@Test
public void Should_dead_letter_the_message_When_the_order_payload_is_invalid() throws Exception {
    try (Channel channel = conn.createChannel()) {
        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder().contentType("application/json").build();
        channel.basicPublish("orders", "order.paid", props,
                "{ not valid order json }".getBytes(StandardCharsets.UTF_8));
    }

    // The consumer (SUT) rejects it with requeue=false → it routes through orders.dlx to orders.dlq.
    // Bounded basicGet poll the DLQ — wait on the condition (a message lands), not a sleep.
    byte[] dead = probe.get("orders.dlq", Duration.ofSeconds(10));

    assertThat(dead).as("the poison message in the dead-letter queue").isNotNull();
    assertThat(new String(dead, StandardCharsets.UTF_8)).contains("not valid order json");   // original payload
}
```

> RabbitMQ adds an `x-death` header (count, reason — `rejected` / `expired` / `maxlen` — original exchange and
> routing key) to a dead-lettered message. Read it from `response.getProps().getHeaders().get("x-death")` when
> you need to prove **why** it was dead-lettered, not just that it landed.

## Exchanges, routing keys & bindings

The AMQP routing model is the distinctive part. Assert the **routing**, not just the publish — that a message
with routing key K reached the queues bound for K, and didn't reach the ones that weren't.

```java
@Test
public void Should_route_only_eu_orders_to_the_eu_queue_When_publishing_by_region() throws Exception {
    // Topic exchange "orders"; eu.q bound with "order.eu.*", us.q bound with "order.us.*" (in base-class setup).
    try (Channel channel = conn.createChannel()) {
        channel.basicPublish("orders", "order.eu.placed", null, Json.write(new OrderPlaced(UUID.randomUUID())));
    }

    byte[] toEu = probe.get("orders.eu.q", Duration.ofSeconds(10));
    byte[] toUs = probe.get("orders.us.q", Duration.ofSeconds(2));   // short window — expect nothing

    assertThat(toEu).as("EU order did not reach the EU queue").isNotNull();   // one behaviour: the topic routing
    assertThat(toUs).as("EU order was wrongly routed to the US queue").isNull();
}
```

A **fanout** exchange (routing key ignored) is the broadcast / SNS-fan-out analogue — every bound queue gets a
copy; assert each one received it. A **direct** exchange routes on an exact routing-key match.

## Receiving a batch / draining

To assert "exactly N messages were produced", pull in a bounded loop and count — the timeout stops it hanging
when fewer than N arrive. (Extend `RabbitProbe` with a `getMany(queue, max, timeout)` that loops `basicGet`
until `max` or the deadline; it acks each.)

```java
List<byte[]> batch = probe.getMany("orders.q", 10, Duration.ofSeconds(5));
assertThat(batch).hasSize(3);                  // SUT produced exactly 3
```

## Anti-patterns

- **`Thread.sleep(5000)` before reading / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* the `RabbitProbe` bounded `basicGet` poll for the receive side, and
  **Awaitility** for consumer side-effects — each returns the instant the condition holds and *fails* if it
  never does. (The only allowed `Thread.sleep` is the short poll cadence *inside* the bounded probe loop.)
- **Publishing before the test queue is declared and bound.** RabbitMQ routes at publish time and **drops** a
  message with no matching bound queue — the probe then reads nothing and the assert flakes for the wrong
  reason. *Fix:* declare exchanges/queues/bindings in `@BeforeClass` (the base-class topology) **before** any
  publish; for a dedicated probe queue, bind it in `@BeforeMethod`.
- **Consuming with `autoAck=true` when testing settlement.** The broker removes the message on delivery, so
  you can't assert ack-vs-nack-vs-dead-letter or redelivery. *Fix:* `autoAck=false` and settle explicitly.
- **Leaving a consumed message un-acked across tests.** On channel close the broker **requeues** it, and the
  next test sees a "phantom" redelivery. *Fix:* ack (or nack) every message; the `RabbitProbe` acks what it
  drains.
- **Expecting an app-level DLT topic (the Kafka habit).** RabbitMQ dead-lettering is **broker-native** — a
  `x-dead-letter-exchange` queue argument, not application code. *Fix:* declare the DLX + DLQ in the topology
  and assert the **DLQ**; don't look for a `<topic>.DLT`.
- **Treating a `null` `basicGet` result as success.** `null` means nothing was on the queue in the window —
  that's a failed produce, not a pass. *Fix:* `assertThat(body).isNotNull()` before deserializing.
- **Sharing one queue across parallel test classes.** Competing consumers steal each other's messages; asserts
  go non-deterministic. *Fix:* a **uniquely named queue per class** (or keep messaging classes out of the same
  parallel group), and drain leftovers in `@BeforeMethod`.
- **Reading the AMQP URL inside an `@Test` / hard-coding it.** *Fix:* surface it from the base class
  (container) or env (shared broker), inject it; never log it.

## Examples

**End-to-end: a consume → process → publish flow, asserted on the output queue, with the poison case routed to
the DLQ.**

```java
public class FulfilmentConsumerTest extends RabbitMqTestBase {

    private Connection conn;

    @BeforeMethod(alwaysRun = true)
    public void setUp() throws Exception {
        conn = newConnection();
        drain("orders.q");                 // independent tests — start from empty
        drain("shipments.q");
    }

    @AfterMethod(alwaysRun = true)
    public void tearDown() throws Exception { conn.close(); }

    @Test
    public void Should_publish_ShipmentReady_When_a_valid_OrderPaid_is_consumed() throws Exception {
        UUID orderId = UUID.randomUUID();
        try (Channel channel = conn.createChannel()) {
            AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                    .contentType("application/json").correlationId(orderId.toString()).build();
            channel.basicPublish("orders", "order.paid", props, Json.write(new OrderPaid(orderId)));
        }

        // The SUT consumer processes "orders.q" and publishes onto the "shipments" exchange → "shipments.q".
        byte[] ready = probe.get("shipments.q", Duration.ofSeconds(10));

        assertThat(ready).as("consumer did not publish a ShipmentReady message").isNotNull();
        ShipmentReady shipment = Json.parse(ready, ShipmentReady.class);
        assertThat(shipment.orderId()).isEqualTo(orderId);   // correlation preserved
    }

    private void drain(String queue) throws Exception {
        while (probe.get(queue, Duration.ofMillis(300)) != null) { }
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` (in `RabbitMqTestBase`) boots the broker once and declares the exchanges/queues/bindings;
   the AMQP URL is surfaced.
2. `@BeforeMethod` opens a connection and drains the queues so the test starts from empty — tests stay
   independent and order-free.
3. The test publishes an input message; the running SUT consumer publishes onto the output exchange; the test
   **polls** the output queue (the condition-wait) and asserts correlation was preserved.
4. `@AfterMethod` closes the connection; `@AfterClass` stops the broker.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```java
public final class Orders {
    public static Order.Builder pending() { return new Order.Builder().status("Pending"); }
}
// Orders.pending().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/java/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** The `RabbitProbe` bounded `basicGet` poll for
  the receive side; **Awaitility** for consumer side-effects. **No `Thread.sleep`** as an assertion wait — the
  only allowed `Thread.sleep` is the short poll cadence inside the bounded probe loop (or drive that loop with
  Awaitility too).
- **Declare the topology before publishing.** Exchanges, queues, and bindings in `@BeforeClass` (or a probe
  queue in `@BeforeMethod`) — RabbitMQ routes at publish time and drops messages with no matching bound queue.
- The SUT's publisher/consumer is **constructor-injected** with the `Connection` / AMQP URL — never a static
  connection or a URL read inside an `@Test`.
- **Consume with `autoAck=false` and settle every message** (`basicAck` / `basicNack` / `basicReject`). Never
  leave a message un-acked into the next test — it requeues and redelivers.
- **Dead-lettering is broker-native** — declare `x-dead-letter-exchange` + a DLX + a dead-letter queue and
  assert the **DLQ**; don't expect a Kafka-style app-level DLT.
- Assert the **fact**, not the absence: a `null` `basicGet` result is a *failed* produce — `isNotNull()`
  before reading the body.
- **Close** every connection/channel (try-with-resources); never leak them across tests.
- **Independent tests:** a uniquely named queue per class **or** drain-to-empty in `@BeforeMethod`; keep
  messaging classes out of the same parallel group unless verified isolated.
- Local broker = **RabbitMQ via Testcontainers** (pinned image); a shared test broker's AMQP URI/credentials
  come from **env, read lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test (AssertJ); builders for 4+-field payloads;
  structured logging (SLF4J message templates); no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical stack** (.NET 8 / NUnit, `RabbitMQ.Client` v7:
  `CreateChannelAsync`, `ExchangeDeclareAsync` / `QueueDeclareAsync(args)` / `QueueBindAsync`,
  `BasicPublishAsync`, `AsyncEventingBasicConsumer` + `BasicConsumeAsync(autoAck:false)`, `BasicAckAsync` /
  `BasicNackAsync` / `BasicRejectAsync`, `BasicGetAsync`, `Testcontainers.RabbitMq`). This file is its port.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`amqplib`: `amqp.connect(url)`,
  `assertExchange` / `assertQueue(..., { arguments })` / `bindQueue`, `channel.publish`,
  `channel.consume(q, cb, { noAck: false })` + `channel.ack`/`nack`/`reject`, `channel.get` polling,
  `expect.poll` for side-effects, `@testcontainers/rabbitmq` `RabbitMQContainer`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure Service
  Bus; **the `rabbitmq`-vs-`service-bus` parallel**: RabbitMQ's manual ack + broker-native DLX is the **closest** of the three
  siblings to Service Bus's peek-lock + DLQ sub-queue — same consume-and-settle shape, different routing model.
- `references/sqs.md` — AWS SQS; same parallel (delete-to-ack + redrive-policy DLQ ≈
  RabbitMQ's ack + DLX). Same condition-wait discipline, different broker.
- `references/kafka.md` (`kafka`, the immediately prior sibling) — **the `rabbitmq`-vs-`kafka` boundary**:
  Kafka log + offsets + app-level DLT vs RabbitMQ queue + manual ack + broker-native DLX.
- `qa-db-connection-java` — the Awaitility poll and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-login-tokens-java` — when authing to a shared cloud broker with credentials from env; the
  secrets-from-env discipline.
- `qa-test-reports-java` — attach the consumed message body / DLQ `x-death` reason to the Allure result.
- `qa-test-data-builder-java` — builders/ObjectMother for message payloads with 4+ fields.
