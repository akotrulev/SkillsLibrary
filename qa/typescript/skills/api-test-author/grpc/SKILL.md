---
name: qa-api-test-author-grpc-typescript
description: Scaffold black-box **gRPC** API tests in Node 24 (22 supported) / TypeScript with Vitest + `@grpc/grpc-js` + `@grpc/proto-loader` against a deployed, proto-defined HTTP/2 service. Triggers: "write a gRPC test for RPC X", "assert the ServiceError code", "test a server-streaming RPC". For end-to-end suite work prefer the phased agent `qa-api-typescript` (or the matching slash command), which loads this skill inside its workflow; use this skill directly for a single targeted artifact.
---

# QA — gRPC API Test Writer (TypeScript / Vitest + @grpc/grpc-js)

> **Ported from the canonical `qa-api-test-author-grpc-java`.** The four ideas and the section order are
> identical; only the runner (Vitest instead of TestNG), the client (`@grpc/grpc-js` + `@grpc/proto-loader`
> instead of grpc-java), the typing (`proto-loader-gen-types` / `ts-proto` instead of `protobuf-gradle-plugin`),
> and the promise-based style change. See the Java file for the family rationale.

Scaffolds black-box API tests in TypeScript against a deployed **gRPC** service. It completes the
`api-test-author` **protocol trio** — REST (`qa-api-test-author-generator-typescript`, HTTP+JSON, status-driven) →
GraphQL (`qa-api-test-author-graphql-typescript`, one HTTP 200 carrying a `{ data, errors }` envelope) → **gRPC
(this skill, proto-defined HTTP/2 binary Protobuf, result carried in the gRPC `status`)**. Three protocols, three
places the result lives, one family. It reuses the **(contract) + Client + Spec** layering of the REST/GraphQL
siblings, but the contract is the **`.proto`** (load + type the messages + client) and the assertion targets the
**typed message + the gRPC `status`**, never an HTTP status code.

> **The discipline this skill encodes** — four ideas that separate a correct gRPC test from a REST/GraphQL reflex:
>
> 1. **There is no HTTP status — the result lives in the gRPC `status` (code + details).** Success is
>    `status.OK`; a failure is the right `status` code (`NOT_FOUND` / `INVALID_ARGUMENT` / `UNAUTHENTICATED` /
>    `PERMISSION_DENIED` / `DEADLINE_EXCEEDED` / …). This is the gRPC analogue of the GraphQL `errors` envelope and
>    the REST HTTP status: *where the outcome lives*. The `@grpc/grpc-js` callback client surfaces a non-OK status
>    as a **`ServiceError`** in the callback's first argument (not as a resolved value) — so the call is
>    **promisified into a `GrpcCallResult<T>` that holds the message OR the status (+ metadata)**, and the test
>    decides whether a non-OK status was expected (the gRPC analogue of the GraphQL "client never throws — return
>    the raw envelope").
> 2. **For rich errors, assert the `google.rpc.Status` details + trailing metadata, not just the code.** The
>    `status` code is the gate; servers attach a structured **`google.rpc.Status`** with `ErrorInfo` / `BadRequest`
>    details in the **`grpc-status-details-bin`** trailing-metadata key carrying the "why". Decode and assert those
>    — they are the gRPC analogue of the GraphQL `extensions.code` + `path`.
> 3. **Assert on the typed generated message — never hand-parse bytes.** The `.proto` is the contract;
>    `proto-loader-gen-types` (or `ts-proto`) types the messages + client; assert on the **typed message fields**
>    (`res.value.email`). A gRPC test never touches the wire bytes — that's the GraphQL "query-shaped typed `data`"
>    analogue, and the messages are the DTO (`qa-api-dto-writer-typescript`).
> 4. **Pick the RPC type deliberately — unary / server- / client- / bidi-streaming each test differently.** A
>    **unary** call asserts the message + status. A **server-streaming** call **`for await`s the
>    `ClientReadableStream` into a buffer, then asserts the sequence** — a *bounded async-iterate* (the stream's
>    `end` + a deadline), **never a `setTimeout`** → it reuses `qa-websocket-sse-testing-typescript`'s
>    drain-then-assert discipline. A **client-streaming** call `write`s a stream of requests → one response.
>    **Bidi-streaming** interleaves both.

## Decision matrix — RPC type / scenario → test shape

| RPC / scenario | What you're proving | Test shape |
|----------------|---------------------|------------|
| **Unary** (req→resp) | The right message comes back | `await client.getUser(id)` via the promisified wrapper → `res.ok` → assert message fields |
| **Unary — not found / invalid** | A failure surfaces with the right code | wrapper resolves a `ServiceError` → `res.code === status.NOT_FOUND` / `INVALID_ARGUMENT` |
| **Unary — rich error** | The structured "why" is correct | assert `status` **and** the `google.rpc.Status` / `ErrorInfo` decoded from `grpc-status-details-bin` |
| **Unary — write** | The change happened and persisted | call the mutating RPC → assert the payload → **round-trip a read RPC** → assert the new state |
| **Server-streaming** (req→stream) | The right sequence of messages arrives | `for await (const m of call)` into an array (bounded by `end` + deadline) → assert size + order + values |
| **Client-streaming** (stream→resp) | The aggregate response is right | `call.write(req)` N times → `call.end()` → await the single response in the callback |
| **Bidi-streaming** (stream↔stream) | Interleaved exchange works | write + `for await` the read side concurrently; assert the received sequence → also `qa-websocket-sse-testing-typescript` |
| **Deadline** | A slow call fails deterministically | call with `{ deadline: Date.now() + d }` → `res.code === status.DEADLINE_EXCEEDED` |
| **Auth** | A call without credentials is rejected | client **without** the bearer metadata → `UNAUTHENTICATED`; with it → `OK` |

## Stack

- Node 20 + TypeScript (strict mode)
- **Vitest** as test runner (`allure-vitest` where the project uses Allure)
- **`@grpc/grpc-js`** (the pure-JS client) + **`@grpc/proto-loader`** (load `.proto` at runtime)
- **`proto-loader-gen-types`** generates the `*.ts` typings for the loaded package (the typed-client path); or
  **`ts-proto`** for fully static generated clients — pick one and keep it
- **`google-proto-files`** / generated `google.rpc` types to decode the `grpc-status-details-bin` rich error
- Layout: `tests/proto/` (the `.proto` + generated types), `tests/clients/`, `tests/specs/`, `tests/setup.ts`

```jsonc
// package.json (excerpt) — typegen runs before the tests
{
  "scripts": {
    "proto:types": "proto-loader-gen-types --longs=String --enums=String --defaults --oneofs --grpcLib=@grpc/grpc-js -O tests/proto/gen tests/proto/user.proto",
    "test": "npm run proto:types && vitest run"
  }
}
```

> **Why promisify `@grpc/grpc-js` rather than use a throw-on-error typed client?** The `@grpc/grpc-js` unary call
> is **callback-based** — `client.getUser(req, md, (err, res) => …)` — and a non-OK status arrives as a
> **`ServiceError`** in `err`, not a thrown value. Typed wrappers (`nice-grpc`, some `ts-proto` setups) **reject /
> throw on a `ServiceError`**, which makes the *failure path* (idea #1) awkward to assert. A black-box test needs
> to assert on **either** outcome uniformly. So the canonical client promisifies the call into a `GrpcCallResult<T>`
> holding **the message OR the status + metadata** — it never rejects on a gRPC error. This is the exact gRPC
> analogue of the GraphQL skill's thin `fetch` client that *never throws on `errors` and returns the raw envelope*.

## Deep-dive reference

These sections live in `references/details.md` — **read it when the task touches them**: **The contract + two layers**.

## Rich error details — assert `ErrorInfo`, not just the code (idea #2)

The `status` code is the gate, but a well-built server attaches a **`google.rpc.Status`** with typed details
(`ErrorInfo`, `BadRequest`, …) in the **`grpc-status-details-bin`** trailing-metadata key — the structured "why".
Decode that binary value with the `google.rpc.Status` proto. This is the gRPC analogue of asserting the GraphQL
`extensions.code` + `path`.

```typescript
import { Status } from '../proto/gen/google/rpc/Status';     // generated google.rpc.Status decoder
import { ErrorInfo } from '../proto/gen/google/rpc/ErrorInfo';

it('CreateUser surfaces an ErrorInfo reason on a duplicate email', async () => {
  const res = await authed.createUser('george.bluth@example.com', 'George', 'Bluth');  // already exists

  expect(res.code).toBe(status.ALREADY_EXISTS);

  // The structured detail rides in the trailers as a google.rpc.Status with an ErrorInfo.
  const bin = res.metadata?.get('grpc-status-details-bin')[0] as Buffer;
  const rich = Status.decode(bin);
  const info = ErrorInfo.decode(rich.details[0].value);       // unpack the Any → ErrorInfo
  expect(info.reason).toBe('EMAIL_TAKEN');
  expect(info.domain).toBe('user.example.com');
});
```

> Asserting only `ALREADY_EXISTS` proves *a* conflict; asserting the `ErrorInfo.reason` proves the **right**
> conflict — the same step up from "an error happened" to "the contracted error happened" that
> `errors[0].extensions.code` makes in the GraphQL sibling.

## Unary write — assert the payload, then round-trip the read (idea #4)

A mutating RPC returns a payload, but the payload alone doesn't prove the write **persisted**. Assert the returned
message, then read it back with the read RPC. Clean up created data in `afterEach`/`afterAll` (wrap cleanup in
`try/catch` so a cleanup error never masks a test failure).

```typescript
it('CreateUser persists and the change is readable', async () => {
  const created = await authed.createUser('neo@example.com', 'Thomas', 'Anderson');
  expect(created.ok).toBe(true);
  expect(created.value?.email).toBe('neo@example.com');

  // round-trip: prove it persisted, don't trust the RPC's own echo
  const fetched = await authed.getUser(created.value!.id);
  expect(fetched.value?.email).toBe('neo@example.com');
});
```

## Server-streaming — drain the stream, then assert (idea #4, bounded-iterate not sleep)

A server-streaming RPC pushes a *sequence* of messages and then ends. `@grpc/grpc-js` returns a
`ClientReadableStream`, which is a Node `Readable` and therefore **async-iterable** — `for await (const m of call)`
completes on the stream's `end` (or the deadline trips), **never a `setTimeout`**. Drain into a buffer, then
assert size + order + values. Same drain-then-assert discipline as `qa-websocket-sse-testing-typescript`.

```typescript
import type { User__Output } from '../proto/gen/user/v1/User';

it('ListUsers streams all users in order', async () => {
  const call = authed.listUsers(50);

  const received: User__Output[] = [];
  for await (const u of call) received.push(u as User__Output);   // drains until 'end' — bounded, no sleep

  expect(received).toHaveLength(12);
  expect(received.map(u => u.id)).toEqual(
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);
});
```

> The bound is the stream's `end` plus the call **deadline** — not a timer you guessed. If a server-streaming RPC
> can run unbounded, pass `{ deadline: Date.now() + ms }` so a hung stream fails as `DEADLINE_EXCEEDED` instead of
> hanging the suite. (An error on the stream rejects the `for await`; wrap it if you want to assert the failure
> status of a streaming call.)

## Client- and bidi-streaming — write the request stream, await the response

For **client-streaming**, `write` N requests, `end()`, and resolve the single response from the callback. For
**bidi**, write while `for await`-ing the read side. No sleeps — the callback / `end` event is the bound.

```typescript
import type { ImportSummary__Output } from '../proto/gen/user/v1/ImportSummary';

it('ImportUsers aggregates all sent requests', async () => {
  const summary = await new Promise<ImportSummary__Output>((resolve, reject) => {
    const call = authed.raw().importUsers((err, res) => (err ? reject(err) : resolve(res!)));
    call.write({ email: 'a@example.com' });
    call.write({ email: 'b@example.com' });
    call.end();                                          // bounded by the server completing the call
  });

  expect(summary.imported).toBe(2);
});
```

> Bidi-streaming follows the same shape — `for await` the read side in one promise while writing to the call, then
> await both. For richer bidi-stream-lifecycle assertions (ordering, mid-stream close), cross-link
> `qa-websocket-sse-testing-typescript` — gRPC streaming and WebSocket/SSE share the
> drain-then-assert-on-a-bounded-condition discipline.

## Deadlines — the sanctioned bounded-wait, asserted as `DEADLINE_EXCEEDED`

A **deadline** is gRPC's first-class timeout, and the *only* sanctioned way to bound a slow call — there is no
`setTimeout` anywhere in these tests. Pass it in the call options; a call that overruns fails deterministically as
`DEADLINE_EXCEEDED`.

```typescript
it('a slow call exceeding its deadline returns DEADLINE_EXCEEDED', async () => {
  const res = await new Promise<number>((resolve) => {
    authed.raw().getUser({ id: 'slow-1' }, new grpc.Metadata(),
      { deadline: Date.now() + 100 },                    // 100ms deadline
      (err) => resolve(err?.code ?? status.OK));
  });

  expect(res).toBe(status.DEADLINE_EXCEEDED);
});
```

> In practice the deadline is set inside a `UserGrpcClient` method (mirroring the unary wrapper) so specs stay
> declarative; the inline form above shows the mechanism.

## Standing the service up — Testcontainers + the client lifecycle

The client target points at the service under test, stood up via Testcontainers. Create the
client once per spec file and `close()` it in `afterAll` — no per-test client churn.

```typescript
// tests/setup.ts — Vitest global setup asserts the target is present before any spec runs
import { beforeAll } from 'vitest';

beforeAll(() => {
  if (!process.env.GRPC_TARGET) throw new Error('GRPC_TARGET not set (Testcontainers should export it)');
});
```

> **Reflection / `grpcurl` are for exploration, not the test path.** gRPC server reflection + `grpcurl` are great
> for poking a service by hand, but a regression test goes through the **typed client** — it's the contract-bound,
> refactor-safe path. Note reflection in a comment; assert through the client.

## Anti-patterns

- **Looking for an HTTP status code.** gRPC has none in the application sense — the outcome is the gRPC `status`
  code. *Fix:* assert `res.code` / `res.ok`, never a 200/404.
- **A typed client that rejects/throws on a `ServiceError` (`nice-grpc`, throw-on-error `ts-proto`).** The failure
  path becomes `expect(...).rejects` plumbing and looks nothing like the success path. *Fix:* `callUnary`
  promisifies the callback and resolves a `GrpcCallResult` for both outcomes (the GraphQL "never throw — return the
  envelope" analogue).
- **Asserting only the `status` code on a rich error.** "An `ALREADY_EXISTS` happened" is not the contract. *Fix:*
  decode the `google.rpc.Status` / `ErrorInfo` from `grpc-status-details-bin` and assert `reason` / `domain` /
  field violations.
- **`setTimeout` / `await page.waitForTimeout` to wait for a stream.** Banned by CLAUDE.md and unnecessary. *Fix:*
  `for await` the `ClientReadableStream` (ends on the stream's `end`) or await the response callback; bound
  unbounded streams with `{ deadline }`.
- **Hand-decoding the response bytes / using an untyped `any` message.** *Fix:* assert on the typed generated
  message; the `.proto` is the contract. Generate types via `proto-loader-gen-types` / `qa-api-dto-writer-typescript`.
- **Trusting a write RPC's echoed payload as proof of persistence.** *Fix:* round-trip a read RPC and assert state.
- **Creating a client per test (or never calling `close()`).** Leaks HTTP/2 connections and can hang Vitest's
  exit. *Fix:* one client per spec file, `close()` in `afterAll`.
- **Hardcoding the target / committing the token.** *Fix:* `process.env.GRPC_TARGET` / `GRPC_TOKEN`, read lazily,
  never logged; bearer via `qa-auth0-test-tokens-typescript`. Reaching for this skill for **load** →
  `qa-performance-k6-typescript`; for a **Protobuf contract** → `qa-contract-testing-pact-typescript`.

## Examples

**End-to-end: a not-found RPC proves the status discipline.** A REST author writes
`expect(res.status).toBe(404)`; a GraphQL author writes `errors[0].extensions.code === 'NOT_FOUND'`. The
gRPC-correct version asserts `res.code === status.NOT_FOUND` — same outcome, third location: the REST status line,
the GraphQL `errors` envelope, the gRPC `status`. One family, three result-location conventions.

**Composing with the protocol-trio siblings.** REST `generator` is status-driven over HTTP+JSON; GraphQL ``api-test-author/graphql`` is
one HTTP 200 carrying `{ data, errors }`; gRPC is proto/HTTP2 with the result in the `status`. All three share the
**Client + Spec** spine and the "wrap the call so the test asserts success *or* failure uniformly" move (the gRPC
`GrpcCallResult` is the GraphQL raw-envelope analogue). Only the transport, the codegen, and where-the-result-lives
differ.

## Rules (hard constraints)

- **The gate is the gRPC `status` code, not an HTTP status.** Assert `res.ok` (success) or the specific failure
  `res.code` (`NOT_FOUND` / `INVALID_ARGUMENT` / `UNAUTHENTICATED` / `DEADLINE_EXCEEDED` / …) — never a 200/404.
- **The client never rejects on a gRPC error.** `callUnary(...)` resolves a `GrpcCallResult<T>` holding the message
  **or** the status + metadata; the spec decides whether a non-OK status was expected. No `expect().rejects` in the
  assertion path, no decoding or assertion inside the client.
- **Rich errors assert the `google.rpc.Status` details** (`ErrorInfo.reason`/`domain`, `BadRequest` field
  violations) decoded from `grpc-status-details-bin` — not a bare `status` code.
- **Assert on the typed generated message** — never hand-decode bytes; the `.proto` is the contract. Types via
  `proto-loader-gen-types` / `qa-api-dto-writer-typescript`.
- **A write RPC test round-trips a read** to prove persistence; data created in a spec is cleaned up in
  `afterEach`/`afterAll` (cleanup in `try/catch`).
- **Streaming = drain-then-assert on a bounded condition** — `for await` the `ClientReadableStream`
  (server-streaming) or await the response callback after `call.end()` (client-streaming); bound unbounded streams
  with `{ deadline }`. **No `setTimeout`/`waitForTimeout`.** Deep stream-lifecycle assertions →
  `qa-websocket-sse-testing-typescript`.

## Cross-references

- `qa-api-test-author-grpc-java` — **the canonical file**: same four ideas, grpc-java + TestNG +
  `GrpcCallResult`/`StatusRuntimeException`. Read it for the family rationale.
- `qa-api-test-author-grpc-dotnet` — the .NET sibling (`Grpc.Net.Client` + `Grpc.Tools`); same four ideas,
  different codegen/client libs.
- `qa-api-test-author-generator-typescript` · `qa-api-test-author-graphql-typescript` — the **protocol-trio
  siblings**: REST (HTTP+JSON status-driven) and GraphQL (HTTP 200 `{ data, errors }` envelope). Three protocols,
  three result-location conventions, one `api-test-author` family + shared Client + Spec spine.
- `qa-websocket-sse-testing-typescript` — gRPC **streaming** reuses its
  drain-then-assert-on-a-bounded-condition discipline; cross-link for deep stream-lifecycle assertions, don't
  duplicate.
- `qa-api-dto-writer-typescript` — generate/type the proto messages (the DTO analogue) in isolation; this skill
  consumes them.
- `qa-contract-testing-pact-typescript` — the **Protobuf contract** boundary vs the functional test this skill
  writes. `qa-performance-k6-typescript` — gRPC **load**.
- `qa-auth0-test-tokens-typescript` — obtain the per-call **bearer** carried in leading metadata.
- `qa-allure-reporting-typescript` — each RPC renders as a named result.
