---
name: <skill-name>
# name rule: topic only — no domain or stack prefix, unique within its plugin, not a reserved name (CONTRIBUTING.md, "Names and registration")
description: Use when the user asks to review, audit, critique, or check existing <stack> code for <concern>. Triggers: "review this for X", "is this idiomatic", "audit this code". Do NOT use for explaining concepts (use <sibling reference>) or generating new code (use <sibling generator>).
---

# <Skill Title>

## When to use

- The user shares existing code and asks for a critique
- The user asks whether their code follows a pattern correctly
- The user asks for an audit or code review

## When NOT to use

- The user asks "what is X" — defer to reference
- The user asks "create X" — defer to generator
- The code is incomplete or pseudocode — ask the user to share the real file

## Procedure

1. Read the file(s) under review. Do not skim.
2. Walk through the checklist below, marking each item pass / fail / N/A.
3. Produce findings in the standard table format.
4. Do NOT rewrite the code. Point to the fix and let the user apply it.

## Checklist

- [ ] Item 1: concrete, testable
- [ ] Item 2: concrete, testable

For each failed item, produce a finding.

## Output format

Use the standard finding table:

```
| Severity | Location          | Issue                          | Suggested fix                |
|----------|-------------------|--------------------------------|------------------------------|
| major    | UserService.cs:42 | <one-line issue>               | <one-line fix>               |
```

After the table, add a short "Overall" paragraph (2–3 sentences) summarizing the state of the code.

## Severity guide

- **blocker**: ships a bug, breaks the build, violates a security rule
- **major**: design or correctness issue
- **minor**: style, naming, small inconsistency
- **nit**: optional preference

## Examples

### Example: review a strategy pattern implementation

Input: a single `OrderProcessor.cs` with an inline `if/else` chain selecting payment type.

Finding:

| Severity | Location              | Issue                                        | Suggested fix                                              |
|----------|----------------------|----------------------------------------------|------------------------------------------------------------|
| major    | OrderProcessor.cs:34 | If/else chain on payment type — strategy missing | Extract IPaymentStrategy, inject via factory or DI keyed service |

Overall: the class is doing two jobs (selection + processing). Introducing a strategy interface will make adding payment types a closed-for-modification change.
