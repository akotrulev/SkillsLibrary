# Contributing to SkillsLibrary

This guide covers how to add a new skill so that Claude actually triggers it correctly and the output stays consistent across the library.

## The three-layer model

For most domains, a skill comes in one of three shapes:

- **reference** — answers conceptual questions. No code is generated, no files are touched.
- **generator** — scaffolds code into the active repo. Asks at most 2–3 clarifying questions.
- **reviewer** — reads existing code and returns findings. Does not rewrite.

If a domain is procedural (Auth0 setup, pipeline YAML) one combined skill is fine.

## File layout

Each skill lives in its own directory and contains a single `SKILL.md`:

```
qa/test-case-writer/SKILL.md
design-patterns/dotnet/generator/SKILL.md
```

Supporting templates or examples go alongside:

```
qa/test-case-writer/
├── SKILL.md
├── templates/
│   ├── functional-test-case.md
│   └── api-test-case.md
└── examples/
    └── login-test-cases.md
```

## SKILL.md structure

Every skill follows the same outline. Copy the right file from `.skill-template/`.

1. **YAML frontmatter** — `name`, `description`. The description is what Claude uses to decide whether to load this skill.
2. **When to use** — concrete trigger phrases.
3. **When NOT to use** — explicit disambiguation from sibling skills.
4. **Inputs needed** — what Claude should know before generating output.
5. **Procedure** — numbered steps Claude follows.
6. **Output format** — exact shape of what gets produced.
7. **Examples** — at least one good example, ideally one bad example with rationale.

## Writing a good `description`

This is the highest-leverage line in the whole skill. Claude reads only descriptions when deciding which skills are relevant — if the description is vague, the skill won't trigger; if it's too broad, it'll trigger for the wrong things.

Rules:
- Start with "Use when..." and list concrete trigger phrases.
- Include the stack/language if the skill is stack-specific.
- Include an explicit "Do NOT use for..." clause to disambiguate from siblings.
- Stay under ~400 characters.

Good:
> Use when the user asks to write, derive, or generate formal test cases from requirements, user stories, or acceptance criteria. Triggers: "write test cases for X", "derive test scenarios from these ACs". Do NOT use for exploratory test charters (use qa/exploratory-charter-writer) or for writing automation code (use qa/api-test-author or qa/ui-test-author).

Bad:
> Helps with test cases.

## Naming conventions

- Folders: `kebab-case`
- Skill names in frontmatter: match the folder name
- Stack-specific skills: include the stack in the path (`auth/auth0-react`, not `auth/react`)

## Testing a new skill

Before merging:

1. Use the skill in a real conversation with Claude Code or Claude Desktop.
2. Try at least three different trigger phrases.
3. Try one phrase that should NOT trigger it — make sure it doesn't.
4. If it's a generator, run the generated code.
5. If it's a reviewer, point it at code with known issues and verify it catches them.

## Versioning

Skills are versioned via git. If you make a breaking change to a skill's output format, call it out in the commit message.

## Pull request checklist

- [ ] New skill follows the template
- [ ] Description starts with "Use when..." and includes a "Do NOT use for..." clause
- [ ] At least one full example in the skill
- [ ] Tested with 3+ trigger phrases
- [ ] Listed in the appropriate section of the root `README.md` status table
