---
name: plan-feature
description: Use when one feature needs deciding and planning, from a system plan's prompt or on its own. Triggers "I want to add X", "plan this feature". Not for a whole system (plan-system).
---

# Plan a feature: interview, spec, plan

You describe one feature, Plan Queue runs a feature prompt from a system plan (or you paste one), or you hand over a document with open questions. This skill interviews you in rounds until every decision is closed and no question about the feature is open, records the project's language and hard-to-reverse decisions as they settle, writes the approved spec with its acceptance criteria and the design sections the feature needs, then writes the implementation plan Plan Queue runs: a plan ready to implement, with no open question in it. From a system plan, it writes the result back into that plan.

**Which front door.** The library has two, and they do not overlap:

| | `/product:plan-feature` (this skill) | `/product:plan-system` (`solution-planner`) |
|---|---|---|
| The input | **One feature**: a system plan's feature prompt, a feature described in words, or a spec, design or plan with open questions | A vision for a whole system, in a new or an existing repo |
| The question | *How* should this feature work, and in what tasks is it built | *What* is the system, what does every feature bind to, and which features make it up |
| The output | `docs/specs/NNN-<feature>-design.md` and `docs/plans/NNN-<feature>.md`, or the answers written back into the document | `docs/plans/<NNN>-<system>-system.md`, one `/product:plan-feature` prompt per feature, run by Plan Queue |

When a described ask turns out to be several capabilities, or a whole system, stop before the first question and tell the user to type `/product:plan-system`; each feature it lists comes back here as a prompt.

**No implementation before an approved design.** Write no code, scaffold nothing and start no implementation skill until the user has approved a design, however small the change: a todo list, a one-function utility and a config change each get a design of a few sentences. A step-by-step agent that runs its own design approval (the `fe-blazor` build, the `qa-*` orchestrators) already satisfies this.

## The three modes

Pick the mode from the input before the first question.

| Mode | Input | Runs | Output |
|---|---|---|---|
| **SYSTEM** | `F<n> of <system plan path>`, from the `Skill:` line of a feature prompt or typed after the command | steps 1–10 | the spec, the implementation plan, then the system plan's close-out |
| **NEW** | One feature described in words | steps 1–10, no write-back | the spec and the implementation plan |
| **SHAPED** | A spec, a design or a plan with open questions | steps 1–6 | each answer written back into the document it came from: a plan's `## Answered questions (YYYY-MM-DD)` as `**O<n> — <question>: <answer>.**` (plan-format §2), a spec's `## Decisions from the interview` |

**SYSTEM mode reads the system plan, not the whole repo's history.** In step 1 read its §2 (vision and scope, `### The product, in plain words` first), §3 (the skeleton), §5 (features side by side), `## Decisions`, `## Open questions` and your feature's task block, plus the `As built` notes of the features it depends on and the specs they name. Every `## Open questions` row naming your feature under `Blocks` goes on the decision tree as open and is asked in the interview. A feature it depends on that has no `As built` note and is not in your §5 row's `Refined beside` is not specced yet: say so, name the feature to paste first, and ask whether to go on regardless. **§3 and the decisions are settled.** Build on them; never re-ask them. A question whose answer would change one is a direction question: worded by what it changes for a person, with "this changes the system plan's D<n> (or §3's <line>)" in its read-back line, and a change the user approves is recorded by the close-out, not by editing §3 now. A feature task block carrying `**On hold (…)**` names a spec draft: read it, mark every decision it settled as answered, and resume from its open question.

## Procedure

1. **Orient.** Read the files, the docs and the recent commits that the feature touches; in SYSTEM mode first read the system plan as above. When they exist, read `docs/business-model/glossary.md` and the titles in `docs/adr/`. Read `product/skills/domain-modeling/SKILL.md`: step 5 applies it in every round. Then draw the **decision tree**: every decision the feature needs, each branching into the decisions that depend on it, each marked **direction** or **engineering** (`## Direction questions and engineering calls`). A decision is **open** until it is answered, and **blocked** while a decision above it is open; a decision the system plan settled is neither, it is given. Before the first round, check the scope: a request naming several independent subsystems goes to `/product:plan-system` now, before any question is spent on it. Done when every decision you can see is on the tree, marked open, blocked or given, and direction or engineering.

2. **Ask the frontier, one round at a time.** The **frontier** is every open direction decision that is not blocked. Ask it as one round, each question in plain words with a recommended answer, then stop and wait for the answers.
   - **Frame first.** The first round opens with the framing, at most five plain sentences: what the feature gives which person (in SYSTEM mode, the journey in `### The product, in plain words` it serves, or the feature's brief when the system plan has none), what is in and out, how many direction questions follow, and that engineering calls are taken and listed for review. The round's first question confirms the framing; a correction redraws the tree before the next round.
   - **With a multiple-choice question tool** (AskUserQuestion): at most 4 questions per round, 2–4 options each, the recommended option first with `(Recommended)` at the end of its label. A frontier larger than 4 is split across consecutive rounds, and the decisions that unblock the most go first.
   - **Without one:** a numbered text round, one entry per question, separated by `---`:

     ```markdown
     **Q1 — Who can cancel a booking:** Members cancel their own; staff cancel anyone's. Should a member also cancel a booking made on their behalf by staff?
     ➡️ Yes: the member owns every booking in their name, whoever made it.
     ```

   Word every question so that "yes" accepts the recommendation. A question that depends on another one in the same round waits for the next round. Done when the round is asked and every answer to it is in.

3. **Facts and engineering calls are yours.** Look up what the repo, the docs or a tool can tell you, decide each engineering call with the answer you would have recommended and record it for `## Engineering calls`, and put only direction questions to the user. A slow lookup runs as a read-only subagent where the session allows one; only the questions downstream of it wait, and the rest of the frontier is asked now. A fact that cannot be found becomes a question like any other. Done when no question in the round has an answer you could have looked up or is an engineering call.

4. **Restate and redraw.** After each round, one line per answer: the answer, the branch it closes, and the branches it opens ("Single tenant → closes *isolation model*; opens *per-tenant config*"). An answer that contradicts an earlier one is a new question: which one stands. Redraw the tree and return to step 2 while the frontier is not empty. Done when every answer of the round has its line and the tree is redrawn.

5. **Domain language, inline.** In every round, apply `domain-modeling` (read in step 1): challenge a term that conflicts with the glossary, sharpen a fuzzy term into a canonical one, probe a boundary with a concrete scenario, check the code against what you are told, write each settled term to the glossary the moment it settles, and offer an ADR only when its three tests hold. Done when every term settled in the interview has its glossary row and every offered ADR is written or declined.

6. **Close the interview.** Read the answers back as one list (question → answer → branches closed), then the engineering calls as a second list, one line each in plain words, and ask the user to confirm that nothing is left assumed and to name any call to revisit. Each named call goes back to step 2 as a direction question. In SHAPED mode, write each answer back into the document it came from (the table in "The three modes") and stop there. Done when the frontier is empty, the user has confirmed, and, in SHAPED mode, every answer is written back.

7. **Propose 2–3 approaches.** Each with its trade-offs; lead with the one you recommend and say why. Done when the user has picked one.

8. **Present the design, section by section.** Scale each section to its complexity: a few sentences when it is plain, up to 300 words when it is not. Ask after each section whether it holds, and go back to it when it does not. Cover the architecture, the components, the data flow, error handling and testing (the design rules in [`references/spec-format.md`](references/spec-format.md)). Then, for each design skill the feature needs, read its `SKILL.md` by path, apply it, and present what it produces as one more section of this spec, never as a file of its own:

   | Skill | Read when the feature | Spec section |
   |---|---|---|
   | `product/skills/data-model-plan/SKILL.md` | adds or changes stored data | `## Data model` |
   | `product/skills/experience-plan/SKILL.md` | adds or changes a screen or a journey | `## Experience`, with its `### Rendering plan` |
   | `product/skills/api-surface-plan/SKILL.md` | adds or changes an endpoint; after the data model | `## API surface` |
   | `product/skills/integration-plan/SKILL.md` | depends on a service outside the system | `## Integrations` |

   A section the feature does not need is left out, never written empty. Done when the user has approved every section.

9. **Write the spec and get it approved.** Write the spec (`## The spec`), commit it on the current branch, then self-review it: no placeholder, no section contradicting another, a scope one implementation plan can hold, every acceptance criterion checkable by a tester, every behaviour in the design covered by a criterion, and no requirement that reads two ways (pick one and say so). Fix what you find inline. Then ask the user to review it: "Spec written and committed to `<path>`. Review it and tell me what to change before the implementation plan is written." Apply changes and repeat the self-review until the user approves. Done when the user has approved the committed spec.

10. **Write the implementation plan, then close out.** Read `product/skills/writing-plans/SKILL.md` and follow it, with the approved spec as its input and its `## Acceptance criteria` as the basis of the plan's `TD` and `Q` tasks. Ask whatever it leaves open (Ready for implementation) before committing. In NEW mode, commit the plan and stop. In SYSTEM mode, run the system plan's own `## Close-out — every feature`: it commits the plan with the system plan's edits (`As built`, the later features' briefs and prompts, `**Status:**`, and your row's `State` set to `specced (plan <NNN>)`), and only then, in a follow-up commit `docs: delete F<n>'s prompt (<system plan>)`, deletes your feature's prompt block. Done when the plan is committed with no open question and, in SYSTEM mode, every close-out step has run.

## Direction questions and engineering calls

Every decision on the tree is one of two kinds.

| Kind | What it decides | Who answers |
|---|---|---|
| **Direction** | What a person sees, does or is told; which users, cases and adopters are in or out; a policy or business rule; a risk, cost or dependency the decision-maker carries; anything that changes the system plan's §2 or a decision | The user, in the rounds |
| **Engineering** | How the feature works inside: a library, a protocol detail, a data format, an algorithm, an order of calls, a retry, refresh or cache policy, a name in code | You, with the answer you would have recommended, listed for review at step 6 |

- **A direction question is in plain words.** The question and each option say what a person sees, does, risks or pays. Identifiers from the code, libraries, protocols and decision ids go in the read-back line after the answer. A decision you cannot word that way is an engineering call.
- **An engineering call that is hard to reverse and moves cost or risk onto the user** is asked as a direction question, worded by its consequence ("every user signs in again after each release"), never by its mechanism.

## Ready for implementation

The implementation plan is the output, and it is written only when nothing about the feature is left to ask.

- **Steps 7–10 can reopen the interview.** A question that surfaces while choosing the approach, presenting a section, reviewing the spec or writing the plan goes to the user as one more round (step 2) before the work it blocks continues. It is never parked in the spec or the plan as an assumption the user has not seen.
- **The plan is committed with no open question.** Where `writing-plans` would write an `## Open questions` row, ask it instead and record the answer under `## Answered questions (YYYY-MM-DD)`. The committed plan's `## Open questions` says `None.`
- **Under Plan Queue the interview is still the task.** A queued session is told to make the reasonable call rather than ask. That holds for engineering calls only: every direction decision on the tree is the user's, asked with AskUserQuestion and waited for in the task's session.
- **A question the user cannot answer now** (it waits on someone else, or on a fact nobody has yet) puts the feature on hold, below. No implementation plan is written for a feature with an open question.

## On hold

The user can stop at any round ("put this on hold", "park it"). Write the answers so far into the spec draft at its `docs/specs/` path, with `**Status:** on hold` in the header and the open question that stopped it. In SYSTEM mode, run the on-hold half of the system plan's `## Close-out — every feature`: the dated `**On hold (YYYY-MM-DD):** <reason> — spec draft <path>` line on the feature's task block, the open question written into the system plan's `## Open questions`, its `State` set to `on hold`, the `**Status:**` line rewritten, the prompt block kept, everything committed together, and, under a queue, the closing line `PLAN_QUEUE: BLOCKED F<n> on hold: <reason>`. In NEW mode, commit the draft and say where it is. Running the prompt again, or naming the draft, resumes from it.

## The spec

Step 9 writes it, and a draft on hold, in the shape of [`references/spec-format.md`](references/spec-format.md): its path, sections and a filled example.

**Branch boundary:** commit the spec and the plan on the current branch, even on `main`; neither is implementation. Writing them creates no branch and no worktree. Plan Queue runs the plan later, in its own worktree.

## Showing something visual

The interview is text by default. When the user asks to *see* a screen ("mock that up", "show me the layouts side by side"), they type `/design:prototype` when the `design` plugin is enabled; without it, use the Artifact tool for the mockup or diagram. A question *about* a UI topic ("what does personality mean here?") is answered in text.

## When to use

- Plan Queue runs a feature prompt from a system plan, or you type its `Skill:` line: `/product:plan-feature F3 of docs/plans/021-gym-system-system.md — …`.
- You describe one feature and want it decided, specced and planned before code: "I want to add X", "plan this feature".
- A spec, design or plan has open questions and you want every one closed: "grill me on this", "what am I missing?".

## When NOT to use

- The ask is a whole system or spans several capabilities: `/product:plan-system`.
- The question has a factual answer in the repo, the docs or a tool: look it up.
