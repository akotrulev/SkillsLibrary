---
name: api-spec-assets
description: Use when an OpenAPI/Swagger spec is handed to an API test suite — store it as a dated, committed asset, and on every later update derive from `git diff` exactly which DTOs and clients must change. Cross-stack. Triggers "here is the swagger json", "the API changed — update our DTOs/clients", "update from the diff". Do NOT use to author the DTOs/clients themselves (`api-models` / `api-client-writer`), to write tests (`api-test-author/*`), or for Pact contracts (`api-contract-testing`).
---

# QA — API Spec Assets & Diff-Driven Updates (Shared)

Cross-stack. An API spec handed to a test suite is **an asset, not a message**: it is stored in the repo, committed, and replaced in place when a newer version arrives. The stored copy is the only thing that makes the *next* hand-over cheap — with it, `git diff` tells you precisely which DTOs and clients are stale; without it, you re-read the whole spec and guess.

Stack siblings that do the actual authoring: `api-models` and `api-client-writer` under `qa/{dotnet,java,typescript}/skills/`. This skill owns **where the spec lives, how it is replaced, and how the delta becomes a work list** — nothing else.

The `qa-api-{stack}` agents expose the two modes below as three sub-modes of their **Mode A** (spec-is-the-basis): **A1** = INGEST · **A2** = UPDATE path A (a newer spec supplied as input) · **A3** = UPDATE path B (the user already replaced the stored file). One mode, three entry points — the difference is only who wrote the bytes and whether there is a baseline to diff.

## The one rule everything else serves

> **The filename date is a record, never an input.** Never decide whether a spec is new, stale, or unchanged by comparing the date in the filename to today, to the `info.version` field, or to anything else. Replace the file content first, then let `git diff` answer that question. A spec can be re-issued the same day with breaking changes, or carry a bumped `info.version` with no schema change at all — only the diff is evidence.

## Asset location & naming

One asset per **upstream service**, named `{service}-openapi-{YYYY-MM-DD}.json` where the date is **when this content was last brought in**.

| Stack | Location |
|-------|----------|
| dotnet | `ApiTests/Specs/{service}-openapi-{YYYY-MM-DD}.json` |
| java | `src/test/resources/specs/{service}-openapi-{YYYY-MM-DD}.json` |
| typescript | `specs/{service}-openapi-{YYYY-MM-DD}.json` |

- `{service}` is a lowercase slug matching how the suite already names the service (`trade`, `user-profile`) — match the project's existing folder/client naming over this default.
- YAML input is converted to JSON on ingest so one canonicalization rule covers every asset. Keep the extension `.json`.
- The asset is **committed**. An untracked spec file arms nothing (see *Fallback when git can't help*).
- Never keep old versions as extra files — git history *is* the version history. One file per service, always.

## Canonicalize on write — identically, every time

A minified or key-shuffled spec produces a one-line or all-red diff, which destroys the whole point. **Every write of the asset passes through the same normalizer**, on ingest and on every replacement you perform:

- pretty-print, 2-space indent
- object keys sorted lexicographically
- array order preserved (`servers`, `parameters`, `security` are order-significant)
- LF line endings, one trailing newline

```bash
# preferred
jq -S . incoming.json > "$ASSET"
# node fallback
node -e 'const s=(o)=>Array.isArray(o)?o.map(s):(o&&typeof o=="object")?Object.fromEntries(Object.keys(o).sort().map(k=>[k,s(o[k])])):o;process.stdout.write(JSON.stringify(s(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"))),null,2)+"\n")' incoming.json > "$ASSET"
# YAML input
npx --yes js-yaml incoming.yaml | jq -S . > "$ASSET"
```

**When the write wasn't yours** (path B — the user replaced the file by hand or by script), the normalizer was bypassed. Do **not** reformat the working-tree file before reading the delta; that rewrites the diff you came to read. Instead, if the raw diff is unusable (the replacement is minified, or its key order shifted, so one real change shows as a whole-file hunk), canonicalize **both sides into scratch copies** and diff those:

```bash
git show HEAD:<asset path> | jq -S . > "$SCRATCH/before.json"
jq -S . <asset path>              > "$SCRATCH/after.json"
git diff --no-index "$SCRATCH/before.json" "$SCRATCH/after.json"
```

Then canonicalize the asset in place as part of this change and say so in the report — the next update gets a clean diff again.

Set `core.autocrlf=false` for this path or add `*.json text eol=lf` to `.gitattributes` if the repo would otherwise rewrite line endings on a Windows checkout — a CRLF flip reads as a whole-file diff.

## Mode 1 — INGEST (the first pass — no asset for this service yet)

1. Canonicalize the incoming spec and write it to the location above with **today's date** in the name.
2. **Generation is not this skill's job and does not change on the first pass.** There is no baseline, so no diff is possible: the run proceeds exactly as it always has — the whole spec drives `api-models` then `api-client-writer` through the `qa-api-{stack}` agent's existing Mode A pipeline. This skill adds one thing to that pass: the stored, committed copy. Say plainly in the report that this pass was full-spec, not delta-driven.
3. **Commit the asset.** This is the one file whose commit is load-bearing: until it is in git history, the next hand-over has nothing to diff against. Ask for the commit explicitly if the run is otherwise not committing anything, and say why. Prefer a commit containing the asset alone (`chore(tests): baseline {service} openapi spec {date}`) so the first delta reads clean.

## Mode 2 — UPDATE (every pass after the first — an asset already exists)

**Two entry paths lead here, and step 0 is deciding which one you are on.** The first pass always takes a spec as an input; after that, the newer spec may still arrive as an input, or the user may have already replaced the file themselves (by hand, by a download script, by a CI job) and simply say *"update from the diff."* Everything from step 3 on is identical — only who wrote the bytes differs.

**Step 0 — establish which path.** Run `git status --porcelain -- <specs dir>` and read it against what the prompt supplied:

| What you see | Path | Do |
|---|---|---|
| No spec supplied, asset shows ` M` (modified, uncommitted) | **B — pre-replaced** | The delta is already in the working tree. **Do not overwrite it.** Skip step 1–2, go to step 3. Do not re-canonicalize either — reformatting a file the user just replaced rewrites the very diff you are about to read |
| A spec supplied, asset clean | **A — you replace it** | Steps 1–2 below |
| A spec supplied, asset also already modified | **ambiguous — ask** | Two candidate deltas exist. One question: is the working-tree copy the one to use, or should the supplied file overwrite it? Never silently pick |
| Asset shows ` R`/`??` + a deleted sibling — the user renamed *and* replaced | **B, renamed** | See *When the user renamed it too* below |
| Asset clean, no spec supplied, and the user says the API changed | **nothing to diff** | The replacement never landed. Say so and ask for the new spec — do not go hunting for the delta in `info.version` or the filename |

**Path A only** — steps 1–2:

1. **Confirm the baseline is clean** (already done in step 0). A dirty asset with no supplied spec is path B, not an error; a dirty asset *plus* a supplied spec is the ambiguous row above.
2. **Overwrite the content, keep the old filename.** Canonicalize the incoming spec over the existing path. Do **not** rename yet, and do **not** `git mv` — a rename plus a content change makes the diff depend on rename detection and staging, for no gain.

**Both paths** — from here the order is not stylistic; each step exists to keep the evidence intact:

3. **Take the diff.**
   ```bash
   git diff -- <asset path>              # the delta, still unstaged
   git diff --stat -- <asset path>       # size of the change, first
   ```
   If the change is large, save it before doing anything else so an interrupted run does not lose it:
   `git diff -- <asset path> > <scratch>/spec-delta.patch`
4. **Do not commit or stage the spec yet.** While the replacement is uncommitted, the diff is reproducible on demand — that is the crash-safety property of this ordering. If the replacement is **already committed** (common on path B — the user replaced and committed the file, or a CI job did), the delta is still reachable, just one indirection away:
   ```bash
   git log --oneline -- <asset path> | head -5      # find the replacing commit
   git diff <sha>~1 <sha> -- <asset path>           # the delta
   ```
   Save it to a patch file immediately in that case, and name the commit sha as the baseline in your report.
5. **Classify every hunk** into a work list using the mapping table below. Every hunk gets a row — including the ones you classify as no-op, so the report shows the delta was read in full rather than skimmed.
6. **Apply the code edits** through the stack siblings — `api-models` for DTOs/schemas, `api-client-writer` for clients — touching **only** the files the work list names. A spec update is not a licence to re-generate the suite.
7. **Verify**: build/typecheck clean, then run the affected tests. Removed or renamed fields surface here as compile errors in tests — those are part of this change, not follow-up work.
8. **Rename the asset to today's date, last.**
   ```bash
   git mv <old dated path> <same dir>/{service}-openapi-$(date +%F).json
   ```
   Last, so an interrupted run leaves an obviously-mid-flight state (old name, new content, uncommitted) rather than a fresh-looking name over unapplied changes. Include the rename in the same commit as the code edits. If the name already carries today's date (same-day second update, or the user renamed it themselves), there is nothing to rename — say so rather than inventing a suffix.
9. **If the content is byte-identical** — no delta at all — apply no code edits and **still rename to today's date**: the date records when the content was last confirmed against upstream, and rule 1 makes an "optimistic" date harmless because nothing ever reads it as a decision. Report it as `no delta — date bumped to record the verification`.

### When the user renamed it too (path B variant)

A user replacing the file by hand often renames it in the same move — dropping in `{service}-openapi-2026-07-29.json` beside the old `…-2026-03-01.json`, or `git mv`-ing then overwriting. The delta is still recoverable; take it against the committed old path rather than the working tree:

```bash
git status --porcelain -- <specs dir>                    # see both sides of the move
git diff -M -- <specs dir>                               # rename-detecting diff (staged move)
# or, explicitly, old committed content vs the new file:
git show HEAD:<old asset path> > "$SCRATCH/spec-before.json"
git diff --no-index "$SCRATCH/spec-before.json" <new asset path>
```

Then continue from step 5. Two rules hold: **the old file must end up deleted** — one asset per service, always, so fix it in this run if the user left both — and **the rename is not evidence**; classify from the diff exactly as on any other path, even when the new name's date makes the change look obvious.

## Diff → code work list

Read hunks by their JSON path, not by line proximity. `#/components/schemas/*` (or Swagger 2's `#/definitions/*`) drives DTOs; `#/paths/*` drives clients.

| Diff hunk | Effect | Action |
|---|---|---|
| Property added to a schema | additive | Add the property to the DTO (`api-models`); existing tests keep passing |
| Property removed from a schema | **breaking** | Remove from the DTO, then fix every test/builder that referenced it — do not leave a dead property "just in case" |
| Property renamed (a remove + an add in the same schema) | **breaking** | One rename in the DTO — including the wire-name attribute (`[JsonPropertyName]` / `@JsonProperty` / Zod key). Diffs never say "renamed"; you infer it from the pair, so state the inference in the report |
| Property type changed | **breaking** | Retype the DTO property per the stack's type-mapping table; check every builder and assertion touching it |
| `required` list changed | contract-visible | Nullability/optionality in the DTO (Zod `.optional()`, C# `?`, Java `@NotNull` expectations) **and** a negative test worth adding — a newly-required field is a new 400 case |
| `format`/`pattern`/`minimum`/`maxLength` changed | validation | Usually no DTO change; it is a **boundary-test** change — hand the new bound to the test-authoring step (BVA at the new edge) |
| Enum value added / removed | additive / **breaking** | Update the enum or union type; a removed value in use by a test is a test change too |
| New schema | additive | New DTO file (`api-models`) — only if a path or an existing schema actually references it; an orphan schema gets reported, not generated |
| Schema removed | **breaking** | Report it and delete only once the DTOs' consumers are handled; never delete a DTO whose tests still reference it in the same silent step |
| New path or new operation on an existing path | additive | New client method (`api-client-writer`) on the resource's existing client; a whole new resource means a new client |
| Path or operation removed | **breaking** | Report and escalate. Remove the client method and the tests that call it together, or mark the tests blocked — a removed endpoint is often an upstream mistake, and silently deleting coverage hides it |
| Path renamed / re-versioned (`/v1/x` → `/v2/x`) | **breaking** | Route change in the client only; DTOs usually unaffected. Check whether both versions are live before deleting the old method |
| Parameter added/removed/made required | **breaking** if required | Client method signature; a newly required query/header param is also a new negative case |
| Response `$ref` or status-code set changed | contract-visible | Client return type and the expected-status assertions |
| `requestBody` content type changed | **breaking** | Client serialization (and the `Content-Type` the client sends) |
| `securitySchemes` / per-operation `security` changed | **breaking** | Auth wiring — the token/lane the client uses (`test-login-tokens`), plus a 401/403 case |
| `servers` / base-URL changed | environment | Config, not code — the suite's per-environment base URL. Never hardcode it into a client |
| `description`, `summary`, `example`, `externalDocs` changed | **no-op** | No code change. Record the count in the report so a large but inert diff isn't mistaken for a real one |
| `info.version` bumped | **no-op** | Informational — record it. It is never evidence that anything changed, and never evidence that nothing did |

**Classify before you edit.** Skim-then-edit reliably misses the remove/add pairs that are actually renames, and a rename mistaken for a delete-plus-create loses every builder and assertion attached to the old name.

## Fallback when git can't help

If the asset is untracked, the repo has no git, or the baseline was lost, do not fall back to reading the whole spec and guessing:

```bash
cp <existing asset> "$SCRATCH/spec-before.json"      # BEFORE overwriting
jq -S . incoming.json > <existing asset>
git diff --no-index "$SCRATCH/spec-before.json" <existing asset>   # or: diff -u
```

Then proceed from step 5. Report that the run used a sidecar diff, and get the asset committed so the next one doesn't have to.

## Anti-patterns

- **Reading the filename date to decide anything.** The one rule. `-2026-03-01` in the name and a spec issued today may be identical; same-day names may differ wildly.
- **Overwriting a working-tree replacement with a supplied spec** without asking. Both were candidate deltas; you just destroyed one.
- **Reformatting a user-replaced file before reading its diff.** Canonicalization is for *your* writes; on path B it comes after the delta is captured, via scratch copies if the raw diff is unreadable.
- **Renaming to today's date first, then editing code.** A crashed run then looks finished.
- **Committing the spec replacement before the delta is consumed**, with no saved patch — the work list's evidence is now one indirection away and easy to get wrong.
- **Keeping `{service}-openapi-2026-03-01.json` *and* `…-2026-07-29.json`.** Two assets means the next diff has no single baseline. Git holds history.
- **Skipping canonicalization** because "the JSON looked fine" — a generator that switched key order turns a two-field change into a 4,000-line diff.
- **Re-generating every DTO and client because the spec changed.** The diff exists precisely so the change is scoped; a full re-generation also silently reverts every local convention applied to those files.
- **Deleting DTOs/clients for removed spec elements without touching their tests**, leaving a suite that does not compile or, worse, coverage that quietly disappeared.
- **Treating an `info.version` bump as the work list.**
- **Storing the spec outside the repo** (a scratch dir, a chat attachment). Next hand-over has no baseline and this skill has nothing to offer.

## Report contract

Whatever invoked this skill reports:

```
Spec asset: <path> (<INGEST | UPDATE | UPDATE — no delta>)
Entry path: <A — spec supplied, replaced by me | B — pre-replaced in the working tree | B — pre-replaced and committed | B — pre-replaced and renamed>
Baseline: <old filename + commit sha, or "none — first ingest">
Delta: +<n> / -<n> lines across <n> hunks — <n> breaking, <n> additive, <n> no-op
Work list:
  <json path> — <classification> → <file(s) to change>   (one row per hunk)
Applied: <path> — <one line each>
Verification: <build/typecheck result>; <affected tests: N passed / N failed>
Escalated: <removed endpoints/schemas, renames inferred, contradictions — or "none">
Renamed: <old name> → <new name (today)>   ← last step, after the edits landed
```

## Fences

- The DTO/client code itself belongs to `api-models` / `api-client-writer` — this skill produces the *work list*, they produce the code.
- New tests for new endpoints and new boundary/negative cases belong to `api-test-author/*`; a formal technique-derived case suite belongs to `qa-test-case-designer`.
- Consumer-driven contracts (Pact) are a different lane entirely: `api-contract-testing` + `qa-<stack>:contract-pact`. This skill diffs a spec the provider handed over; Pact verifies a contract the consumer wrote.
- Generating a client with an OpenAPI **codegen tool** is out of scope and generally rejected in this library: the suite's clients and DTOs follow house conventions the stack skills own, and a codegen run overwrites them.
