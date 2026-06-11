# Messaging Testing — Azure Service Bus (Java 21 / TestNG)

Ported from the **canonical** `.NET` stack of the `qa/java/skills/messaging-testing/` node (Service Bus is
Azure-native and `Azure.Messaging.ServiceBus` is its most first-class client, so .NET led; this file
re-expresses the same model in Java idioms — `com.azure:azure-messaging-servicebus`, TestNG + AssertJ,
Awaitility, Testcontainers). This node **opens the `messaging-testing` family** (service-bus → SQS →
Kafka → RabbitMQ). Translate-the-concepts, not redesign — the Java SDK mirrors the same client →
sender/receiver model.

Messaging tests assert one of two things about an **async** flow:

- **Producer-assert** — the SUT, when exercised, **produced** message X onto a queue or topic.
- **Consumer-assert** — the SUT **consumed** a message and produced an observable **side-effect Y** (a row
  written, an email sent, another message published).

> **The boundary that defines this skill — eventual consistency.** Unlike an HTTP call, a message flow has
> no synchronous return you can assert on the next line. The message is in flight; the consumer runs on its
> own schedule; the side-effect lands "soon". So the core discipline is: **wait on a condition** for the
> message (or its effect) to appear, with a bounded timeout — **never `Thread.sleep`**. This is the exact
> lineage of `qa-db-testing-client-java`'s Awaitility usage and `qa-api-mocking-java`'s Scenario +
> Awaitility condition-wait. Service Bus gives you a *better* primitive than polling for the receive side:
> `receiveMessages(maxMessages, maxWaitTime)` **long-polls** — it blocks up to a bounded window for messages,
> then returns what arrived (possibly empty). That bounded wait *is* the condition-wait; a fixed sleep is not.

## Stack

- Java 21 + TestNG + AssertJ (`org.testng:testng`, `org.assertj:assertj-core`) + Awaitility
  (`org.awaitility:awaitility`)
- `com.azure:azure-messaging-servicebus` (the data-plane SDK — client builder / sender / receiver / processor)
- `com.azure:azure-messaging-servicebus` administration client (`ServiceBusAdministrationClient`) only when a
  test must **create/clear entities** the emulator config didn't pre-declare (most tests don't)
- `org.testcontainers:azure` (`ServiceBusEmulatorContainer`) — boots the **Azure Service Bus emulator** wired
  to its required **MS SQL** sidecar and surfaces a ready connection string (cross-link
  `qa-test-environments-java`)
- The SUT's typed publisher/consumer is **constructor-injected** with the connection string (or an injected
  client) — never a static connection string read inside an `@Test`

```
src/test/java/.../messaging/
├── ServiceBusTestBase.java     ← boots the emulator (+MS SQL), exposes the connection string
├── ServiceBusProbe.java        ← test-side receive/peek helpers (read messages + DLQ)
└── OrderPublishingTest.java
src/test/resources/
└── Config.json                 ← declares the namespace + queues/topics the tests use
```

## The Service Bus model — entities, settlement, sub-queues

- **Queue** — one log, competing consumers. Send with a **sender**, receive with a **receiver**.
- **Topic + subscription** — publish once to the topic; each **subscription** gets its own copy (filtered).
  You receive via `.receiver().topicName(...).subscriptionName(...)`.
- **Dead-letter queue (DLQ)** — every queue and subscription has a system **sub-queue** where messages that
  can't be processed (explicit dead-letter, max-delivery-count exceeded, TTL expiry) land. Reach it with
  `.subQueue(SubQueue.DEAD_LETTER)`.
- **Receive modes** (the settlement contract):
  - **Peek-lock** (`ServiceBusReceiveMode.PEEK_LOCK`, the **default**) — the broker hands you the message
    under an **exclusive lock** and waits for you to **settle** it: `complete(msg)` (done, remove),
    `abandon(msg)` (release the lock, redeliver), `deadLetter(msg, options)` (move to DLQ),
    `defer(msg)` (set aside). If you do nothing, the lock expires and it redelivers. This is what production
    code uses and what DLQ assertions depend on.
  - **Receive-and-delete** (`ServiceBusReceiveMode.RECEIVE_AND_DELETE`) — the broker deletes on delivery; no
    settlement, no redelivery, no DLQ. **Convenient for test-side draining/assertion**; never for code that
    must not lose a message on a crash.

## Local broker for tests — the Azure Service Bus emulator

There is no in-memory Service Bus. For deterministic local + CI tests, run the **Azure Service Bus
emulator**, which **depends on an MS SQL** container for its store. The emulator reads a **`Config.json`**
that declares the namespace, queues, topics and subscriptions up front (limits: **1 namespace, 50
queues/topics**). The connection string carries `UseDevelopmentEmulator=true`.

The cleanest path in Java is Testcontainers' **`ServiceBusEmulatorContainer`** — it wires the emulator to a
linked SQL container, waits for readiness, and hands you a connection string. Reuse the fixture-base
discipline from `qa-test-environments-java` (boot once per class; **never `Thread.sleep` for readiness** —
the container owns the wait strategy).

```java
import com.azure.messaging.servicebus.*;
import org.testcontainers.azure.ServiceBusEmulatorContainer;
import org.testcontainers.containers.MSSQLServerContainer;
import org.testcontainers.utility.MountableFile;
import org.testng.annotations.*;

public abstract class ServiceBusTestBase {

    // Pin tags, never `latest`. The MS SQL sidecar is the emulator's required store.
    private final MSSQLServerContainer<?> mssql =
            new MSSQLServerContainer<>("mcr.microsoft.com/mssql/server:2022-latest").acceptLicense();

    private ServiceBusEmulatorContainer emulator;

    // Intent, not the container handle. Secrets (the emulator string) are surfaced, never logged.
    protected String connectionString;

    @BeforeClass(alwaysRun = true)
    public void startBroker() {
        mssql.start();
        emulator = new ServiceBusEmulatorContainer(
                        "mcr.microsoft.com/azure-messaging/servicebus-emulator:1.1.2")
                .acceptLicense()                                            // ACCEPT_EULA=Y
                .withConfig(MountableFile.forClasspathResource("Config.json"))
                .withMsSqlServerContainer(mssql);                           // the required store
        emulator.start();
        connectionString = emulator.getConnectionString();
    }

    @AfterClass(alwaysRun = true)
    public void stopBroker() {
        if (emulator != null) emulator.stop();
        mssql.stop();
    }
}
```

`Config.json` (`src/test/resources`) declares the entities the tests use:

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
> the namespace FQDN) **from env, lazily** — never hard-code it, never log it (cross-link
> `qa-auth0-test-tokens-java` for the token-acquisition discipline). The emulator is the default for CI
> determinism; a shared cloud namespace makes tests order-dependent unless each uses a unique
> queue/subscription.

## Core pattern 1 — producer-assert (the SUT produced message X)

The SUT publishes; the test **drains the queue with a bounded receive** and asserts the message body and
properties. `receiveMessages(maxMessages, maxWaitTime)` long-polls — it *is* the condition-wait; an empty
result means "nothing arrived within the window" and fails the assertion deterministically.

```java
import static org.assertj.core.api.Assertions.assertThat;

public class OrderPublishingTest extends ServiceBusTestBase {

    private ServiceBusClientBuilder builder;
    private OrderPublisher sut;     // production code, constructor-injected with the client builder

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        builder = new ServiceBusClientBuilder().connectionString(connectionString);
        sut = new OrderPublisher(builder.sender().queueName("orders").buildClient());  // constructor injection
    }

    @Test
    public void Should_publish_OrderPlaced_When_an_order_is_submitted() {
        Order order = Orders.pending().withTotal(1999).build();   // builder (qa/java/skills/test-data-builder)

        sut.submit(order);                                        // SUT produces the message

        // Read-and-delete on the TEST side: we only want to see what was produced, no settlement needed.
        try (ServiceBusReceiverClient receiver = builder.receiver()
                .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE)
                .queueName("orders").buildClient()) {

            // Bounded long-poll = the condition-wait. Never a fixed Thread.sleep before receiving.
            ServiceBusReceivedMessage message = receiver
                    .receiveMessages(1, Duration.ofSeconds(10))
                    .stream().findFirst().orElse(null);

            assertThat(message).as("a message published to 'orders' within the wait window").isNotNull();
            OrderPlaced placed = message.getBody().toObject(OrderPlaced.class);
            assertThat(placed.orderId()).isEqualTo(order.id());   // one logical assertion: the published fact
        }
    }

    @Test
    public void Should_stamp_correlation_metadata_When_publishing() {
        Order order = Orders.pending().build();

        sut.submit(order);

        try (ServiceBusReceiverClient receiver = builder.receiver()
                .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE)
                .queueName("orders").buildClient()) {
            ServiceBusReceivedMessage message = receiver
                    .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElse(null);

            assertThat(message).isNotNull();
            assertThat(message).satisfies(m -> {                  // one behaviour: the message envelope
                assertThat(m.getSubject()).isEqualTo("OrderPlaced");
                assertThat(m.getCorrelationId()).isEqualTo(order.id().toString());
                assertThat(m.getContentType()).isEqualTo("application/json");
            });
        }
    }
}
```

## Core pattern 2 — consumer-assert (the SUT consumed → side-effect Y)

Here the SUT is a **consumer**. The test **seeds a message**, lets the consumer run, and waits for the
observable side-effect (a DB row, another message) — the side-effect is eventually consistent, so use
**Awaitility** to poll a probe on a condition. This reuses `qa-db-testing-client-java`'s discipline.

```java
import static org.awaitility.Awaitility.await;

@Test
public void Should_write_a_shipment_row_When_an_OrderPaid_message_is_consumed() {
    UUID orderId = UUID.randomUUID();

    // 1. Seed the input message onto the queue the consumer listens to.
    try (ServiceBusSenderClient sender = builder.sender().queueName("orders").buildClient()) {
        sender.sendMessage(new ServiceBusMessage(BinaryData.fromObject(new OrderPaid(orderId)))
                .setSubject("OrderPaid")
                .setContentType("application/json")
                .setCorrelationId(orderId.toString()));
    }

    // 2. The SUT (a ServiceBusProcessorClient consumer) is already running and picks it up.

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

## Peek-lock vs receive-and-delete — message settlement

When the **SUT is the consumer** and you're testing its settlement behaviour, the consumer runs in
**peek-lock** (production default) and explicitly settles. When the **test** drains a queue just to assert
what's there, **receive-and-delete** is simpler (no lock to manage). Pick by role:

| Side | Mode | Why |
|------|------|-----|
| Test asserting *what was produced* (drain + read) | `RECEIVE_AND_DELETE` | No settlement bookkeeping; you only want to see the message |
| Test exercising the *consumer's* settlement logic | `PEEK_LOCK` | Lets you assert complete vs abandon vs deadLetter and redelivery |

```java
// Consumer settlement — peek-lock, explicit settle:
try (ServiceBusReceiverClient receiver = builder.receiver()
        .queueName("orders").buildClient()) {                  // PEEK_LOCK is the default
    ServiceBusReceivedMessage msg = receiver
            .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElseThrow();

    if (canProcess(msg)) {
        receiver.complete(msg);                                // remove it — processed
    } else {
        receiver.deadLetter(msg, new DeadLetterOptions()
                .setDeadLetterReason("ValidationFailed")
                .setDeadLetterErrorDescription("missing customerId"));   // move to DLQ with a reason
    }
}
```

## Dead-letter-queue assertions

A common, high-value assertion: **a message that failed processing landed in the DLQ** (either the consumer
explicitly dead-lettered it, or it exceeded `MaxDeliveryCount`). Receive from the **DLQ sub-queue**:

```java
@Test
public void Should_dead_letter_the_message_When_the_order_payload_is_invalid() {
    try (ServiceBusSenderClient sender = builder.sender().queueName("orders").buildClient()) {
        sender.sendMessage(new ServiceBusMessage(BinaryData.fromString("{ not valid order json }"))
                .setSubject("OrderPaid").setContentType("application/json"));
    }

    // The consumer (SUT) rejects it and dead-letters it. Assert on the DLQ.
    try (ServiceBusReceiverClient dlq = builder.receiver()
            .queueName("orders")
            .subQueue(SubQueue.DEAD_LETTER)
            .buildClient()) {

        // Bounded long-poll the DLQ — wait on the condition (a message lands), not a sleep.
        ServiceBusReceivedMessage dead = dlq
                .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElse(null);

        assertThat(dead).as("the poison message in the dead-letter queue").isNotNull();
        assertThat(dead.getDeadLetterReason()).isEqualTo("ValidationFailed");   // the documented reason
    }
}
```

For a **topic subscription's** DLQ, the sub-queue hangs off the subscription:
`builder.receiver().topicName("order-events").subscriptionName("fulfilment").subQueue(SubQueue.DEAD_LETTER)`.

## Topics, subscriptions & filters

Publish to a **topic**; assert each **subscription** received the copy it should. Subscription **filters**
(SQL filters on properties, or correlation filters) mean not every subscription gets every message — assert
the routing, not just the publish.

```java
@Test
public void Should_fan_out_to_fulfilment_and_audit_When_an_order_event_is_published() {
    try (ServiceBusSenderClient sender = builder.sender().topicName("order-events").buildClient()) {
        ServiceBusMessage msg = new ServiceBusMessage(BinaryData.fromObject(new OrderPlaced(UUID.randomUUID())))
                .setSubject("OrderPlaced");
        msg.getApplicationProperties().put("region", "EU");    // a SQL filter on the subscription can match this
        sender.sendMessage(msg);
    }

    // Each subscription gets its own copy — read from both.
    try (ServiceBusReceiverClient fulfilment = builder.receiver()
                 .topicName("order-events").subscriptionName("fulfilment")
                 .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE).buildClient();
         ServiceBusReceiverClient audit = builder.receiver()
                 .topicName("order-events").subscriptionName("audit")
                 .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE).buildClient()) {

        ServiceBusReceivedMessage toFulfilment = fulfilment
                .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElse(null);
        ServiceBusReceivedMessage toAudit = audit
                .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElse(null);

        assertThat(toFulfilment).as("fulfilment subscription copy").isNotNull();   // one behaviour: fan-out
        assertThat(toAudit).as("audit subscription copy").isNotNull();
    }
}
```

## Receiving a batch / draining

To assert "exactly N messages were produced", drain with `receiveMessages(maxMessages, maxWaitTime)` and
count — the bounded wait stops it hanging when fewer than N arrive:

```java
try (ServiceBusReceiverClient receiver = builder.receiver()
        .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE).queueName("orders").buildClient()) {
    long count = receiver.receiveMessages(10, Duration.ofSeconds(5)).stream().count();
    assertThat(count).isEqualTo(3);                            // SUT produced exactly 3
}
```

## Anti-patterns

- **`Thread.sleep(5000)` before receiving / before asserting the side-effect.** Races the broker and the
  consumer; slow and flaky. *Fix:* `receiveMessages(n, maxWaitTime)` for the receive side (it long-polls),
  and **Awaitility** for consumer side-effects. The wait returns the instant the condition holds and *fails*
  if it never does.
- **Asserting on a peek-locked message but never settling it.** The lock expires, the message redelivers,
  and the next test sees a "phantom" message. *Fix:* `complete` (or dead-letter) every message you peek-lock,
  or drain with `RECEIVE_AND_DELETE` when you only need to read.
- **Sharing one queue across parallel test classes.** Competing receivers steal each other's messages.
  *Fix:* a unique queue/subscription per class, drain residuals in `@BeforeMethod`, and don't run messaging
  classes in the same TestNG parallel group unless verified isolated.
- **Not draining residual messages between tests.** *Fix:* drain-to-empty in `@BeforeMethod` (receive in a
  loop until empty), or a fresh queue per test.
- **Reading the connection string inside an `@Test` / hard-coding it.** *Fix:* surface it from the base class
  (emulator) or env (cloud test namespace), inject it; never log it.
- **Treating an empty receive as success.** Empty means nothing arrived in the window — a failed produce, not
  a pass. *Fix:* `assertThat(message).isNotNull()` first.
- **Using `RECEIVE_AND_DELETE` to test the consumer's settlement logic.** You can't assert complete vs abandon
  vs deadLetter if the broker already deleted it. *Fix:* peek-lock when settlement is under test.
- **Reaching for Service Bus when the dependency is an HTTP call.** *Fix:* `qa-api-mocking-java` —
  messaging is for async queues/topics, not request/response fakes.

## Examples

**End-to-end: a consume → process → republish flow, asserted on the side-message.**

```java
public class FulfilmentConsumerTest extends ServiceBusTestBase {

    private ServiceBusClientBuilder builder;

    @BeforeMethod(alwaysRun = true)
    public void setUp() {
        builder = new ServiceBusClientBuilder().connectionString(connectionString);
        drain("orders");                                       // independent tests — start from empty
        drain("shipments");
    }

    @Test
    public void Should_publish_ShipmentReady_When_a_valid_OrderPaid_is_consumed() {
        UUID orderId = UUID.randomUUID();
        try (ServiceBusSenderClient sender = builder.sender().queueName("orders").buildClient()) {
            sender.sendMessage(new ServiceBusMessage(BinaryData.fromObject(new OrderPaid(orderId)))
                    .setSubject("OrderPaid").setContentType("application/json")
                    .setCorrelationId(orderId.toString()));
        }

        // The SUT consumer processes "orders" and republishes onto "shipments".
        try (ServiceBusReceiverClient shipments = builder.receiver()
                .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE).queueName("shipments").buildClient()) {
            ServiceBusReceivedMessage ready = shipments
                    .receiveMessages(1, Duration.ofSeconds(10)).stream().findFirst().orElse(null);

            assertThat(ready).as("consumer republished a ShipmentReady message").isNotNull();
            assertThat(ready.getCorrelationId()).isEqualTo(orderId.toString());   // correlation preserved
        }
    }

    private void drain(String queue) {
        try (ServiceBusReceiverClient receiver = builder.receiver()
                .receiveMode(ServiceBusReceiveMode.RECEIVE_AND_DELETE).queueName(queue).buildClient()) {
            while (!receiver.receiveMessages(10, Duration.ofMillis(500)).stream().toList().isEmpty()) { }
        }
    }
}
```

Lifecycle for this test:
1. `@BeforeClass` (in `ServiceBusTestBase`) boots the emulator + MS SQL once; the connection string is
   surfaced. Entities come from `Config.json`.
2. `@BeforeMethod` drains the queues so the test starts from empty — tests stay independent and order-free.
3. The test seeds an input message; the running SUT consumer republishes; the test **long-polls** the output
   queue (the condition-wait) and asserts correlation was preserved.
4. `@AfterClass` stops the broker + SQL sidecar.

**Test-data builder for message payloads (4+ fields → builder, per the global rules).**

```java
public final class Orders {
    public static Order.Builder pending() { return new Order.Builder().status("Pending"); }
}
// Orders.pending().withTotal(...).withCurrency(...).withCustomer(...).build() — see qa/java/skills/test-data-builder
```

## Rules (hard constraints)

- **Eventual consistency = wait on a condition, never a sleep.** `receiveMessages(n, maxWaitTime)` for the
  receive side (bounded long-poll); **Awaitility** for consumer side-effects. **No `Thread.sleep`** as an
  assertion wait.
- The SUT's publisher/consumer is **constructor-injected** with the client/connection string — never a static
  client or a connection string read inside an `@Test`.
- **Settle every peek-locked message** (`complete` / `abandon` / `deadLetter`), or use `RECEIVE_AND_DELETE`
  when the test only reads. Never leave a lock to expire and redeliver into the next test.
- **Independent tests:** unique queue/subscription per class **or** drain-to-empty in `@BeforeMethod`; keep
  messaging classes out of the same parallel group unless verified isolated.
- Assert the **fact**, not the absence: an empty receive is a *failed* produce — `isNotNull()` before reading
  the body.
- **Close every client** (`try (... = builder....buildClient())`); the SDK's network calls are bounded by the
  `maxWaitTime` you pass — never block unbounded.
- Local broker = the **emulator via Testcontainers** (pinned image + MS SQL sidecar + `Config.json`); a cloud
  test namespace's connection string/token comes from **env, read lazily, never logged**.
- Test names `Should_X_When_Y`; one logical assertion per test (AssertJ); builders for 4+-field payloads;
  structured logging (SLF4J message templates); no secrets in code.

## Cross-references

- `qa-messaging-testing-dotnet` — the **canonical** stack, .NET 8 / NUnit
  (`Azure.Messaging.ServiceBus`: `new ServiceBusClient(...)`, `CreateReceiver(queue, options)`,
  `ReceiveMessageAsync(maxWaitTime)`, `SubQueue.DeadLetter`, `WaitFor.Async` poll). This file is ported from it.
- `qa-messaging-testing-typescript` — same skill, Node 20 + TS (`@azure/service-bus`:
  `new ServiceBusClient(connStr)`, `createReceiver(queue, { subQueueType: "deadLetter" })`,
  `receiveMessages(maxCount, { maxWaitTimeInMs })`, `expect.poll`).
- `references/sqs.md` (`sqs`, next in family) — AWS SQS/SNS on LocalStack; visibility timeout +
  redrive-policy DLQ — same condition-wait discipline, different broker. Then Kafka (`kafka`, offset-based) and
  RabbitMQ (`rabbitmq`, AMQP exchanges) close the family.
- `qa-db-testing-client-java` — the Awaitility poll and seeder/probe split reused for the consumer
  side-effect assertions; the **eventual-consistency lineage** this skill leans on hardest.
- `qa-test-environments-java` — booting the emulator + MS SQL sidecar; the per-class lifecycle and
  readiness-wait discipline (never `Thread.sleep`) mirrored here.
- `qa-auth0-test-tokens-java` — when authing to a cloud test namespace with an Azure AD token
  (`DefaultAzureCredential`) instead of the emulator connection string; secrets-from-env discipline.
- `qa-api-mocking-java` — the *synchronous* counterpart: fake an HTTP dependency the SUT calls.
  The boundary: WireMock = request/response fake; Service Bus = async queue/topic assertions.
- `qa-allure-reporting-java` — attach the received message body / DLQ reason to the Allure result.
- `qa-test-data-builder-java` — builders/ObjectMother for message payloads with 4+ fields.
