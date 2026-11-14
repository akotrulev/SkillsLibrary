# Snapshot testing with Vitest

Read this when a unit's output is a **large, structured value** whose whole shape is the contract: a mapper that
builds a 30-field DTO, an error-to-ProblemDetails translation, a generated document, a rendered template, a
serialized payload. Vitest serializes the value the first time, a person reviews it, and every later run diffs the
new output against the stored one.

## Snapshot or targeted assertion

| The behaviour under test | Use |
|---|---|
| One value, one rule (a total, a status, a rounding boundary) | A targeted `expect(...).toBe(...)` — a snapshot hides the one thing the test is about inside output nobody reads |
| A branch of a mapper or schema | A targeted assertion per branch — the coverage floor counts asserting tests, and a snapshot asserts everything at once |
| A Zod rejection | `issues[].path` and `code` (`SKILL.md`, *Zod schemas*) — never a snapshot of the error object, whose messages change between Zod versions |
| The full shape of a large output, where any unintended change is a defect (field renamed, `undefined` appeared, order changed) | **A snapshot** |
| Output with no single owner of truth (generated SQL, an OpenAPI document, a rendered template) | **A snapshot**, reviewed in the diff like code |

A snapshot is **one logical assertion** — "the output equals the approved output" — so it obeys the one-assertion
rule. It never replaces the boundary tests: keep `it.each` rows for the rules, add one snapshot for the shape.

## Inline, file, or `.snap`

| Matcher | Stored | Use when |
|---|---|---|
| `toMatchInlineSnapshot()` | In the test file, written back by Vitest | The output is short (up to ~20 lines): the reader sees the expectation beside the call |
| `toMatchSnapshot()` | `__snapshots__/<file>.test.ts.snap` | Longer structured output from a function |
| `toMatchFileSnapshot(path)` | A file you name, any extension | Output that is itself a document — HTML, SQL, YAML, JSON — reviewed with its own syntax highlighting |

```ts
it('should map every order field when the order is shipped', () => {
  const order = new OrderBuilder().withStatus('Shipped').build();

  expect(toOrderDto(order)).toMatchSnapshot();
});

it('should render the query for a filtered listing', async () => {
  const sql = buildListingQuery(new ListingFilterBuilder().withStatus('Open').build());

  await expect(sql).toMatchFileSnapshot('./__file_snapshots__/listing-open.sql');
});
```

- **`toMatchFileSnapshot` returns a promise — `await` it**, or the test ends before the comparison and passes.
- A file snapshot lives in its own folder, never inside Vitest's managed `__snapshots__/`.
- On a Jest suite, `toMatchSnapshot` and `toMatchInlineSnapshot` work the same way; Jest has no file snapshot.

## What makes a snapshot stable

Every value that differs between runs breaks the snapshot on every run. In order of preference:

1. **Fix the seam.** A timestamp from the injected clock and an id from the injected id generator (`SKILL.md`, *The
   five seams*) are already fixed — `() => new Date('2026-08-09T12:00:00Z')`, a counter-backed id stub. Nothing to
   scrub, and the snapshot proves the value was carried through.
2. **Property matchers** for a value the test cannot control, keeping its type in the assertion:

   ```ts
   expect(event).toMatchSnapshot({ eventId: expect.any(String), occurredAt: expect.any(Date) });
   ```

   The matched fields are stored as `Any<String>` / `Any<Date>`; every other field is compared exactly.
3. **Scrub inside strings** — a URL carrying an id, a message carrying a timestamp — with one helper that replaces
   the **value** and keeps the **shape**, applied before the matcher:

   ```ts
   const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

   export const scrubIds = (text: string): string => text.replace(UUID, '{Uuid}');
   ```

   `href="/orders/{Uuid}/receipt"` still proves the link points at the receipt route of an order.

A snapshot serializer (`expect.addSnapshotSerializer`, or `snapshotSerializers` in the config) changes how **every**
matching value prints across the suite; reach for it only when one type needs the same treatment in many tests.

## Source control

- **Commit every `.snap` file and every file snapshot**, reviewed in the pull request like code. A snapshot diff
  nobody read is an assertion nobody made.
- `.gitattributes`: `*.snap text eol=lf` and the same for the file-snapshot folders, so a Windows checkout does not
  fail every comparison on line endings.

## CI never accepts a snapshot

- With `CI` set, Vitest writes no snapshots: a missing, changed or obsolete snapshot fails the run. Make it explicit
  in the pipeline with `vitest run --update=none`, so a runner without `CI` behaves the same.
- **`-u` is run by a person**, locally, after reading the diff — never in a pipeline step, a pre-commit hook, or as
  the reflex to a red test. A red snapshot means the output changed; whether that is the defect or the feature is a
  review decision.
- **An obsolete snapshot fails CI too.** Renaming or deleting a test leaves its entry behind; remove it with `-u`
  in the same change that renamed the test.
- Updating `vitest` can change snapshot formatting in a major version: bump it alone, re-run, review the diffs, then
  accept.

## When not to snapshot

- **To avoid writing the expectation.** Snapshotting a value because spelling out the expected one is tedious
  records whatever the code returns today, bug included. If the expected value is small enough to write, write it.
- **Error messages, log lines, stack traces** — not the contract (`SKILL.md`, *`vi.mock` traps*: don't assert on the
  logger).
- **Output that changes on purpose with every feature** (a full API response with dozens of optional fields): the
  snapshot is updated on every change, stops being read, and stops catching anything. Assert the fields the test is
  about.
