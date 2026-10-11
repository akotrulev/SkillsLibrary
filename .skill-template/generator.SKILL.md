---
name: <skill-name>
# name rule: topic only — no domain or stack prefix, unique within its plugin, not a reserved name (CONTRIBUTING.md, "Names and registration")
description: Use when the user asks to scaffold, generate, create, or set up <thing> in <stack>. Triggers: "scaffold X", "create a Y for Z", "set up <thing>". Do NOT use for explaining concepts (use <sibling reference>) or reviewing existing code (use <sibling reviewer>).
---

# <Skill Title>

## When to use

- The user asks to scaffold or create something
- The user has an existing repo and wants code added to it

## When NOT to use

- The user wants a concept explained — defer to the reference skill
- The user wants their code critiqued — defer to the reviewer skill

## Inputs needed

Before generating, confirm these. Ask at most 2–3 questions; infer the rest from context.

- Target project path
- Specific variant (e.g. which pattern, which framework version)
- Naming convention in the project (check existing files)

## Procedure

1. Read 1–2 existing files in the target project to infer style and conventions.
2. If a global `CLAUDE.md` exists in the project, honor it.
3. Generate files using the template below.
4. Run the test suite if one exists; if it fails, fix and re-run once before reporting.
5. Report what was created and what to do next.

## Output format

For each file created, produce:

```
Created: <path>
Purpose: <one line>
```

Then a short "Next steps" block listing what the user should do (register DI, add to startup, write the first test, etc.).

## Templates

### <Variant name>

```<lang>
// 30–80 lines, parameterized with {{placeholders}}
```

## Examples

### Example: scaffold X for the Users domain

User: "scaffold a strategy pattern in C# for payment processing"

Claude reads `Services/` for naming, then creates:
- `Services/Payments/IPaymentStrategy.cs`
- `Services/Payments/CreditCardPaymentStrategy.cs`
- `Services/Payments/PayPalPaymentStrategy.cs`
- `Services/Payments/PaymentStrategyFactory.cs`
- `Tests/Payments/PaymentStrategyTests.cs`

Then reports the files and recommends registering the strategies in DI.

## Anti-examples

User: "what is the strategy pattern"
→ This is a reference question. Defer to `<sibling reference>` and do not generate any files.
