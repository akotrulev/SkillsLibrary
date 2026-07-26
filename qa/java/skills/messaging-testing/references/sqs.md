# Messaging Testing — AWS SQS / SNS (Java 21 / TestNG)

Ported from the **canonical** `.NET` stack of the `qa/java/skills/messaging-testing/` node (.NET led this node by the
user's choice; this file re-expresses the same model in Java idioms — `software.amazon.awssdk:sqs`/`sns`,
TestNG + AssertJ, Awaitility, Testcontainers). This is the **second `messaging-testing` sibling** (`service-bus`
service-bus → **SQS** → Kafka → RabbitMQ); it keeps the **same two assertion patterns and the same
eventual-consistency condition-wait discipline** as `service-bus` — only the broker SDK and its settlement semantics
change. Translate-the-concepts, not redesign — the Java AWS SDK v2 mirrors the same send / receive / delete
model.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has no
> synchronous return you can assert on the next line. The message is in flight; the consumer runs on its own
> schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the message
> (or its effect) to appear, with a bounded timeout — **never `Thread.sleep`**. This is the exact lineage of
> `qa-db-connection-java`'s Awaitility usage and `references/service-bus.md`'s condition-wait.
> SQS gives you the **`waitTimeSeconds` long-poll** as a better primitive than spin-polling for the receive
> side: `receiveMessage` with `waitTimeSeconds` blocks up to a bounded window (max **20s**) for a message to
> arrive, then returns it or an empty `messages()` list. That bounded wait *is* the condition-wait; a fixed
> sleep is not.

## Stack

- Java 21 + TestNG + AssertJ (`org.testng:testng`, `org.assertj:assertj-core`) + Awaitility
  (`org.awaitility:awaitility`)
- `software.amazon.awssdk:sqs` (`SqsClient` — send / receive / delete / queue attributes) and
  `software.amazon.awssdk:sns` (`SnsClient`) for SNS→SQS fan-out
- `org.testcontainers:localstack` (`LocalStackContainer`) — boots **LocalStack** (the local AWS emulator) and
  surfaces an endpoint URI / region / credentials the SDK clients point at
- The SUT's typed publisher/consumer is **constructor-injected** with the `SqsClient` (or the resolved queue
  URL) — never a static client or an endpoint read inside an `@Test`

```
src/test/java/.../messaging/
├── SqsTestBase.java        ← boots LocalStack, creates the queues (+DLQ via redrive), exposes the SQS client + URLs
└── OrderPublishingTest.java
```

## The SQS model — visibility timeout, redrive → DLQ, FIFO, SNS fan-out

SQS has **no peek-lock and no per-message ack**. The whole settlement model is:

- **Queue** — competing consumers; one `receiveMessage` returns up to 10 messages and **hides** each one for
  its **visibility timeout** instead of removing it. You then call **`deleteMessage`** (with the message's
  **`receiptHandle`**) to remove it — that delete *is* the "I processed it" ack. If you don't delete before
  the visibility timeout elapses, the message becomes visible again and is **redelivered**. There is no
  "receive-and-delete" mode — every receive is followed by an explicit delete when you're done.
- **Visibility timeout** — the SQS analogue of Service Bus's peek-lock: a received message is *invisible*, not
  gone, until you delete it (or the timeout expires → redelivery). `changeMessageVisibility` lets a test
  shorten it to force fast redelivery.
- **Redrive policy → dead-letter queue (DLQ)** — a queue's `RedrivePolicy` attribute names a separate DLQ and
  a `maxReceiveCount`. After a message has been **received** `maxReceiveCount` times **without being deleted**,
  SQS moves it to the DLQ. The DLQ is just another SQS queue — you receive from it to assert. *(This is the
  redrive-policy analogue of Service Bus's max-delivery-count → DLQ sub-queue.)*
- **Standard vs FIFO** — a **FIFO** queue's name ends `.fifo` (`FifoQueue=true`); every send needs a
  **`messageGroupId`** (ordering scope) and a **`messageDeduplicationId`** (or `ContentBasedDeduplication=true`
  to derive it from the body). Standard queues are best-effort-ordered and at-least-once; FIFO is
  exactly-once-per-dedup-window and ordered within a group.
- **SNS→SQS fan-out** — the topics/subscriptions analogue. Publish once to an **SNS topic**; each **SQS queue
  subscribed** to it gets a copy. Set `RawMessageDelivery=true` on the subscription or the SNS envelope wraps
  your payload in JSON. The subscribed queue also needs an access policy allowing the topic to send to it
  (LocalStack sets this for you when SNS creates the subscription).

## Local broker for tests — LocalStack

There is no in-memory SQS. For deterministic local + CI tests, run **LocalStack** (`localstack/localstack`),
which emulates SQS + SNS on a single endpoint. Point every SDK client at that endpoint via `endpointOverride`;
the container surfaces the region and (placeholder) credentials, and the account id is `000000000000`. The
cleanest path in Java is Testcontainers' **`LocalStackContainer`** — it boots the container, owns the
readiness wait, and surfaces the endpoint. Reuse the standard Testcontainers fixture discipline (boot
once per class; **never `Thread.sleep` for readiness** — the container owns the wait strategy). **Create the
queues in `@BeforeClass`** (there is no `Config.json` equivalent — you declare them through the SDK).

```java
import org.testcontainers.containers.localstack.LocalStackContainer;
import org.testcontainers.containers.localstack.LocalStackContainer.Service;
import org.testcontainers.utility.DockerImageName;
import org.testng.annotations.*;
import software.amazon.awssdk.auth.credentials.*;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.sqs.SqsClient;
import software.amazon.awssdk.services.sqs.model.*;

import java.util.Map;

public abstract class SqsTestBase {

    // Pin the image tag, never `latest`. The container declares its own readiness wait strategy.
    private final LocalStackContainer localstack =
            new LocalStackContainer(DockerImageName.parse("localstack/localstack:3.5"))
                    .withServices(Service.SQS, Service.SNS);

    protected SqsClient sqs;
    protected String ordersUrl;
    protected String ordersDlqUrl;

    @BeforeClass(alwaysRun = true)
    public void startBroker() {
        localstack.start();

        sqs = SqsClient.builder()
                .endpointOverride(localstack.getEndpoint())
                .region(Region.of(localstack.getRegion()))
                .credentialsProvider(StaticCredentialsProvider.create(   // placeholder creds, never logged
                        AwsBasicCredentials.create(localstack.getAccessKey(), localstack.getSecretKey())))
                .build();

        // Declare the queues: DLQ first, then the source queue wired to it by a redrive policy.
        ordersDlqUrl = sqs.createQueue(b -> b.queueName("orders-dlq")).queueUrl();
        String dlqArn = sqs.getQueueAttributes(b -> b.queueUrl(ordersDlqUrl)
                .attributeNames(QueueAttributeName.QUEUE_ARN)).attributes().get(QueueAttributeName.QUEUE_ARN);

        String redrive = "{\"deadLetterTargetArn\":\"" + dlqArn + "\",\"maxReceiveCount\":\"3\"}";
        ordersUrl = sqs.createQueue(b -> b.queueName("orders").attributes(Map.of(
                QueueAttributeName.VISIBILITY_TIMEOUT, "1",   // short, so redelivery is fast (default 30s)
                QueueAttributeName.REDRIVE_POLICY, redrive))).queueUrl();
    }

    @AfterClass(alwaysRun = true)
    public void stopBroker() {
        if (sqs != null) sqs.close();
        localstack.stop();
    }

    // Independent tests: purge a queue so each starts from empty.
    protected void purge(String queueUrl) { sqs.purgeQueue(b -> b.queueUrl(queueUrl)); }
}
```

> **Cloud test queue alternative.** If your org runs against a real **test** AWS account instead of LocalStack,
> drop the `endpointOverride` and let the SDK resolve the real endpoint; read the region from env and the
> credentials from the **default credential provider chain** (`DefaultCredentialsProvider`) — never hard-code
> an access key, never log it (cross-link `qa-test-login-tokens-java` for the secrets-from-env discipline).
> LocalStack is the default for CI determinism; a shared cloud queue makes tests order-dependent unless each
> uses a uniquely named queue.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT sends; the test **receives with a bounded long-poll** and asserts the message body and attributes.
`receiveMessage` with `waitTimeSeconds` long-polls — it *is* the condition-wait; an empty `messages()` list
means "nothing arrived within the window" and fails the assertion deterministically. Delete what you read so
it doesn't leak into the next test.

```java
import static org.assertj.core.api.Assertions.assertThat;

public class OrderPublishingTest extends SqsTestBase {

    private OrderPublisher sut;     // production code, constructor-injected with the SQS client + URL

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        purge(ordersUrl);                          // independent tests — start from empty
        sut = new OrderPublisher(sqs, ordersUrl);  // constructor injection — no static client
    }

    @Test
    public void Should_send_OrderPlaced_When_an_order_is_submitted() {
        Order order = Orders.pending().withTotal(1999).build();   // builder (qa/java/skills/test-data-builder)

        sut.submit(order);                                        // SUT produces the message

        // Bounded long-poll = the condition-wait. Never a fixed Thread.sleep before receiving.
        ReceiveMessageResponse received = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
                .waitTimeSeconds(10).maxNumberOfMessages(1).messageAttributeNames("All"));

        assertThat(received.messages()).as("a message sent to 'orders' within the wait window").isNotEmpty();
        OrderPlaced placed = Json.parse(received.messages().get(0).body(), OrderPlaced.class);
        assertThat(placed.orderId()).isEqualTo(order.id());       // one logical assertion: the published fact

        sqs.deleteMessage(b -> b.queueUrl(ordersUrl)              // ack/clean up
                .receiptHandle(received.messages().get(0).receiptHandle()));
    }

    @Test
    public void Should_stamp_event_type_attribute_When_publishing() {
        Order order = Orders.pending().build();

        sut.submit(order);

        ReceiveMessageResponse received = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
                .waitTimeSeconds(10).maxNumberOfMessages(1).messageAttributeNames("All"));

        assertThat(received.messages()).isNotEmpty();
        Message message = received.messages().get(0);
        assertThat(message.messageAttributes()).satisfies(attrs -> {   // one behaviour: the message envelope
            assertThat(attrs.get("eventType").stringValue()).isEqualTo("OrderPlaced");
            assertThat(attrs.get("correlationId").stringValue()).isEqualTo(order.id().toString());
        });
        sqs.deleteMessage(b -> b.queueUrl(ordersUrl).receiptHandle(message.receiptHandle()));
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so use
**Awaitility** to poll a probe on a condition. This reuses `qa-db-connection-java`'s discipline.

```java
import static org.awaitility.Awaitility.await;

@Test
public void Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed() {
    UUID orderId = UUID.randomUUID();

    // 1. Seed the input message onto the queue the consumer polls.
    sqs.sendMessage(b -> b.queueUrl(ordersUrl)
            .messageBody(Json.write(new OrderPaid(orderId)))
            .messageAttributes(Map.of("eventType", MessageAttributeValue.builder()
                    .dataType("String").stringValue("OrderPaid").build())));

    // 2. The SUT (an SQS-polling consumer) is already running and picks it up.

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

## Visibility timeout — received-but-not-deleted → redelivery (the peek-lock analogue)

A received message is **invisible**, not gone, for its visibility timeout. If the consumer doesn't
`deleteMessage` before that window elapses, the message becomes visible again and is **redelivered**. This is
SQS's settlement primitive — there's no `complete`/`abandon`. To assert redelivery deterministically, shorten
the visibility window (we set the queue's `VISIBILITY_TIMEOUT=1` in the base, or call
`changeMessageVisibility(..., 0)` to make it immediately visible again).

```java
@Test
public void Should_redeliver_the_message_When_it_is_received_but_not_deleted() {
    sqs.sendMessage(b -> b.queueUrl(ordersUrl).messageBody("{\"orderId\":\"abc\"}"));

    // First receive — DON'T delete. The message is now invisible for the visibility timeout.
    ReceiveMessageResponse first = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(1)
            .messageSystemAttributeNames(MessageSystemAttributeName.APPROXIMATE_RECEIVE_COUNT));
    assertThat(first.messages()).isNotEmpty();

    // Make it visible again immediately (instead of sleeping for the timeout) → forces redelivery.
    sqs.changeMessageVisibility(b -> b.queueUrl(ordersUrl)
            .receiptHandle(first.messages().get(0).receiptHandle()).visibilityTimeout(0));

    // Second receive long-polls until the redelivered copy reappears — the condition-wait, not a sleep.
    ReceiveMessageResponse second = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(1)
            .messageSystemAttributeNames(MessageSystemAttributeName.APPROXIMATE_RECEIVE_COUNT));

    assertThat(second.messages()).as("the un-deleted message was redelivered").isNotEmpty();
    int receiveCount = Integer.parseInt(
            second.messages().get(0).attributes().get(MessageSystemAttributeName.APPROXIMATE_RECEIVE_COUNT));
    assertThat(receiveCount).isGreaterThanOrEqualTo(2);   // delivered at least twice — proof of redelivery
}
```

## Redrive-policy DLQ assertions

The high-value assertion: **a message that kept failing landed in the DLQ**. With `maxReceiveCount=3` (set in
the base's redrive policy), a message received 3 times without a delete is moved to the DLQ on the **next**
receive attempt (a documented SQS/LocalStack behaviour — the move is triggered by a receive, so do one more
receive than `maxReceiveCount`). Then receive from the **DLQ** to assert.

```java
@Test
public void Should_redrive_to_the_dlq_When_max_receive_count_is_exceeded() {
    sqs.sendMessage(b -> b.queueUrl(ordersUrl).messageBody("{ not valid order json }"));

    // Receive-without-delete maxReceiveCount+1 times, resetting visibility to 0 each time to force fast
    // redelivery. The bounded long-poll is the condition-wait; no Thread.sleep anywhere.
    for (int attempt = 0; attempt < 4; attempt++) {   // 4 = maxReceiveCount(3) + 1 to trigger the move
        ReceiveMessageResponse poll = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
                .waitTimeSeconds(5).maxNumberOfMessages(1));
        if (!poll.messages().isEmpty()) {
            sqs.changeMessageVisibility(b -> b.queueUrl(ordersUrl)
                    .receiptHandle(poll.messages().get(0).receiptHandle()).visibilityTimeout(0));
        }
    }

    // Assert on the DLQ — long-poll the condition (the message lands), not a sleep.
    ReceiveMessageResponse dead = sqs.receiveMessage(b -> b.queueUrl(ordersDlqUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(1));

    assertThat(dead.messages()).as("the poison message in the dead-letter queue").isNotEmpty();
    assertThat(dead.messages().get(0).body()).contains("not valid order json");   // the original payload
    sqs.deleteMessage(b -> b.queueUrl(ordersDlqUrl).receiptHandle(dead.messages().get(0).receiptHandle()));
}
```

> When the **SUT consumer** owns the failing/deleting, you don't drive the receive loop yourself — you seed the
> poison message, let the consumer fail it `maxReceiveCount` times, and Awaitility-poll the DLQ for the moved
> message. The manual loop above is for when the *test* is exercising the redrive wiring directly.

## Standard vs FIFO queues

A **FIFO** queue (`.fifo` suffix, `FifoQueue=true`) guarantees ordering within a `messageGroupId` and
deduplicates within a 5-minute window. Each send must carry a `messageGroupId`, and a `messageDeduplicationId`
unless the queue has `ContentBasedDeduplication=true`.

```java
String fifoUrl = sqs.createQueue(b -> b.queueName("orders.fifo").attributes(Map.of(
        QueueAttributeName.FIFO_QUEUE, "true",
        QueueAttributeName.CONTENT_BASED_DEDUPLICATION, "true"))).queueUrl();   // dedup id from the body

@Test
public void Should_deduplicate_When_the_same_message_is_sent_twice_within_the_window() {
    String body = "{\"orderId\":\"dup-1\"}";
    sqs.sendMessage(b -> b.queueUrl(fifoUrl).messageBody(body).messageGroupId("orders"));
    sqs.sendMessage(b -> b.queueUrl(fifoUrl).messageBody(body).messageGroupId("orders"));   // duplicate

    ReceiveMessageResponse received = sqs.receiveMessage(b -> b.queueUrl(fifoUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(10));

    assertThat(received.messages()).hasSize(1);   // dedup collapsed the duplicate
}
```

## SNS→SQS fan-out

Publish once to an **SNS topic**; assert each **subscribed SQS queue** received its copy — the topics/
subscriptions analogue. Use `RawMessageDelivery=true` so the queue gets your raw payload, not the SNS JSON
envelope.

```java
@Test
public void Should_fan_out_to_both_queues_When_an_order_event_is_published() {
    SnsClient sns = SnsClient.builder()
            .endpointOverride(localstack.getEndpoint()).region(Region.of(localstack.getRegion()))
            .credentialsProvider(StaticCredentialsProvider.create(
                    AwsBasicCredentials.create(localstack.getAccessKey(), localstack.getSecretKey())))
            .build();

    String topicArn = sns.createTopic(b -> b.name("order-events")).topicArn();
    for (String queueUrl : List.of(fulfilmentUrl, auditUrl)) {
        String arn = sqs.getQueueAttributes(b -> b.queueUrl(queueUrl)
                .attributeNames(QueueAttributeName.QUEUE_ARN)).attributes().get(QueueAttributeName.QUEUE_ARN);
        sns.subscribe(b -> b.topicArn(topicArn).protocol("sqs").endpoint(arn)
                .attributes(Map.of("RawMessageDelivery", "true")));
    }

    sns.publish(b -> b.topicArn(topicArn).message(Json.write(new OrderPlaced(UUID.randomUUID()))));

    // Each subscribed queue gets its own copy — long-poll both (the condition-wait).
    ReceiveMessageResponse toFulfilment = sqs.receiveMessage(b -> b.queueUrl(fulfilmentUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(1));
    ReceiveMessageResponse toAudit = sqs.receiveMessage(b -> b.queueUrl(auditUrl)
            .waitTimeSeconds(10).maxNumberOfMessages(1));

    assertThat(toFulfilment.messages()).as("fulfilment queue copy").isNotEmpty();   // one behaviour: fan-out
    assertThat(toAudit.messages()).as("audit queue copy").isNotEmpty();
}
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain in a loop with `waitTimeSeconds` and count — the bounded
long-poll stops it hanging when fewer than N arrive. SQS returns **at most 10** per receive, so loop:

```java
List<Message> drained = new ArrayList<>();
while (true) {
    ReceiveMessageResponse page = sqs.receiveMessage(b -> b.queueUrl(ordersUrl)
            .waitTimeSeconds(2).maxNumberOfMessages(10));
    if (page.messages().isEmpty()) break;       // bounded wait returned empty → drained
    drained.addAll(page.messages());
    page.messages().forEach(m -> sqs.deleteMessage(d -> d.queueUrl(ordersUrl).receiptHandle(m.receiptHandle())));
}
assertThat(drained).hasSize(3);                 // SUT produced exactly 3
```

## Anti-patterns

- **`Thread.sleep(5000)` before receiving / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* `receiveMessage` with `waitTimeSeconds` for the receive side (it long-polls,
  max 20s), and **Awaitility** for consumer side-effects.
- **`waitTimeSeconds(0)` (short-polling) in a test.** Short-poll returns immediately, usually empty even when a
  message is in flight, so it races the produce. *Fix:* always set `waitTimeSeconds` (long-poll) — that *is*
  the condition-wait.
- **Receiving but never deleting.** The message stays invisible for the visibility timeout, then redelivers
  into the next test as a "phantom". *Fix:* `deleteMessage(receiptHandle)` every message you've finished with —
  that's the SQS ack — or `purgeQueue` in `@BeforeMethod`.
- **Treating an empty `messages()` list as success.** Empty means nothing arrived in the window — a failed
  produce, not a pass. *Fix:* `assertThat(received.messages()).isNotEmpty()` first.
- **Expecting the DLQ move after exactly `maxReceiveCount` receives.** SQS moves the message on the *next*
  receive after the count is exceeded. *Fix:* receive `maxReceiveCount + 1` times (resetting visibility to 0),
  then assert on the DLQ — or let the SUT consumer fail it and Awaitility-poll the DLQ.
- **Sharing one queue across parallel test classes.** Competing receivers steal each other's messages. *Fix:*
  a uniquely named queue per class, `purgeQueue` in `@BeforeMethod`, and keep messaging classes out of the same
  TestNG parallel group unless verified isolated.
- **FIFO send without a `messageGroupId`.** The send is rejected. *Fix:* every FIFO send carries a
  `messageGroupId`; supply a `messageDeduplicationId` unless `ContentBasedDeduplication=true`.
- **Hard-coding the endpoint / an AWS access key in an `@Test`.** *Fix:* surface the LocalStack endpoint from
  the base class; for a cloud test account use `DefaultCredentialsProvider` + region from env; never log
  secrets.

## Examples

**End-to-end: a consume → process → republish flow, asserted on the side-message.**

```java
public class FulfilmentConsumerTest extends SqsTestBase {

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        purge(ordersUrl);          // independent tests — start from empty
        purge(shipmentsUrl);
    }

    @Test
    public void Should_send_ShipmentReady_When_a_valid_OrderPaid_is_consumed() {
        UUID orderId = UUID.randomUUID();
        sqs.sendMessage(b -> b.queueUrl(ordersUrl)
                .messageBody(Json.write(new OrderPaid(orderId)))
                .messageAttributes(Map.of(
                        "eventType", MessageAttributeValue.builder().dataType("String").stringValue("OrderPaid").build(),
                        "correlationId", MessageAttributeValue.builder().dataType("String").stringValue(orderId.toString()).build())));

        // The SUT consumer polls "orders" and republishes onto "shipments".
        ReceiveMessageResponse ready = sqs.receiveMessage(b -> b.queueUrl(shipmentsUrl)
                .waitTimeSeconds(10).maxNumberOfMessages(1).messageAttributeNames("All"));

        assertThat(ready.messages()).as("consumer republished a ShipmentReady message").isNotEmpty();
        assertThat(ready.messages().get(0).messageAttributes().get("correlationId").stringValue())
                .isEqualTo(orderId.toString());      // correlation preserved
        sqs.deleteMessage(b -> b.queueUrl(shipmentsUrl).receiptHandle(ready.messages().get(0).receiptHandle()));
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` (in `SqsTestBase`) boots LocalStack once and creates the queues (DLQ + source wired by a
   redrive policy); the SQS client + URLs are surfaced.
2. `@BeforeMethod` purges the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the output
   queue (the condition-wait) and asserts correlation was preserved, then deletes what it read.
4. `@AfterClass` closes the client and stops the container.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```java
public final class Orders {
    public static Order.Builder pending() { return new Order.Builder().status("Pending"); }
}
// Orders.pending().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/java/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `receiveMessage` with `waitTimeSeconds` for
  the receive side (bounded long-poll, max 20s); **Awaitility** for consumer side-effects. **No `Thread.sleep`**
  as an assertion wait. Never short-poll (`waitTimeSeconds(0)`) in a test.
- The SUT's publisher/consumer is **constructor-injected** with the `SqsClient` / queue URL — never a static
  client or an endpoint read inside an `@Test`.
- **Delete (ack) every message you've finished processing** with its `receiptHandle`, or `purgeQueue` in
  `@BeforeMethod`. Never leave an un-deleted message to redeliver into the next test.
- **Independent tests:** uniquely named queue per class **or** `purgeQueue` in `@BeforeMethod`; keep messaging
  classes out of the same parallel group unless verified isolated.
- Assert the **fact**, not the absence: an empty `messages()` list is a *failed* produce — `isNotEmpty()`
  before reading the body.
- **DLQ via redrive policy:** receive `maxReceiveCount + 1` times (visibility reset to 0) to trigger the move,
  then assert on the DLQ — or let the SUT fail it and Awaitility-poll the DLQ.
- **Close every client** (`sqs.close()` / `sns.close()`); the SDK's network calls are bounded by the
  `waitTimeSeconds` you pass — never block unbounded.
- Local broker = **LocalStack via Testcontainers** (pinned image; queues created in `@BeforeClass`); a cloud
  test account uses `DefaultCredentialsProvider` + region from env, read lazily, never logged.
- Test names `Should_X_When_Y`; one logical assertion per test (AssertJ); builders for 4+-field payloads;
  structured logging (SLF4J message templates); no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical** stack, .NET 8 / NUnit (`AWSSDK.SQS`:
  `new AmazonSQSClient(creds, new AmazonSQSConfig { ServiceURL })`, `ReceiveMessageAsync(WaitTimeSeconds)`,
  `RedrivePolicy` attribute, `WaitFor.Async` poll, `Testcontainers.LocalStack`). This file is ported from it.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`@aws-sdk/client-sqs`/`client-sns`:
  `new SQSClient({ endpoint })`, `ReceiveMessageCommand({ WaitTimeSeconds: 10 })`, `expect.poll`,
  `@testcontainers/localstack`).
- `references/service-bus.md` (`service-bus`, the **structure this node is ported from**) — Azure Service
  Bus on the emulator; **the `service-bus`-vs-`sqs` boundary**: Service Bus peek-lock + DLQ *sub-queue* vs SQS
  visibility-timeout + redrive-policy *DLQ queue* — same condition-wait discipline, different settlement.
  Kafka (`kafka`, offset-based) and RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-connection-java` — the Awaitility poll and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-login-tokens-java` — when running against a cloud test account; the
  default-credential-provider-chain + secrets-from-env discipline.
- `qa-test-reports-java` — attach the received message body / DLQ payload to the Allure result.
- `qa-test-data-builder-java` — builders/ObjectMother for message payloads with 4+ fields.
