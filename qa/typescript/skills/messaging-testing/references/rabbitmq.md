# Messaging Testing — RabbitMQ / AMQP (Node 20 + TypeScript / Vitest)

This is the **TypeScript** sibling of the `qa/typescript/skills/messaging-testing/` node, the **fourth and final
`messaging-testing` sibling** (service-bus → SQS → Kafka → **RabbitMQ**) — building it
**closes the family**. The **canonical stack is .NET** (`qa-messaging-testing-dotnet`): RabbitMQ's
clients are first-class across all three stacks, so .NET was chosen to keep the family .NET-led for three of
its four siblings. This file is a **direct port** — same section order, same concepts, re-expressed in Node 20
+ TypeScript (strict) / Vitest idioms with `amqplib`.

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
> message (or its effect) to appear, with a bounded timeout — **never `setTimeout` / `page.waitForTimeout`**.
> This is the exact lineage of `qa-db-testing-client-typescript`'s `expect.poll` usage and
> `references/service-bus.md`'s condition-wait. RabbitMQ's pull primitive,
> `channel.get(queue, { noAck })`, resolves to a message **or `false` immediately** — so wrapping it in
> `expect.poll` (get until a message appears, or a deadline passes) *is* the condition-wait; a fixed sleep
> is not.

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
  **dropped** (unless published `{ mandatory: true }`, which returns it). **This is the sharpest contrast with
  Kafka's retained log** — RabbitMQ does **not** keep a message for a queue that didn't exist when it was
  published. **Consequence for tests:** to producer-assert, the test queue **must be declared and bound to the
  exchange *before* the SUT publishes**. (See the `RabbitProbe` and producer-assert pattern below.)
- **Manual ack — the consume-and-settle contract.** Consume with **`{ noAck: false }`**: the broker delivers
  the message and waits for you to settle it.
  - `channel.ack(msg)` — processed, remove it (the Service Bus `complete` / SQS `deleteMessage` analogue).
  - `channel.nack(msg, false, true)` / `channel.reject(msg, true)` — failed, **put it back** on the queue →
    redelivered (the peek-lock `abandon` / SQS visibility-timeout analogue).
  - `channel.nack(msg, false, false)` / `channel.reject(msg, false)` — failed, **don't requeue** → routed to
    the **dead-letter exchange** if one is configured, else discarded.
  - **Un-acked on channel/connection close → automatically requeued and redelivered** (the lock-expiry
    analogue). So an un-settled message is never silently lost — it comes back.
- **Dead-letter exchange (DLX) — broker-native, like `service-bus`/`sqs`'s DLQ, *unlike* Kafka's app-level DLT.** A queue
  declared with the argument **`x-dead-letter-exchange`** (amqplib also exposes the `deadLetterExchange`
  option shortcut) sends its dead-lettered messages — **rejected/nacked with `requeue=false`**, **TTL-expired**,
  or **max-length-dropped** — to that exchange, which routes them to a **dead-letter queue** you assert on.
  This is broker plumbing, not application code (the contrast to assert against Kafka's `<topic>.DLT`).
- **Prefetch / QoS.** `channel.prefetch(n)` caps how many un-acked messages the broker hands a consumer at
  once — back-pressure. Rarely the thing under assertion; declare it where the consumer's concurrency matters,
  and otherwise leave it.

## Stack

- Node 20 + TypeScript (`strict: true`) + Vitest — **async all the way** (`await amqp.connect`,
  `await channel.assertQueue`, `await channel.get`; every AMQP call is a promise)
- `amqplib` (the AMQP client — `connect` / `Connection` / `Channel`). Use the promise API
  (`import amqp from 'amqplib'`), not the callback variant.
- `@testcontainers/rabbitmq` (`RabbitMQContainer`) — boots a **local RabbitMQ broker** and surfaces
  `getAmqpUrl()` (cross-link `qa-test-environments-typescript`)
- The SUT's typed publisher/consumer takes the AMQP URL (or an injected `Connection`) via its **constructor /
  factory** — never a module-level URL read inside a test

```
test/messaging/
├── rabbit-fixture.ts       ← boots the broker, declares exchanges/queues/bindings, exposes the AMQP URL
├── rabbit-probe.ts         ← test-side reader: bounded channel.get poll over a bound test queue (the "drain")
└── order-publishing.test.ts
```

## Local broker for tests — RabbitMQ via Testcontainers

There is no in-memory RabbitMQ. For deterministic local + CI tests, run a **real broker in a container** and
point the client at `getAmqpUrl()`. The `@testcontainers/rabbitmq` module wires it up, waits for readiness,
and exposes the AMQP URL. Reuse the fixture discipline from `qa-test-environments-typescript` (boot once per
suite; **never `setTimeout` for readiness** — the container owns the wait strategy). **Declare the topology —
exchanges, queues, bindings — up front** (RabbitMQ auto-declares nothing, and routing happens at publish time,
so the bindings must pre-exist).

```typescript
import amqp from "amqplib";
import { RabbitMQContainer, type StartedRabbitMQContainer } from "@testcontainers/rabbitmq";

export interface RabbitFixture {
  amqpUrl: string;
  stop: () => Promise<void>;
}

export async function startRabbit(): Promise<RabbitFixture> {
  // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
  const broker: StartedRabbitMQContainer = await new RabbitMQContainer(
    "rabbitmq:3.13-management",
  ).start();
  const amqpUrl = broker.getAmqpUrl(); // amqp://guest:guest@host:port

  await declareTopology(amqpUrl);

  return { amqpUrl, stop: () => broker.stop().then(() => undefined) };
}

// Declare the AMQP topology once: the order exchange, the consumer's queue (with a DLX), the
// dead-letter exchange + queue, and the bindings. Routing is at publish time, so this must pre-exist.
async function declareTopology(amqpUrl: string): Promise<void> {
  const conn = await amqp.connect(amqpUrl);
  const channel = await conn.createChannel();

  await channel.assertExchange("orders", "topic", { durable: false });
  await channel.assertExchange("orders.dlx", "fanout", { durable: false });

  // The consumer's work queue dead-letters rejected/expired messages to orders.dlx.
  await channel.assertQueue("orders.q", {
    durable: false,
    arguments: { "x-dead-letter-exchange": "orders.dlx" },
  });
  await channel.bindQueue("orders.q", "orders", "order.#");

  // The dead-letter queue you assert on.
  await channel.assertQueue("orders.dlq", { durable: false });
  await channel.bindQueue("orders.dlq", "orders.dlx", ""); // fanout ignores the routing key

  await channel.close();
  await conn.close();
}
```

> **Cloud / shared test broker alternative.** If your org runs against a real **test** RabbitMQ broker instead
> of a container, read the AMQP URI (and credentials) from `process.env`, **lazily** — never hard-code it,
> never log it (cross-link `qa-auth0-test-tokens-typescript` for the secrets-from-env discipline). A container
> is the default for CI determinism; a shared broker makes tests order-dependent unless each uses a
> **uniquely named queue** (since a queue retains messages until they're consumed).

## The test-side reader — `RabbitProbe` (the "drain" analogue)

The test reads a queue by **polling `channel.get` in `expect.poll`** until a message appears or a deadline
passes — that *is* the condition-wait. `channel.get` is a single pull (resolves to a message or `false`
immediately), so `expect.poll`, not the call, supplies the wait. The probe acks what it reads so the queue
empties cleanly.

```typescript
import amqp, { type Channel, type Connection } from "amqplib";
import { expect } from "vitest";

export class RabbitProbe {
  constructor(private readonly amqpUrl: string) {}

  /** Pull one message from `queue` within `timeoutMs`, via expect.poll. Returns the body string, or null if
   *  nothing arrived in the window. Acks what it reads (a test probe drains, it doesn't requeue). */
  async get(queue: string, timeoutMs = 10_000): Promise<string | null> {
    const conn: Connection = await amqp.connect(this.amqpUrl);
    const channel: Channel = await conn.createChannel();
    try {
      // expect.poll re-invokes the getter on an interval until it returns truthy or the timeout fails the test.
      let body: string | null = null;
      await expect
        .poll(
          async () => {
            const msg = await channel.get(queue, { noAck: false }); // single pull
            if (msg === false) return null;
            channel.ack(msg); // drain → ack
            body = msg.content.toString();
            return body;
          },
          { timeout: timeoutMs, interval: 100 },
        )
        .not.toBeNull();
      return body;
    } finally {
      await channel.close();
      await conn.close();
    }
  }
}
```

> `expect.poll` re-invokes the getter on the interval and resolves the instant it returns a message — it does
> **not** wait the full timeout when a message is present, and it *fails the test* if the window passes empty.
> That is the condition-wait; a bare `await new Promise(r => setTimeout(r, 5000))` "until the message probably
> arrived" races the broker and is banned. (When you only need the value, not an inline assertion, a small
> bounded `while (Date.now() < deadline)` loop around `channel.get` is the equivalent — never an unbounded one.)

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes to the **exchange**; the test reads the **bound queue** and asserts the body and properties.
Because RabbitMQ routes at publish time, the queue must be **declared and bound before the SUT publishes** —
the fixture's `declareTopology` did that. A `null` result means "nothing routed here within the window" — a
failed produce, asserted deterministically.

```typescript
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import amqp, { type Connection } from "amqplib";
import { startRabbit, type RabbitFixture } from "./rabbit-fixture";
import { RabbitProbe } from "./rabbit-probe";
import { OrderPublisher } from "../../src/messaging/order-publisher";
import { orders } from "../builders/orders"; // qa/typescript/skills/test-data-builder

describe("OrderPublisher", () => {
  let fixture: RabbitFixture;
  let probe: RabbitProbe;
  let conn: Connection;
  let sut: OrderPublisher;

  beforeAll(async () => {
    fixture = await startRabbit();
    probe = new RabbitProbe(fixture.amqpUrl);
  });
  afterAll(async () => await fixture.stop());

  beforeEach(async () => {
    conn = await amqp.connect(fixture.amqpUrl);
    sut = new OrderPublisher(conn); // constructor injection — no module-level connection
  });

  it("Should_publish_OrderPlaced_When_an_order_is_submitted", async () => {
    const order = orders.pending().withTotal(1999).build();

    await sut.submit(order); // SUT publishes to the "orders" exchange

    // Read the bound test queue; the expect.poll get is the condition-wait. Never a fixed setTimeout.
    const body = await probe.get("orders.q", 10_000);

    expect(body, "no message was routed to 'orders.q' within the wait window").not.toBeNull();
    const placed = JSON.parse(body!) as { orderId: string };
    expect(placed.orderId).toBe(order.id); // one logical assertion: the published fact
  });
});
```

> **Producer-assert with a dedicated probe queue.** If the SUT publishes to an exchange whose only bound queue
> is the *real* consumer's (so reading it would steal the consumer's work), declare an **exclusive,
> auto-delete test queue** bound to the same exchange + routing key in `beforeEach`, and read *that* — a topic/
> direct exchange delivers a copy to every matching binding, so your probe queue and the real queue each get
> one. (This is the fanout-style "give me my own copy" trick; it only works because the binding pre-exists the
> publish.)

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer** (a `channel.consume` callback). The test **publishes an input message**, lets
the consumer run, and waits for the observable side-effect (a DB row, another message) — eventually
consistent, so use **`expect.poll`** on a probe. This reuses `qa-db-testing-client-typescript`'s discipline.

```typescript
it("Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed", async () => {
  const orderId = crypto.randomUUID();

  // 1. Publish the input message to the exchange the consumer's queue is bound to.
  const channel = await conn.createChannel();
  channel.publish("orders", "order.paid", Buffer.from(JSON.stringify({ orderId })), {
    contentType: "application/json",
    correlationId: orderId,
  });
  await channel.close();

  // 2. The SUT consumer is already running and picks it up.

  // 3. Wait on the SIDE-EFFECT, not on a clock. Poll the DB probe until the row appears (or time out).
  await expect
    .poll(() => shipmentsProbe.getByOrderId(orderId), { timeout: 10_000, interval: 200 })
    .toMatchObject({ orderId, status: "Ready" }); // one logical assertion: the side-effect
});
```

> `expect.poll` re-invokes the probe and resolves the instant the condition holds, failing if it never does.
> That is the condition-wait — **never** `await new Promise(r => setTimeout(r, 5000))` standing in for "the
> message probably arrived by now", which races the broker.

## Manual ack / nack / reject — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs with
**`{ noAck: false }`** and explicitly settles each message. The settlement choice is what later DLX assertions
depend on, so model it the way production does:

| Outcome | Call | Effect |
|---------|------|--------|
| Processed OK | `channel.ack(msg)` | Remove the message (the `complete` / `deleteMessage` analogue) |
| Transient failure, retry | `channel.nack(msg, false, true)` | Put it back → redelivered (the `abandon` / visibility-timeout analogue) |
| Permanent failure, dead-letter | `channel.nack(msg, false, false)` | Don't requeue → routed to the DLX (or discarded if none) |
| Single-message reject | `channel.reject(msg, false)` | Like nack, but exactly one message |

```typescript
// Consumer settlement — manual ack on a channel.consume callback:
const channel = await conn.createChannel();
await channel.prefetch(10); // back-pressure (optional)

await channel.consume(
  "orders.q",
  (msg) => {
    if (msg === null) return; // consumer cancelled
    if (canProcess(msg.content)) channel.ack(msg); // done — remove it
    else channel.nack(msg, false, false); // → dead-letter exchange
  },
  { noAck: false },
);
```

> **Un-acked messages come back.** If a consumer reads with `{ noAck: false }` and the channel closes before
> it acks, the broker **requeues** the message — so a crashed consumer never silently loses work. In tests
> this means: ack (or nack) every message you consume, or you'll see it **redelivered** into the next test.
> The redelivery is also *assertable* — `msg.fields.redelivered` is `true` on a second delivery.

## Dead-letter-exchange assertions

A common, high-value assertion: **a message that failed processing landed in the dead-letter queue.** The work
queue was declared with `x-dead-letter-exchange: "orders.dlx"` (fixture topology), so a
`channel.nack(msg, false, false)` / `channel.reject(msg, false)` — or a TTL expiry, or a max-length drop —
routes the message through the DLX to `orders.dlq`. Read **that** queue:

```typescript
it("Should_dead_letter_the_message_When_the_order_payload_is_invalid", async () => {
  const channel = await conn.createChannel();
  channel.publish("orders", "order.paid", Buffer.from("{ not valid order json }"), {
    contentType: "application/json",
  });
  await channel.close();

  // The consumer (SUT) rejects it with requeue=false → it routes through orders.dlx to orders.dlq.
  // expect.poll the DLQ — wait on the condition (a message lands), not a sleep.
  const dead = await probe.get("orders.dlq", 10_000);

  expect(dead, "expected the poison message in the dead-letter queue").not.toBeNull();
  expect(dead).toContain("not valid order json"); // the original payload
});
```

> RabbitMQ adds an `x-death` header (count, reason — `rejected` / `expired` / `maxlen` — original exchange and
> routing key) to a dead-lettered message. Read it from `msg.properties.headers["x-death"]` when you need to
> prove **why** it was dead-lettered, not just that it landed.

## Exchanges, routing keys & bindings

The AMQP routing model is the distinctive part. Assert the **routing**, not just the publish — that a message
with routing key K reached the queues bound for K, and didn't reach the ones that weren't.

```typescript
it("Should_route_only_eu_orders_to_the_eu_queue_When_publishing_by_region", async () => {
  // Topic exchange "orders"; eu.q bound with "order.eu.*", us.q bound with "order.us.*" (in fixture setup).
  const channel = await conn.createChannel();
  channel.publish("orders", "order.eu.placed", Buffer.from(JSON.stringify({ orderId: crypto.randomUUID() })));
  await channel.close();

  const toEu = await probe.get("orders.eu.q", 10_000);
  const toUs = await probe.get("orders.us.q", 2_000); // short window — expect nothing

  expect(toEu, "EU order did not reach the EU queue").not.toBeNull(); // one behaviour: the topic routing
  expect(toUs, "EU order was wrongly routed to the US queue").toBeNull();
});
```

A **fanout** exchange (routing key ignored) is the broadcast / SNS-fan-out analogue — every bound queue gets a
copy; assert each one received it. A **direct** exchange routes on an exact routing-key match.

## Receiving a batch / draining

To assert "exactly N messages were produced", pull in a bounded loop and count — the timeout stops it hanging
when fewer than N arrive. (Extend `RabbitProbe` with a `getMany(queue, max, timeoutMs)` that loops
`channel.get` until `max` or the deadline; it acks each.)

```typescript
const batch = await probe.getMany("orders.q", 10, 5_000);
expect(batch).toHaveLength(3); // SUT produced exactly 3
```

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 5000))` before reading / before asserting the side-effect.** Races
  the broker and the consumer; slow and flaky. *Fix:* the `RabbitProbe` `expect.poll` over `channel.get` for
  the receive side, and `expect.poll` for consumer side-effects — each resolves the instant the condition holds
  and *fails* if it never does.
- **Publishing before the test queue is declared and bound.** RabbitMQ routes at publish time and **drops** a
  message with no matching bound queue — the probe then reads nothing and the assert flakes for the wrong
  reason. *Fix:* declare exchanges/queues/bindings in `beforeAll` (the fixture topology) **before** any publish;
  for a dedicated probe queue, bind it in `beforeEach`.
- **Consuming with `{ noAck: true }` when testing settlement.** The broker removes the message on delivery, so
  you can't assert ack-vs-nack-vs-dead-letter or redelivery. *Fix:* `{ noAck: false }` and settle explicitly.
- **Leaving a consumed message un-acked across tests.** On channel close the broker **requeues** it, and the
  next test sees a "phantom" redelivery. *Fix:* ack (or nack) every message; the `RabbitProbe` acks what it
  drains.
- **Expecting an app-level DLT topic (the Kafka habit).** RabbitMQ dead-lettering is **broker-native** — a
  `x-dead-letter-exchange` queue argument, not application code. *Fix:* declare the DLX + DLQ in the topology
  and assert the **DLQ**; don't look for a `<topic>.DLT`.
- **Treating a `false` / `null` `get` result as success.** It means nothing was on the queue in the window —
  that's a failed produce, not a pass. *Fix:* `expect(body).not.toBeNull()` before parsing.
- **Sharing one queue across parallel test files.** Vitest runs files in parallel workers; competing consumers
  steal each other's messages. *Fix:* a **uniquely named queue per file** (or run messaging files
  single-threaded), and drain leftovers in `beforeEach`.
- **Reading the AMQP URL at module scope / hard-coding it.** *Fix:* surface it from the fixture (container) or
  `process.env` (shared broker), inject it; never log it.
- **Reaching for RabbitMQ when the dependency is an HTTP call.** *Fix:* `qa-api-mocking-typescript` —
  messaging is for async queues/exchanges, not request/response fakes.

## Examples

**End-to-end: a consume → process → publish flow, asserted on the output queue, with the poison case routed to
the DLQ.**

```typescript
describe("FulfilmentConsumer", () => {
  let fixture: RabbitFixture;
  let probe: RabbitProbe;
  let conn: Connection;

  beforeAll(async () => {
    fixture = await startRabbit();
    probe = new RabbitProbe(fixture.amqpUrl);
  });
  afterAll(async () => await fixture.stop());

  beforeEach(async () => {
    conn = await amqp.connect(fixture.amqpUrl);
    await drain("orders.q"); // independent tests — start from empty
    await drain("shipments.q");
  });

  it("Should_publish_ShipmentReady_When_a_valid_OrderPaid_is_consumed", async () => {
    const orderId = crypto.randomUUID();
    const channel = await conn.createChannel();
    channel.publish("orders", "order.paid", Buffer.from(JSON.stringify({ orderId })), {
      contentType: "application/json",
      correlationId: orderId,
    });
    await channel.close();

    // The SUT consumer processes "orders.q" and publishes onto the "shipments" exchange → "shipments.q".
    const ready = await probe.get("shipments.q", 10_000);

    expect(ready, "consumer did not publish a ShipmentReady message").not.toBeNull();
    const shipment = JSON.parse(ready!) as { orderId: string };
    expect(shipment.orderId).toBe(orderId); // correlation preserved
  });

  async function drain(queue: string): Promise<void> {
    while ((await probe.get(queue, 300)) !== null) {
      /* drain to empty */
    }
  }
});
```

Lifecycle for this test:
1. `beforeAll` boots the broker once and declares the exchanges/queues/bindings; the AMQP URL is surfaced.
2. `beforeEach` opens a connection and drains the queues so the test starts from empty — tests stay
   independent and order-free.
3. The test publishes an input message; the running SUT consumer publishes onto the output exchange; the test
   **`expect.poll`s** the output queue (the condition-wait) and asserts correlation was preserved.
4. `afterAll` stops the broker.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```typescript
export const orders = {
  pending: () => new OrderBuilder().withStatus("Pending"),
};
// orders.pending().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/typescript/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `expect.poll` over `channel.get` for the
  receive side; `expect.poll` for consumer side-effects. **No `setTimeout`-as-wait / `waitForTimeout`** —
  `setTimeout` only as the poll cadence inside a bounded helper (and `expect.poll`'s `interval` already does
  that for you).
- **Declare the topology before publishing.** Exchanges, queues, and bindings in `beforeAll` (or a probe queue
  in `beforeEach`) — RabbitMQ routes at publish time and drops messages with no matching bound queue.
- The SUT's publisher/consumer is **constructor-injected** with the `Connection` / AMQP URL — never a
  module-level connection or a URL read inside a test.
- **Consume with `{ noAck: false }` and settle every message** (`ack` / `nack` / `reject`). Never leave a
  message un-acked into the next test — it requeues and redelivers.
- **Dead-lettering is broker-native** — declare `x-dead-letter-exchange` + a DLX + a dead-letter queue and
  assert the **DLQ**; don't expect a Kafka-style app-level DLT.
- Assert the **fact**, not the absence: a `false`/`null` `get` result is a *failed* produce — `not.toBeNull()`
  before parsing the body.
- **Close** every connection/channel (in `finally` / `afterAll`); never leak them across tests.
- **Independent tests:** a uniquely named queue per file **or** drain-to-empty in `beforeEach`; run messaging
  files single-threaded unless verified isolated.
- Local broker = **RabbitMQ via Testcontainers** (pinned image); a shared test broker's AMQP URI/credentials
  come from `process.env`, **read lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test; builders for 4+-field payloads; structured
  logging; no secrets in code; `strict: true`.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical stack** (.NET 8 / NUnit, `RabbitMQ.Client` v7:
  `CreateChannelAsync`, `ExchangeDeclareAsync` / `QueueDeclareAsync(args)` / `QueueBindAsync`,
  `BasicPublishAsync`, `AsyncEventingBasicConsumer` + `BasicConsumeAsync(autoAck:false)`, `BasicAckAsync` /
  `BasicNackAsync` / `BasicRejectAsync`, `BasicGetAsync`, `Testcontainers.RabbitMq`). This file is its port.
- `qa-messaging-testing-java` — same skill, Java 21 / TestNG (`com.rabbitmq:amqp-client`:
  `ConnectionFactory().setUri(...)`, `exchangeDeclare` / `queueDeclare(args)` / `queueBind`, `basicPublish`,
  `basicConsume(queue, false, callback)` + `basicAck`/`basicNack`/`basicReject`, `basicGet` polling, Awaitility
  for side-effects; **Spring AMQP** noted for the listener/DLX convention; `RabbitMQContainer`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure
  Service Bus; **the `rabbitmq`-vs-`service-bus` parallel**: RabbitMQ's manual ack + broker-native DLX is the **closest** of the
  three siblings to Service Bus's peek-lock + DLQ sub-queue — same consume-and-settle shape, different routing.
- `references/sqs.md` — AWS SQS; same parallel (delete-to-ack + redrive-policy DLQ ≈
  RabbitMQ's ack + DLX). Same condition-wait discipline, different broker.
- `references/kafka.md` (`kafka`, the immediately prior sibling) — **the `rabbitmq`-vs-`kafka` boundary**:
  Kafka log + offsets + app-level DLT vs RabbitMQ queue + manual ack + broker-native DLX. (Note: kafkajs has
  no synchronous poll, so its probe is a collector buffer; RabbitMQ's `channel.get` is a real pull, so the
  probe is the cleaner `expect.poll` loop.)
- `qa-db-testing-client-typescript` — the `expect.poll` and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-environments-typescript` — booting the RabbitMQ container; the per-suite lifecycle and
  readiness-wait discipline (never `setTimeout`) mirrored here.
- `qa-auth0-test-tokens-typescript` — when authing to a shared cloud broker with credentials from env;
  the secrets-from-env discipline.
- `qa-api-mocking-typescript` — the *synchronous* counterpart: fake an HTTP dependency the SUT calls.
  The boundary: MSW = request/response fake; RabbitMQ = async exchange/queue assertions.
- `qa-allure-reporting-typescript` — attach the consumed message body / DLQ `x-death` reason to the Allure result.
- `qa-test-data-builder-typescript` — builders/ObjectMother for message payloads with 4+ fields.
