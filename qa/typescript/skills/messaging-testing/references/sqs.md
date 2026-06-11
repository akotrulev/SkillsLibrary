# Messaging Testing — AWS SQS / SNS (Node 20 + TypeScript / Vitest)

Ported from the **canonical** `.NET` stack of the `qa/typescript/skills/messaging-testing/` node (.NET led this node by the
user's choice; this file re-expresses the same model in TypeScript idioms — `@aws-sdk/client-sqs`/`client-sns`,
Vitest, `expect.poll`, Testcontainers). This is the **second `messaging-testing` sibling** (service-bus →
**SQS** → Kafka → RabbitMQ); it keeps the **same two assertion patterns and the same
eventual-consistency condition-wait discipline** as `service-bus` — only the broker SDK and its settlement semantics
change. Translate-the-concepts, not redesign — the JS AWS SDK v3 mirrors the same send / receive / delete
model.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The message is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the message
> (or its effect) to appear, with a bounded timeout — **never `setTimeout` / `page.waitForTimeout`**. This is
> the exact lineage of `qa-db-testing-client-typescript`'s `expect.poll` usage and
> `references/service-bus.md`'s condition-wait. SQS gives you the **`WaitTimeSeconds`
> long-poll** as a better primitive than spin-polling for the receive side: `ReceiveMessageCommand` with
> `WaitTimeSeconds` waits up to a bounded window (max **20s**) for a message to arrive, then returns it or an
> undefined/empty `Messages` array. That bounded wait *is* the condition-wait; a fixed sleep is not.

## Stack

- Node 20 + TypeScript (strict) + Vitest
- `@aws-sdk/client-sqs` (`SQSClient` + command objects — send / receive / delete / queue attributes) and
  `@aws-sdk/client-sns` (`SNSClient`) for SNS→SQS fan-out
- `@testcontainers/localstack` (`LocalstackContainer`) — boots **LocalStack** (the local AWS emulator) and
  surfaces a connection URI the SDK clients point at via `endpoint` (cross-link
  `qa-test-environments-typescript`)
- The SUT's typed publisher/consumer is **constructor-injected** with the `SQSClient` (or the resolved queue
  URL) — never a static client or an endpoint read inside a test

```
test/
├── fixtures/
│   └── sqsBroker.ts        ← boots LocalStack, creates the queues (+DLQ via redrive), returns the client + URLs
└── orderPublishing.test.ts
```

## The SQS model — visibility timeout, redrive → DLQ, FIFO, SNS fan-out

SQS has **no peek-lock and no per-message ack**. The whole settlement model is:

- **Queue** — competing consumers; one `ReceiveMessageCommand` returns up to 10 messages and **hides** each
  one for its **visibility timeout** instead of removing it. You then call **`DeleteMessageCommand`** (with the
  message's **`ReceiptHandle`**) to remove it — that delete *is* the "I processed it" ack. If you don't delete
  before the visibility timeout elapses, the message becomes visible again and is **redelivered**. There is no
  "receive-and-delete" mode — every receive is followed by an explicit delete when you're done.
- **Visibility timeout** — the SQS analogue of Service Bus's peek-lock: a received message is *invisible*, not
  gone, until you delete it (or the timeout expires → redelivery). `ChangeMessageVisibilityCommand` lets a
  test shorten it to force fast redelivery.
- **Redrive policy → dead-letter queue (DLQ)** — a queue's `RedrivePolicy` attribute names a separate DLQ and
  a `maxReceiveCount`. After a message has been **received** `maxReceiveCount` times **without being deleted**,
  SQS moves it to the DLQ. The DLQ is just another SQS queue — you receive from it to assert. *(This is the
  redrive-policy analogue of Service Bus's max-delivery-count → DLQ sub-queue.)*
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
which emulates SQS + SNS on a single endpoint. Point every SDK client at that endpoint via `endpoint`;
LocalStack accepts any credentials (`test`/`test` by convention) and the account id is `000000000000`. Use the
**`@testcontainers/localstack`** module — it boots the container, owns the readiness wait, and surfaces the
URI. Reuse the fixture discipline from `qa-test-environments-typescript` (boot once per suite; **never
`setTimeout` for readiness** — the module owns the wait strategy). **Create the queues in the fixture** (there
is no `Config.json` equivalent — you declare them through the SDK).

```typescript
// test/fixtures/sqsBroker.ts
import { LocalstackContainer, type StartedLocalStackContainer } from "@testcontainers/localstack";
import {
  SQSClient, CreateQueueCommand, GetQueueAttributesCommand, PurgeQueueCommand,
} from "@aws-sdk/client-sqs";

export interface Broker {
  sqs: SQSClient;
  endpoint: string;
  ordersUrl: string;
  ordersDlqUrl: string;
  purge: (queueUrl: string) => Promise<void>;
  stop: () => Promise<void>;
}

export async function startSqsBroker(): Promise<Broker> {
  // Pin the image tag, never `latest`. The module declares its own readiness wait strategy.
  const container: StartedLocalStackContainer =
    await new LocalstackContainer("localstack/localstack:3.5").start();
  const endpoint = container.getConnectionUri();

  // LocalStack accepts any creds; surfaced for the client, never logged.
  const sqs = new SQSClient({
    endpoint,
    region: "us-east-1",
    credentials: { accessKeyId: "test", secretAccessKey: "test" },
  });

  // Declare the queues: DLQ first, then the source queue wired to it by a redrive policy.
  const ordersDlqUrl = (await sqs.send(new CreateQueueCommand({ QueueName: "orders-dlq" }))).QueueUrl!;
  const dlqArn = (await sqs.send(new GetQueueAttributesCommand({
    QueueUrl: ordersDlqUrl, AttributeNames: ["QueueArn"],
  }))).Attributes!.QueueArn;

  const ordersUrl = (await sqs.send(new CreateQueueCommand({
    QueueName: "orders",
    Attributes: {
      VisibilityTimeout: "1",   // short, so redelivery is fast in tests (default is 30s)
      RedrivePolicy: JSON.stringify({ deadLetterTargetArn: dlqArn, maxReceiveCount: "3" }),
    },
  }))).QueueUrl!;

  return {
    sqs, endpoint, ordersUrl, ordersDlqUrl,
    purge: async (queueUrl) => { await sqs.send(new PurgeQueueCommand({ QueueUrl: queueUrl })); },
    stop: async () => { sqs.destroy(); await container.stop(); },
  };
}
```

> **Cloud test account alternative.** If your org runs against a real **test** AWS account instead of
> LocalStack, drop the `endpoint` override and let the SDK resolve the real endpoint; read the region from
> `process.env` and let the SDK use the **default credential chain** (instance role / SSO / env vars) — never
> hard-code an access key, never log it (cross-link `qa-auth0-test-tokens-typescript` for the secrets-from-env
> discipline). LocalStack is the default for CI determinism; a shared cloud queue makes tests order-dependent
> unless each uses a uniquely named queue.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT sends; the test **receives with a bounded long-poll** and asserts the message body and attributes.
`ReceiveMessageCommand` with `WaitTimeSeconds` long-polls — it *is* the condition-wait; an undefined/empty
`Messages` array means "nothing arrived within the window" and fails the assertion deterministically. Delete
what you read so it doesn't leak into the next test.

```typescript
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import {
  ReceiveMessageCommand, DeleteMessageCommand,
} from "@aws-sdk/client-sqs";
import { startSqsBroker, type Broker } from "./fixtures/sqsBroker";
import { OrderPublisher } from "../src/orderPublisher";
import { anOrder } from "./builders/order"; // builder (qa/typescript/skills/test-data-builder)

describe("order publishing", () => {
  let broker: Broker;
  let sut: OrderPublisher;

  beforeAll(async () => { broker = await startSqsBroker(); });
  afterAll(async () => { await broker.stop(); });

  beforeEach(async () => {
    await broker.purge(broker.ordersUrl);              // independent tests — start from empty
    sut = new OrderPublisher(broker.sqs, broker.ordersUrl); // constructor injection — no static client
  });

  it("sends OrderPlaced when an order is submitted", async () => {
    const order = anOrder().pending().withTotal(1999).build();

    await sut.submit(order); // SUT produces the message

    // Bounded long-poll = the condition-wait. Never a fixed setTimeout before receiving.
    const received = await broker.sqs.send(new ReceiveMessageCommand({
      QueueUrl: broker.ordersUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1, MessageAttributeNames: ["All"],
    }));

    expect(received.Messages, "a message sent to 'orders' within the wait window").toBeDefined();
    const placed = JSON.parse(received.Messages![0].Body!);
    expect(placed.orderId).toBe(order.id); // one logical assertion: the published fact

    await broker.sqs.send(new DeleteMessageCommand({   // ack/clean up
      QueueUrl: broker.ordersUrl, ReceiptHandle: received.Messages![0].ReceiptHandle,
    }));
  });

  it("stamps the eventType attribute when publishing", async () => {
    const order = anOrder().pending().build();

    await sut.submit(order);

    const received = await broker.sqs.send(new ReceiveMessageCommand({
      QueueUrl: broker.ordersUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1, MessageAttributeNames: ["All"],
    }));

    expect(received.Messages).toBeDefined();
    const attrs = received.Messages![0].MessageAttributes!;
    expect({ // one behaviour: the message envelope
      eventType: attrs.eventType.StringValue,
      correlationId: attrs.correlationId.StringValue,
    }).toEqual({ eventType: "OrderPlaced", correlationId: order.id });
  });
});
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so use
`expect.poll` to wait on a condition. This reuses `qa-db-testing-client-typescript`'s discipline.

```typescript
import { SendMessageCommand } from "@aws-sdk/client-sqs";

it("writes a shipment row when an OrderPaid message is consumed", async () => {
  const orderId = crypto.randomUUID();

  // 1. Seed the input message onto the queue the consumer polls.
  await broker.sqs.send(new SendMessageCommand({
    QueueUrl: broker.ordersUrl,
    MessageBody: JSON.stringify({ orderId }),
    MessageAttributes: { eventType: { DataType: "String", StringValue: "OrderPaid" } },
  }));

  // 2. The SUT (an SQS-polling consumer) is already running and picks it up.

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

## Visibility timeout — received-but-not-deleted → redelivery (the peek-lock analogue)

A received message is **invisible**, not gone, for its visibility timeout. If the consumer doesn't delete it
before that window elapses, the message becomes visible again and is **redelivered**. This is SQS's settlement
primitive — there's no complete/abandon. To assert redelivery deterministically, shorten the visibility window
(we set the queue's `VisibilityTimeout=1` in the fixture, or send a `ChangeMessageVisibilityCommand` with `0`
to make it immediately visible again).

```typescript
import { ChangeMessageVisibilityCommand } from "@aws-sdk/client-sqs";

it("redelivers the message when it is received but not deleted", async () => {
  await broker.sqs.send(new SendMessageCommand({
    QueueUrl: broker.ordersUrl, MessageBody: JSON.stringify({ orderId: "abc" }),
  }));

  // First receive — DON'T delete. The message is now invisible for the visibility timeout.
  const first = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: broker.ordersUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1,
    MessageSystemAttributeNames: ["ApproximateReceiveCount"],
  }));
  expect(first.Messages).toBeDefined();

  // Make it visible again immediately (instead of sleeping for the timeout) → forces redelivery.
  await broker.sqs.send(new ChangeMessageVisibilityCommand({
    QueueUrl: broker.ordersUrl, ReceiptHandle: first.Messages![0].ReceiptHandle, VisibilityTimeout: 0,
  }));

  // Second receive long-polls until the redelivered copy reappears — the condition-wait, not a sleep.
  const second = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: broker.ordersUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1,
    MessageSystemAttributeNames: ["ApproximateReceiveCount"],
  }));

  expect(second.Messages, "the un-deleted message was redelivered").toBeDefined();
  expect(Number(second.Messages![0].Attributes!.ApproximateReceiveCount))
    .toBeGreaterThanOrEqual(2); // delivered at least twice — proof of redelivery
});
```

## Redrive-policy DLQ assertions

The high-value assertion: **a message that kept failing landed in the DLQ**. With `maxReceiveCount=3` (set in
the fixture's redrive policy), a message received 3 times without a delete is moved to the DLQ on the **next**
receive attempt (a documented SQS/LocalStack behaviour — the move is triggered by a receive, so do one more
receive than `maxReceiveCount`). Then receive from the **DLQ** to assert.

```typescript
it("redrives to the DLQ when maxReceiveCount is exceeded", async () => {
  await broker.sqs.send(new SendMessageCommand({
    QueueUrl: broker.ordersUrl, MessageBody: "{ not valid order json }",
  }));

  // Receive-without-delete maxReceiveCount+1 times, resetting visibility to 0 each time to force fast
  // redelivery. The bounded long-poll is the condition-wait; no setTimeout anywhere.
  for (let attempt = 0; attempt < 4; attempt++) { // 4 = maxReceiveCount(3) + 1 to trigger the move
    const poll = await broker.sqs.send(new ReceiveMessageCommand({
      QueueUrl: broker.ordersUrl, WaitTimeSeconds: 5, MaxNumberOfMessages: 1,
    }));
    if (poll.Messages?.length) {
      await broker.sqs.send(new ChangeMessageVisibilityCommand({
        QueueUrl: broker.ordersUrl, ReceiptHandle: poll.Messages[0].ReceiptHandle, VisibilityTimeout: 0,
      }));
    }
  }

  // Assert on the DLQ — long-poll the condition (the message lands), not a sleep.
  const dead = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: broker.ordersDlqUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1,
  }));

  expect(dead.Messages, "the poison message in the dead-letter queue").toBeDefined();
  expect(dead.Messages![0].Body).toContain("not valid order json"); // the original payload
  await broker.sqs.send(new DeleteMessageCommand({
    QueueUrl: broker.ordersDlqUrl, ReceiptHandle: dead.Messages![0].ReceiptHandle,
  }));
});
```

> When the **SUT consumer** owns the failing/deleting, you don't drive the receive loop yourself — you seed the
> poison message, let the consumer fail it `maxReceiveCount` times, and `expect.poll` the DLQ for the moved
> message. The manual loop above is for when the *test* is exercising the redrive wiring directly.

## Standard vs FIFO queues

A **FIFO** queue (`.fifo` suffix, `FifoQueue=true`) guarantees ordering within a `MessageGroupId` and
deduplicates within a 5-minute window. Each send must carry a `MessageGroupId`, and a `MessageDeduplicationId`
unless the queue has `ContentBasedDeduplication=true`.

```typescript
const fifoUrl = (await broker.sqs.send(new CreateQueueCommand({
  QueueName: "orders.fifo",
  Attributes: { FifoQueue: "true", ContentBasedDeduplication: "true" }, // dedup id from the body
}))).QueueUrl!;

it("deduplicates when the same message is sent twice within the window", async () => {
  const body = JSON.stringify({ orderId: "dup-1" });
  await broker.sqs.send(new SendMessageCommand({ QueueUrl: fifoUrl, MessageBody: body, MessageGroupId: "orders" }));
  await broker.sqs.send(new SendMessageCommand({ QueueUrl: fifoUrl, MessageBody: body, MessageGroupId: "orders" }));

  const received = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: fifoUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 10,
  }));

  expect(received.Messages).toHaveLength(1); // dedup collapsed the duplicate
});
```

## SNS→SQS fan-out

Publish once to an **SNS topic**; assert each **subscribed SQS queue** received its copy — the topics/
subscriptions analogue. Use `RawMessageDelivery=true` so the queue gets your raw payload, not the SNS JSON
envelope.

```typescript
import { SNSClient, CreateTopicCommand, SubscribeCommand, PublishCommand } from "@aws-sdk/client-sns";
import { GetQueueAttributesCommand } from "@aws-sdk/client-sqs";

it("fans out to both queues when an order event is published", async () => {
  const sns = new SNSClient({
    endpoint: broker.endpoint, region: "us-east-1",
    credentials: { accessKeyId: "test", secretAccessKey: "test" },
  });

  const topicArn = (await sns.send(new CreateTopicCommand({ Name: "order-events" }))).TopicArn!;
  for (const queueUrl of [fulfilmentUrl, auditUrl]) {
    const arn = (await broker.sqs.send(new GetQueueAttributesCommand({
      QueueUrl: queueUrl, AttributeNames: ["QueueArn"],
    }))).Attributes!.QueueArn;
    await sns.send(new SubscribeCommand({
      TopicArn: topicArn, Protocol: "sqs", Endpoint: arn, Attributes: { RawMessageDelivery: "true" },
    }));
  }

  await sns.send(new PublishCommand({ TopicArn: topicArn, Message: JSON.stringify({ orderId: crypto.randomUUID() }) }));

  // Each subscribed queue gets its own copy — long-poll both (the condition-wait).
  const toFulfilment = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: fulfilmentUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1,
  }));
  const toAudit = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: auditUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1,
  }));

  expect(toFulfilment.Messages, "fulfilment queue copy").toBeDefined(); // one behaviour: the fan-out
  expect(toAudit.Messages, "audit queue copy").toBeDefined();
});
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain in a loop with `WaitTimeSeconds` and count — the bounded
long-poll stops it hanging when fewer than N arrive. SQS returns **at most 10** per receive, so loop:

```typescript
const drained: string[] = [];
for (;;) {
  const page = await broker.sqs.send(new ReceiveMessageCommand({
    QueueUrl: broker.ordersUrl, WaitTimeSeconds: 2, MaxNumberOfMessages: 10,
  }));
  if (!page.Messages?.length) break; // bounded wait returned empty → drained
  for (const m of page.Messages) {
    drained.push(m.Body!);
    await broker.sqs.send(new DeleteMessageCommand({ QueueUrl: broker.ordersUrl, ReceiptHandle: m.ReceiptHandle }));
  }
}
expect(drained).toHaveLength(3); // SUT produced exactly 3
```

## Anti-patterns

- **`await new Promise(r => setTimeout(r, 5000))` / `page.waitForTimeout` before receiving / asserting the
  side-effect.** Races the broker and the consumer; slow and flaky. *Fix:* `ReceiveMessageCommand` with
  `WaitTimeSeconds` for the receive side (it long-polls, max 20s), and `expect.poll` for consumer side-effects.
- **`WaitTimeSeconds: 0` (short-polling) in a test.** Short-poll returns immediately, usually empty even when a
  message is in flight, so it races the produce. *Fix:* always set `WaitTimeSeconds` (long-poll) — that *is*
  the condition-wait.
- **Receiving but never deleting.** The message stays invisible for the visibility timeout, then redelivers
  into the next test as a "phantom". *Fix:* `DeleteMessageCommand` every message you've finished with — that's
  the SQS ack — or purge in `beforeEach`.
- **Treating an undefined/empty `Messages` as success.** Empty means nothing arrived in the window — a failed
  produce, not a pass. *Fix:* `expect(received.Messages).toBeDefined()` first (and remember `Messages` is
  `undefined`, not `[]`, when empty).
- **Expecting the DLQ move after exactly `maxReceiveCount` receives.** SQS moves the message on the *next*
  receive after the count is exceeded. *Fix:* receive `maxReceiveCount + 1` times (resetting visibility to 0),
  then assert on the DLQ — or let the SUT consumer fail it and `expect.poll` the DLQ.
- **Sharing one queue across parallel test files.** Vitest runs files in parallel; competing receivers steal
  each other's messages. *Fix:* a uniquely named queue per file, purge in `beforeEach`, or `test.sequential` /
  a single worker for messaging suites.
- **FIFO send without a `MessageGroupId`.** The send is rejected. *Fix:* every FIFO send carries a
  `MessageGroupId`; supply a `MessageDeduplicationId` unless `ContentBasedDeduplication=true`.
- **Hard-coding the endpoint / an AWS access key in a test.** *Fix:* surface the LocalStack endpoint from the
  fixture; for a cloud test account use the default credential chain + region from `process.env`; never log
  secrets.
- **Reaching for SQS when the dependency is an HTTP call.** *Fix:* `qa-api-mocking-typescript` — messaging
  is for async queues, not request/response fakes.

## Examples

**End-to-end: a consume → process → republish flow, asserted on the side-message.**

```typescript
describe("fulfilment consumer", () => {
  let broker: Broker;

  beforeAll(async () => { broker = await startSqsBroker(); });
  afterAll(async () => { await broker.stop(); });

  beforeEach(async () => {
    await broker.purge(broker.ordersUrl);    // independent tests — start from empty
    await broker.purge(shipmentsUrl);
  });

  it("sends ShipmentReady when a valid OrderPaid is consumed", async () => {
    const orderId = crypto.randomUUID();
    await broker.sqs.send(new SendMessageCommand({
      QueueUrl: broker.ordersUrl,
      MessageBody: JSON.stringify({ orderId }),
      MessageAttributes: {
        eventType: { DataType: "String", StringValue: "OrderPaid" },
        correlationId: { DataType: "String", StringValue: orderId },
      },
    }));

    // The SUT consumer polls "orders" and republishes onto "shipments".
    const ready = await broker.sqs.send(new ReceiveMessageCommand({
      QueueUrl: shipmentsUrl, WaitTimeSeconds: 10, MaxNumberOfMessages: 1, MessageAttributeNames: ["All"],
    }));

    expect(ready.Messages, "consumer republished a ShipmentReady message").toBeDefined();
    expect(ready.Messages![0].MessageAttributes!.correlationId.StringValue).toBe(orderId); // correlation preserved
    await broker.sqs.send(new DeleteMessageCommand({
      QueueUrl: shipmentsUrl, ReceiptHandle: ready.Messages![0].ReceiptHandle,
    }));
  });
});
```

Lifecycle for this test:
1. `beforeAll` boots LocalStack once and creates the queues (DLQ + source wired by a redrive policy); the SQS
   client + URLs are surfaced.
2. `beforeEach` purges the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the output
   queue (the condition-wait) and asserts correlation was preserved, then deletes what it read.
4. `afterAll` destroys the client and stops the container.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```typescript
export const anOrder = () => new OrderBuilder().status("Pending");
// anOrder().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/typescript/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `ReceiveMessageCommand` with `WaitTimeSeconds`
  for the receive side (bounded long-poll, max 20s); `expect.poll` for consumer side-effects. **No `setTimeout`
  / `waitForTimeout`** as an assertion wait. Never short-poll (`WaitTimeSeconds: 0`) in a test.
- The SUT's publisher/consumer is **constructor-injected** with the `SQSClient` / queue URL — never a static
  client or an endpoint read inside a test.
- **Delete (ack) every message you've finished processing** with its `ReceiptHandle`, or purge in `beforeEach`.
  Never leave an un-deleted message to redeliver into the next test.
- **Independent tests:** uniquely named queue per file **or** purge in `beforeEach`; messaging suites run
  single-worker / `test.sequential` unless verified isolated.
- Assert the **fact**, not the absence: an undefined/empty `Messages` is a *failed* produce — `toBeDefined()`
  before reading the body (`Messages` is `undefined`, not `[]`, when empty).
- **`destroy()` every client**; the SDK's network calls are bounded by the `WaitTimeSeconds` you pass — never
  await unbounded.
- **DLQ via redrive policy:** receive `maxReceiveCount + 1` times (visibility reset to 0) to trigger the move,
  then assert on the DLQ — or let the SUT fail it and `expect.poll` the DLQ.
- Local broker = **LocalStack via Testcontainers** (pinned image; queues created in the fixture); a cloud test
  account uses the **default credential chain + region from `process.env`**, read lazily, never logged.
- Test names describe behaviour; one logical assertion per test; builders for 4+-field payloads; `strict: true`;
  no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical** stack, .NET 8 / NUnit (`AWSSDK.SQS`:
  `new AmazonSQSClient(creds, new AmazonSQSConfig { ServiceURL })`, `ReceiveMessageAsync(WaitTimeSeconds)`,
  `RedrivePolicy` attribute, `WaitFor.Async` poll, `Testcontainers.LocalStack`). This file is ported from it.
- `qa-messaging-testing-java` — same skill, Java 21 / TestNG (`software.amazon.awssdk:sqs`/`sns`:
  `SqsClient.builder().endpointOverride(...)`, `receiveMessage(b -> b.waitTimeSeconds(10)...)`, Awaitility,
  `org.testcontainers:localstack`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure
  Service Bus on the emulator; **the `service-bus`-vs-`sqs` boundary**: Service Bus peek-lock + DLQ *sub-queue* vs SQS
  visibility-timeout + redrive-policy *DLQ queue* — same condition-wait discipline, different settlement.
  Kafka (`kafka`, offset-based) and RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-testing-client-typescript` — the `expect.poll` and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-environments-typescript` — booting the LocalStack container; the per-suite lifecycle and
  readiness-wait discipline (never `setTimeout`) mirrored here.
- `qa-auth0-test-tokens-typescript` — when running against a cloud test account; the default-credential
  -chain + secrets-from-env discipline.
- `qa-api-mocking-typescript` — the *synchronous* counterpart: fake the app's outbound HTTP
  in-runtime. The boundary: MSW = request/response fake; SQS = async queue assertions.
- `qa-allure-reporting-typescript` — attach the received message body / DLQ payload to the Allure result.
- `qa-test-data-builder-typescript` — builders for message payloads with 4+ fields.
