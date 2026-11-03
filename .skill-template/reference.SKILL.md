---
name: <skill-name>
# name rule: topic only — no domain or stack prefix, unique within its plugin, not a reserved name (CONTRIBUTING.md, "Names and registration")
description: Use when explaining or looking up <concept> in <stack>. Triggers "what is X", "when should I use X". Not for scaffolding code (<sibling generator>).
---

# <Skill Title>

## When to use

- The user asks for an explanation of a concept
- The user wants to compare two patterns
- The user wants canonical example code, not scaffolding into their repo

## When NOT to use

- The user wants code generated into their project — defer to the generator skill
- The user wants their code critiqued — defer to the reviewer skill

## Pattern card format

For each concept covered, use this structure:

### <Concept name>

**Intent**: one sentence

**When to use**:
- Bullet, one line each

**When NOT to use**:
- Bullet, one line each

**Minimal example**:

```<lang>
// 10–30 lines of canonical code
```

**Common mistakes**:
- Bullet

**Related patterns**:
- Link to sibling skills via relative path

## Coverage checklist

List the concepts this skill is expected to cover:

- [ ] Concept A
- [ ] Concept B
