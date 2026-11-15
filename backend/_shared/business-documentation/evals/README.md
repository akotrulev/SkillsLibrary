# doc-business-model evals

Regression evals for `dev:doc-business-model`, run through `be-feature-documenter` (eval 1) and `be-documenter` in FULL mode (eval 2 — the fixture has no knowledge base, so a run on it is FULL by definition; the prompt pre-confirms the scope and the one-area split). Eval 3 runs `be-documenter` with a two-session split confirmed, so it must write a runnable plan and stop. Eval 4 runs `be-feature-documenter` with no environment and no waiver, so it must stop at the screens gate.

The fixture is an API with no runnable screens, so evals 1 and 2 waive the screenshots in their prompts; the screenshot rules themselves are covered by the lint's unit tests and the golden example.

- `fixture/` — a small .NET 8 minimal-API / EF Core codebase for the workshop-booking credits domain: plans (Basic 8 credits at £6.00, Plus 16 credits at £5.00), tiers 1/2/3, booking and cancellation endpoints, the 24-hour late-cancel rule, monthly posting, at-least-once pricing. It is the **only** source for these evals. The golden examples (`../references/example-*.md`) describe the same domain over an imagined codebase and deliberately differ from the fixture in several facts.
- `evals.json` — the prompts and their rule-based expectations (skill-creator format). Expectations are never line-exact.

This README sits outside `fixture/`, so the agent under test never sees it.

## What is tested

- One guide per run and nothing beside it: no `.behind-the-scenes.md`, `.technical.md` or screenshots folder; `doc-lint.py` passes.
- Shape: the first `##` is `Who uses it`; members and staff (the fixture's administrators) each have a `For <person>` section; no internal id outside `About this document`; the fixture has no member screen, so member tasks carry no `**Where:**` and no bold label, and every bold label in a staff task is a value of `staff-ui.en.json`.
- Content: exact numbers, a worked example whose overage arithmetic uses fixture values and is correct, client vocabulary, the quoted refusal text, no code nouns, no tier tags, no judging words.
- Defects (the fixture has some, deliberately not listed here) go to the run's report for `code-auditor`, never into the guide.
- The screenshot waiver is recorded in `About this document`.
- **Golden-copy detectors.** The expectations prefixed `Golden-copy check:` hold only for a guide traced from the fixture and fail for one copied from the golden: fixed tier costs, no way to set a personal overage rate, and the Plus plan.
- Eval 2 only: `system-overview.md` exists without retired siblings, `INDEX.md` has the credits line in its shape, and the KB models carry `file:line` evidence tiered `#observed` / `#inferred`.
- Eval 3 only: one plan in `docs/plans/` in the library's plan format (`engineering-practices/writing-plans/references/plan-format.md`, shaped by `backend/_shared/codebase-survey/references/documentation-plan.md`) — tasks A1, A2 and K1 in sequence, machine-readable prompt headings and first lines, the close-out section — no area documented in the survey session, and the environment named but never its address or logins.
- Eval 4 only: the screens gate stops the run and asks, and nothing is written.

## How to run

```bash
W=$(mktemp -d) && cp -R fixture/. "$W" && cd "$W"
git init -q && git add -A && git commit -qm "fixture"
```

Open Claude Code in `$W` with the plugins enabled — eval 1: `dev` and `be-dotnet`; eval 2: `dev`, `be-dotnet` and `business-analysis` (`be-documenter` uses its knowledge-base skills) — then:

- eval 1: `/dev:document-feature` with the eval 1 prompt from `evals.json` (it carries the screenshot waiver)
- eval 2: `/dev:document-system` with the eval 2 prompt from `evals.json` (scope and split pre-confirmed, so the survey gate does not stop)
- eval 3: `/dev:document-system` with the eval 3 prompt (same plugins as eval 2); it ends at the written plan — do not run the plan's prompts
- eval 4: `/dev:document-feature` with the eval 4 prompt (no waiver); it ends at the screens gate

Then lint and check each expectation by hand or with a grader:

```bash
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/features        # eval 1
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/business-model  # eval 2
```

Evals 3 and 4 have nothing to lint: read `docs/plans/*.md` and the agent's reply against their expectations.

## When an expectation fails

Fix the skill or agent, not the expectation. A failed `Golden-copy check` means the agent took facts from a golden example instead of tracing the fixture — fix the instruction that let it, never the expectation or the fixture. For any other expectation that contradicts a golden example in shape or tone, fix whichever of the two is wrong and say why in the commit.

Goldens are illustrations, never sources; where they differ from the fixture in any fact or wording (retries, timing, tier configuration, plans, paths, the plan-name refusal text), the fixture wins.
