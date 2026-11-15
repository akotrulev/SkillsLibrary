# doc-business-model evals

Regression evals for `dev:doc-business-model`, run through `be-feature-documenter` (evals 1, 4, 5, 6) and `be-documenter` (eval 2 in FULL mode, eval 3 as a plan-writing run).

| # | Agent and run | Protects against |
|---|---|---|
| 1 | `be-feature-documenter`, screenshots waived | A feature guide that is not the contract's shape, takes facts from a golden, or cannot be understood by its three readers |
| 2 | `be-documenter`, FULL, one area, scope and split pre-confirmed, screenshots waived | The same for an area guide, plus the overview, `INDEX.md` and the KB models |
| 3 | `be-documenter`, FULL, two sessions confirmed | A documentation plan that is not runnable, or that documents anything in the survey session |
| 4 | `be-feature-documenter`, no environment and no waiver | Blocking on screenshots, a guide without `pending`, an image invented without a screen, the app being started |
| 5 | `be-feature-documenter` as `DOC1` of a delivery plan with stories | A purpose not taken from a story, a story the code does not do written up as built, a missing or wrong delivery note, a plan left unfiled |
| 6 | `be-feature-documenter`, a guide with two answered questions | An answer folded wrongly (or not at all), an answer the code contradicts silently accepted, a guide rewritten instead of updated |

The fixture is an API with no runnable screens, so evals 1, 2 and 6 waive the screenshots in their prompts (6 already carries the waiver in the guide); the screenshot rules themselves are covered by the lint's unit tests and the golden example.

- `fixture/` — a small .NET 8 minimal-API / EF Core codebase for the workshop-booking credits domain: plans (Basic 8 credits at £6.00, Plus 16 credits at £5.00), tiers 1/2/3, booking and cancellation endpoints, the 24-hour late-cancel rule, monthly posting, at-least-once pricing. It is the **only** source for evals 1–4. The golden examples (`../references/example-*.md`) describe the same domain over an imagined codebase and deliberately differ from the fixture in several facts.
- `fixture-delivery/` — an overlay for eval 5: `docs/plans/001-session-credits/` holding a delivery plan whose only live prompt is `DOC1`, and the initiative's `requirements.md`, `epics.md` and `stories.md` (US1–US4, AC1–AC16).
- `fixture-folding/` — an overlay for eval 6: `docs/features/001-credit-pricing-and-overage.md`, a complete guide in the current shape whose open questions hold one agreeing and one contradicted answer.
- `evals.json` — the prompts and their rule-based expectations (skill-creator format). Expectations are never line-exact. An eval that needs an overlay lists it in `files` after `evals/fixture/`; the schema has no overlay field, so the order is the instruction: copy them in that order.

This README sits outside the fixtures, so the agent under test never sees it.

**Why overlays, not stories inside `fixture/`.** A standalone run now searches `docs/plans/**` for stories. Stories in `fixture/` would hand evals 1 and 2 purposes, and their expectations that no purpose is stated and that the cut-off's purpose is an open question would turn into their opposite. Keeping the plan, the stories and the existing guide in overlays leaves evals 1–4 on the bare code and lets 5 and 6 add exactly what they need.

## What is tested

- One guide per run and nothing beside it: no `.behind-the-scenes.md`, `.technical.md` or screenshots folder (unless captured); `doc-lint.py` passes.
- Shape (evals 1, 2): the first `##` is `In short` with three to five bullets; members and staff each have a `For <person>` section; the stamp comment closes the file and the visible About lines carry no id, owner, derivation, model or audience; internal ids only in the stamp; the fixture has no member screen, so member tasks carry no `**Where:**` and no bold label, and every bold label in a staff task is a value of `staff-ui.en.json`; `Rules and limits` holds every rule with `Where you meet it`; formulas sit under `How it is calculated` and the task keeps its `**Example**`; automatic work is `**When:**` / `**What people notice**`; the diagram is a `flowchart LR` because the fixture shows no status; no `Related areas`.
- Content: exact numbers, a worked example whose overage arithmetic uses fixture values and is correct, client vocabulary, the quoted refusal texts, no code nouns, no tier tags, no judging words.
- Defects (the fixture has some, deliberately not listed here) go to the run's report for `code-auditor`, never into the guide.
- **Golden-copy detectors.** The expectations prefixed `Golden-copy check:` hold only for a guide traced from the fixture and fail for one copied from the golden: fixed tier costs, no way to set a personal overage rate, the Plus plan, no way for staff to cancel one member's booking, and a refusal text with no full stop.
- **Comprehension (evals 1, 2 and the delivery note in 5).** Eight questions the three readers would ask, each with the one correct answer the fixture's code fixes: a Basic member out of credits books a Masterclass (£18.00, charged on the 1st); a Plus member's Workshop (1 credit, £5.00); a cancellation 20 hours ahead; one exactly 24 hours ahead; staff cancelling a session; who changes the overage rate, where, and from when; unused credits at month end; what a member sees on the 1st. The fixture file and line that fix each answer are in the expectation's grader note, never in the question. Beside them: no term the guide leaves unexplained (the grader lists any), the `In short` bullets alone tell a product owner the rules with their numbers, and every numeric rule a task states is a row of `Rules and limits`.
- Eval 2 only: `system-overview.md` exists without retired siblings and has the overview's shape, `INDEX.md` has the credits line in its shape, the KB models carry `file:line` evidence tiered `#observed` / `#inferred`, and one comprehension question is answered from the overview alone.
- Eval 3 only: one plan in `docs/plans/` in the library's plan format (`engineering-practices/writing-plans/references/plan-format.md`, shaped by `backend/_shared/codebase-survey/references/documentation-plan.md`) — tasks A1, A2 and K1 in sequence, machine-readable prompt headings and first lines, the close-out section, the screens line (ask once, never block) — no area documented in the survey session, and the environment named but never its address or logins.
- Eval 4 only: the agent asks once for the environment and logins and does not stop; the guide is written in full with `**Screenshots:** pending —`, no image; the lint's only finding is `screenshots-pending`; the report says what the capture pass needs; the app is never built or started.
- Eval 5 only: the stories are read as the source of purpose (the cut-off's purpose is stated, no open question asks it, `stories:` in the stamp, no story id in the body); the delivery note is at `docs/deliveries/001-session-credits.md` in the contract's shape, its `New` rows link real guide tasks, and `Not delivered` holds exactly the three planted differences — **US3 AC12** (personal rate: nothing sets it), **US4 AC14** (built differently: charged on the 1st, not the last day) and **US4 AC16** (roll-over: credits are lost) — while the plan's own B2 `As built` line overstates ("US3 and US4 covered"), so a run that trusts it fails; the close-out is done as the plan format says (As built, Status, prompt deleted, whole folder moved to `implemented/`, two commits).
- Eval 6 only: Q1 (answer agrees with the code) is folded into the body as one sentence and its row removed, its id never reused; Q2 (answer the code contradicts) stays with its answer and the report escalates both readings; the guide is updated in place (same file, same `**Created:**`, `**Last updated:**` added, the stamp's sha is the run's HEAD); `Answers folded: 1`.

**How the comprehension expectations are graded.** The grader is given the produced guide (or the overview, or the delivery note, as each question says) and nothing else: not the fixture, not the report, not the agent's reasoning. It answers each question from that text and compares with the expectation's `Correct:` answer; a document that does not say, or says it differently, fails. Only then does it read the grader note to see where the answer comes from. A failure means the guide cannot be understood by its reader, which is a defect of the guide even when every fact in it is true.

## How to run

```bash
E=<library>/backend/_shared/business-documentation/evals
W=$(mktemp -d) && cp -R "$E/fixture/." "$W" && cd "$W"
git init -q && git add -A && git commit -qm "fixture"
```

Each eval starts from a fresh `$W`. Open Claude Code in `$W` with the plugins enabled — evals 1, 4, 5, 6: `dev` and `be-dotnet`; eval 2: `dev`, `be-dotnet` and `business-analysis` (`be-documenter` uses its knowledge-base skills); eval 3: as eval 2 — then:

- eval 1: `/dev:document-feature` with the eval 1 prompt from `evals.json` (it carries the screenshot waiver)
- eval 2: `/dev:document-system` with the eval 2 prompt (scope and split pre-confirmed, so the survey gate does not stop)
- eval 3: `/dev:document-system` with the eval 3 prompt; it ends at the written plan — do not run the plan's prompts
- eval 4: `/dev:document-feature` with the eval 4 prompt (no waiver); it asks once and writes the guide with the screenshots pending
- eval 5: first add the overlay, then run `DOC1` as the `be-feature-documenter` agent, the way Plan Queue would, with the eval 5 prompt:

  ```bash
  cp -R "$E/fixture-delivery/." . && git add -A && git commit -qm "plan and stories"
  ```

- eval 6: first add the overlay; its stamp carries a placeholder sha, which is replaced by the fixture commit so the guide looks like one written on it. Then `/dev:document-feature` with the eval 6 prompt:

  ```bash
  SHA=$(git rev-parse --short HEAD)
  cp -R "$E/fixture-folding/." . && sed -i.bak "s/@ 0000000/@ $SHA/" docs/features/001-credit-pricing-and-overage.md && rm docs/features/*.bak
  git add -A && git commit -qm "existing guide"
  ```

Then lint and check each expectation by hand or with a grader (comprehension expectations by a grader that sees the guide only):

```bash
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/features        # evals 1, 4, 5, 6
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/business-model  # eval 2
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --dir docs/deliveries      # eval 5
python3 <library>/backend/_shared/business-documentation/scripts/doc-lint.py --kept-from "$SHA" --dir docs/features   # eval 6
```

Eval 3 has nothing to lint: read `docs/plans/*.md` and the agent's reply against its expectations. In eval 4 the only finding must be the `screenshots-pending` WARN; in eval 5 the same for `docs/features`.

The overlay guide is test data and must stay clean under the current lint: `doc-lint.py "$E"/fixture-folding/docs/features/*.md` exits 0 with no finding. Rerun it whenever the lint or the shape changes.

## When an expectation fails

Fix the skill or agent, not the expectation. A failed `Golden-copy check` means the agent took facts from a golden example instead of tracing the fixture — fix the instruction that let it, never the expectation or the fixture. A failed comprehension question means a reader of the guide would have got the answer wrong or not found it: fix what the skill says about where that fact goes, not the question. For any other expectation that contradicts a golden example in shape or tone, fix whichever of the two is wrong and say why in the commit.

Goldens are illustrations, never sources; where they differ from the fixture in any fact or wording (retries, timing, tier configuration, plans, paths, the plan-name refusal text, who can cancel a booking), the fixture wins. The overlays are test data, correct against the fixture line by line: change one only together with the expectations that quote it.
