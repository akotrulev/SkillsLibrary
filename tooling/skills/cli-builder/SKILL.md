---
name: tool-cli-builder
description: Use when a project's capabilities must be driven from a terminal or a script — render a confirmed capability contract as a subcommand CLI with typed flags, a `--json` mode, meaningful exit codes, and a smoke test. Triggers "build a CLI for this project", "expose these functions as commands", "we need a command-line tool for X". Do NOT use to derive the capabilities first (`tool-capability-contract`), to build an MCP surface (`tool-mcp-builder`), or to write CI pipeline YAML (`devops/*`).
---

# CLI Builder — the contract, rendered as commands

A CLI is the same capability contract as an MCP server, addressed to a shell instead of a protocol. Every design question — what commands exist, what they accept, what they print, what they refuse — was answered in `docs/specs/<NNN>-<surface>-tool-contract.md`. This skill renders that document into a binary that validates its flags, prints one predictable shape under `--json`, and exits with a code that means something.

**Two readers, both first-class:** a human at a prompt, and an agent (or a CI step) capturing stdout. The human gets the default text rendering; the agent passes `--json` and gets the envelope. **They are renderings of the same object, never two different objects.**

**Prerequisite: a confirmed capability contract.** Read its capability table, flows, and dependency section, plus `tooling/_shared/capability-contract/references/output-contract.md` — the envelope `--json` emits.

## When to use

- Step 2 of a `tooling-engineer` run, after the contract is confirmed
- An existing CLI gains commands (`EXTEND` — read it, inherit its binary name, flag conventions, and exit codes; add only the delta)
- An MCP server built from the same contract now needs a terminal twin

## When NOT to use

- The surface is for an agent over a protocol → `tool-mcp-builder` (build both from one contract when both are wanted)
- The ask is CI pipeline configuration → `devops/*` owns pipelines; this skill builds the tool a pipeline step *calls*
- The project already has a CLI and the ask is to *use* it → nothing to build

## Implementation lane

From the contract's detected stack:

| Project stack | Lane |
|---|---|
| Node / TypeScript | **TypeScript** — `commander` + Zod, `bin` entry, distributed by `npx` |
| .NET | **C#** — `System.CommandLine`, packaged as a `dotnet tool` |
| Java 21 | **Java** — `picocli`, packaged as a runnable jar or a native image |
| Anything else with an HTTP API | **TypeScript** sidecar, as with MCP |

Unlike MCP, a CLI has no SDK-quality reason to prefer TypeScript: **match the project's stack when the project has one**, so the tool ships and is tested with everything else. Reach for a sidecar only when the capabilities are only reachable over HTTP.

- **TypeScript:** [`references/typescript.md`](references/typescript.md)
- **.NET / Java:** [`references/stack-native.md`](references/stack-native.md)

---

## Procedure

### Step 1 — Orient

Read the project's existing scripts, `Makefile`, or tool entry points before writing. If a CLI already exists, extend it — a second binary doing adjacent things in the same repo is a defect, not a feature. Match the project's config, logging, and error conventions over this skill's defaults.

Confirm the parser library version actually installed and check its API against that version. `System.CommandLine` in particular has renamed core members across betas; do not write from memory.

### Step 2 — The command tree

Mechanical, per row of the capability table:

| Contract | CLI |
|---|---|
| Capability id `orders.place` | `<bin> orders place` |
| Intent sentence | The command's help text, verbatim |
| Inputs table | One option per row — `--customer-id`, `--currency`, `--line` (repeatable) |
| Required input | A required option, enforced by the parser |
| Output shape | The `--json` payload; the text renderer is derived from it |
| Kind `destructive` | Interactive confirmation, bypassed only by `--yes` |
| Errors table | The exit-code map, documented in `--help` |

Rules:

- **`<bin> <noun> <verb>`, always two levels.** The noun and verb come from the capability id and match the MCP tool names exactly — one contract, two renderings, no divergence.
- **Kebab-case flags for camelCase fields.** `customerId` → `--customer-id`. Mechanical, so it is never surprising.
- **Options over positional arguments**, except for the one obviously-primary argument (`orders get <order-id>`). Positional order is a memory tax; flags are self-describing.
- **No interactive prompts except the destructive confirmation.** A CLI that asks questions cannot be scripted. Every input is a flag; a missing required flag is a parse error naming the flag.
- **Global flags, on the root, inherited by every command:** `--json` · `--yes` · `--quiet` · `--verbose` · `--version` · `--help`. Nothing else global without a reason.

### Step 3 — Two renderings, one object

Every command builds the envelope object first, then renders it:

- `--json` → the envelope, serialized, on **stdout**, nothing else on stdout ever.
- default → a compact human rendering of the same envelope: a line per record, a small aligned table for lists, the summary sentence for a single object. No ASCII art, no spinner in non-TTY, no colour when stdout is not a TTY or `NO_COLOR` is set.
- **Diagnostics, progress, and logs go to stderr.** Always. This is what makes `tool orders list --json | jq` work, and it is the single most common way a CLI becomes unusable in a pipeline.

### Step 4 — Exit codes that mean something

From the contract's error vocabulary, documented in `--help`:

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | `internal` — unhandled fault |
| `2` | `validation_failed` — bad input, including parse errors |
| `3` | `not_found` |
| `4` | `conflict` |
| `5` | `forbidden` / `unauthenticated` |
| `6` | `rate_limited` / `unavailable` — retryable |

A caller must be able to branch on the exit code without parsing output. `exit 1` for everything is the failure this table exists to prevent.

### Step 5 — Config and secrets

Precedence, highest first: **flag → environment variable → config file → default.** State it in `--help`.

- **Secrets come from the environment or a secret store, never a flag.** A `--token` flag lands in shell history, `ps` output, and CI logs. If the contract has a credential as an input, that is a blocker — fix the contract.
- Validate every required dependency **before running the command**, and fail with exit `2` naming the missing variable.
- `--dry-run` on every `write` and `destructive` command: perform validation and resolution, print exactly what would happen, change nothing, exit `0`.

### Step 6 — Flows are documented, not automated

As with MCP: do not build a `place-order-flow` command that runs the sequence. The value of a CLI to an agent is that each step's output feeds the next step's input, visibly.

What you do build:

- **Every list command's `--json` output carries the ids the next command needs** — a flow that requires a second call to learn an id is a contract defect.
- **A `## Flows` section in the README**, one block per flow from the contract, written as literal shell:

  ```bash
  CUSTOMER=$(orders customers list --email ada@example.com --json | jq -r '.data[0].id')
  PRODUCT=$(orders products search --query widget --json | jq -r '.data[0].id')
  orders orders place --customer-id "$CUSTOMER" --line "$PRODUCT:2" \
    --currency EUR --idempotency-key "place-$(date +%s)" --json
  ```

A composite command is justified only when the steps are atomic — all succeed or all are undone — and the reason goes in the code's one permitted doc comment.

### Step 7 — Help that answers the question

`--help` on the root lists the nouns with one line each. `--help` on a command shows: the intent sentence, every flag with its constraint and example, the exit codes, and **one worked example** taken from the contract's `Example` column. A help text without an example makes the reader guess the format of exactly the field they are unsure about.

### Step 8 — Build, smoke, verify

1. **Build clean** — no warnings, `strict: true` / nullable on.
2. **Run every command once** with the contract's `Example` values, in both `--json` and text mode.
3. **Prove one flow** as a shell script, piping each step's output into the next. Commit it as the smoke test.
4. **Prove the exit codes** — force a validation failure and a conflict, and assert the code, not the message.
5. **Destructive commands:** prove the prompt refuses without `--yes`, and that `--dry-run` changes nothing.

Report what you ran and what it printed. Inside a `Gate: none` plan task, write the smoke script but run none of these checks, and report the CLI as "written, not run".

### Step 9 — Ship it installable

The CLI is not delivered until someone can run it. Emit in the README: the install line (`npx`, `dotnet tool install`, or the jar), the env vars and where to get them, the command table, the flows, and the exit-code table.

---

## Anti-patterns

| Anti-pattern | Why it fails | Instead |
|---|---|---|
| One command taking a free-text query | Undocumented grammar, nothing validated | One command per capability, typed flags |
| Human-formatted output only | Unparseable; agents and CI resort to regex | `--json` emitting the envelope |
| Logs, progress, or banners on stdout | Breaks every pipe, silently | Everything diagnostic to stderr |
| `exit 1` for every failure | Caller cannot branch without parsing text | The exit-code table |
| Interactive prompts for missing input | Hangs in CI, hangs under an agent | Required flags; parse error names the flag |
| `--token` / `--password` flags | Leaks to history, `ps`, and CI logs | Env var or secret store |
| Destructive command with no confirmation or `--dry-run` | One typo away from an incident | Prompt + `--yes` + `--dry-run` |
| A second binary beside the existing one | Two conventions, two install paths | Extend the existing CLI |
| Colour and spinners unconditionally | Corrupts captured output | TTY check + `NO_COLOR` |
