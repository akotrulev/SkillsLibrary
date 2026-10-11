# Good signals — the counter-list for the TypeScript API review

- Every spec call goes through a `create{Resource}Client(token)` factory; raw methods return `ApiResponse` and never assert, `…Typed` methods assert status + `Schema.parse(response.bodyJson)`.
- Happy path uses the typed method (no re-asserting status); 4xx tests use the raw method and parse with `ProblemDetailsSchema`, asserting `title`, `status`, and `errors[field]`.
- Auth state is the factory `jwt`: the spec fetches it via `authHelper.getToken(...)` and passes it in; `''` for unauthenticated. No token literals, no `x-api-key`.
- Each `it(...)` constructs its own client; no top-level `let` reassigned between tests.
- Test titles read like behavior sentences and carry the TC-ID when a document exists.
- `it.each([...])` for parameterized cases; `tsc --noEmit` passes; `strict: true` is on; no `any` in the diff.
- Cleanup runs in `afterEach` / `afterAll` over ids tracked as they were created — with no `try/catch`, so a failing cleanup fails the hook loudly.
