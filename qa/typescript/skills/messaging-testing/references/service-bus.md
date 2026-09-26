# Messaging Testing — Azure Service Bus (Node 24 + TypeScript / Vitest)

Ported from the **canonical** `.NET` stack of the `qa/typescript/skills/messaging-testing/` node (Service Bus is
Azure-native and `Azure.Messaging.ServiceBus` is its most first-class client, so .NET led; this file
re-expresses the same model in TypeScript idioms — `@azure/service-bus`, Vitest, `expect.poll`,
Testcontainers). This node **opens the `messaging-testing` family** (service-bus → SQS → Kafka →
RabbitMQ). Translate-the-concepts, not redesign — the JS SDK mirrors the same client → sender/receiver
model.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue or topic.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has
> no synchronous return you can assert on the next line. The message is in flight; the consumer runs on its
> own schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the
> message (or its effect) to appear, with a bounded timeout — **never `setTimeout` / `page.waitForTimeout`**.
> This is the exact lineage of `qa-db-connection-typescript`'s `expect.poll` usage. Service Bus gives you a *better* primitive than
> polling for the receive side: `receiveMessages(maxCount, { maxWaitTimeInMs })` **long-polls** — it waits up
> to a bounded window for messages, then returns what arrived (possibly an empty array). That bounded wait
> *is* the condition-wait; a fixed sleep is not.

## Stack

- Node 24 + TypeScript (strict) + Vitest
- `@azure/service-bus` (the data-plane SDK — client / sender / receiver)
- `@azure/service-bus` `ServiceBusAdministrationClient` only when a test must **create/clear entities** the
  emulator config didn't pre-declare (most tests don't)
- `testcontainers` (`GenericContainer`, `Network`, `Wait`) — boots the **Azure Service Bus emulator** plus
  its required **MS SQL** sidecar on a shared network and surfaces the connection string. The Node Testcontainers binding has **no dedicated Service Bus module**,
  so wire the two `GenericContainer`s by hand
- The SUT's typed publisher/consumer is **constructor-injected** with the connection string (or an injected
  `ServiceBusClient`) — never a static connection string read inside a test

```
test/
├── fixtures/
│   ├── serviceBusBroker.ts     ← boots the emulator (+MS SQL) on a network, returns the connection string
│   └── config.json             ← declares the namespace + queues/topics the tests use
└── orderPublishing.test.ts
```

## The Service Bus model — entities, settlement, sub-queues

- **Queue** — one log, competing consumers. Send with a **sender**, receive with a **receiver**.
- **Topic + subscription** — publish once to the topic; each **subscription** gets its own copy (filtered).
  You receive via `client.createReceiver(topicName, subscriptionName)`.
- **Dead-letter queue (DLQ)** — every queue and subscription has a system **sub-queue** where messages that
  can't be processed (explicit dead-letter, max-delivery-count exceeded, TTL expiry) land. Reach it with
  `{ subQueueType: "deadLetter" }`.
- **Receive modes** (the settlement contract):
  - **Peek-lock** (`receiveMode: "peekLock"`, the **default**) — the broker hands you the message under an
    **exclusive lock** and waits for you to **settle** it: `completeMessage(msg)` (done, remove),
    `abandonMessage(msg)` (release the lock, redeliver), `deadLetterMessage(msg, options)` (move to DLQ),
    `deferMessage(msg)` (set aside). If you do nothing, the lock expires and it redelivers. This is what
    production code uses and what DLQ assertions depend on.
  - **Receive-and-delete** (`receiveMode: "receiveAndDelete"`) — the broker deletes on delivery; no
    settlement, no redelivery, no DLQ. **Convenient for test-side draining/assertion**; never for code that
    must not lose a message on a crash.

## Local broker for tests — the Azure Service Bus emulator

There is no in-memory Service Bus. For deterministic local + CI tests, run the **Azure Service Bus
emulator**, which **depends on an MS SQL** container for its store. The emulator reads a **`config.json`**
that declares the namespace, queues, topics and subscriptions up front (limits: **1 namespace, 50
queues/topics**). The connection string carries `UseDevelopmentEmulator=true`.

There's no Node Service Bus Testcontainers module, so wire the emulator + SQL sidecar by hand on a shared
network. **Never `setTimeout` for readiness** — use a
`Wait` strategy.

```typescript
// test/fixtures/serviceBusBroker.ts
import { GenericContainer, Network, Wait, type StartedTestContainer } from "testcontainers";
import path from "node:path";

export interface Broker {
  connectionString: string;
  stop: () => Promise<void>;
}

export async function startServiceBusBroker(): Promise<Broker> {
  const network = await new Network().start();

  // The emulator's required store. Pin tags, never `latest`.
  const sql = await new GenericContainer("mcr.microsoft.com/mssql/server:2022-latest")
    .withNetwork(network)
    .withNetworkAliases("sql")
    .withEnvironment({ ACCEPT_EULA: "Y", MSSQL_SA_PASSWORD: "Str0ng!Passw0rd" })
    .withWaitStrategy(Wait.forLogMessage(/SQL Server is now ready/i))
    .start();

  const emulator = await new GenericContainer(
    "mcr.microsoft.com/azure-messaging/servicebus-emulator:1.1.2",
  )
    .withNetwork(network)
    .withEnvironment({
      ACCEPT_EULA: "Y",                       // required by the emulator
      SQL_SERVER: "sql",                      // reach the sidecar by its network alias
      MSSQL_SA_PASSWORD: "Str0ng!Passw0rd",
    })
    .withCopyFilesToContainer([
      { source: path.join(__dirname, "config.json"), target: "/ServiceBus_Emulator/ConfigFiles/Config.json" },
    ])
    .withExposedPorts(5672)
    .withWaitStrategy(Wait.forLogMessage(/Emulator Service is Successfully Up/i))
    .start();

  const host = emulator.getHost();
  const port = emulator.getMappedPort(5672);
  return {
    // Emulator connection string — surfaced for injection, never logged.
    connectionString:
      `Endpoint=sb://${host}:${port};SharedAccessKeyName=RootManageSharedAccessKey;` +
      `SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;`,
    stop: async () => {
      await emulator.stop();
      await sql.stop();
      await network.stop();
    },
  };
}
```

`config.json` declares the entities the tests use:

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
> instead of the emulator, read the connection string (or an Azure AD token via `DefaultAzureCredential` +
> the namespace FQDN, `@azure/identity`) **from `process.env`, lazily** — never hard-code it, never log it
> (cross-link `qa-test-login-tokens-typescript` for the token-acquisition discipline). The emulator is the
> default for CI determinism; a shared cloud namespace makes tests order-dependent unless each uses a unique
> queue/subscription.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes; the test **drains the queue with a bounded receive** and asserts the message body and
properties. `receiveMessages(maxCount, { maxWaitTimeInMs })` long-polls — it *is* the condition-wait; an
empty array means "nothing arrived within the window" and fails the assertion deterministically.

```typescript
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { ServiceBusClient } from "@azure/service-bus";
import { startServiceBusBroker, type Broker } from "./fixtures/serviceBusBroker";
import { OrderPublisher } from "../src/orderPublisher";
import { anOrder } from "./builders/order"; // builder (qa/typescript/skills/test-data-builder)

describe("order publishing", () => {
  let broker: Broker;
  let client: ServiceBusClient;
  let sut: OrderPublisher;

  beforeAll(async () => { broker = await startServiceBusBroker(); });
  afterAll(async () => { await broker.stop(); });

  beforeEach(() => {
    client = new ServiceBusClient(broker.connectionString);
    sut = new OrderPublisher(client); // constructor injection — no static client
  });
  afterEach(async () => { await client.close(); });

  it("publishes OrderPlaced when an order is submitted", async () => {
    const order = anOrder().pending().withTotal(1999).build();

    await sut.submit(order); // SUT produces the message

    // Read-and-delete on the TEST side: we only want to see what was produced, no settlement needed.
    const receiver = client.createReceiver("orders", { receiveMode: "receiveAndDelete" });
    // Bounded long-poll = the condition-wait. Never a fixed setTimeout before receiving.
    const [message] = await receiver.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
    await receiver.close();

    expect(message, "a message published to 'orders' within the wait window").toBeDefined();
    expect(message.body.orderId).toBe(order.id); // one logical assertion: the published fact
  });

  it("stamps correlation metadata when publishing", async () => {
    const order = anOrder().pending().build();

    await sut.submit(order);

    const receiver = client.createReceiver("orders", { receiveMode: "receiveAndDelete" });
    const [message] = await receiver.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
    await receiver.close();

    expect(message).toBeDefined();
    expect(message).toMatchObject({ // one behaviour: the message envelope
      subject: "OrderPlaced",
      correlationId: order.id,
      contentType: "application/json",
    });
  });
});
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so use
`expect.poll` to wait on a condition. This reuses `qa-db-connection-typescript`'s discipline.

```typescript
it("writes a shipment row when an OrderPaid message is consumed", async () => {
  const orderId = crypto.randomUUID();

  // 1. Seed the input message onto the queue the consumer listens to.
  const sender = client.createSender("orders");
  await sender.sendMessages({
    body: { orderId },
    subject: "OrderPaid",
    contentType: "application/json",
    correlationId: orderId,
  });
  await sender.close();

  // 2. The SUT (a ServiceBusReceiver-based consumer) is already running and picks it up.

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
> message probably arrived by now", which races the broker.

## Peek-lock vs receive-and-delete — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs in
**peek-lock** (production default) and explicitly settles. When the **test** drains a queue just to assert
what's there, **receive-and-delete** is simpler (no lock to manage). Pick by role:

| Side | Mode | Why |
|------|------|-----|
| Test asserting *what was produced* (drain + read) | `"receiveAndDelete"` | No settlement bookkeeping; you only want to see the message |
| Test exercising the *consumer's* settlement logic | `"peekLock"` | Lets you assert complete vs abandon vs deadLetter and redelivery |

```typescript
// Consumer settlement — peek-lock, explicit settle:
const receiver = client.createReceiver("orders"); // peekLock is the default
const [msg] = await receiver.receiveMessages(1, { maxWaitTimeInMs: 10_000 });

if (canProcess(msg)) {
  await receiver.completeMessage(msg); // remove it — processed
} else {
  await receiver.deadLetterMessage(msg, {
    deadLetterReason: "ValidationFailed",
    deadLetterErrorDescription: "missing customerId",
  }); // move to DLQ with a reason
}
await receiver.close();
```

## Dead-letter-queue assertions

A common, high-value assertion: **a message that failed processing landed in the DLQ** (either the consumer
explicitly dead-lettered it, or it exceeded `MaxDeliveryCount`). Receive from the **DLQ sub-queue**:

```typescript
it("dead-letters the message when the order payload is invalid", async () => {
  const sender = client.createSender("orders");
  await sender.sendMessages({
    body: "{ not valid order json }",
    subject: "OrderPaid",
    contentType: "application/json",
  });
  await sender.close();

  // The consumer (SUT) rejects it and dead-letters it. Assert on the DLQ.
  const dlq = client.createReceiver("orders", { subQueueType: "deadLetter" });
  // Bounded long-poll the DLQ — wait on the condition (a message lands), not a sleep.
  const [dead] = await dlq.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
  await dlq.close();

  expect(dead, "the poison message in the dead-letter queue").toBeDefined();
  expect(dead.deadLetterReason).toBe("ValidationFailed"); // the documented reason
});
```

For a **topic subscription's** DLQ, the sub-queue hangs off the subscription:
`client.createReceiver("order-events", "fulfilment", { subQueueType: "deadLetter" })`.

## Topics, subscriptions & filters

Publish to a **topic**; assert each **subscription** received the copy it should. Subscription **filters**
(SQL filters on properties, or correlation filters) mean not every subscription gets every message — assert
the routing, not just the publish.

```typescript
it("fans out to fulfilment and audit when an order event is published", async () => {
  const sender = client.createSender("order-events");
  await sender.sendMessages({
    body: { orderId: crypto.randomUUID() },
    subject: "OrderPlaced",
    applicationProperties: { region: "EU" }, // a SQL filter on the subscription can match this
  });
  await sender.close();

  // Each subscription gets its own copy — read from both.
  const fulfilment = client.createReceiver("order-events", "fulfilment", { receiveMode: "receiveAndDelete" });
  const audit = client.createReceiver("order-events", "audit", { receiveMode: "receiveAndDelete" });

  const [toFulfilment] = await fulfilment.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
  const [toAudit] = await audit.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
  await fulfilment.close();
  await audit.close();

  expect(toFulfilment, "fulfilment subscription copy").toBeDefined(); // one behaviour: the fan-out
  expect(toAudit, "audit subscription copy").toBeDefined();
});
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain with `receiveMessages(maxCount, { maxWaitTimeInMs })` and
count — the bounded wait stops it hanging when fewer than N arrive:

```typescript
const receiver = client.createReceiver("orders", { receiveMode: "receiveAndDelete" });
const batch = await receiver.receiveMessages(10, { maxWaitTimeInMs: 5_000 });
await receiver.close();
expect(batch).toHaveLength(3); // SUT produced exactly 3
```

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 5000))` / `page.waitForTimeout` before receiving / asserting the
  side-effect.** Races the broker and the consumer; slow and flaky. *Fix:* `receiveMessages(n, { maxWaitTimeInMs })`
  for the receive side (it long-polls), and `expect.poll` for consumer side-effects. The wait passes the
  instant the condition holds and *fails* if it never does.
- **Asserting on a peek-locked message but never settling it.** The lock expires, the message redelivers, and
  the next test sees a "phantom" message. *Fix:* `completeMessage` (or dead-letter) every message you
  peek-lock, or drain with `receiveAndDelete` when you only need to read.
- **Sharing one queue across parallel test files.** Vitest runs files in parallel; competing receivers steal
  each other's messages. *Fix:* a unique queue/subscription per file, drain residuals in `beforeEach`, or
  `test.sequential` / a single worker for messaging suites.
- **Not draining residual messages between tests.** *Fix:* drain-to-empty in `beforeEach` (receive in a loop
  until the array is empty), or a fresh queue per test.
- **Reading the connection string inside a test / hard-coding it.** *Fix:* surface it from the fixture
  (emulator) or `process.env` (cloud test namespace), inject it; never log it.
- **Treating an empty array as success.** Empty means nothing arrived in the window — a failed produce, not a
  pass. *Fix:* `expect(message).toBeDefined()` first.
- **Using `receiveAndDelete` to test the consumer's settlement logic.** You can't assert complete vs abandon
  vs deadLetter if the broker already deleted it. *Fix:* peek-lock when settlement is under test.

## Examples

**End-to-end: a consume → process → republish flow, asserted on the side-message.**

```typescript
describe("fulfilment consumer", () => {
  let broker: Broker;
  let client: ServiceBusClient;

  beforeAll(async () => { broker = await startServiceBusBroker(); });
  afterAll(async () => { await broker.stop(); });

  beforeEach(async () => {
    client = new ServiceBusClient(broker.connectionString);
    await drain(client, "orders");    // independent tests — start from empty
    await drain(client, "shipments");
  });
  afterEach(async () => { await client.close(); });

  it("publishes ShipmentReady when a valid OrderPaid is consumed", async () => {
    const orderId = crypto.randomUUID();
    const sender = client.createSender("orders");
    await sender.sendMessages({
      body: { orderId }, subject: "OrderPaid", contentType: "application/json", correlationId: orderId,
    });
    await sender.close();

    // The SUT consumer processes "orders" and republishes onto "shipments".
    const shipments = client.createReceiver("shipments", { receiveMode: "receiveAndDelete" });
    const [ready] = await shipments.receiveMessages(1, { maxWaitTimeInMs: 10_000 });
    await shipments.close();

    expect(ready, "consumer republished a ShipmentReady message").toBeDefined();
    expect(ready.correlationId).toBe(orderId); // correlation preserved
  });
});

async function drain(client: ServiceBusClient, queue: string): Promise<void> {
  const receiver = client.createReceiver(queue, { receiveMode: "receiveAndDelete" });
  let batch = await receiver.receiveMessages(10, { maxWaitTimeInMs: 500 });
  while (batch.length > 0) batch = await receiver.receiveMessages(10, { maxWaitTimeInMs: 500 });
  await receiver.close();
}
```

Lifecycle for this test:
1. `beforeAll` boots the emulator + MS SQL once on a shared network; the connection string is surfaced.
   Entities come from `config.json`.
2. `beforeEach` drains the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the output
   queue (the condition-wait) and asserts correlation was preserved.
4. `afterEach` closes the client; `afterAll` stops the broker + SQL sidecar + network.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```typescript
export const anOrder = () => new OrderBuilder().status("Pending");
// anOrder().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/typescript/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `receiveMessages(n, { maxWaitTimeInMs })` for
  the receive side (bounded long-poll); `expect.poll` for consumer side-effects. **No `setTimeout` /
  `waitForTimeout`** as an assertion wait.
- The SUT's publisher/consumer is **constructor-injected** with the `ServiceBusClient` / connection string —
  never a static client or a connection string read inside a test.
- **Settle every peek-locked message** (`completeMessage` / `abandonMessage` / `deadLetterMessage`), or use
  `receiveAndDelete` when the test only reads. Never leave a lock to expire and redeliver into the next test.
- **Independent tests:** unique queue/subscription per file **or** drain-to-empty in `beforeEach`; messaging
  suites run single-worker / `test.sequential` unless verified isolated.
- Assert the **fact**, not the absence: an empty array is a *failed* produce — `toBeDefined()` before reading
  the body.
- **`await` and `close()` every sender/receiver/client**; the SDK's network calls are bounded by the
  `maxWaitTimeInMs` you pass — never await unbounded.
- Local broker = the **emulator via Testcontainers** (pinned image + MS SQL sidecar + `config.json`, wired by
  hand — no Node SB module); a cloud test namespace's connection string/token comes from **`process.env`, read
  lazily, never logged**.
- Test names describe behaviour; one logical assertion per test; builders for 4+-field payloads; `strict: true`;
  no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical** stack, .NET 8 / NUnit
  (`Azure.Messaging.ServiceBus`: `new ServiceBusClient(...)`, `CreateReceiver(queue, options)`,
  `ReceiveMessageAsync(maxWaitTime)`, `SubQueue.DeadLetter`, `WaitFor.Async` poll). This file is ported from it.
- `qa-messaging-testing-java` — same skill, Java 21 / TestNG
  (`azure-messaging-servicebus`: `ServiceBusClientBuilder`, `receiveMessages(n, maxWaitTime)`,
  `SubQueue.DEAD_LETTER`, Awaitility).
- `references/sqs.md` (`sqs`, next in family) — AWS SQS/SNS on LocalStack; visibility timeout +
  redrive-policy DLQ — same condition-wait discipline, different broker. Then Kafka (`kafka`, offset-based) and
  RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-connection-typescript` — the `expect.poll` and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-login-tokens-typescript` — when authing to a cloud test namespace with an Azure AD token
  (`@azure/identity` `DefaultAzureCredential`) instead of the emulator connection string; secrets-from-env.
- `qa-test-reports-typescript` — attach the received message body / DLQ reason to the Allure result.
- `qa-test-data-builder-typescript` — builders for message payloads with 4+ fields.
