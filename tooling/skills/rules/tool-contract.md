---
paths:
  - "**/docs/specs/*-tool-contract.md"
---

<!-- tooling rules v1 (2026-11-03): capability contracts. Installed by /tooling:rules; edit the paths above to where this project keeps its MCP / CLI tool contracts, re-run to compare with the plugin's copy. -->

# Capability contract standards (the document an MCP server and a CLI are rendered from)

Apply these to every tool contract you write, extend or review. The tag after a rule is the severity a review reports: **blocker** exposes a credential or an ungated irreversible action, **major** leaves an agent unable to call or compose the surface correctly, **minor** is a convention, **nit** is preference.

**The existing surface wins.** When the contract extends an MCP server or CLI that already exists, inherit its name, tool prefix, envelope, error vocabulary and paging style without exception; a second convention inside one surface is a defect. The code and the contract never disagree silently: when they do, the contract is fixed first, then the code. *major*

## The document

- One file, `docs/specs/<NNN>-<surface>-tool-contract.md`. It names the source of truth it was derived from (an approved API surface, OpenAPI or proto, or the code) and records the detected stack and version. *minor*
- The capability table has Capability, Intent, Kind, Source, Auth, Idempotent and Flow for every row. Source is a `file:line`; a row with none is marked as an invention. An extension specs only the delta; recovered rows are marked `#confirmed`. *major*
- A capability id is `<noun>.<verb>`, lower-case and dot-separated, with the noun singular or plural consistently across the surface. It is the only name: the MCP tool is `<prefix>_<noun>_<verb>`, the command `<bin> <noun> <verb>`. *major*
- Intent is a sentence an agent can route on, not the name restated. *minor*
- No capability without a consumer; near-identical getters collapse into one capability with a filter; no free-text `execute` / `query` capability. *major*
- Kind is `read`, `write` or `destructive`. Anything that deletes, spends money, mutates production or reads secrets is `destructive` and gated (MCP `destructiveHint` plus a required `confirm`; CLI a prompt plus `--yes` and `--dry-run`), or not exposed. *blocker*
- A credential is process configuration, read at startup, never a capability input; the dependency table says where each secret comes from. *blocker*
- Each capability has a block: an inputs table (Name, Type, Required, Constraints, Example, Notes) with every field typed, never `object` / `any`, every enum enumerated, an `Example` on every input, and a Note naming the capability that produces any input fed from another; the output shape; an error table whose last column says what the caller does next. *major*
- Every capability is in a flow or marked a leaf. A flow names the field carried between its steps and the recovery for its likeliest failure; a flow that needs a capability the table lacks is a finding, never an assumption. *major*
- The not-exposed list says what is deliberately left out and why. *minor*

## The output contract every capability inherits

- One envelope: `{ ok: true, data, meta }` or `{ ok: false, error: { code, message, field, retryable } }`. A block states only its deltas; nothing returns a raw upstream payload. *major*
- Error codes come from the closed vocabulary (`validation_failed`, `not_found`, `conflict`, `forbidden`, `unauthenticated`, `rate_limited`, `unavailable`, `internal`); a new code only where an agent would act differently. `retryable` is stated, `field` is a JSON path into the input, `message` is one sentence saying what to do, and nothing leaks internals (`internal` carries a `traceId` only). *major*
- CLI exit codes map to the codes: 0 success, 1 internal, 2 validation_failed, 3 not_found, 4 conflict, 5 forbidden / unauthenticated, 6 rate_limited / unavailable. *major*
- Every list is paged in the one style the surface chose (page or cursor), with a default and a hard maximum `pageSize` (50 / 200 unless the domain says otherwise), a stated default sort, and `hasMore` always present. *major*
- A response targets ≤ 25 KB: lists return the summary projection the block names, a cut sets `meta.truncated` with the reason and how to get the rest, and binary goes to a path, never base64. *minor*
- Wire types: ISO 8601 UTC timestamps with `Z`, money as integer minor units plus `currency`, ids as strings, enums as lower-case strings, one absence convention, real booleans. *major*
- The same inputs against the same state return the same bytes: no "now" in `data` unless the capability is about now, stable ordering. *minor*
