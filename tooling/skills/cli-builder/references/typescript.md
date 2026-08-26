# TypeScript CLI — patterns

Node 24 (active LTS) · TypeScript `strict: true` · `commander` for parsing · `zod` for validating and for reusing the contract's constraints.

Use the same Zod schemas the MCP server uses when both surfaces exist in one repo — one contract, one set of schemas, two renderings.

## Project

```
package.json      "type": "module", bin entry, build script
src/cli.ts        root command, global flags, exit-code mapping
src/config.ts     flag → env → file → default resolution, validated
src/client.ts     typed client to the project
src/envelope.ts   shared with the MCP surface when both exist
src/render.ts     envelope → text; the only place formatting lives
src/commands/
  orders.ts       one file per capability noun
```

```json
{
  "name": "@acme/orders-cli",
  "type": "module",
  "bin": { "orders": "dist/cli.js" },
  "scripts": { "build": "tsc" },
  "dependencies": { "commander": "^12", "zod": "^3" }
}
```

`src/cli.ts` starts with `#!/usr/bin/env node`.

## Root and global flags

```ts
import { Command } from "commander";

const program = new Command()
  .name("orders")
  .description("Drive the Contoso ordering surface from a terminal or a script.")
  .version(VERSION)
  .option("--json", "Emit the result envelope as JSON on stdout")
  .option("--yes", "Skip confirmation prompts for destructive commands")
  .option("--quiet", "Suppress non-error diagnostics")
  .option("--verbose", "Diagnostic logging to stderr")
  .addHelpText("after", EXIT_CODE_HELP);

registerOrderCommands(program);
registerProductCommands(program);

await program.parseAsync();
```

`EXIT_CODE_HELP` is the exit-code table as text. It belongs in `--help` because the caller who needs it is reading `--help`, not the README.

## One command per capability

```ts
import { z } from "zod";
import { run } from "../runner.js";
import { api } from "../client.js";

const LINE = /^(?<productId>[0-9a-f-]{36}):(?<quantity>\d{1,3})$/;

const PlaceInput = z.object({
  customerId: z.string().uuid(),
  currency: z.enum(["EUR", "USD", "GBP"]),
  lines: z.array(z.object({ productId: z.string().uuid(), quantity: z.number().int().min(1).max(999) }))
    .min(1).max(100),
  idempotencyKey: z.string().min(8).max(64),
});

export function registerOrderCommands(program: Command) {
  const orders = program.command("orders").description("Orders");

  orders
    .command("place")
    .description("Create a pending order from resolved customer and product ids and reserve stock.")
    .requiredOption("--customer-id <uuid>", "Customer id from `orders customers list`. Example: 3f2a1c8e-…")
    .requiredOption("--currency <code>", "ISO 4217, one of EUR|USD|GBP. Example: EUR")
    .requiredOption("--line <productId:quantity...>", "Repeatable, 1–100 lines. Example: 9c1b77d2-…:2", collect, [])
    .requiredOption("--idempotency-key <key>", "Stable across retries of one attempt. Example: place-7f3a")
    .option("--dry-run", "Validate and resolve, print what would happen, change nothing")
    .addHelpText("after", "\nExample:\n  orders orders place --customer-id 3f2a1c8e-… --line 9c1b77d2-…:2 \\\n    --currency EUR --idempotency-key place-7f3a --json\n")
    .action((opts, cmd) =>
      run(cmd, () => {
        const input = PlaceInput.parse({
          customerId: opts.customerId,
          currency: opts.currency,
          lines: opts.line.map(parseLine),
          idempotencyKey: opts.idempotencyKey,
        });
        return opts.dryRun ? api.previewOrder(input) : api.placeOrder(input);
      }),
    );
}
```

- **Zod parses; the action does not validate.** A Zod failure maps to exit `2` with the offending path — `issues[].path` and `issues[].code`, never the raw message.
- **Every option's description ends with its example**, taken from the contract.
- **Repeatable options for arrays** (`--line a:2 --line b:1`) beat a JSON blob in a flag, which nobody can type correctly.

## The runner — one place that renders and exits

```ts
const EXIT: Record<ErrorCode, number> = {
  internal: 1, validation_failed: 2, not_found: 3, conflict: 4,
  forbidden: 5, unauthenticated: 5, rate_limited: 6, unavailable: 6,
};

export async function run<T>(cmd: Command, work: () => Promise<Ok<T> | Err>): Promise<never> {
  const { json } = cmd.optsWithGlobals();
  const result = await work().catch(toEnvelopeError);

  if (json) process.stdout.write(JSON.stringify(result) + "\n");
  else process.stdout.write(renderText(result) + "\n");

  process.exit(result.ok ? 0 : EXIT[result.error.code]);
}
```

Every command funnels through this. It is why no command can invent its own output shape, its own exit code, or its own way of failing.

**Nothing else in the codebase writes to stdout.** Diagnostics go through a logger bound to `process.stderr`.

## Destructive commands

```ts
orders
  .command("cancel <order-id>")
  .description("Cancel a pending or paid order and release its stock reservation.")
  .requiredOption("--reason <text>", "Recorded in the audit log, 3–200 chars.")
  .option("--dry-run", "Show what would be cancelled, change nothing")
  .action(async (orderId, opts, cmd) => {
    const { yes } = cmd.optsWithGlobals();
    if (!opts.dryRun && !yes && !(await confirm(`Cancel order ${orderId}? This cannot be undone.`))) {
      process.stderr.write("Aborted.\n");
      process.exit(0);
    }
    return run(cmd, () => api.cancelOrder(orderId, opts.reason, { dryRun: opts.dryRun }));
  });
```

`confirm` reads from stdin **only when stdin is a TTY**. When it is not — CI, a pipe, an agent — it returns `false` immediately rather than hanging forever waiting for input nobody will type. A CLI that hangs in CI is worse than one that refuses.

## Config

```ts
export function resolve(name: string, flag: string | undefined, env: string): string {
  const value = flag ?? process.env[env] ?? fileConfig[name];
  if (!value) {
    process.stderr.write(`Missing configuration: set ${env} or pass --${kebab(name)}.\n`);
    process.exit(2);
  }
  return value;
}
```

Flag → env → file → default, resolved before any work starts. Secrets are env-or-store only and have **no flag** — `resolve` is not called with one for a token.

## Rendering text

```ts
export function renderText(result: Ok<unknown> | Err): string {
  if (!result.ok) return `${result.error.code}: ${result.error.message}` + (result.error.field ? ` (${result.error.field})` : "");
  if (Array.isArray(result.data)) return table(result.data) + footer(result.meta);
  return summary(result.data);
}
```

- `footer(meta)` prints `showing 1–50 of 412 — pass --page 2 for more` when `hasMore`. The next command to run belongs in the output, not in the reader's head.
- Colour only when `process.stdout.isTTY && !process.env.NO_COLOR`.
- Text mode never contains a fact the JSON lacks.

## Smoke test

A shell script, committed, that walks one flow with real ids and asserts exit codes:

```bash
#!/usr/bin/env bash
set -euo pipefail

CUSTOMER=$(orders customers list --email ada@example.com --json | jq -er '.data[0].id')
PRODUCT=$(orders products search --query widget --json | jq -er '.data[0].id')
ORDER=$(orders orders place --customer-id "$CUSTOMER" --line "$PRODUCT:2" \
  --currency EUR --idempotency-key "smoke-$$" --json | jq -er '.data.id')

orders orders get "$ORDER" --json | jq -e '.data.status == "pending"'

set +e; orders orders place --customer-id not-a-uuid --json >/dev/null 2>&1
[ $? -eq 2 ] || { echo "expected exit 2 on validation failure"; exit 1; }
```

`set -euo pipefail` plus `jq -e` means a broken contract fails the script instead of quietly producing an empty string.

## Checklist

- [ ] `strict: true`, no `any`, build clean
- [ ] `<bin> <noun> <verb>` matching the capability ids and the MCP tool names
- [ ] Every input a flag; every flag's description carries its example
- [ ] Zod parses input; failures map to exit `2` with the field path
- [ ] `--json` emits the envelope; nothing else ever touches stdout
- [ ] Exit-code table implemented and printed in `--help`
- [ ] Secrets from env/store only, no flag
- [ ] `--dry-run` on every write/destructive command
- [ ] Confirmation on destructive commands, `--yes` to bypass, no hang on non-TTY
- [ ] Lists print paging state and the next command to run
- [ ] Colour gated on TTY + `NO_COLOR`
- [ ] Committed smoke script walking one flow and asserting exit codes
- [ ] README ships install, env vars, command table, flows, exit codes
