# Message pacts (async CDCT) — Java / Pact-JVM

For event-driven interactions the consumer never makes an HTTP call — it consumes a message off a broker. Pact contracts the **message body + metadata**, not the broker. The consumer test asserts that its real message handler can process a message of the agreed shape; the provider test asserts the code that produces the message emits that shape. The broker (Kafka/SQS/RabbitMQ) is mocked out on both sides — its wiring belongs to `qa/java/skills/messaging-testing`, not here.

Use the V4 async DSL: `@PactTestFor(providerType = ProviderType.ASYNCH)` and the `PactBuilder` (not `PactDslWithProvider`).

### Consumer side — feed the message through the real handler

```java
package com.example.cart.contract;

import au.com.dius.pact.consumer.dsl.PactBuilder;
import au.com.dius.pact.consumer.junit5.PactConsumerTestExt;
import au.com.dius.pact.consumer.junit5.PactTestFor;
import au.com.dius.pact.consumer.junit5.ProviderType;
import au.com.dius.pact.core.model.V4Interaction;
import au.com.dius.pact.core.model.V4Pact;
import au.com.dius.pact.core.model.annotations.Pact;
import com.example.cart.messaging.OrderPaidHandler;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(PactConsumerTestExt.class)
@PactTestFor(providerName = "orders-service", providerType = ProviderType.ASYNCH)
class OrderPaidConsumerTest {

    @Pact(consumer = "cart-service")
    public V4Pact orderPaidPact(PactBuilder builder) {
        return builder
            .expectsToReceive("an OrderPaid event", "core/interaction/message")
            .with(java.util.Map.of(
                "message.contents", new au.com.dius.pact.consumer.dsl.PactDslJsonBody()
                    .stringType("orderId", "123")
                    .stringType("customerId", "cus_alice")
                    .integerType("amountMinor", 9999)
                    .stringMatcher("currency", "^[A-Z]{3}$", "EUR")
                    .datetime("paidAt", "yyyy-MM-dd'T'HH:mm:ssXXX"),
                "message.metadata", java.util.Map.of("contentType", "application/json", "topic", "order.paid")
            ))
            .toPact();
    }

    @Test
    @PactTestFor(pactMethod = "orderPaidPact")
    void handlerProcessesOrderPaid(V4Pact pact) {
        List<V4Interaction.AsynchronousMessage> messages = pact.getInteractions().stream()
            .map(i -> (V4Interaction.AsynchronousMessage) i)
            .toList();

        var payload = messages.get(0).getContents().getContents().valueAsString();
        new OrderPaidHandler().handle(payload);

        assertThat(/* observable side effect of the handler */ true).isTrue();
    }
}
```

- Assert the message through the **actual handler** the consumer ships — a passing test means "our deserialization + processing works against this shape", which is the only thing worth contracting.
- `eachLike(min)`, `stringType`, `datetime` matchers apply to message bodies exactly as to HTTP bodies.
- Metadata (topic, partition key, `contentType`) is part of the contract — assert it via `message.metadata`.

### Provider side — `@PactVerifyProvider` returns the produced message

```java
package com.example.orders.contract;

import au.com.dius.pact.provider.junit5.MessageTestTarget;
import au.com.dius.pact.provider.junit5.PactVerificationContext;
import au.com.dius.pact.provider.junit5.PactVerificationInvocationContextProvider;
import au.com.dius.pact.provider.junitsupport.Provider;
import au.com.dius.pact.provider.junitsupport.State;
import au.com.dius.pact.provider.junitsupport.loader.PactBroker;
import au.com.dius.pact.provider.junitsupport.loader.VersionSelector;
import au.com.dius.pact.provider.junitsupport.target.PactVerifyProvider;
import com.example.orders.events.OrderPaidPublisher;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.TestTemplate;
import org.junit.jupiter.api.extension.ExtendWith;

@Provider("orders-service")
@PactBroker(selectors = {
    @VersionSelector(mainBranch = "true"),
    @VersionSelector(deployedOrReleased = "true")
})
class OrderPaidProviderVerificationTest {

    @BeforeEach
    void setTarget(PactVerificationContext context) {
        context.setTarget(new MessageTestTarget());
    }

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) {
        context.verifyInteraction();
    }

    @PactVerifyProvider("an OrderPaid event")
    String produceOrderPaid() {
        return new OrderPaidPublisher().serialize(/* a representative OrderPaid */);
    }
}
```

- Provider target is **`MessageTestTarget`**, never `HttpTestTarget`.
- `@PactVerifyProvider("<description>")` matches the consumer's `expectsToReceive(...)` description; the returned string is replayed against the consumer's expected body/metadata.
- State setup (`@State`) works the same as HTTP when the produced message depends on data.
- Publish/verify CI and `can-i-deploy` are identical to the HTTP flow — message pacts go to the same Broker.
