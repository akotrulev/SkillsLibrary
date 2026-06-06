---
name: qa-contract-testing-pact-java
description: Use when the user asks to set up consumer-driven contract testing with Pact in a Java 21 + Spring Boot 3 service (Pact-JVM, JUnit 5) — consumer tests, provider verification, Pact Broker publish, can-i-deploy, state handlers. Triggers: "set up Pact-JVM for our Spring Boot service", "consumer Pact test in Java for X", "verify our Java provider against Y's contract", "wire can-i-deploy in the Gradle deploy". Do NOT use for .NET consumers or providers (use `qa/dotnet/skills/contract-testing-pact`), TypeScript/Node consumers or providers (use `qa/typescript/skills/contract-testing-pact`), live-service API tests (use `qa/java/skills/api-test-author/generator`), or OpenAPI-only validation. Load `qa/_shared/contract-testing-pact` alongside this skill for the Broker / matchers / can-i-deploy concepts.
---

# QA — Contract Testing with Pact (Java / Pact-JVM)

Wires Pact V4 into a Java 21 + Spring Boot 3 service via **Pact-JVM** for consumer-driven contract testing with JUnit 5. Covers the consumer test, provider verification, state handlers, and Gradle/CI publish. Load `qa/_shared/contract-testing-pact` for the Broker model, matchers reference, and `can-i-deploy` gate that are shared across all stacks.

## When to use

- A Java 21 / Spring Boot 3 service consumes or produces an HTTP API and needs contract coverage.
- Replacing brittle multi-service E2E tests with Pact-JVM verification.
- Catching breaking changes at the Java producer side before they ship.
- Pairing with `qa/_shared/contract-testing-pact` for Broker / `can-i-deploy` wiring.

## When NOT to use

- .NET consumer or provider → `qa/dotnet/skills/contract-testing-pact`
- TypeScript / Node consumer or provider → `qa/typescript/skills/contract-testing-pact`
- Live-service API tests (no contract) → `qa/java/skills/api-test-author/generator`
- OpenAPI-only validation with no consumer-driven aspect → schema validation library

## Stack

- **Runtime**: Java 21
- **Framework**: Spring Boot 3.x
- **Build**: Gradle (Kotlin DSL)
- **Test runner**: **JUnit 5** for contract tests (see note below)
- **Pact lib**: `au.com.dius.pact.consumer:junit5` and `au.com.dius.pact.provider:junit5` (Pact-JVM 4.6+)
- **Broker CLI**: `pactfoundation/pact-cli:latest` (containerized — language-independent)

> **Why JUnit 5 here despite the library-wide TestNG default?** Pact-JVM ships its consumer test runner (`PactConsumerTestExt`) and provider runner (`PactVerificationInvocationContextProvider`) as JUnit 5 extensions only — there is no maintained TestNG equivalent. Keep contract tests in their own Gradle sub-module so the rest of the suite stays on TestNG.

Project layout (multi-module Gradle):

```
settings.gradle.kts
build.gradle.kts
cart-service/                          ← consumer
├── build.gradle.kts
└── src/main/java/...
orders-service/                        ← provider
├── build.gradle.kts
└── src/main/java/...
cart-service-contract-tests/           ← JUnit 5 module
├── build.gradle.kts                   ← useJUnitPlatform()
└── src/test/java/...
└── build/pacts/                       ← generated, gitignored
orders-service-contract-tests/         ← JUnit 5 module
├── build.gradle.kts
└── src/test/java/...
```

`build/pacts/` is generated output — `.gitignore` it. The Broker is the source of truth.

### Dependencies (consumer-contract-tests module)

```kotlin
// cart-service-contract-tests/build.gradle.kts
plugins { java }

dependencies {
    testImplementation("au.com.dius.pact.consumer:junit5:4.6.+")
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.+")
    testImplementation("org.assertj:assertj-core:3.25.+")
    testImplementation(project(":cart-service"))   // for the client class under test
}

tasks.test {
    useJUnitPlatform()
    systemProperty("pact.rootDir", "$buildDir/pacts")
}
```

### Dependencies (provider-contract-tests module)

```kotlin
dependencies {
    testImplementation("au.com.dius.pact.provider:junit5:4.6.+")
    testImplementation("au.com.dius.pact.provider:junit5spring:4.6.+")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation(project(":orders-service"))
}

tasks.test { useJUnitPlatform() }
```

## Consumer test (JUnit 5)

```java
package com.example.cart.contract;

import au.com.dius.pact.consumer.MockServer;
import au.com.dius.pact.consumer.dsl.PactDslJsonBody;
import au.com.dius.pact.consumer.dsl.PactDslWithProvider;
import au.com.dius.pact.consumer.junit5.PactConsumerTestExt;
import au.com.dius.pact.consumer.junit5.PactTestFor;
import au.com.dius.pact.core.model.V4Pact;
import au.com.dius.pact.core.model.annotations.Pact;
import com.example.cart.clients.OrdersClient;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(PactConsumerTestExt.class)
@PactTestFor(providerName = "orders-service")
class OrdersConsumerTest {

    @Pact(consumer = "cart-service")
    public V4Pact getOrderPact(PactDslWithProvider builder) {
        return builder
            .given("order 123 exists for customer cus_alice")
            .uponReceiving("a request for order 123")
                .path("/orders/123")
                .method("GET")
                .headers("Accept", "application/json")
            .willRespondWith()
                .status(200)
                .headers(Map.of("Content-Type", "application/json"))
                .body(new PactDslJsonBody()
                    .stringType("id", "123")
                    .stringType("customerId", "cus_alice")
                    .stringMatcher("status", "pending|paid|cancelled|refunded", "paid")
                    .integerType("totalMinor", 9999)
                    .stringMatcher("currency", "^[A-Z]{3}$", "EUR"))
            .toPact(V4Pact.class);
    }

    @Test
    @PactTestFor(pactMethod = "getOrderPact")
    void shouldFetchOrder(MockServer mockServer) {
        var client = new OrdersClient(mockServer.getUrl());
        var order = client.getOrder("123");
        assertThat(order.id()).isEqualTo("123");
        assertThat(order.status()).isEqualTo("paid");
    }
}
```

- Assert **types** via `stringType` / `integerType` / `stringMatcher` (regex). Reserve exact values for true enum constraints.
- `given(...)` names a provider state — the provider implements a matching handler.
- `MockServer` is injected by the extension. Pass `mockServer.getUrl()` to the client under test.

## Provider verification (JUnit 5, Spring Boot)

```java
package com.example.orders.contract;

import au.com.dius.pact.provider.junit5.HttpTestTarget;
import au.com.dius.pact.provider.junit5.PactVerificationContext;
import au.com.dius.pact.provider.junit5.PactVerificationInvocationContextProvider;
import au.com.dius.pact.provider.junitsupport.Provider;
import au.com.dius.pact.provider.junitsupport.State;
import au.com.dius.pact.provider.junitsupport.loader.PactBroker;
import au.com.dius.pact.provider.junitsupport.loader.VersionSelector;
import au.com.dius.pact.provider.junitsupport.reporter.VerificationReports;
import com.example.orders.domain.Order;
import com.example.orders.domain.OrdersRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.TestTemplate;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

@Provider("orders-service")
@PactBroker(
    selectors = {
        @VersionSelector(mainBranch = "true"),
        @VersionSelector(deployedOrReleased = "true")
    }
)
@VerificationReports({ "console", "markdown" })
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class OrdersProviderVerificationTest {

    @LocalServerPort int port;
    @Autowired OrdersRepository repo;

    @BeforeEach
    void setTarget(PactVerificationContext context) {
        context.setTarget(new HttpTestTarget("localhost", port));
    }

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) {
        context.verifyInteraction();
    }

    @State("order 123 exists for customer cus_alice")
    void orderExists() {
        repo.save(new Order("123", "cus_alice", "paid", 9999, "EUR"));
    }
}
```

System properties required at test run time:

```
-Dpact.provider.version=$GIT_SHA
-Dpact.provider.branch=$BRANCH_NAME
-Dpact.verifier.publishResults=true
-Dpactbroker.url=$PACT_BROKER_BASE_URL
-Dpactbroker.auth.token=$PACT_BROKER_TOKEN
```

Pass them via the Gradle `test` task in CI:

```kotlin
tasks.test {
    useJUnitPlatform()
    systemProperty("pact.provider.version", System.getenv("GIT_SHA") ?: "")
    systemProperty("pact.provider.branch", System.getenv("BRANCH_NAME") ?: "")
    systemProperty("pact.verifier.publishResults", "true")
    systemProperty("pactbroker.url", System.getenv("PACT_BROKER_BASE_URL") ?: "")
    systemProperty("pactbroker.auth.token", System.getenv("PACT_BROKER_TOKEN") ?: "")
}
```

## CI — consumer side

```bash
./gradlew :cart-service-contract-tests:test

docker run --rm \
  -v "$PWD/cart-service-contract-tests/build/pacts:/pacts" \
  -e PACT_BROKER_BASE_URL=$PACT_BROKER_BASE_URL \
  -e PACT_BROKER_TOKEN=$PACT_BROKER_TOKEN \
  pactfoundation/pact-cli:latest \
  broker publish /pacts \
  --consumer-app-version "$GIT_SHA" \
  --branch "$BRANCH_NAME"
```

## CI — provider side

```bash
PACT_BROKER_BASE_URL=$BROKER \
PACT_BROKER_TOKEN=$TOKEN \
GIT_SHA=$GIT_SHA \
BRANCH_NAME=$BRANCH_NAME \
  ./gradlew :orders-service-contract-tests:test
```

Verification results are published back to the Broker via `pact.verifier.publishResults=true`.

## `can-i-deploy` gate (both pipelines)

See `qa/_shared/contract-testing-pact` for the shared `can-i-deploy` and `record-deployment` commands. Wire them in the deploy stage of **both** the consumer and the provider pipelines, before `kubectl apply` / `helm upgrade`.

## Rules (Java-specific)

- **Contract tests live in a dedicated Gradle sub-module** using `useJUnitPlatform()`; the rest of the suite stays on TestNG.
- **Consumer's HTTP client takes the base URL via constructor.** Tests pass `mockServer.getUrl()` — never use static config.
- **`@SpringBootTest(webEnvironment = RANDOM_PORT)`** on the provider verification class; bind via `@LocalServerPort`.
- **State handlers use `@State("...")`** methods on the verification class, with `@Autowired` repositories / services to seed real persistence.
- **`V4Pact`** for new contracts; `RequestResponsePact` only for legacy interop.
- **`pact.rootDir` system property** points at `build/pacts/`; that directory is gitignored.
- **AssertJ** for assertions; `assertEquals(...)` from JUnit is acceptable but AssertJ reads better.
- **Records** for client DTOs returned in tests; no mutable POJOs in test code.
- **No `Thread.sleep`** between the consumer call and the assertion — `MockServer` is already running.

## What NOT to do

- No verifying against the consumer's `localhost` test instance — boot the provider with `@SpringBootTest(RANDOM_PORT)` and target it via `HttpTestTarget`.
- No state handlers that call out to staging/prod systems — handlers seed local data only.
- No exact-value matchers everywhere — over-asserting breaks on harmless field additions.
- No pact files committed and treated as the source of truth.
- No `MockMvc` for provider verification — Pact-JVM needs a real HTTP target (`HttpTestTarget`).
- No mixing the consumer's contract test with its regular unit tests in the same Gradle task — keep them separate so the test task can be skipped on PRs that don't touch the contract.
- No publishing without `--branch` and `--consumer-app-version` — Broker becomes incapable of correctly answering `can-i-deploy`.
- No `@VersionSelector(mainBranch = "true")` alone — always also include `@VersionSelector(deployedOrReleased = "true")`.

## Generation steps

1. Add a Gradle sub-module `{service}-contract-tests` with `useJUnitPlatform()`.
2. For the consumer: scaffold `{Provider}ConsumerTest.java` annotated with `@ExtendWith(PactConsumerTestExt.class)` + `@PactTestFor(providerName = "{provider}")`; author one `@Pact` method + one `@Test`; run `./gradlew :{module}:test`; confirm a pact file appears under `build/pacts/`.
3. For the provider: scaffold `{Service}ProviderVerificationTest.java` with `@Provider`, `@PactBroker`, `@SpringBootTest(RANDOM_PORT)`, and a `@State("…")` handler per state name.
4. Configure Gradle `test` task system properties (`pact.provider.version`, `pact.provider.branch`, `pact.verifier.publishResults`, `pactbroker.url`, `pactbroker.auth.token`).
5. Wire consumer CI: `./gradlew :{consumer}-contract-tests:test` → `pact-cli broker publish` with `--branch` and `--consumer-app-version`.
6. Wire provider CI: `./gradlew :{provider}-contract-tests:test` with `PACT_BROKER_*` / `GIT_SHA` / `BRANCH_NAME` env vars.
7. Add `can-i-deploy` and `record-deployment` to both deploy pipelines (see `_shared`).
8. Smoke a full cycle: change the contract on the consumer → fail provider verification → fix → success.

## Handoffs

- Cross-stack Broker / `can-i-deploy` / matchers concepts → `qa/_shared/contract-testing-pact`
- .NET consumer/provider → `qa/dotnet/skills/contract-testing-pact`
- TypeScript consumer/provider → `qa/typescript/skills/contract-testing-pact`
- Live-service API tests → `qa/java/skills/api-test-author/generator`
- DTOs → `qa/java/skills/api-dto-writer`
- CI pipeline syntax → `qa/java/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Allure publishing for contract test results → `qa/java/skills/allure-reporting`
