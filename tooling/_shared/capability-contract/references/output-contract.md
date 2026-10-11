# Output contract — the shape every capability returns

Decided once for the whole surface. Per-capability blocks state only their deltas. Both `tooling:mcp-builder` and `tooling:cli-builder` implement this file literally; if the two surfaces disagree on a response shape, this file is what they were supposed to agree on.

The reader is an agent with a token budget and no ability to re-read a truncated payload. Every rule below exists because of that.

## 1. One envelope, always

Every capability returns the same outer shape, success or failure:

```jsonc
// success
{ "ok": true,  "data": <capability-specific>, "meta": { … } }
// failure
{ "ok": false, "error": { "code": "conflict", "message": "…", "field": "lines[2].quantity", "retryable": false } }
```

- **`ok` is the branch.** An agent should never have to parse a message to learn whether it worked.
- **`data` is the only capability-specific part.** Everything else is inherited.
- **`meta` carries paging and truncation**, never domain data.
- A capability that returns nothing meaningful returns `{ "ok": true, "data": null }` — not an empty string, not silence.

**CLI rendering:** the same JSON on stdout under `--json`, plus a non-zero exit code on `ok: false`. Human-readable text mode is a *rendering* of this object, never a different object.

**MCP rendering:** the object goes in `structuredContent`, and a compact human-readable summary goes in `content[0].text`. Both are the same facts — the text is a summary, never extra data the structured branch lacks.

## 2. Errors are a closed vocabulary

Eight codes cover almost every surface. Add a ninth only when an agent would genuinely act differently on it:

| `code` | Means | `retryable` | Agent's move |
|---|---|---|---|
| `validation_failed` | An input violated the schema or a stated constraint | no | Fix the field named in `field`, retry |
| `not_found` | A referenced id does not exist | no | Re-resolve the id via the capability that produces it |
| `conflict` | State forbids it (wrong status, out of stock, duplicate) | no | Read current state, then decide |
| `forbidden` | Caller lacks the permission | no | Stop and report — retrying never helps |
| `unauthenticated` | Missing/expired credential | no | Stop and report — it is a config problem |
| `rate_limited` | Throttled | **yes** | Wait `meta.retryAfterSeconds`, retry |
| `unavailable` | Upstream dependency down or timed out | **yes** | Retry with backoff, then stop |
| `internal` | Unhandled fault | no | Stop and report; include `error.traceId` |

Rules:

- **`retryable` is stated, not inferred.** It is the single field that keeps an agent out of a retry loop.
- **`field` uses a JSON path into the input** (`lines[2].quantity`), so the agent can fix precisely one thing.
- **`message` is one sentence, addressed to the caller, saying what to do** — "Product 9c1b… has 1 in stock, requested 2", not "Constraint violation in PlaceOrderHandler".
- **Never leak internals.** No stack traces, no SQL, no connection strings. `internal` carries a `traceId` and nothing else.
- **A non-zero CLI exit code maps to the code**: `2` validation_failed · `3` not_found · `4` conflict · `5` forbidden/unauthenticated · `6` rate_limited/unavailable · `1` internal. Documented in the CLI's `--help`.

## 3. Paging is mandatory on every list

An unbounded list is the most common way an agent surface becomes unusable.

```jsonc
{ "ok": true, "data": [ … ], "meta": { "page": 1, "pageSize": 50, "total": 412, "hasMore": true } }
```

or, when the source is cursor-based:

```jsonc
{ "ok": true, "data": [ … ], "meta": { "nextCursor": "eyJpZCI6…", "hasMore": true } }
```

- **Pick one style for the whole surface.** A mixed surface is a permanent tax on every caller.
- **`pageSize` has a default and a hard maximum** (default 50, max 200 unless the domain says otherwise). An agent asking for 10 000 gets the maximum and `hasMore: true`, never a timeout.
- **Every list has a stated default sort**, or paging is nondeterministic and the agent silently misses rows.
- **`hasMore` is always present** — it is what an agent loops on. `total` is optional when counting is expensive; say so in the capability block.

## 4. Token budget

- **A single response targets ≤ 25 KB of serialized JSON.** Over that, truncate and say so: `meta.truncated: true` with `meta.truncatedReason` and the way to get the rest (`"use pageSize=20"` / `"fetch fields=summary"`).
- **Default to the summary projection on lists, the full object on `get`.** A list of 50 orders each with 100 lines is not a list, it is an outage. State the summary field set in the capability block.
- **Support a `fields` input where projection genuinely varies.** One optional parameter beats four near-identical capabilities.
- **No decorative payload** — no HTML, no ANSI colour, no ASCII tables inside `data`, no base64 blobs. Binary goes to a path on disk and the path goes in `data`.

## 5. Types that survive the wire

| Kind | Wire form | Why |
|---|---|---|
| Timestamps | ISO 8601 UTC with `Z` | Local time in an agent transcript is a bug factory |
| Money | integer minor units + `currency` | Floating point money is a defect on arrival |
| Ids | strings, always | Numeric ids get JSON-rounded and reformatted |
| Enums | lower-case strings, enumerated in the schema | The agent's first call is correct |
| Absent value | field omitted, or `null` — pick one and hold it | Mixed absence semantics cost a turn every time |
| Booleans | real booleans | Never `"true"`, never `1` |

## 6. Determinism

The same inputs against the same state return the same bytes.

- No timestamps of "now" in `data` unless the capability is *about* now.
- Stable ordering everywhere, including object key order where the serializer allows it.
- No random ids in the response that are not real domain ids.

This is not fussiness: it is what makes a capability testable, cacheable, and diffable, and what lets an agent tell "nothing changed" from "something changed".
