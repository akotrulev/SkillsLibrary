---
name: qa-contract-testing-pact-shared
description: Cross-stack reference for Pact consumer-driven contract testing — mental model, Pact Broker setup, matchers, can-i-deploy, record-deployment, versioning, and global rules that apply to .NET, Java, and TypeScript consumer/provider implementations. Load alongside one of `qa/{dotnet,java,typescript}/skills/contract-testing-pact` when configuring Pact. Do NOT load standalone to write Pact code — pair it with the stack-specific sibling.
---

# QA — Contract Testing with Pact (Shared)

Cross-stack concepts shared by `qa/{dotnet,java,typescript}/skills/contract-testing-pact`. The stack siblings carry the consumer + provider code recipes; this skill carries the model, Broker wiring, matchers, and the CI gate pattern.

## Mental model

1. **Consumer** writes a Pact test: "When I call `GET /orders/123`, I expect a 200 with shape X."
2. The Pact mock provider runs in-process; the consumer's HTTP client thinks it's talking to the real provider.
3. The test passes → a **pact file** (JSON describing interactions) is generated under `pacts/`.
4. The consumer **publishes** the pact to the **Pact Broker**, tagged with its version + branch.
5. The provider's CI **fetches** the pact, replays each interaction against the real provider, and publishes the result back to the Broker.
6. Before any deploy, the deploying side asks the Broker: **`can-i-deploy --pacticipant X --version Y --to-environment prod`**.

The Broker is the source of truth. Pact files in Git are dev-time only.

## Inputs needed (regardless of stack)

1. **Consumer + provider names** as they'll appear in the Broker (slug-stable)
2. **Broker** — Pactflow (managed) or self-hosted `pact-foundation/pact_broker`
3. **CI** — runs consumer test + publish on consumer side; runs verify + publish-verification on provider side
4. **Environments** — `dev` / `staging` / `prod`; pacts tagged per env

## Publishing the pact (any stack)

The consumer's CI publishes the pact after a successful test using the `pact-cli` container — independent of the consumer language:

```bash
docker run --rm \
  -v "$PWD/pacts:/pacts" \
  -e PACT_BROKER_BASE_URL=https://yourco.pactflow.io \
  -e PACT_BROKER_TOKEN=$PACT_BROKER_TOKEN \
  pactfoundation/pact-cli:latest \
  broker publish /pacts \
  --consumer-app-version "$GIT_SHA" \
  --branch "$BRANCH_NAME"
```

The pact is tagged with the consumer's git SHA + branch. The Broker links the pact to that version.

## Provider verification (concept)

The provider's CI fetches all pacts tagged for the deploy target and replays each interaction against the **real running provider**. Stack-specific verifier APIs live in the sibling skills; the inputs are the same:

- `pactBrokerUrl` + token from CI secrets
- `consumerVersionSelectors`: at minimum `{ mainBranch: true }` and `{ deployedOrReleased: true }`
- `publishVerificationResult: true`
- `providerVersion: $GIT_SHA`, `providerVersionBranch: $BRANCH_NAME`
- `stateHandlers` — code that sets up each `given(...)` state before the matching interaction runs

### Provider state handlers

The `given(...)` clauses on the consumer side are **state names**. The provider implements handlers that set up that state before the interaction runs (insert a row, mock a downstream, plant a token in cache). Handlers are code, owned by the provider, and part of the test surface.

## `can-i-deploy` (gate every deploy)

The Broker computes whether a version is compatible with what's already deployed in the target environment. Add this gate to **every** deploy pipeline — consumer side and provider side:

```bash
docker run --rm \
  -e PACT_BROKER_BASE_URL=https://yourco.pactflow.io \
  -e PACT_BROKER_TOKEN=$PACT_BROKER_TOKEN \
  pactfoundation/pact-cli:latest \
  broker can-i-deploy \
  --pacticipant "cart-service" \
  --version "$GIT_SHA" \
  --to-environment "prod"
```

Exit code 0 = safe to deploy; non-zero = blocked. Wire it before `kubectl apply` / `helm upgrade` / `az containerapp update`.

After a successful deploy, **record** the deployment:

```bash
pact-cli broker record-deployment \
  --pacticipant "cart-service" \
  --version "$GIT_SHA" \
  --environment "prod"
```

The Broker now knows what's running where. `can-i-deploy` decisions become accurate from that point.

## Matchers — type, not value

Use Pact matchers on every variable value:

| Want to assert | Matcher concept (stack-specific syntax in sibling skills) |
|---|---|
| Field is a string | `stringType` / `Match.Type` / `MatchersV3.string` |
| Field is an integer | `integerType` / `Match.Integer` |
| Field matches a regex | `stringMatcher` / `Match.Regex` |
| Field is a date / datetime | `datetime` matcher |
| Array has at least N items | `eachLike` (with `min`) |
| Field equals a specific value | `equals` — use sparingly (binds the contract too tightly) |

**Rule:** assert as little as the consumer truly needs. A consumer that uses three fields should assert three fields' types. Over-asserting creates false contract failures on harmless additions (the producer adds a new field → consumer's pact fails verification → nothing was actually broken).

## Broker setup

- **Pactflow** (managed) is the path of least resistance — Pact's own SaaS, free tier covers small teams.
- **Self-hosted** via `pactfoundation/pact_broker` container — needs a Postgres backing store, ingress, and TLS. Worth it only at scale or for compliance.

In both cases:

- Webhook on the Broker to trigger provider verification when a consumer publishes a new contract
- Environment definitions (`dev`, `staging`, `prod`) so `can-i-deploy --to-environment` works
- Authentication via short-lived broker tokens stored as CI secrets — never raw Basic auth in repo

## Versioning

Tag every pact and every verification with the **consumer's commit SHA + branch**. The Broker uses the SHA as the version. After deploy, record the deployment with the same SHA. This is what makes `can-i-deploy` accurate — without it, the Broker doesn't know what's actually running.

## Global rules (all stacks)

- Pact files are generated by tests; never hand-written.
- Contracts assert **types**, not values; let the provider return any conforming value.
- Provider state handlers are code, owned by the provider, kept under version control with the provider.
- Pact Broker is the source of truth. Git is dev-only.
- Every deploy pipeline runs `can-i-deploy` before deploying.
- Every successful deploy records the deployment to the Broker.
- Per-environment tags on pacts (`prod`, `staging`); verify accordingly.
- One pact file per consumer-provider pair; multiple interactions inside it.
- Bi-directional with OpenAPI is fine **in addition**, not instead — Pact handles the consumer's actual usage; OpenAPI describes the producer's intent.

## What NOT to do (all stacks)

- No pact files committed and used as the source of truth — Broker is the source.
- No exact-value matchers everywhere — over-asserting breaks on harmless changes.
- No deploy without `can-i-deploy`.
- No skipping `record-deployment` after deploy — Broker becomes blind.
- No contract-per-environment file — one pact per consumer-provider pair, tagged.
- No Pact when the contract is internal to one team and one repo — direct integration test is fine.
- No verifying a provider against pacts from `mainBranch` only — include `deployedOrReleased` so currently-running consumers are honored.
- No state handlers that run real production-like side effects (emails, payments) — mock or stub.
- No huge pact files (100+ interactions) — split the consumer's pact by use case or feature.

## When to use Pact at all

- Two or more services talk over HTTP and you want safety before deploys.
- Replacing brittle multi-service E2E tests with cheaper contract verification.
- Catching breaking changes at the producer side before they ship.
- Sequencing deploys safely with `can-i-deploy`.

## When NOT to use Pact

- Single-service API tests against a deployed service → `qa/<stack>/skills/api-test-author/generator/<stack>`.
- UI tests → `qa/<stack>/skills/ui-test-author/<stack>`.
- OpenAPI-only validation with no consumer-driven aspect → use schema validation libraries directly.
- One-shot integration tests that don't need versioning or multi-consumer fan-in — contract testing is overkill for a 1:1 internal call.

## Handoffs

- Consumer / provider code on .NET → `qa/dotnet/skills/contract-testing-pact`
- Consumer / provider code on Java → `qa/java/skills/contract-testing-pact`
- Consumer / provider code on TypeScript → `qa/typescript/skills/contract-testing-pact`
- Live-service API tests → `qa/<stack>/skills/api-test-author/generator/<stack>`
- DTO authoring → `qa/<stack>/skills/api-dto-writer/<stack>`
- CI pipeline syntax → `qa/<stack>/skills/ci-pipelines/{github-actions,azure-pipelines,gitlab-ci}` or `devops/<ci>`
- Test strategy decisions (when contract vs E2E) → `qa/manual/test-strategy`
