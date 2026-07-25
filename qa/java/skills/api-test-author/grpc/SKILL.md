---
name: qa-api-test-author-grpc-java
description: Scaffold black-box **gRPC** API tests in Java 21 with grpc-java + TestNG against a deployed, proto-defined HTTP/2 service. Triggers: "write a gRPC test for RPC X", "assert the StatusRuntimeException status code", "test a server-streaming RPC". For end-to-end suite work prefer the phased agent `qa-api-java` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — gRPC API Test Writer (Java 21 / grpc-java + TestNG)

Scaffolds black-box API tests in Java against a deployed **gRPC** service. It completes the `api-test-author`
**protocol trio** — REST (`qa-api-test-author-generator-java`, HTTP+JSON, status-driven) → GraphQL
(`qa-api-test-author-graphql-java`, one HTTP 200 carrying a `{ data, errors }` envelope) → **gRPC (this skill,
proto-defined HTTP/2 binary Protobuf, result carried in the gRPC `status`)**. Three protocols, three places the
result lives, one family. It reuses the **(contract) + Action + Test** layering of the REST/GraphQL siblings, but
the contract is the **`.proto`** (codegen the messages + stub) and the assertion targets the **typed message +
the gRPC status**, never an HTTP status code.

> **The discipline this skill encodes** — four ideas that separate a correct gRPC test from a REST/GraphQL reflex:
>
> 1. **There is no HTTP status — the result lives in the gRPC `status` (code + message + details).** Success is
>    `Status.OK`; a failure is the right `Status.Code` (`NOT_FOUND` / `INVALID_ARGUMENT` / `UNAUTHENTICATED` /
>    `PERMISSION_DENIED` / `DEADLINE_EXCEEDED` / …). This is the gRPC analogue of the GraphQL `errors` envelope and
>    the REST HTTP status: *where the outcome lives*. The generated **blocking stub throws
>    `StatusRuntimeException` on any non-OK status** — so the call is **wrapped to return a `GrpcCallResult<T>`
>    that holds the message OR the status**, and the test decides whether a non-OK status was expected (the gRPC
>    analogue of the GraphQL "client never throws — return the raw envelope").
> 2. **For rich errors, assert the `google.rpc.Status` details + trailing metadata, not just the code.** The
>    `Status.Code` is the gate; servers attach a structured **`google.rpc.Status`** with `ErrorInfo` /
>    `BadRequest` details (the `error_details` payload) and other **trailing metadata** carrying the "why". Assert
>    those — they are the gRPC analogue of the GraphQL `extensions.code` + `path`.
> 3. **Assert on the typed generated message — never hand-parse bytes.** The `.proto` is the contract; codegen the
>    messages + stub; assert on the **typed message fields** (`response.getEmail()`). A gRPC test never touches the
>    wire bytes — that's the GraphQL "query-shaped typed `data`" analogue, and the messages are the DTO
>    (`qa-api-dto-writer-java`).
> 4. **Pick the RPC type deliberately — unary / server- / client- / bidi-streaming each test differently.** A
>    **unary** call asserts the message + status. A **server-streaming** call **drains the response stream into a
>    buffer, then asserts the sequence** — a *bounded condition-wait* (the server's `onCompleted` + a deadline),
>    **never a `Thread.sleep`** → it reuses `qa-websocket-sse-testing-java`'s drain-then-assert discipline. A
>    **client-streaming** call sends a stream of requests → one response. **Bidi-streaming** interleaves both (the
>    async stub + a bounded latch).

## Decision matrix — RPC type / scenario → test shape

| RPC / scenario | What you're proving | Test shape |
|----------------|---------------------|------------|
| **Unary** (req→resp) | The right message comes back | `stub.getUser(req)` via the wrapper → `result.isOk()` → assert message fields |
| **Unary — not found / invalid** | A failure surfaces with the right code | wrapper catches `StatusRuntimeException` → `result.getStatus().getCode() == NOT_FOUND` / `INVALID_ARGUMENT` |
| **Unary — rich error** | The structured "why" is correct | assert `Status.Code` **and** the `google.rpc.Status` / `ErrorInfo` from the trailers (reason, domain, field violations) |
| **Unary — write** | The change happened and persisted | call the mutating RPC → assert the payload → **round-trip a read RPC** → assert the new state |
| **Server-streaming** (req→stream) | The right sequence of messages arrives | drain the `Iterator<T>` into a `List` (bounded by `onCompleted` + a deadline) → assert size + order + values |
| **Client-streaming** (stream→resp) | The aggregate response is right | async stub: send N requests via `requestObserver` → `onCompleted()` → await one response on a bounded latch |
| **Bidi-streaming** (stream↔stream) | Interleaved exchange works | async stub: send + collect on a bounded latch; assert the received sequence → also `qa-websocket-sse-testing-java` |
| **Deadline** | A slow call fails deterministically | `stub.withDeadlineAfter(d).slowRpc(req)` → `result.getStatus().getCode() == DEADLINE_EXCEEDED` |
| **Auth** | A call without credentials is rejected | stub **without** the bearer metadata → `UNAUTHENTICATED`; with it → `OK` |

## Stack

- Java 21, Gradle (Kotlin DSL)
- **grpc-java** — `io.grpc:grpc-netty-shaded` (transport), `io.grpc:grpc-protobuf`, `io.grpc:grpc-stub`
- **TestNG** (`org.testng:testng`) — the global default Java runner
- **`com.google.protobuf` Gradle plugin** (`protobuf-gradle-plugin`) — codegen the messages + stubs from `.proto`
- **`proto-google-common-protos`** + `io.grpc:grpc-protobuf` for `google.rpc.Status` rich-error details
- **AssertJ** (`assertThat(...)`) for fluent assertions; **Allure TestNG** for reporting
- Layout: `src/main/proto/` (the `.proto` contract), `src/main/java/action/` (stub wrappers), `src/test/java/<service>/`

```kotlin
// build.gradle.kts (excerpt)
plugins {
    java
    id("com.google.protobuf") version "0.9.5"
}
dependencies {
    implementation("io.grpc:grpc-netty-shaded:1.81.0")
    implementation("io.grpc:grpc-protobuf:1.81.0")
    implementation("io.grpc:grpc-stub:1.81.0")
    implementation("com.google.protobuf:protobuf-java:3.25.8")
    implementation("com.google.api.grpc:proto-google-common-protos:2.43.0") // google.rpc.Status, ErrorInfo
    compileOnly("org.apache.tomcat:annotations-api:6.0.53")                  // @Generated for javax.annotation
    testImplementation("org.testng:testng:7.10.2")
    testImplementation("org.assertj:assertj-core:3.26.3")
}
protobuf {
    protoc { artifact = "com.google.protobuf:protoc:3.25.8" }
    plugins { create("grpc") { artifact = "io.grpc:protoc-gen-grpc-java:1.81.0" } }
    generateProtoTasks { all().forEach { it.plugins { create("grpc") } } }
}
```

> **Why wrap the blocking stub instead of calling it directly?** The generated blocking stub **throws
> `StatusRuntimeException` the moment the server returns a non-OK status**. If a test calls the stub directly, the
> *failure path* (idea #1) becomes `assertThrows` plumbing and the *success* and *failure* assertions look nothing
> alike. A black-box test needs to assert on **either** outcome uniformly. So the canonical wrapper invokes the
> RPC, catches `StatusRuntimeException`, and returns a `GrpcCallResult<T>` holding **the message OR the status +
> trailers** — never letting the throw escape into the assertion path. This is the exact gRPC analogue of the
> GraphQL skill's thin client that *never throws on `errors` and returns the raw envelope*.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The contract + two layers**.

## Rich error details — assert `ErrorInfo`, not just the code (idea #2)

`Status.Code` is the gate, but a well-built server attaches a **`google.rpc.Status`** with typed details
(`ErrorInfo`, `BadRequest`, `QuotaFailure`, …) in the **trailing metadata** — the structured "why". Read it from
the trailers with `StatusProto`. This is the gRPC analogue of asserting the GraphQL `extensions.code` + `path`.

```java
import com.google.rpc.ErrorInfo;
import com.google.rpc.Status;            // the google.rpc.Status proto (NOT io.grpc.Status)
import io.grpc.protobuf.StatusProto;

@Test
public void createUserWhenDuplicateEmailReturnsErrorInfoReason() {
    UserGrpcAction action = new UserGrpcAction(channel, true);

    GrpcCallResult<com.example.user.v1.User> result = action.createUser(
        "george.bluth@example.com", "George", "Bluth");           // already exists

    assertThat(result.code()).isEqualTo(io.grpc.Status.Code.ALREADY_EXISTS);

    // The structured detail rides in the trailers as a google.rpc.Status with an ErrorInfo.
    Status richStatus = StatusProto.fromStatusAndTrailers(result.status(), result.trailers());
    ErrorInfo info = richStatus.getDetails(0).unpack(ErrorInfo.class);
    assertThat(info.getReason()).isEqualTo("EMAIL_TAKEN");
    assertThat(info.getDomain()).isEqualTo("user.example.com");
}
```

> Asserting only `ALREADY_EXISTS` proves *a* conflict; asserting the `ErrorInfo.reason` proves the **right**
> conflict — the same step up from "an error happened" to "the contracted error happened" that
> `errors[0].extensions.code` makes in the GraphQL sibling.

## Unary write — assert the payload, then round-trip the read (idea #4)

A mutating RPC returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
message, then read it back with the read RPC. Clean up created data in `@AfterMethod` (guarded so a cleanup
failure can't mask a test failure).

```java
@Test
public void createUserWhenValidPersistsAndIsReadable() {
    UserGrpcAction action = new UserGrpcAction(channel, true);

    GrpcCallResult<User> created = action.createUser("neo@example.com", "Thomas", "Anderson");
    assertThat(created.isOk()).isTrue();
    assertThat(created.value().getEmail()).isEqualTo("neo@example.com");

    // round-trip: prove it persisted, don't trust the RPC's own echo
    GrpcCallResult<User> fetched = action.getUser(created.value().getId());
    assertThat(fetched.value().getEmail()).isEqualTo("neo@example.com");
}
```

## Server-streaming — drain the stream, then assert (idea #4, bounded-wait not sleep)

A server-streaming RPC pushes a *sequence* of messages and then completes. The blocking stub hands back an
`Iterator<T>`; **draining it blocks until the server calls `onCompleted`** (or the deadline trips) — a *bounded
condition-wait*, **never a `Thread.sleep`**. Drain into a buffer, then assert size + order + values. This is the
same drain-then-assert discipline as `qa-websocket-sse-testing-java`.

```java
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Test
public void listUsersStreamsAllUsersInOrder() {
    UserGrpcAction action = new UserGrpcAction(channel, true);

    // Deadline bounds the wait — the stream ends on onCompleted, or DEADLINE_EXCEEDED trips deterministically.
    Iterator<User> stream = action.listUsers(/* pageSize */ 50);

    List<User> received = new ArrayList<>();
    stream.forEachRemaining(received::add);   // drains until server completes — bounded, no sleep

    assertThat(received).hasSize(12);
    assertThat(received).extracting(User::getId).containsExactly(
        "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12");
}
```

> The bound is the server's `onCompleted` plus the channel/stub **deadline** — not a timer you guessed. If a
> server-streaming RPC can run unbounded, attach `stub.withDeadlineAfter(...)` so a hung stream fails as
> `DEADLINE_EXCEEDED` instead of hanging the suite.

## Client- and bidi-streaming — async stub + a bounded latch

The blocking stub can't drive client- or bidi-streaming (the client itself produces a stream). Use the **async
stub** with a `StreamObserver`, and wait on a **`CountDownLatch` with a bounded `await(timeout)`** — the
sanctioned no-sleep wait — never an unbounded `latch.await()`.

```java
import com.example.user.v1.*;
import io.grpc.stub.StreamObserver;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

@Test
public void importUsersAggregatesAllSentRequests() throws InterruptedException {
    UserGrpcAction action = new UserGrpcAction(channel, true);

    CountDownLatch done = new CountDownLatch(1);
    AtomicReference<ImportSummary> summary = new AtomicReference<>();
    AtomicReference<Throwable> failure = new AtomicReference<>();

    StreamObserver<ImportSummary> responseObserver = new StreamObserver<>() {
        @Override public void onNext(ImportSummary s) { summary.set(s); }
        @Override public void onError(Throwable t)    { failure.set(t); done.countDown(); }
        @Override public void onCompleted()           { done.countDown(); }
    };

    StreamObserver<CreateUserRequest> requestObserver = action.async().importUsers(responseObserver);
    requestObserver.onNext(CreateUserRequest.newBuilder().setEmail("a@example.com").build());
    requestObserver.onNext(CreateUserRequest.newBuilder().setEmail("b@example.com").build());
    requestObserver.onCompleted();

    assertThat(done.await(5, TimeUnit.SECONDS)).as("server completed within deadline").isTrue();  // bounded wait
    assertThat(failure.get()).isNull();
    assertThat(summary.get().getImported()).isEqualTo(2);
}
```

> Bidi-streaming follows the same shape — interleave `requestObserver.onNext(...)` with messages collected in
> `onNext`, all gated by a bounded latch. For richer bidi-stream-lifecycle assertions (ordering, mid-stream close
> codes), cross-link `qa-websocket-sse-testing-java` — gRPC streaming and WebSocket/SSE share the
> drain-then-assert-on-a-bounded-condition discipline.

## Deadlines — the sanctioned bounded-wait, asserted as `DEADLINE_EXCEEDED`

A **deadline** is gRPC's first-class timeout, and the *only* sanctioned way to bound a slow call — there is no
`Thread.sleep` anywhere in these tests. Set it per call on the stub; a call that overruns fails deterministically
as `DEADLINE_EXCEEDED`.

```java
@Test
public void slowCallExceedingDeadlineReturnsDeadlineExceeded() {
    UserGrpcAction action = new UserGrpcAction(channel, true);

    GrpcCallResult<User> result = action.getUserWithDeadline("slow-1", /* millis */ 100);

    assertThat(result.code()).isEqualTo(io.grpc.Status.Code.DEADLINE_EXCEEDED);
}
```
```java
// in UserGrpcAction:
public GrpcCallResult<User> getUserWithDeadline(String id, long millis) {
    return call(() -> blocking
        .withDeadlineAfter(millis, java.util.concurrent.TimeUnit.MILLISECONDS)
        .getUser(GetUserRequest.newBuilder().setId(id).build()));
}
```

## Standing the service up — Testcontainers + the channel lifecycle

The channel points at the service under test, stood up via Testcontainers. The `BaseGrpcTest`
opens one `ManagedChannel` for the suite and shuts it down after — no per-test channel churn.

```java
package base;

import io.grpc.ManagedChannel;
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import utility.SystemPropertyUtil;
import java.util.concurrent.TimeUnit;

public abstract class BaseGrpcTest {
    protected ManagedChannel channel;

    @BeforeClass
    public void openChannel() {
        // host:port from Testcontainers / env — never hardcoded. usePlaintext only for local test brokers.
        channel = NettyChannelBuilder.forTarget(SystemPropertyUtil.getGrpcTarget())
            .usePlaintext()
            .build();
    }

    @AfterClass(alwaysRun = true)
    public void closeChannel() throws InterruptedException {
        if (channel != null) channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
    }
}
```

> **Reflection / `grpcurl` are for exploration, not the test path.** gRPC server reflection + `grpcurl` are great
> for poking a service by hand, but a regression test goes through the **typed stub** — it's the contract-bound,
> refactor-safe path. Note reflection in a comment; assert through the stub.

## Anti-patterns

- **Looking for an HTTP status code.** gRPC has none in the application sense — the outcome is the gRPC
  `Status.Code`. *Fix:* assert `result.code()` / `result.isOk()`, never a 200/404.
- **Calling the blocking stub directly and letting `StatusRuntimeException` fly.** The failure path becomes
  `assertThrows` plumbing and looks nothing like the success path. *Fix:* the wrapper catches it and returns a
  `GrpcCallResult<T>` the test asserts on uniformly (the GraphQL "never throw — return the envelope" analogue).
- **Asserting only the `Status.Code` on a rich error.** "An `ALREADY_EXISTS` happened" is not the contract. *Fix:*
  unpack the `google.rpc.Status` / `ErrorInfo` from the trailers and assert `reason` / `domain` / field violations.
- **`Thread.sleep` to wait for a stream.** Banned by CLAUDE.md and unnecessary. *Fix:* drain the `Iterator` (it
  blocks until `onCompleted`) or await a `CountDownLatch` with a **bounded** `await(timeout)`; bound unbounded
  streams with `withDeadlineAfter`.
- **An unbounded `latch.await()` with no timeout.** A hung server hangs the whole suite. *Fix:* always
  `await(timeout, unit)` and assert it returned `true`.
- **Hand-parsing the response bytes / using a dynamic `Struct`.** *Fix:* assert on the typed generated message;
  the `.proto` is the contract. Model/generate messages via `qa-api-dto-writer-java`.
- **Trusting a write RPC's echoed payload as proof of persistence.** *Fix:* round-trip a read RPC and assert state.
- **Re-using one channel per test method (or never shutting it down).** *Fix:* one `ManagedChannel` per suite in
  `@BeforeClass`, `shutdownNow().awaitTermination(...)` in `@AfterClass(alwaysRun = true)`.
- **Hardcoding the target / committing the token.** *Fix:* `SystemPropertyUtil` / env, read lazily, never logged;
  bearer via `qa-auth0-test-tokens-java`. Reaching for this skill for **load** → `qa-performance-gatling-java`; for
  a **Protobuf contract** → `qa-contract-testing-pact-java`.

## Examples

**End-to-end: a not-found RPC proves the status discipline.** A REST author writes
`assertEquals(response.getStatusCode(), SC_NOT_FOUND)`; a GraphQL author writes
`errors[0].extensions.code == "NOT_FOUND"`. The gRPC-correct version asserts
`result.code() == Status.Code.NOT_FOUND` — same outcome, third location: the REST status line, the GraphQL
`errors` envelope, the gRPC `status`. One family, three result-location conventions.

**Composing with the protocol-trio siblings.** REST `generator` is status-driven over HTTP+JSON; GraphQL ``api-test-author/graphql`` is
one HTTP 200 carrying `{ data, errors }`; gRPC is proto/HTTP2 with the result in the `status`. All three share the
**Action + Test** spine and the "wrap the call so the test asserts success *or* failure uniformly" move (the gRPC
`GrpcCallResult` is the GraphQL raw-envelope analogue). Only the transport, the codegen, and where-the-result-lives
differ.

## Rules (hard constraints)

- **The gate is the gRPC `Status.Code`, not an HTTP status.** Assert `result.isOk()` (success) or the specific
  failure `code()` (`NOT_FOUND` / `INVALID_ARGUMENT` / `UNAUTHENTICATED` / `DEADLINE_EXCEEDED` / …) — never a
  200/404.
- **The action never lets `StatusRuntimeException` escape.** `call(...)` returns a `GrpcCallResult<T>` holding the
  message **or** the status + trailers; the test decides whether a non-OK status was expected. No `assertThrows`
  in the assertion path, no deserialization or assertion inside the action.
- **Rich errors assert the `google.rpc.Status` details** (`ErrorInfo.reason`/`domain`, `BadRequest` field
  violations) from the trailers — not a bare `Status.Code`.
- **Assert on the typed generated message** — never hand-parse bytes; the `.proto` is the contract. Messages via
  `qa-api-dto-writer-java`.
- **A write RPC test round-trips a read** to prove persistence; data created in a test is cleaned up in
  `@AfterMethod` (guarded so it can't mask a failure).
- **Streaming = drain-then-assert on a bounded condition** — drain the `Iterator` (server-streaming) or await a
  `CountDownLatch` with `await(timeout, unit)` (client-/bidi-streaming); bound unbounded streams with
  `withDeadlineAfter`. **No `Thread.sleep`, no unbounded `await()`.** Deep stream-lifecycle assertions →
  `qa-websocket-sse-testing-java`.
- **One `ManagedChannel` per suite** (`@BeforeClass` open, `@AfterClass(alwaysRun=true)` shutdown); service stood
  up via Testcontainers. **Target + token via `SystemPropertyUtil`/env**, lazy, never logged. TestNG +
  grpc-java + AssertJ.

## Cross-references

- `qa-api-test-author-grpc-typescript` · `qa-api-test-author-grpc-dotnet` — the sibling stacks (`@grpc/grpc-js` +
  `@grpc/proto-loader` · `Grpc.Net.Client` + `Grpc.Tools`); same four ideas, different codegen/client/assertion
  libs.
- `qa-api-test-author-generator-java` · `qa-api-test-author-graphql-java` — the **protocol-trio siblings**: REST
  (HTTP+JSON status-driven) and GraphQL (HTTP 200 `{ data, errors }` envelope). Three protocols, three
  result-location conventions, one `api-test-author` family + shared Action + Test spine.
- `qa-websocket-sse-testing-java` — gRPC **streaming** reuses its drain-then-assert-on-a-bounded-condition
  discipline; cross-link for deep stream-lifecycle (ordering, mid-stream close) assertions, don't duplicate.
- `qa-api-dto-writer-java` — generate/model the proto messages (the DTO analogue) in isolation; this skill
  consumes them.
- `qa-contract-testing-pact-java` — the **Protobuf contract** boundary (Pact's Protobuf/gRPC plugin) vs the
  functional test this skill writes. `qa-performance-gatling-java` — gRPC **load**.
- `qa-auth0-test-tokens-java` — obtain the per-call **bearer** carried in leading metadata.
- `qa-allure-reporting-java` — each RPC renders as a named result.
