# Messaging Testing — Apache Kafka (Java 21 / TestNG) — **canonical stack**

This is the **canonical** stack of the `qa/java/skills/messaging-testing/` node, the **third `messaging-testing`
sibling** (service-bus → SQS → **Kafka** → RabbitMQ). **Java leads here by judgment** (the same
"lead where the tool is most authentic" call WireMock and Service Bus made): Kafka is **JVM-native**
and `org.apache.kafka:kafka-clients` is its most first-class, authoritative client — the reference producer/
consumer surface every other client mirrors. The `dotnet` (`Confluent.Kafka`) and `typescript` (`kafkajs`)
siblings are **ported** from this file. All three clients produce / subscribe / poll, so it's a true
translate-the-concepts port — but Kafka's broker model is the **biggest departure in the family**, so read
the model section before the code.

This node **ports the service-bus structure** onto Kafka: the **same two assertion patterns** and the
**same eventual-consistency condition-wait discipline** — only the broker model changes, and it changes a lot.

- **Producer-assert** — the SUT, when exercised, **produced** record X onto a topic.
- **Consumer-assert** — the SUT **consumed** a record and produced an observable **side-effect Y** (a row
  written, an email sent, another record produced).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The record is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the record
> (or its effect) to appear, with a bounded timeout — **never `Thread.sleep`**. This is the exact lineage of
> `qa-db-testing-client-java`'s Awaitility usage and `references/service-bus.md`'s condition-wait.
> Kafka gives you **`consumer.poll(Duration)`** as the receive-side primitive: it long-polls up to a bounded
> window for records, then returns them or an empty batch. A **bounded poll loop** (poll until you have the
> records you expect, or a deadline passes) *is* the condition-wait; a fixed sleep is not.

## The Kafka model — a LOG, not a queue (read this first)

Kafka is **not a queue**. It's an append-only, partitioned **commit log**, and that changes every settlement
assumption SQS and Service Bus baked in:

- **Topics + partitions.** A topic is split into **partitions**; each partition is an ordered, immutable log.
  Ordering is guaranteed **only within a partition**, not across a topic.
- **You read from an offset; you do NOT ack/delete per record.** Consuming a record does **not** remove it —
  it stays in the log until the topic's **retention** window expires. There is no per-message ack, no
  visibility timeout, no "complete/abandon". Instead each **consumer group** tracks an **offset** per
  partition: "I've read up to here". `commitSync()` / `commitAsync()` persist that position. So the SQS
  "delete = ack" and Service Bus "complete = ack" have **no analogue** — the closest thing is *committing an
  offset*, and it marks a position, it doesn't consume-and-destroy.
- **Consumer groups.** Records are delivered to **each consumer group** independently. Two groups reading the
  same topic each get every record (fan-out is built in — no SNS/topic-subscription wiring needed). Within a
  group, partitions are divided among members (competing consumers, per partition).
- **`auto.offset.reset=earliest`** decides where a group with **no committed offset** starts: `earliest` =
  the beginning of the log, `latest` = only new records. **Test-side reads use a fresh group id + `earliest`**
  so they read the whole topic from the start — that's the "drain the queue" analogue, except the log isn't
  drained, just re-read.
- **Keys → partition routing.** A record's **key** is hashed to pick a partition, so all records with the same
  key land on the same partition and keep their relative order. This is the ordering primitive (the rough
  analogue of SQS FIFO's `MessageGroupId`).
- **No broker-native DLQ.** Kafka has **no dead-letter queue**. A "DLT" (dead-letter topic) is an
  **application-level convention**: on a processing failure the consumer's error handler **produces the record
  to a separate `<topic>.DLT` topic**. Spring Kafka automates this with `DeadLetterPublishingRecoverer` /
  `@RetryableTopic`; a plain `kafka-clients` consumer does it in a `catch` block. This is the sharpest
  contrast with `service-bus` (broker DLQ *sub-queue*) and `sqs` (redrive-policy DLQ *queue*) — same job, **app code**
  instead of a broker feature.
- **Log compaction** (mention): a compacted topic keeps only the **latest** value per key. Rarely what a test
  asserts on directly; just don't expect every historical record on a compacted topic.

## Stack

- Java 21 + TestNG + AssertJ (`org.testng:testng`, `org.assertj:assertj-core`) + Awaitility
  (`org.awaitility:awaitility`)
- `org.apache.kafka:kafka-clients` (`KafkaProducer` / `KafkaConsumer` / `ProducerRecord` / `ConsumerRecords`).
  **Spring Kafka** (`org.springframework.kafka:spring-kafka`) is noted **only** for the DLT/retry convention
  (`DeadLetterPublishingRecoverer` / `@RetryableTopic`) — the assertion code stays on plain `kafka-clients`.
- `org.testcontainers:kafka` (`ConfluentKafkaContainer`) **or** `org.testcontainers:redpanda`
  (`RedpandaContainer`) — boots a **local broker** and surfaces `getBootstrapServers()` (cross-link
  `qa-test-environments-java`, which already boots a Kafka container in its multi-service topology)
- The SUT's typed producer/consumer is **constructor-injected** with the bootstrap servers (or an injected
  `KafkaProducer`/`KafkaConsumer`) — never a static client or a bootstrap string read inside an `@Test`

```
src/test/java/.../messaging/
├── KafkaTestBase.java     ← boots the Kafka/Redpanda container, exposes bootstrap servers + a producer factory
├── KafkaProbe.java        ← test-side reader: fresh consumer group at `earliest`, bounded poll-until-N (the "drain" analogue)
└── OrderPublishingTest.java
```

## Local broker for tests — Kafka / Redpanda via Testcontainers

There is no in-memory Kafka. For deterministic local + CI tests, run a **real broker in a container** and
point the clients at `getBootstrapServers()`. Two good options:

- **`org.testcontainers:kafka` `ConfluentKafkaContainer`** (`confluentinc/cp-kafka`) — the mainstream choice,
  a real Kafka broker. (The older `KafkaContainer` class is deprecated in favour of `ConfluentKafkaContainer`
  / the Apache KRaft-native image.)
- **`org.testcontainers:redpanda` `RedpandaContainer`** — a **Kafka-API-compatible** single binary that
  **starts ~2× faster**; ideal when you boot a fresh broker per suite for isolation. Same `getBootstrapServers()`.

Reuse the fixture discipline from `qa-test-environments-java` (boot once per class; **never `Thread.sleep` for
readiness** — the container owns the wait strategy). **Create topics up front** (auto-create is off in a real
broker config) via an `AdminClient`, or let the test produce to a topic and rely on the broker default — but
explicit creation with a known partition count makes partition assertions deterministic.

```java
import org.apache.kafka.clients.admin.*;
import org.apache.kafka.clients.producer.*;
import org.apache.kafka.common.serialization.StringSerializer;
import org.testcontainers.kafka.ConfluentKafkaContainer;
import org.testcontainers.utility.DockerImageName;
import org.testng.annotations.*;

import java.util.*;
import java.util.concurrent.ExecutionException;

public abstract class KafkaTestBase {

    // Pin the image tag, never `latest`. The container declares its own readiness wait strategy.
    private final ConfluentKafkaContainer broker =
            new ConfluentKafkaContainer(DockerImageName.parse("confluentinc/cp-kafka:7.6.1"));
    // Lighter alternative — Redpanda (Kafka-API-compatible, ~2× faster start):
    //   new RedpandaContainer(DockerImageName.parse("redpandadata/redpanda:v24.1.7"));

    protected String bootstrapServers;
    protected KafkaProbe probe;

    @BeforeClass(alwaysRun = true)
    public void startBroker() throws ExecutionException, InterruptedException {
        broker.start();
        bootstrapServers = broker.getBootstrapServers();
        probe = new KafkaProbe(bootstrapServers);

        // Create the topics with a known partition count so partition/ordering assertions are deterministic.
        try (Admin admin = Admin.create(Map.of(AdminClientConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers))) {
            admin.createTopics(List.of(
                    new NewTopic("orders", 3, (short) 1),
                    new NewTopic("orders.DLT", 1, (short) 1),
                    new NewTopic("shipments", 1, (short) 1))).all().get();
        }
    }

    @AfterClass(alwaysRun = true)
    public void stopBroker() { broker.stop(); }

    // A short-lived producer for seeding input records. Block on the send future so the record is flushed
    // before the test moves on — that's a confirm, not a sleep.
    protected KafkaProducer<String, String> newProducer() {
        Properties props = new Properties();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class.getName());
        props.put(ProducerConfig.ACKS_CONFIG, "all");   // wait for the broker to persist
        return new KafkaProducer<>(props);
    }
}
```

> **Cloud / shared test cluster alternative.** If your org runs against a real **test** Kafka cluster instead
> of a container, read `bootstrap.servers` and the SASL/SSL credentials **from env, lazily** — never hard-code
> them, never log them (cross-link `qa-auth0-test-tokens-java` for the secrets-from-env discipline). A
> container is the default for CI determinism; a shared cluster makes tests order-dependent unless each uses a
> **uniquely named topic** and a **fresh consumer group** (because the log isn't drained between tests).

## The test-side reader — `KafkaProbe` (the "drain" analogue)

Because consuming doesn't remove records, the test-side reader subscribes a **fresh consumer group** at
`earliest` and **polls until it has the records it expects or a deadline passes**. The bounded poll loop is the
condition-wait — `consumer.poll(Duration)` long-polls each iteration; no `Thread.sleep` anywhere.

```java
import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.time.*;
import java.util.*;

public final class KafkaProbe {

    private final String bootstrapServers;

    public KafkaProbe(String bootstrapServers) { this.bootstrapServers = bootstrapServers; }

    /** Read up to `count` records from `topic`, from the start, within `timeout`. Fresh group → reads the
     *  whole log; the bounded poll loop IS the condition-wait. Returns what arrived (possibly fewer). */
    public List<ConsumerRecord<String, String>> records(String topic, int count, Duration timeout) {
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "probe-" + UUID.randomUUID());   // fresh group → from the start
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);                // a probe commits nothing
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());

        List<ConsumerRecord<String, String>> collected = new ArrayList<>();
        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(List.of(topic));
            Instant deadline = Instant.now().plus(timeout);
            while (Instant.now().isBefore(deadline) && collected.size() < count) {
                consumer.poll(Duration.ofMillis(500)).forEach(collected::add);   // long-poll = the wait
            }
        }
        return collected;
    }
}
```

> `poll(Duration)` blocks up to that window for records and returns the instant they arrive — it does **not**
> sleep the full duration when records are present. The loop ends as soon as `count` records are in, or fails
> the test (via the assertion below) if the deadline passes empty. That is the condition-wait; a bare
> `Thread.sleep(5000)` "until the record probably arrived" races the broker and is banned.

## Core pattern 1 — producer-assert (the SUT produced record X)

The SUT produces; the test reads with the probe and asserts the record's key, value and headers. An **empty**
result means "nothing arrived within the window" — a failed produce, asserted deterministically.

```java
import static org.assertj.core.api.Assertions.assertThat;

public class OrderPublishingTest extends KafkaTestBase {

    private OrderPublisher sut;     // production code, constructor-injected with the bootstrap servers

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        sut = new OrderPublisher(bootstrapServers, "orders");   // constructor injection — no static client
    }

    @Test
    public void Should_produce_OrderPlaced_When_an_order_is_submitted() {
        Order order = Orders.pending().withTotal(1999).build();   // builder (qa/java/skills/test-data-builder)

        sut.submit(order);                                        // SUT produces the record

        // Fresh-group read from the start, bounded poll = the condition-wait. Never a Thread.sleep.
        List<ConsumerRecord<String, String>> records = probe.records("orders", 1, Duration.ofSeconds(10));

        assertThat(records).as("a record produced to 'orders' within the poll window").isNotEmpty();
        OrderPlaced placed = Json.parse(records.get(0).value(), OrderPlaced.class);
        assertThat(placed.orderId()).isEqualTo(order.id());       // one logical assertion: the produced fact
    }

    @Test
    public void Should_stamp_the_key_and_eventType_header_When_producing() {
        Order order = Orders.pending().build();

        sut.submit(order);

        List<ConsumerRecord<String, String>> records = probe.records("orders", 1, Duration.ofSeconds(10));

        assertThat(records).isNotEmpty();
        ConsumerRecord<String, String> record = records.get(0);
        assertThat(record).satisfies(r -> {                        // one behaviour: the record envelope
            assertThat(r.key()).isEqualTo(order.id().toString());  // key drives partition routing
            assertThat(new String(r.headers().lastHeader("eventType").value(), UTF_8)).isEqualTo("OrderPlaced");
        });
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer** (a `@KafkaListener` or a poll loop). The test **produces an input record**, lets
the consumer run, and waits for the observable side-effect — eventually consistent, so use **Awaitility** to
poll a probe on a condition. This reuses `qa-db-testing-client-java`'s discipline verbatim.

```java
import static org.awaitility.Awaitility.await;

@Test
public void Should_write_a_shipment_row_When_an_OrderPaid_record_is_consumed() throws Exception {
    UUID orderId = UUID.randomUUID();

    // 1. Produce the input record onto the topic the consumer subscribes to. Block on the send → flushed.
    try (KafkaProducer<String, String> producer = newProducer()) {
        producer.send(new ProducerRecord<>("orders", orderId.toString(),
                Json.write(new OrderPaid(orderId)))).get();
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
> the condition-wait — **never** a bare `Thread.sleep(5000)` standing in for "the record probably arrived by
> now", which races the broker.

## Offsets, consumer groups & commit semantics

The defining Kafka behaviour: **consuming doesn't remove the record; committing an offset only marks your
group's position.** A *different* group, or the same group reset to `earliest`, re-reads the whole log. Tests
exploit this — the probe always uses a **fresh group**, so it sees every record regardless of what the SUT's
group has committed.

```java
@Test
public void Should_let_a_fresh_group_reread_the_whole_log_When_a_prior_group_already_consumed() throws Exception {
    try (KafkaProducer<String, String> producer = newProducer()) {
        producer.send(new ProducerRecord<>("orders", "k1", "{\"orderId\":\"a\"}")).get();
    }

    // Group A reads and commits its offset — the record is NOT deleted.
    List<ConsumerRecord<String, String>> groupA = probe.records("orders", 1, Duration.ofSeconds(10));
    assertThat(groupA).hasSize(1);

    // A brand-new group at `earliest` still sees the same record — the log was never drained.
    List<ConsumerRecord<String, String>> groupB = probe.records("orders", 1, Duration.ofSeconds(10));
    assertThat(groupB).hasSize(1);   // proof: Kafka is a re-readable log, not a consume-and-destroy queue
}
```

When the **SUT consumer** commits manually (`enable.auto.commit=false` + `commitSync()` after processing), the
behaviour you assert is the *side-effect* (pattern 2), not the offset — offsets are the consumer's
bookkeeping, the row/record is the contract.

## Keys → partition routing & per-key ordering

A record's **key** is hashed to a partition, so same-key records share a partition and keep their order. This
is the ordering primitive — assert it directly.

```java
record Seq(int seq) {}

@Test
public void Should_keep_per_key_ordering_When_records_share_a_key() throws Exception {
    try (KafkaProducer<String, String> producer = newProducer()) {
        for (int i = 1; i <= 3; i++)
            producer.send(new ProducerRecord<>("orders", "cust-42", "{\"seq\":" + i + "}")).get();
    }

    List<ConsumerRecord<String, String>> records = probe.records("orders", 3, Duration.ofSeconds(10));

    assertThat(records).hasSize(3);
    assertThat(records).extracting(ConsumerRecord::partition)
            .containsOnly(records.get(0).partition());          // same key → same partition
    assertThat(records).extracting(r -> Json.parse(r.value(), Seq.class).seq())
            .containsExactly(1, 2, 3);                           // order preserved within the partition
}
```

> Records with **different** keys may land on different partitions and arrive **interleaved** — never assert a
> total order across a multi-partition topic. Order is a *per-partition* (per-key) guarantee only.

## App-level dead-letter topic (DLT) — a convention, not a broker feature

Kafka has **no broker DLQ**. When the SUT consumer can't process a record, its **error handler produces the
record to a separate `<topic>.DLT` topic**. The test seeds a poison record and asserts it lands on the DLT —
exactly the same shape as `service-bus`/`sqs`'s DLQ assertion, but the dead-lettering is **app code**, not the broker.

```java
@Test
public void Should_route_the_poison_record_to_the_DLT_When_processing_fails() throws Exception {
    try (KafkaProducer<String, String> producer = newProducer()) {
        producer.send(new ProducerRecord<>("orders", "bad", "{ not valid order json }")).get();
    }

    // The SUT consumer fails to deserialize/process; its error handler (Spring Kafka
    // DeadLetterPublishingRecoverer / @RetryableTopic, or a manual catch → producer.send) republishes
    // onto the DLT topic. Read the DLT with the probe — the bounded poll is the condition-wait.
    List<ConsumerRecord<String, String>> dead = probe.records("orders.DLT", 1, Duration.ofSeconds(10));

    assertThat(dead).as("the poison record on the DLT topic").isNotEmpty();
    assertThat(dead.get(0).value()).contains("not valid order json");   // the original payload
}
```

> **DLT naming.** Spring Kafka's `DeadLetterPublishingRecoverer` defaults to **`<topic>.DLT`** (uppercase);
> `@RetryableTopic` creates retry topics `<topic>-retry-0/1/...` and a final **`<topic>-dlt`** (lowercase).
> Assert on whichever name your app's convention produces — the topic is just another topic you read.

## Receiving a batch / draining

To assert "exactly N records were produced", read with a count and bounded timeout — the probe's poll loop
stops as soon as N arrive (or the deadline passes):

```java
List<ConsumerRecord<String, String>> drained = probe.records("orders", 3, Duration.ofSeconds(5));
assertThat(drained).hasSize(3);                  // SUT produced exactly 3
```

(There's no delete step — the records stay in the log; a fresh group re-reads them. Isolation comes from a
**unique topic per fixture**, not from draining.)

## Anti-patterns

- **`Thread.sleep(5000)` before reading / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* the `KafkaProbe` bounded poll loop (`consumer.poll(Duration)`) for the
  receive side, and **Awaitility** for consumer side-effects.
- **A test-side consumer with `auto.offset.reset=latest` (or a reused group id).** It starts **after** the
  records the SUT already produced and reads **nothing**, so the assert flakes or fails for the wrong reason.
  *Fix:* a **fresh group id** + **`earliest`** for every probe read (the `KafkaProbe` does this).
- **Treating an empty poll result as success.** Empty means nothing arrived in the window — a failed produce,
  not a pass. *Fix:* `assertThat(records).isNotEmpty()` (or `.hasSize(n)`) before reading values.
- **Asserting a total order across a multi-partition topic.** Different keys → different partitions → records
  interleave. *Fix:* assert order **within a key/partition** only; pin records to one partition with a shared
  key when order is under test.
- **Expecting a broker DLQ.** Kafka has none — an un-handled poison record just sits in the log and the
  consumer may spin on it. *Fix:* assert the **app-level DLT** topic the consumer's error handler produces to.
- **Sharing one topic across parallel test classes.** Because the log isn't drained, leftovers from another
  class show up in your fresh-group read. *Fix:* a **uniquely named topic per class** (or per test), and keep
  messaging classes out of the same parallel group unless verified isolated.
- **Forgetting to flush the producer.** A fire-and-forget `send(...)` may not have reached the broker before
  the assert. *Fix:* block on the send future (`.get()`) or `producer.flush()` — a confirm, not a sleep.
- **Hard-coding `bootstrap.servers` / SASL creds in an `@Test`.** *Fix:* surface bootstrap servers from the
  base class (container) or env (shared cluster); never log secrets.
- **Reaching for Kafka when the dependency is an HTTP call.** *Fix:* `qa-api-mocking-java` — messaging
  is for async topics, not request/response fakes.

## Examples

**End-to-end: a consume → process → produce flow, asserted on the output topic, with the poison case routed to
the DLT.**

```java
public class FulfilmentConsumerTest extends KafkaTestBase {

    @Test
    public void Should_produce_ShipmentReady_When_a_valid_OrderPaid_is_consumed() throws Exception {
        UUID orderId = UUID.randomUUID();
        try (KafkaProducer<String, String> producer = newProducer()) {
            producer.send(new ProducerRecord<>("orders", orderId.toString(),
                    Json.write(new OrderPaid(orderId)))).get();
        }

        // The SUT consumer subscribes to "orders" and produces onto "shipments".
        List<ConsumerRecord<String, String>> ready = probe.records("shipments", 1, Duration.ofSeconds(10));

        assertThat(ready).as("consumer produced a ShipmentReady record").isNotEmpty();
        assertThat(ready.get(0).key()).isEqualTo(orderId.toString());   // correlation key preserved
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` (in `KafkaTestBase`) boots the Kafka/Redpanda container once and creates the topics with a
   known partition count; bootstrap servers + the `KafkaProbe` are surfaced.
2. The test produces an input record (blocking on the send → flushed); the running SUT consumer produces onto
   the output topic.
3. The test reads the output topic with a **fresh-group** probe (the condition-wait) and asserts the
   correlation key was preserved.
4. `@AfterClass` stops the container. (No per-test drain — isolation is by unique topic, since the log isn't
   consumed-and-destroyed.)

**Test-data builder for record payloads (4+ fields → builder, per the global rules).**

```java
public final class Orders {
    public static Order.Builder pending() { return new Order.Builder().status("Pending"); }
}
// Orders.pending().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/java/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** The `KafkaProbe` bounded poll loop
  (`consumer.poll(Duration)`) for the receive side; **Awaitility** for consumer side-effects. **No
  `Thread.sleep`** as an assertion wait.
- **Every test-side read uses a fresh consumer group + `auto.offset.reset=earliest`** so it reads the topic
  from the start (the log isn't drained — `latest` or a reused group would miss already-produced records).
- The SUT's producer/consumer is **constructor-injected** with the bootstrap servers / client — never a static
  client or a bootstrap string read inside an `@Test`.
- Assert the **fact**, not the absence: an empty poll result is a *failed* produce — `isNotEmpty()` /
  `hasSize(n)` before reading values.
- **Order is a per-partition (per-key) guarantee** — never assert a total order across a multi-partition topic.
- **No broker DLQ** — assert the **app-level DLT** topic (`<topic>.DLT` / `<topic>-dlt`) the consumer's error
  handler produces to.
- **Independent tests:** a **uniquely named topic per class** (the log isn't consumed-and-destroyed, so a
  shared topic leaks records); keep messaging classes out of the same parallel group unless verified isolated.
- **Flush/confirm produces** (`send(...).get()` or `flush()`); **close** every producer/consumer.
- Local broker = **Kafka/Redpanda via Testcontainers** (pinned image; topics created in `@BeforeClass`); a
  shared test cluster reads `bootstrap.servers` + SASL creds from **env, lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test (AssertJ); builders for 4+-field payloads;
  structured logging (SLF4J message templates); no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — same skill, .NET 8 / NUnit (`Confluent.Kafka`:
  `ProducerBuilder`/`ConsumerBuilder`, `consumer.Consume(TimeSpan)` poll, `AutoOffsetReset.Earliest`,
  `EnableAutoCommit=false` + `Commit()`, `WaitFor.Async` for side-effects, `Testcontainers.Kafka`
  `KafkaContainer`). Structure ported, not code.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`kafkajs`: `consumer.subscribe({
  fromBeginning: true })` + `consumer.run({ eachMessage })` collecting into a buffer, `expect.poll` for the
  buffer and for side-effects, `@testcontainers/kafka` `KafkaContainer`). Note: kafkajs has **no synchronous
  `poll()`** — the buffer + `expect.poll` is the port of this file's bounded poll loop.
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure Service
  Bus; **the `kafka`-vs-`service-bus` boundary**: queue + peek-lock settlement + broker DLQ sub-queue vs Kafka log + offsets
  + app-level DLT.
- `references/sqs.md` (`sqs`, the immediately prior sibling) — AWS SQS; **the `kafka`-vs-`sqs` boundary**:
  delete-to-ack + visibility timeout + redrive-policy DLQ vs Kafka commit-offset + re-readable log + app-level
  DLT. Same condition-wait discipline, different broker model.
- `qa-db-testing-client-java` — the Awaitility poll and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-environments-java` — booting the Kafka container (it already runs `confluentinc/cp-kafka` in
  its multi-service topology); the per-class lifecycle and readiness-wait discipline (never `Thread.sleep`).
- `qa-auth0-test-tokens-java` — when running against a shared cloud cluster with SASL/OAuth creds; the
  secrets-from-env discipline.
- `qa-api-mocking-java` — the *synchronous* counterpart: fake an HTTP dependency the SUT calls.
  The boundary: WireMock = request/response fake; Kafka = async topic assertions.
- `qa-allure-reporting-java` — attach the consumed record value / DLT payload to the Allure result.
- `qa-test-data-builder-java` — builders/ObjectMother for record payloads with 4+ fields.
