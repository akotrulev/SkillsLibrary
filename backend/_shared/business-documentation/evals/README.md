# doc-business-model evals

Regression evals for `dev:doc-business-model`, run through `be-feature-documenter` (eval 1) and `be-documenter` in AREA mode (eval 2).

- `fixture/` — a small .NET 8 minimal-API / EF Core codebase for the workshop-booking credits domain. It is the executable source of the behaviour the golden examples (`../references/example-*.md`) illustrate: Basic plan 8 credits at £6.00, tiers 1/2/3, 24-hour late-cancel rule, monthly posting, at-least-once pricing.
- `evals.json` — the two prompts and their rule-based expectations (skill-creator format). Expectations are never line-exact.

## What is tested

The three files exist; `doc-lint.py` passes; exact numbers and the worked-example arithmetic in Level 1; client vocabulary and quoted refusal text; no code nouns in Level 1; no `#confirmed`; defects (the fixture has some, deliberately not listed here) reported as Level 3 Findings only; same sha and Audience lines across the set.

## How to run

```bash
W=$(mktemp -d) && cp -R fixture/. "$W" && cd "$W"
git init -q && git add -A && git commit -qm "fixture"
```

Open Claude Code in `$W` with the `dev` and `be-dotnet` plugins enabled, then:

- eval 1: `/dev:document-feature Document the credit pricing and overage charges feature of the fixture`
- eval 2: `/dev:document-system` with the eval 2 prompt from `evals.json` (scope pre-confirmed, so the Step 1 gate does not stop)

Then lint and check each expectation by hand or with a grader:

```bash
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/features            # eval 1
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/business-model/areas # eval 2
```

## When an expectation fails

Fix the skill or agent, not the expectation — unless the expectation contradicts a golden example, in which case fix whichever of the two is wrong and say why in the commit.

Goldens are illustrative (their citations point at an imagined codebase); the fixture is the executable source of the same behaviour. Where they differ in wording (e.g. the plan-name refusal text), the fixture wins for these evals.
