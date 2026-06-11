---
name: qa-api-test-author-grpc-dotnet
description: Scaffold black-box **gRPC** API tests in .NET 8 with Grpc.Net.Client + NUnit against a deployed, proto-defined HTTP/2 service. Triggers: "write a gRPC test for RPC X", "assert the RpcException StatusCode", "test a server-streaming RPC".
---

# QA — gRPC API Test Writer (.NET 8 / Grpc.Net.Client + NUnit)

> **Ported from the canonical `qa-api-test-author-grpc-java`.** The four ideas and the section order are
> identical; only the runner (NUnit instead of TestNG), the client (`Grpc.Net.Client` instead of grpc-java), the
> codegen (`Grpc.Tools` `.csproj` `<Protobuf>` items instead of `protobuf-gradle-plugin`), and the
> async-all-the-way style change. See the Java file for the family rationale.

Scaffolds black-box API tests in .NET against a deployed **gRPC** service. It completes the `api-test-author`
**protocol trio** — REST (`qa-api-test-author-generator-dotnet`, HTTP+JSON, status-driven) → GraphQL
(`qa-api-test-author-graphql-dotnet`, one HTTP 200 carrying a `{ data, errors }` envelope) → **gRPC (this skill,
proto-defined HTTP/2 binary Protobuf, result carried in the gRPC `Status`)**. Three protocols, three places the
result lives, one family. It reuses the **(contract) + Action + Test** layering of the REST/GraphQL siblings, but
the contract is the **`.proto`** (codegen the messages + client) and the assertion targets the **typed message +
the gRPC `StatusCode`**, never an HTTP status code.

> **The discipline this skill encodes** — four ideas that separate a correct gRPC test from a REST/GraphQL reflex:
>
> 1. **There is no HTTP status — the result lives in the gRPC `Status` (code + detail + details).** Success is
>    `StatusCode.OK`; a failure is the right `StatusCode` (`NotFound` / `InvalidArgument` / `Unauthenticated` /
>    `PermissionDenied` / `DeadlineExceeded` / …). This is the gRPC analogue of the GraphQL `errors` envelope and
>    the REST HTTP status: *where the outcome lives*. The generated async client **throws `RpcException` on any
>    non-OK status** — so the call is **wrapped to return a `GrpcCallResult<T>` that holds the message OR the
>    status (+ trailers)**, and the test decides whether a non-OK status was expected (the gRPC analogue of the
>    GraphQL "client never throws — return the raw envelope").
> 2. **For rich errors, assert the `google.rpc.Status` details + trailing metadata, not just the code.** The
>    `StatusCode` is the gate; servers attach a structured **`google.rpc.Status`** with `ErrorInfo` / `BadRequest`
>    details (read via `RpcException.GetRpcStatus()`) and other **trailing metadata** carrying the "why". Assert
>    those — they are the gRPC analogue of the GraphQL `extensions.code` + `path`.
> 3. **Assert on the typed generated message — never hand-parse bytes.** The `.proto` is the contract; `Grpc.Tools`
>    codegen the messages + client; assert on the **typed message fields** (`response.Email`). A gRPC test never
>    touches the wire bytes — that's the GraphQL "query-shaped typed `data`" analogue, and the messages are the DTO
>    (`qa-api-dto-writer-dotnet`).
> 4. **Pick the RPC type deliberately — unary / server- / client- / bidi-streaming each test differently.** A
>    **unary** call asserts the message + status. A **server-streaming** call **drains
>    `ResponseStream.ReadAllAsync()` into a buffer, then asserts the sequence** — a *bounded async-await* (the
>    server's stream completion + a deadline), **never a `Task.Delay`** → it reuses
>    `qa-websocket-sse-testing-dotnet`'s drain-then-assert discipline. A **client-streaming** call writes a stream
>    of requests → one response. **Bidi-streaming** interleaves both.

## Decision matrix — RPC type / scenario → test shape

| RPC / scenario | What you're proving | Test shape |
|----------------|---------------------|------------|
| **Unary** (req→resp) | The right message comes back | `await client.GetUserAsync(req)` via the wrapper → `result.IsOk` → assert message fields |
| **Unary — not found / invalid** | A failure surfaces with the right code | wrapper catches `RpcException` → `result.Code == StatusCode.NotFound` / `InvalidArgument` |
| **Unary — rich error** | The structured "why" is correct | assert `StatusCode` **and** the `google.rpc.Status` / `ErrorInfo` via `GetRpcStatus()` (reason, domain, field violations) |
| **Unary — write** | The change happened and persisted | call the mutating RPC → assert the payload → **round-trip a read RPC** → assert the new state |
| **Server-streaming** (req→stream) | The right sequence of messages arrives | `await foreach (var m in call.ResponseStream.ReadAllAsync())` into a `List` (bounded by completion + deadline) → assert |
| **Client-streaming** (stream→resp) | The aggregate response is right | `RequestStream.WriteAsync` N times → `CompleteAsync()` → `await call.ResponseAsync` |
| **Bidi-streaming** (stream↔stream) | Interleaved exchange works | write + drain `ResponseStream.ReadAllAsync()` concurrently; assert the received sequence → also `qa-websocket-sse-testing-dotnet` |
| **Deadline** | A slow call fails deterministically | `GetUserAsync(req, deadline: DateTime.UtcNow.AddMilliseconds(d))` → `StatusCode.DeadlineExceeded` |
| **Auth** | A call without credentials is rejected | client **without** the bearer metadata → `Unauthenticated`; with it → `OK` |

## Stack

- .NET 8, C# (nullable reference types enabled)
- **`Grpc.Net.Client`** (`GrpcChannel.ForAddress`) — the channel + generated client
- **`Grpc.Tools`** — `.csproj` `<Protobuf>` codegen of messages + client from `.proto`; **`Google.Protobuf`**
- **`Grpc.StatusProto`** (+ `Google.Api.CommonProtos`) for `RpcException.GetRpcStatus()` rich-error details
- **NUnit** (`NUnit` + `NUnit3TestAdapter` + `Microsoft.NET.Test.Sdk`); **Allure.NUnit** for reporting
- **Testcontainers** to stand the service under test up (`qa-test-environments-dotnet`); target via env, never hardcoded
- Layout: `Protos/` (the `.proto`), `Actions/` (client wrappers), `Tests/`

```xml
<!-- in the test project .csproj -->
<ItemGroup>
  <PackageReference Include="Grpc.Net.Client" Version="2.66.0" />
  <PackageReference Include="Grpc.Tools" Version="2.66.0" PrivateAssets="All" />
  <PackageReference Include="Google.Protobuf" Version="3.27.3" />
  <PackageReference Include="Grpc.StatusProto" Version="2.66.0" />
</ItemGroup>
<ItemGroup>
  <!-- GrpcServices="Client" => generate only the client + messages, not the server base class -->
  <Protobuf Include="Protos\user.proto" GrpcServices="Client" />
</ItemGroup>
```

> **Why wrap the generated client instead of calling it directly?** The generated async client **throws
> `RpcException` the moment the server returns a non-OK status**. If a test `await`s the client directly, the
> *failure path* (idea #1) becomes `Assert.ThrowsAsync` plumbing and the *success* and *failure* assertions look
> nothing alike. A black-box test needs to assert on **either** outcome uniformly. So the canonical wrapper awaits
> the RPC, catches `RpcException`, and returns a `GrpcCallResult<T>` holding **the message OR the status +
> trailers** — never letting the throw escape into the assertion path. This is the exact gRPC analogue of the
> GraphQL skill's thin client that *never throws on `errors` and returns the raw envelope*.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The contract + two layers**.

## Rich error details — assert `ErrorInfo`, not just the code (idea #2)

`StatusCode` is the gate, but a well-built server attaches a **`google.rpc.Status`** with typed details
(`ErrorInfo`, `BadRequest`, `QuotaFailure`, …) in the **trailing metadata** — the structured "why". Read it from
the `RpcException` with `GetRpcStatus()` (from `Grpc.StatusProto`). This is the gRPC analogue of asserting the
GraphQL `extensions.code` + `path`.

```csharp
using Google.Rpc;                 // ErrorInfo, the google.rpc.Status proto
using Grpc.Core;
using Grpc.StatusProto;           // RpcException.GetRpcStatus(), Status.GetDetail<T>()

[Test]
public async Task CreateUser_WhenDuplicateEmail_ReturnsErrorInfoReason()
{
    var action = new UserGrpcAction(Channel, authenticated: true);

    GrpcCallResult<User> result = await action.CreateUserAsync(
        "george.bluth@example.com", "George", "Bluth");          // already exists

    Assert.That(result.Code, Is.EqualTo(StatusCode.AlreadyExists));

    // The structured detail rides in the trailers as a google.rpc.Status with an ErrorInfo.
    Google.Rpc.Status? rich = result.Exception!.GetRpcStatus();
    ErrorInfo info = rich!.GetDetail<ErrorInfo>()!;
    Assert.That(info.Reason, Is.EqualTo("EMAIL_TAKEN"));
    Assert.That(info.Domain, Is.EqualTo("user.example.com"));
}
```

> Asserting only `AlreadyExists` proves *a* conflict; asserting the `ErrorInfo.Reason` proves the **right**
> conflict — the same step up from "an error happened" to "the contracted error happened" that
> `errors[0].extensions.code` makes in the GraphQL sibling.

## Unary write — assert the payload, then round-trip the read (idea #4)

A mutating RPC returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
message, then read it back with the read RPC. Clean up created data in `[TearDown]` (guarded so a cleanup failure
can't mask a test failure).

```csharp
[Test]
public async Task CreateUser_WhenValid_PersistsAndIsReadable()
{
    var action = new UserGrpcAction(Channel, authenticated: true);

    GrpcCallResult<User> created = await action.CreateUserAsync("neo@example.com", "Thomas", "Anderson");
    Assert.That(created.IsOk, Is.True);
    Assert.That(created.Value!.Email, Is.EqualTo("neo@example.com"));

    // round-trip: prove it persisted, don't trust the RPC's own echo
    GrpcCallResult<User> fetched = await action.GetUserAsync(created.Value.Id);
    Assert.That(fetched.Value!.Email, Is.EqualTo("neo@example.com"));
}
```

## Server-streaming — drain the stream, then assert (idea #4, bounded-await not sleep)

A server-streaming RPC pushes a *sequence* of messages and then completes. The call exposes
`ResponseStream.ReadAllAsync()` (an `IAsyncEnumerable<T>`); **`await foreach` over it completes when the server
finishes** (or the deadline trips) — a *bounded async-await*, **never a `Task.Delay`**. Drain into a buffer, then
assert size + order + values. Same drain-then-assert discipline as `qa-websocket-sse-testing-dotnet`.

```csharp
using Grpc.Core;

[Test]
public async Task ListUsers_StreamsAllUsersInOrder()
{
    var action = new UserGrpcAction(Channel, authenticated: true);

    using AsyncServerStreamingCall<User> call = action.ListUsers(pageSize: 50);

    var received = new List<User>();
    await foreach (User u in call.ResponseStream.ReadAllAsync())   // drains until server completes — bounded, no sleep
        received.Add(u);

    Assert.That(received, Has.Count.EqualTo(12));
    Assert.That(received.Select(u => u.Id),
        Is.EqualTo(new[] { "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12" }));
}
```

> The bound is the server's stream completion plus the call **deadline** — not a timer you guessed. If a
> server-streaming RPC can run unbounded, pass `deadline:` so a hung stream fails as `DeadlineExceeded` instead of
> hanging the suite.

## Client- and bidi-streaming — write the request stream, await the response

For **client-streaming**, write N requests to `RequestStream`, `CompleteAsync()`, then `await ResponseAsync`. For
**bidi**, write and drain `ResponseStream.ReadAllAsync()` concurrently. No sleeps — the awaits are the bound.

```csharp
[Test]
public async Task ImportUsers_AggregatesAllSentRequests()
{
    var action = new UserGrpcAction(Channel, authenticated: true);

    using AsyncClientStreamingCall<CreateUserRequest, ImportSummary> call = action.Client.ImportUsers();

    await call.RequestStream.WriteAsync(new CreateUserRequest { Email = "a@example.com" });
    await call.RequestStream.WriteAsync(new CreateUserRequest { Email = "b@example.com" });
    await call.RequestStream.CompleteAsync();

    ImportSummary summary = await call.ResponseAsync;             // bounded by the server completing the call
    Assert.That(summary.Imported, Is.EqualTo(2));
}
```

> Bidi-streaming follows the same shape — kick off a `Task` draining `ResponseStream.ReadAllAsync()` while writing
> to `RequestStream`, then `await` both. For richer bidi-stream-lifecycle assertions (ordering, mid-stream close),
> cross-link `qa-websocket-sse-testing-dotnet` — gRPC streaming and WebSocket/SSE share the
> drain-then-assert-on-a-bounded-condition discipline.

## Deadlines — the sanctioned bounded-wait, asserted as `DeadlineExceeded`

A **deadline** is gRPC's first-class timeout, and the *only* sanctioned way to bound a slow call — there is no
`Task.Delay` anywhere in these tests. Set it per call via `CallOptions`/`deadline:`; a call that overruns fails
deterministically as `DeadlineExceeded`.

```csharp
[Test]
public async Task SlowCall_ExceedingDeadline_ReturnsDeadlineExceeded()
{
    var action = new UserGrpcAction(Channel, authenticated: true);

    GrpcCallResult<User> result = await action.GetUserWithDeadlineAsync("slow-1", millis: 100);

    Assert.That(result.Code, Is.EqualTo(StatusCode.DeadlineExceeded));
}
```
```csharp
// in UserGrpcAction:
public Task<GrpcCallResult<User>> GetUserWithDeadlineAsync(string id, int millis) =>
    CallAsync(async () => await _client.GetUserAsync(
        new GetUserRequest { Id = id },
        deadline: DateTime.UtcNow.AddMilliseconds(millis), headers: _headers));
```

## Standing the service up — Testcontainers + the channel lifecycle

The channel points at the service under test, stood up via `qa-test-environments-dotnet`. The `BaseGrpcTest`
opens one `GrpcChannel` for the fixture and disposes it after — no per-test channel churn.

```csharp
using Grpc.Net.Client;
using NUnit.Framework;

namespace Tests;

public abstract class BaseGrpcTest
{
    protected GrpcChannel Channel = null!;

    [OneTimeSetUp]
    public void OpenChannel() =>
        // address from Testcontainers / env — never hardcoded. http:// only for a local test broker.
        Channel = GrpcChannel.ForAddress(Env.GrpcTarget);

    [OneTimeTearDown]
    public async Task CloseChannel()
    {
        if (Channel is not null) await Channel.ShutdownAsync();
        Channel?.Dispose();
    }
}
```

> **Reflection / `grpcurl` are for exploration, not the test path.** gRPC server reflection + `grpcurl` are great
> for poking a service by hand, but a regression test goes through the **typed client** — it's the contract-bound,
> refactor-safe path. Note reflection in a comment; assert through the client.

## Anti-patterns

- **Looking for an HTTP status code.** gRPC has none in the application sense — the outcome is the gRPC
  `StatusCode`. *Fix:* assert `result.Code` / `result.IsOk`, never a 200/404.
- **Calling the generated client directly and letting `RpcException` fly.** The failure path becomes
  `Assert.ThrowsAsync` plumbing and looks nothing like the success path. *Fix:* the wrapper catches it and returns
  a `GrpcCallResult<T>` the test asserts on uniformly (the GraphQL "never throw — return the envelope" analogue).
- **Asserting only the `StatusCode` on a rich error.** "An `AlreadyExists` happened" is not the contract. *Fix:*
  read the `google.rpc.Status` / `ErrorInfo` via `GetRpcStatus()` and assert `Reason` / `Domain` / field violations.
- **`Task.Delay` / `Thread.Sleep` to wait for a stream.** Banned by CLAUDE.md and unnecessary. *Fix:*
  `await foreach` over `ResponseStream.ReadAllAsync()` (completes on server finish) or `await ResponseAsync`; bound
  unbounded streams with `deadline:`.
- **`.Result` / `.Wait()` / `.GetAwaiter().GetResult()` anywhere.** Banned by CLAUDE.md. *Fix:* tests are
  `async Task`, every RPC is `await`ed.
- **Hand-parsing the response bytes / using a dynamic message.** *Fix:* assert on the typed generated message; the
  `.proto` is the contract. Model/generate messages via `qa-api-dto-writer-dotnet`.
- **Trusting a write RPC's echoed payload as proof of persistence.** *Fix:* round-trip a read RPC and assert state.
- **Re-creating the channel per test (or never disposing it).** *Fix:* one `GrpcChannel` per fixture in
  `[OneTimeSetUp]`, `ShutdownAsync()` + `Dispose()` in `[OneTimeTearDown]`.
- **Hardcoding the target / committing the token.** *Fix:* env, read lazily, never logged; bearer via
  `qa-auth0-test-tokens-dotnet`. Reaching for this skill for **load** → `qa-performance-nbomber-dotnet`; for a
  **Protobuf contract** → `qa-contract-testing-pact-dotnet`.

## Examples

**End-to-end: a not-found RPC proves the status discipline.** A REST author writes
`Assert.That(response.StatusCode, Is.EqualTo(HttpStatusCode.NotFound))`; a GraphQL author writes
`errors[0].extensions.code == "NOT_FOUND"`. The gRPC-correct version asserts
`result.Code == StatusCode.NotFound` — same outcome, third location: the REST status line, the GraphQL `errors`
envelope, the gRPC `Status`. One family, three result-location conventions.

**Composing with the protocol-trio siblings.** REST `generator` is status-driven over HTTP+JSON; GraphQL ``api-test-author/graphql`` is
one HTTP 200 carrying `{ data, errors }`; gRPC is proto/HTTP2 with the result in the `Status`. All three share the
**Action + Test** spine and the "wrap the call so the test asserts success *or* failure uniformly" move (the gRPC
`GrpcCallResult` is the GraphQL raw-envelope analogue). Only the transport, the codegen, and where-the-result-lives
differ.

## Rules (hard constraints)

- **The gate is the gRPC `StatusCode`, not an HTTP status.** Assert `result.IsOk` (success) or the specific
  failure `Code` (`NotFound` / `InvalidArgument` / `Unauthenticated` / `DeadlineExceeded` / …) — never a 200/404.
- **The action never lets `RpcException` escape.** `CallAsync(...)` returns a `GrpcCallResult<T>` holding the
  message **or** the status + trailers; the test decides whether a non-OK status was expected. No
  `Assert.ThrowsAsync` in the assertion path, no deserialization or assertion inside the action.
- **Rich errors assert the `google.rpc.Status` details** (`ErrorInfo.Reason`/`Domain`, `BadRequest` field
  violations) via `GetRpcStatus()` — not a bare `StatusCode`.
- **Assert on the typed generated message** — never hand-parse bytes; the `.proto` is the contract. Messages via
  `qa-api-dto-writer-dotnet`.
- **A write RPC test round-trips a read** to prove persistence; data created in a test is cleaned up in
  `[TearDown]` (guarded so it can't mask a failure).
- **Streaming = drain-then-assert on a bounded condition** — `await foreach` over `ResponseStream.ReadAllAsync()`
  (server-streaming) or `await ResponseAsync` (client-streaming); bound unbounded streams with `deadline:`. **No
  `Task.Delay`/`Thread.Sleep`, async all the way (no `.Result`).** Deep stream-lifecycle assertions →
  `qa-websocket-sse-testing-dotnet`.
- **One `GrpcChannel` per fixture** (`[OneTimeSetUp]` open, `[OneTimeTearDown]` shutdown + dispose); service stood
  up via `qa-test-environments-dotnet`. **Target + token via env**, lazy, never logged. NUnit + Grpc.Net.Client.

## Cross-references

- `qa-api-test-author-grpc-java` — **the canonical file**: same four ideas, grpc-java + TestNG +
  `GrpcCallResult`/`StatusRuntimeException`. Read it for the family rationale.
- `qa-api-test-author-grpc-typescript` — the TypeScript sibling (`@grpc/grpc-js` + `@grpc/proto-loader`); same four
  ideas, different codegen/client libs.
- `qa-api-test-author-generator-dotnet` · `qa-api-test-author-graphql-dotnet` — the **protocol-trio siblings**:
  REST (HTTP+JSON status-driven) and GraphQL (HTTP 200 `{ data, errors }` envelope). Three protocols, three
  result-location conventions, one `api-test-author` family + shared Action + Test spine.
- `qa-websocket-sse-testing-dotnet` — gRPC **streaming** reuses its
  drain-then-assert-on-a-bounded-condition discipline; cross-link for deep stream-lifecycle assertions, don't
  duplicate.
- `qa-api-dto-writer-dotnet` — generate/model the proto messages (the DTO analogue) in isolation; this skill
  consumes them.
- `qa-contract-testing-pact-dotnet` — the **Protobuf contract** boundary vs the functional test this skill writes.
  `qa-performance-nbomber-dotnet` — gRPC **load**.
- `qa-auth0-test-tokens-dotnet` — obtain the per-call **bearer** carried in leading metadata.
- `qa-test-environments-dotnet` — stand the gRPC service up via Testcontainers and feed the channel target.
- `qa-allure-reporting-dotnet` — each RPC renders as a named result.
