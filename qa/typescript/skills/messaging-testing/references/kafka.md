# Messaging Testing — Apache Kafka (Node 24 + TypeScript / Vitest)

Ported from the **canonical** `java` stack of the `qa/typescript/skills/messaging-testing/` node (Java leads this node by
judgment — Kafka is JVM-native and `org.apache.kafka:kafka-clients` is its most first-class client; this file
re-expresses the same model in TypeScript idioms — `kafkajs`, Vitest, `expect.poll`, Testcontainers). This is
the **third `messaging-testing` sibling** (service-bus → SQS → **Kafka** → RabbitMQ); it keeps
the **same two assertion patterns and the same eventual-consistency condition-wait discipline** as `service-bus` — only
the broker model changes, and Kafka's is the **biggest departure in the family**, so read the model section
before the code. Translate-the-concepts, not redesign — though `kafkajs` has **one structural difference** from
the JVM/.NET clients worth flagging up front: **there is no synchronous `poll()`**. kafkajs is callback-driven
(`consumer.run({ eachMessage })`), so the canonical's bounded poll loop becomes a **buffer + `expect.poll`**.

- **Producer-assert** — the SUT, when exercised, **produced** record X onto a topic.
- **Consumer-assert** — the SUT **consumed** a record and produced an observable **side-effect Y** (a row
  written, an email sent, another record produced).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The record is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the record
> (or its effect) to appear, with a bounded timeout — **never `setTimeout` / `page.waitForTimeout`**. This is
> the exact lineage of `qa-db-connection-typescript`'s `expect.poll` usage and
> `references/service-bus.md`'s condition-wait. Because kafkajs delivers records to an
> `eachMessage` callback, the test collects them into a **buffer** and **`expect.poll`s the buffer** until the
> records it expects arrive. That bounded poll *is* the condition-wait; a fixed sleep is not.

## The Kafka model — a LOG, not a queue (read this first)

Kafka is **not a queue**. It's an append-only, partitioned **commit log**, and that changes every settlement
assumption SQS and Service Bus baked in:

- **Topics + partitions.** A topic is split into **partitions**; each partition is an ordered, immutable log.
  Ordering is guaranteed **only within a partition**, not across a topic.
- **You read from an offset; you do NOT ack/delete per record.** Consuming a record does **not** remove it —
  it stays in the log until the topic's **retention** window expires. There is no per-message ack, no
  visibility timeout, no "complete/abandon". Instead each **consumer group** tracks an **offset** per
  partition: "I've read up to here". `commitOffsets` persists that position. So the SQS "delete = ack" and
  Service Bus "complete = ack" have **no analogue** — the closest thing is *committing an offset*, and it marks
  a position, it doesn't consume-and-destroy.
- **Consumer groups.** Records are delivered to **each consumer group** independently. Two groups reading the
  same topic each get every record (fan-out is built in — no SNS/topic-subscription wiring needed). Within a
  group, partitions are divided among members (competing consumers, per partition).
- **`fromBeginning: true`** (kafkajs's `auto.offset.reset=earliest`) decides where a group with **no committed
  offset** starts: `true` = the beginning of the log, `false` = only new records. **Test-side reads use a
  fresh group id + `fromBeginning: true`** so they read the whole topic from the start — that's the "drain the
  queue" analogue, except the log isn't drained, just re-read.
- **Keys → partition routing.** A record's **key** is hashed to pick a partition, so all records with the same
  key land on the same partition and keep their relative order. This is the ordering primitive (the rough
  analogue of SQS FIFO's `MessageGroupId`).
- **No broker-native DLQ.** Kafka has **no dead-letter queue**. A "DLT" (dead-letter topic) is an
  **application-level convention**: on a processing failure the consumer's error handler **produces the record
  to a separate `<topic>.DLT` topic** (a `catch` block that calls `producer.send` — the kafkajs analogue of
  Spring Kafka's `DeadLetterPublishingRecoverer`). This is the sharpest contrast with `service-bus` (broker DLQ
  *sub-queue*) and `sqs` (redrive-policy DLQ *queue*) — same job, **app code** instead of a broker feature.
- **Log compaction** (mention): a compacted topic keeps only the **latest** value per key. Rarely what a test
  asserts on directly; just don't expect every historical record on a compacted topic.

## Stack

- Node 24 + TypeScript (strict) + Vitest
- `kafkajs` (`new Kafka(...)` → `producer()` / `consumer()` / `admin()`). Callback-driven consumer: `run({
  eachMessage })`, **no synchronous poll**.
- `@testcontainers/kafka` (`KafkaContainer`) — boots a **local broker** and surfaces `getBootstrapServers()`. A Redpanda image (Kafka-API-compatible, ~2× faster start) is
  a drop-in alternative when you boot a fresh broker per suite.
- The SUT's typed producer/consumer is **constructor-injected** with the brokers (or an injected `Producer`/
  `Consumer`) — never a static client or a brokers string read inside a test

```
test/
├── fixtures/
│   └── kafkaBroker.ts      ← boots Kafka, creates topics, returns the client + a startCollector helper
└── orderPublishing.test.ts
```

## Local broker for tests — Kafka / Redpanda via Testcontainers

There is no in-memory Kafka. For deterministic local + CI tests, run a **real broker in a container** and point
the client at `getBootstrapServers()`. Use the **`@testcontainers/kafka`** module (`confluentinc/cp-kafka`); a
Redpanda image is the lighter, faster-starting Kafka-API-compatible alternative. Reuse the fixture discipline (boot once per suite; **never `setTimeout` for readiness** — the module
owns the wait strategy). **Create topics up front** with a known partition count (via `admin()`) so partition
assertions are deterministic.

```typescript
// test/fixtures/kafkaBroker.ts
import { KafkaContainer, type StartedKafkaContainer } from "@testcontainers/kafka";
import { Kafka, logLevel, type Consumer, type IHeaders } from "kafkajs";
import { randomUUID } from "node:crypto";

export interface CollectedRecord {
  key: string | null;
  value: string | null;
  partition: number;
  headers: IHeaders;
}

export interface Collector {
  records: CollectedRecord[];                 // live buffer — expect.poll it
  stop: () => Promise<void>;
}

export interface Broker {
  kafka: Kafka;
  bootstrapServers: string;
  startCollector: (topic: string) => Promise<Collector>;
  stop: () => Promise<void>;
}

export async function startKafkaBroker(): Promise<Broker> {
  // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
  const container: StartedKafkaContainer =
    await new KafkaContainer("confluentinc/cp-kafka:7.6.1").start();
  const bootstrapServers = container.getBootstrapServers();

  const kafka = new Kafka({ brokers: [bootstrapServers], logLevel: logLevel.NOTHING });

  // Create the topics with a known partition count so partition/ordering assertions are deterministic.
  const admin = kafka.admin();
  await admin.connect();
  await admin.createTopics({
    topics: [
      { topic: "orders", numPartitions: 3 },
      { topic: "orders.DLT", numPartitions: 1 },
      { topic: "shipments", numPartitions: 1 },
    ],
  });
  await admin.disconnect();

  return {
    kafka,
    bootstrapServers,
    // A fresh consumer group at the start of the log, pushing records into a live buffer.
    // kafkajs has no synchronous poll, so the test expect.polls `records` until what it expects arrives.
    startCollector: async (topic) => {
      const consumer: Consumer = kafka.consumer({ groupId: `probe-${randomUUID()}` });
      await consumer.connect();
      await consumer.subscribe({ topic, fromBeginning: true });   // fromBeginning = earliest → reads from start
      const records: CollectedRecord[] = [];
      await consumer.run({
        eachMessage: async ({ message, partition }) => {
          records.push({
            key: message.key?.toString() ?? null,
            value: message.value?.toString() ?? null,
            partition,
            headers: message.headers ?? {},
          });
        },
      });
      return { records, stop: () => consumer.disconnect() };
    },
    stop: async () => { await container.stop(); },
  };
}
```

> **Cloud / shared test cluster alternative.** If your org runs against a real **test** Kafka cluster instead
> of a container, read the brokers and the SASL/SSL credentials **from `process.env`, lazily** — never
> hard-code them, never log them (cross-link `qa-test-login-tokens-typescript` for the secrets-from-env
> discipline). A container is the default for CI determinism; a shared cluster makes tests order-dependent
> unless each uses a **uniquely named topic** and a **fresh consumer group** (the log isn't drained between
> tests).

## The test-side reader — a collector + `expect.poll` (the "drain" analogue)

Because consuming doesn't remove records, the collector subscribes a **fresh consumer group** at the start of
the log (`fromBeginning: true`) and pushes records into a **live buffer**. The test **`expect.poll`s the
buffer** until the expected records arrive — that poll is the condition-wait; no `setTimeout` anywhere. (Start
the collector before or after the produce — `fromBeginning` reads from offset 0 either way.)

## Core pattern 1 — producer-assert (the SUT produced record X)

The SUT produces; the test collects with a fresh-group consumer and `expect.poll`s the buffer, then asserts the
record's key, value and headers. A buffer that **stays empty** means "nothing arrived within the window" — a
failed produce, asserted deterministically by the poll timing out.

```typescript
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { startKafkaBroker, type Broker, type Collector } from "./fixtures/kafkaBroker";
import { OrderPublisher } from "../src/orderPublisher";
import { anOrder } from "./builders/order"; // builder (qa/typescript/skills/test-data-builder)

describe("order publishing", () => {
  let broker: Broker;
  let sut: OrderPublisher;
  let collector: Collector;

  beforeAll(async () => { broker = await startKafkaBroker(); });
  afterAll(async () => { await broker.stop(); });

  beforeEach(async () => {
    sut = new OrderPublisher(broker.bootstrapServers, "orders"); // constructor injection — no static client
    collector = await broker.startCollector("orders");
  });

  it("produces OrderPlaced when an order is submitted", async () => {
    const order = anOrder().pending().withTotal(1999).build();

    await sut.submit(order); // SUT produces the record

    // expect.poll the live buffer = the condition-wait. Never a fixed setTimeout.
    await expect.poll(() => collector.records.length, { timeout: 10_000, interval: 200 })
      .toBeGreaterThanOrEqual(1);

    const placed = JSON.parse(collector.records[0].value!);
    expect(placed.orderId).toBe(order.id); // one logical assertion: the produced fact
    await collector.stop();
  });

  it("stamps the key and eventType header when producing", async () => {
    const order = anOrder().pending().build();

    await sut.submit(order);

    await expect.poll(() => collector.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);

    const record = collector.records[0];
    expect({ // one behaviour: the record envelope
      key: record.key,
      eventType: record.headers.eventType?.toString(),
    }).toEqual({ key: order.id, eventType: "OrderPlaced" }); // key drives partition routing
    await collector.stop();
  });
});
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **produces an input record**, lets the consumer run, and waits for the
observable side-effect — eventually consistent, so use `expect.poll` to wait on a condition. This reuses
`qa-db-connection-typescript`'s discipline.

```typescript
import { randomUUID } from "node:crypto";

it("writes a shipment row when an OrderPaid record is consumed", async () => {
  const orderId = randomUUID();

  // 1. Produce the input record onto the topic the consumer subscribes to. Await the send → flushed.
  const producer = broker.kafka.producer();
  await producer.connect();
  await producer.send({
    topic: "orders",
    messages: [{ key: orderId, value: JSON.stringify({ orderId }) }],
  });
  await producer.disconnect();

  // 2. The SUT consumer is already running and picks it up.

  // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
  await expect
    .poll(async () => (await shipmentsProbe.getByOrderId(orderId))?.status, {
      timeout: 10_000,
      interval: 200,
    })
    .toBe("Ready"); // one logical assertion: the side-effect
});
```

> `expect.poll` re-runs the probe and passes the instant the condition holds, failing if it never does. That
> is the condition-wait — **never** a bare `await new Promise(r => setTimeout(r, 5000))` standing in for "the
> record probably arrived by now", which races the broker.

## Offsets, consumer groups & commit semantics

The defining Kafka behaviour: **consuming doesn't remove the record; committing an offset only marks your
group's position.** A *different* group, or the same group reset to the start, re-reads the whole log. Tests
exploit this — every collector uses a **fresh group**, so it sees every record regardless of what the SUT's
group has committed.

```typescript
it("lets a fresh group re-read the whole log after a prior group consumed", async () => {
  const producer = broker.kafka.producer();
  await producer.connect();
  await producer.send({ topic: "orders", messages: [{ key: "k1", value: JSON.stringify({ orderId: "a" }) }] });
  await producer.disconnect();

  // Group A reads — the record is NOT deleted.
  const groupA = await broker.startCollector("orders");
  await expect.poll(() => groupA.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);
  await groupA.stop();

  // A brand-new group from the start still sees the same record — the log was never drained.
  const groupB = await broker.startCollector("orders");
  await expect.poll(() => groupB.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);
  await groupB.stop(); // proof: Kafka is a re-readable log, not a consume-and-destroy queue
});
```

When the **SUT consumer** commits manually (autoCommit off + `commitOffsets` after processing), the behaviour
you assert is the *side-effect* (pattern 2), not the offset — offsets are the consumer's bookkeeping, the
row/record is the contract.

## Keys → partition routing & per-key ordering

A record's **key** is hashed to a partition, so same-key records share a partition and keep their order. This
is the ordering primitive — assert it directly.

```typescript
it("keeps per-key ordering when records share a key", async () => {
  const collector = await broker.startCollector("orders");

  const producer = broker.kafka.producer();
  await producer.connect();
  for (let i = 1; i <= 3; i++) {
    await producer.send({ topic: "orders", messages: [{ key: "cust-42", value: JSON.stringify({ seq: i }) }] });
  }
  await producer.disconnect();

  await expect.poll(() => collector.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(3);

  const partitions = new Set(collector.records.map((r) => r.partition));
  expect(partitions.size).toBe(1); // same key → same partition
  expect(collector.records.map((r) => JSON.parse(r.value!).seq)).toEqual([1, 2, 3]); // order within the partition
  await collector.stop();
});
```

> Records with **different** keys may land on different partitions and arrive **interleaved** — never assert a
> total order across a multi-partition topic. Order is a *per-partition* (per-key) guarantee only.

## App-level dead-letter topic (DLT) — a convention, not a broker feature

Kafka has **no broker DLQ**. When the SUT consumer can't process a record, its **error handler produces the
record to a separate `<topic>.DLT` topic**. The test seeds a poison record and asserts it lands on the DLT —
exactly the same shape as `service-bus`/`sqs`'s DLQ assertion, but the dead-lettering is **app code**, not the broker.

```typescript
it("routes the poison record to the DLT when processing fails", async () => {
  const dlt = await broker.startCollector("orders.DLT");

  const producer = broker.kafka.producer();
  await producer.connect();
  await producer.send({ topic: "orders", messages: [{ key: "bad", value: "{ not valid order json }" }] });
  await producer.disconnect();

  // The SUT consumer fails to parse/process; its error handler (a catch → producer.send, the kafkajs analogue
  // of Spring Kafka's DeadLetterPublishingRecoverer) republishes onto the DLT topic.
  await expect.poll(() => dlt.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);

  expect(dlt.records[0].value).toContain("not valid order json"); // the original payload
  await dlt.stop();
});
```

> **DLT naming.** The convention is `<topic>.DLT` (Spring Kafka's `DeadLetterPublishingRecoverer` default) or
> `<topic>-dlt` (Spring Kafka `@RetryableTopic` + retry topics). In a kafkajs consumer you pick the destination
> topic name in your error handler — assert on whatever your app produces to. The topic is just another topic.

## Receiving a batch / draining

To assert "exactly N records were produced", `expect.poll` the buffer to the expected length, then assert the
count is exactly N (poll for at-least-N, then assert equality once stable):

```typescript
const collector = await broker.startCollector("orders");
// ...SUT produces 3...
await expect.poll(() => collector.records.length, { timeout: 5_000 }).toBeGreaterThanOrEqual(3);
expect(collector.records).toHaveLength(3); // SUT produced exactly 3
await collector.stop();
```

(There's no delete step — the records stay in the log; a fresh group re-reads them. Isolation comes from a
**unique topic per file**, not from draining.)

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 5000))` / `page.waitForTimeout` before asserting on the buffer or the
  side-effect.** Races the broker and the consumer; slow and flaky. *Fix:* `expect.poll` the collector buffer
  for the receive side, and `expect.poll` the DB probe for consumer side-effects.
- **A collector with `fromBeginning: false` (or a reused group id).** It starts **after** the records the SUT
  already produced and reads **nothing**, so the assert flakes. *Fix:* a **fresh group id** + **`fromBeginning:
  true`** for every collector (the fixture's `startCollector` does this).
- **Treating an empty buffer as a non-failure.** If `expect.poll` times out the test fails — good — but never
  read `collector.records[0]` without first `expect.poll`-ing the length. *Fix:* poll the length, then index.
- **Asserting a total order across a multi-partition topic.** Different keys → different partitions → records
  interleave. *Fix:* assert order **within a key/partition** only; pin records to one partition with a shared
  key when order is under test.
- **Expecting a broker DLQ.** Kafka has none — an un-handled poison record just sits in the log and the
  consumer may spin on it. *Fix:* assert the **app-level DLT** topic the consumer's error handler produces to.
- **Sharing one topic across parallel test files.** Vitest runs files in parallel; because the log isn't
  drained, leftovers from another file show up in your fresh-group read. *Fix:* a **uniquely named topic per
  file**, or `test.sequential` / a single worker for messaging suites.
- **Not stopping the collector / disconnecting clients.** Leaked consumers keep rebalancing the group and slow
  the suite. *Fix:* `await collector.stop()` and disconnect producers in each test (or in `afterEach`).
- **Forgetting to await the producer send.** A send that isn't awaited may not have reached the broker before
  the assert. *Fix:* `await producer.send(...)` — a confirm, not a sleep.
- **Hard-coding brokers / SASL creds in a test.** *Fix:* surface brokers from the fixture (container) or
  `process.env` (shared cluster); never log secrets.

## Examples

**End-to-end: a consume → process → produce flow, asserted on the output topic, with the poison case routed to
the DLT.**

```typescript
describe("fulfilment consumer", () => {
  let broker: Broker;

  beforeAll(async () => { broker = await startKafkaBroker(); });
  afterAll(async () => { await broker.stop(); });

  it("produces ShipmentReady when a valid OrderPaid is consumed", async () => {
    const orderId = randomUUID();
    const shipments = await broker.startCollector("shipments");

    const producer = broker.kafka.producer();
    await producer.connect();
    await producer.send({ topic: "orders", messages: [{ key: orderId, value: JSON.stringify({ orderId }) }] });
    await producer.disconnect();

    // The SUT consumer subscribes to "orders" and produces onto "shipments".
    await expect.poll(() => shipments.records.length, { timeout: 10_000 }).toBeGreaterThanOrEqual(1);

    expect(shipments.records[0].key).toBe(orderId); // correlation key preserved
    await shipments.stop();
  });
});
```

Lifecycle for this test:
1. `beforeAll` boots the Kafka container once and creates the topics with a known partition count; the client +
   `startCollector` are surfaced.
2. The test starts a fresh-group collector on the output topic, then produces an input record (awaiting the
   send → flushed); the running SUT consumer produces onto the output topic.
3. The test `expect.poll`s the collector buffer (the condition-wait) and asserts the correlation key was
   preserved, then stops the collector.
4. `afterAll` stops the container. (No per-test drain — isolation is by unique topic, since the log isn't
   consumed-and-destroyed.)

**Test-data builder for record payloads (4+ fields → builder, per the global rules).**

```typescript
export const anOrder = () => new OrderBuilder().status("Pending");
// anOrder().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/typescript/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `expect.poll` the collector buffer for the
  receive side and the DB probe for consumer side-effects. **No `setTimeout` / `waitForTimeout`** as an
  assertion wait. (kafkajs has no synchronous poll — the buffer + `expect.poll` is the receive-side wait.)
- **Every collector uses a fresh consumer group + `fromBeginning: true`** so it reads the topic from the start
  (the log isn't drained — `fromBeginning: false` or a reused group would miss already-produced records).
- The SUT's producer/consumer is **constructor-injected** with the brokers / client — never a static client or
  a brokers string read inside a test.
- Assert the **fact**, not the absence: `expect.poll` the buffer length **before** indexing into it; an empty
  buffer that never fills fails the poll (a failed produce).
- **Order is a per-partition (per-key) guarantee** — never assert a total order across a multi-partition topic.
- **No broker DLQ** — assert the **app-level DLT** topic (`<topic>.DLT` / `<topic>-dlt`) the consumer's error
  handler produces to.
- **Independent tests:** a **uniquely named topic per file** (the log isn't consumed-and-destroyed, so a shared
  topic leaks records); messaging suites run single-worker / `test.sequential` unless verified isolated.
- **Await sends; stop collectors & disconnect producers** (a leaked consumer keeps rebalancing the group).
- Local broker = **Kafka/Redpanda via Testcontainers** (pinned image; topics created in the fixture); a shared
  test cluster reads brokers + SASL creds from **`process.env`, lazily, never logged**.
- Test names describe behaviour; one logical assertion per test; builders for 4+-field payloads; `strict: true`;
  no secrets in code.

## Cross-references

- `qa-messaging-testing-java` — the **canonical** stack, Java 21 / TestNG (`org.apache.kafka:kafka-clients`:
  `KafkaProducer`/`KafkaConsumer`, `consumer.poll(Duration)`, `auto.offset.reset=earliest`, `commitSync`,
  Awaitility for side-effects, `ConfluentKafkaContainer`/`RedpandaContainer`). This file is ported from it.
- `qa-messaging-testing-dotnet` — same skill, .NET 8 / NUnit (`Confluent.Kafka`: `ProducerBuilder`/
  `ConsumerBuilder`, `Consume(TimeSpan)` poll, `AutoOffsetReset.Earliest`, `WaitFor.Async`,
  `Testcontainers.Kafka`). Note: the JVM/.NET clients have a synchronous `poll`/`Consume`; **kafkajs does
  not** — the buffer + `expect.poll` here is the port of their bounded poll loop.
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure
  Service Bus; **the `kafka`-vs-`service-bus` boundary**: queue + peek-lock settlement + broker DLQ sub-queue vs Kafka log +
  offsets + app-level DLT.
- `references/sqs.md` (`sqs`, the immediately prior sibling) — AWS SQS; **the `kafka`-vs-`sqs`
  boundary**: delete-to-ack + visibility timeout + redrive-policy DLQ vs Kafka commit-offset + re-readable log
  + app-level DLT. Same condition-wait discipline, different broker model.
- `qa-db-connection-typescript` — the `expect.poll` and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-login-tokens-typescript` — when running against a shared cloud cluster with SASL/OAuth creds;
  the secrets-from-env discipline.
- `qa-test-reports-typescript` — attach the consumed record value / DLT payload to the Allure result.
- `qa-test-data-builder-typescript` — builders for record payloads with 4+ fields.
