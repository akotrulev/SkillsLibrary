# Streaming rows — `qa-typescript:data-driven-testing`

Moved out of SKILL.md for on-demand loading.

## Streaming rows for huge datasets

`csv-parse` exposes an **async iterator** — for a large file, stream it instead of `readFileSync` + full
materialization, so memory stays flat:

```typescript
import { parse } from "csv-parse";
import { createReadStream } from "node:fs";

export async function* streamTaxCases(path: string): AsyncGenerator<TaxCase> {
  const parser = createReadStream(path).pipe(parse({ columns: true, trim: true }));
  for await (const record of parser) yield TaxCaseSchema.parse(record);
}
```

Streaming keeps the **parse** flat; the runner still needs every row at collection to name a test after it. So
collect at module scope (Vitest supports top-level `await`; `Array.fromAsync(streamTaxCases(path))` on Node 22
and 24) and hand the array to `test.for`. Never assert rows one by one inside a single streaming test — that is
the loop-in-a-test this skill exists to replace. A dataset too large to name every row is a load or batch job
(`qa-typescript:load-testing`), not a data-driven suite.
