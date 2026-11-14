# Generation checks — oracles before code, a hallucination gate before review

Two checks bracket every generated API or UI test. The first decides what each test proves before any code
exists; the second proves, mechanically, that the code only touches things that exist. Both are written to the
response (or the PR description, or the plan task's `As built`), never as comments in the test code.

## 1. Design the oracles first

An oracle is the expected outcome a test checks, taken from the requirement, the story's acceptance criteria,
the OpenAPI contract or the test-case document — **never from running the code or reading its
implementation**: an expected value copied from what the code returns passes whatever the code does.

For every scenario, before writing code, fill one row:

| Scenario | Response / UI-state oracle | Data oracle | Negative oracle | Side-effect oracle |
|---|---|---|---|---|
| Create order with two lines | `201`; body echoes both lines, `status` `Pending` · the confirmation banner shows the order number | `GET /orders/{id}` returns both lines and the total | no second order for the idempotency key; the cart is not left half-cleared | one `OrderPlaced` event; one confirmation email to the buyer |
| Create order, empty cart | `400`, `ProblemDetails` `errors.lines` · the form error under the cart | no order row for the customer | no event, no email | none |

- **Response / UI-state** — the status and the fields (API), or what the user sees: text, enabled state, URL,
  focus (UI).
- **Data** — what was persisted, read back through the API or the database, not through the response just
  received.
- **Negative** — what must not happen: a duplicate, another user's data in the response, a field changed that
  the operation does not own, a charge on a failed submit.
- **Side effect** — events, emails, audit rows, downstream calls; checked through the project's harness
  (`messaging-testing`, `email-testing`) or recorded as out of scope with the reason.

A cell is `n/a` only with a reason. **No test code before the scenario × oracle table exists**, and each test
then asserts its row: the response oracle in the assertion, the others as the round-trip, negative and
side-effect checks the row names. A scenario with no credible oracle is raised with the user, not guessed.

## 2. The hallucination gate

After generating and before review or the first run, list every test id and every endpoint the new code uses
and look each one up in the source of truth. Anything not found is reported as `MISSING` — never replaced with
a guessed id, path or field.

```bash
grep -rhoE 'GetByTestId\("[^"]+"' Tests Pages | sed -E 's/.*\("//; s/"$//' | sort -u > /tmp/used-testids.txt
while read -r id; do grep -rqF -- "$id" "$APP_SRC" || echo "MISSING testid $id"; done < /tmp/used-testids.txt

jq -r '.paths | keys[]' "$OPENAPI_JSON" | sed -E 's/\{[^}]+\}/{}/g' | sort -u > /tmp/spec-paths.txt
grep -rhoE '"/api/[^"]*"' ApiTests/Clients | tr -d '"' | sed -E 's/\{[^}]+\}/{}/g' | sort -u > /tmp/used-paths.txt
comm -23 /tmp/used-paths.txt /tmp/spec-paths.txt | sed 's/^/MISSING endpoint /'
```

`APP_SRC` is the front end's source folder (the React or Blazor tree that renders `data-testid`); `OPENAPI_JSON`
the stored spec (a YAML spec goes through `yq -o=json` first). Path parameters are normalised to `{}` on both
sides, so `{id}` and `{orderId}` match. Where the spec's paths omit a prefix the server URL carries (`/api`),
strip it from the client paths before `comm`. The HTTP method of each matched path is checked by reading the
spec entry.

- **A `MISSING` test id** means the element has none, or the generator invented it. Read the component: if the
  element exists without a test id, use the next locator rung and add a `missing-testids.md` row
  (`ui-test-author/playwright`, `references/locators.md` §1); if the element does not exist, the scenario is
  wrong — raise it.
- **A `MISSING` endpoint** stops that test: no test is written against a path the contract does not have.
  Check the stored spec is current (`qa/_shared/api-spec-assets`), then raise the gap with the user.
- An id composed at runtime (`` `${row}.Title` ``) cannot be grepped literally and is reported `MISSING` for a
  human to confirm — a false alarm is cheaper than a guessed locator.
- The gate's output goes in the report even when it is empty: `hallucination gate: 0 MISSING (14 test ids, 6
  endpoints checked)`.
