---
name: plan-feature
description: Use when one feature needs deciding and planning, from a system plan's prompt or on its own. Triggers "I want to add X", "plan this feature". Not for a whole system (plan-system).
---

# Plan a feature: interview, spec, plan

You describe one feature, paste a feature prompt from a system plan, or hand over a document with open questions. This skill interviews you in rounds until every decision is closed, records the project's language and hard-to-reverse decisions as they settle, writes the approved spec with its acceptance criteria and the design sections the feature needs, then writes the implementation plan Plan Queue runs. From a system plan, it writes the result back into that plan.

**Which front door.** The library has two, and they do not overlap:

| | `/product:plan-feature` (this skill) | `/product:plan-system` (`solution-planner`) |
|---|---|---|
| The input | **One feature**: a system plan's feature prompt, a feature described in words, or a spec, design or plan with open questions | A vision for a whole system, in a new or an existing repo |
| The question | *How* should this feature work, and in what tasks is it built | *What* is the system, what does every feature bind to, and which features make it up |
| The output | `docs/specs/NNN-<feature>-design.md` and `docs/plans/NNN-<feature>.md`, or the answers written back into the document | `docs/plans/<NNN>-<system>-system.md`, one `/product:plan-feature` prompt per feature |

When a described ask turns out to be several capabilities, or a whole system, stop before the first question and tell the user to type `/product:plan-system`; each feature it lists comes back here as a prompt.

**No implementation before an approved design.** Write no code, scaffold nothing and start no implementation skill until the user has approved a design, however small the change: a todo list, a one-function utility and a config change each get a design of a few sentences. A step-by-step agent that runs its own design approval (the `fe-blazor` build, the `qa-*` orchestrators) already satisfies this.

## The three modes

Pick the mode from the input before the first question.

| Mode | Input | Runs | Output |
|---|---|---|---|
| **SYSTEM** | `F<n> of <system plan path>`, the first line of a feature prompt | steps 1–10 | the spec, the implementation plan, then the system plan's close-out |
| **NEW** | One feature described in words | steps 1–10, no write-back | the spec and the implementation plan |
| **SHAPED** | A spec, a design or a plan with open questions | steps 1–6 | each answer written back into the document it came from: a plan's `## Answered questions (YYYY-MM-DD)` as `**O<n> — <question>: <answer>.**` (plan-format §2), a spec's `## Decisions from the interview` |

**SYSTEM mode reads the system plan, not the whole repo's history.** In step 1 read its §2 (vision and scope), §3 (the skeleton), §5 (features side by side), `## Decisions` and your feature's task block, plus the `As built` notes of the features it depends on and the specs they name. **§3 and the decisions are settled.** Build on them; never re-ask them. A question whose answer would change one goes to the user worded as "this changes the system plan's D<n> (or §3's <line>): keep it or change it?", and a change the user approves is recorded by the close-out, not by editing §3 now. A feature task block carrying `**On hold (…)**` names a spec draft: read it, mark every decision it settled as answered, and resume from its open question.

## Procedure

1. **Orient.** Read the files, the docs and the recent commits that the feature touches; in SYSTEM mode first read the system plan as above. When they exist, read `docs/business-model/glossary.md` and the titles in `docs/adr/`. Read `product/skills/domain-modeling/SKILL.md`: step 5 applies it in every round. Then draw the **decision tree**: every decision the feature needs, each branching into the decisions that depend on it. A decision is **open** until you answer it, and **blocked** while a decision above it is open; a decision the system plan settled is neither, it is given. Before the first round, check the scope: a request naming several independent subsystems goes to `/product:plan-system` now, before any question is spent on it. Done when every decision you can see is on the tree, marked open, blocked or given.

2. **Ask the frontier, one round at a time.** The **frontier** is every open decision that is not blocked. Ask it as one round, each question with a recommended answer, then stop and wait for the answers.
   - **With a multiple-choice question tool** (AskUserQuestion): at most 4 questions per round, 2–4 options each, the recommended option first with `(Recommended)` at the end of its label. A frontier larger than 4 is split across consecutive rounds, and the decisions that unblock the most go first.
   - **Without one:** a numbered text round, one entry per question, separated by `---`:

     ```markdown
     **Q1 — Who can cancel a booking:** Members cancel their own; staff cancel anyone's. Should a member also cancel a booking made on their behalf by staff?
     ➡️ Yes: the member owns every booking in their name, whoever made it.
     ```

   Word every question so that "yes" accepts the recommendation. A question that depends on another one in the same round waits for the next round. Done when the round is asked and every answer to it is in.

3. **Facts are yours to find.** Look up what the repo, the docs or a tool can tell you, and put only choices, priorities and constraints to the user. A slow lookup runs as a read-only subagent where the session allows one; only the questions downstream of it wait, and the rest of the frontier is asked now. A fact that cannot be found becomes a question like any other. Done when no question in the round has an answer you could have looked up.

4. **Restate and redraw.** After each round, one line per answer: the answer, the branch it closes, and the branches it opens ("Single tenant → closes *isolation model*; opens *per-tenant config*"). An answer that contradicts an earlier one is a new question: which one stands. Redraw the tree and return to step 2 while the frontier is not empty. Done when every answer of the round has its line and the tree is redrawn.

5. **Domain language, inline.** In every round, apply `domain-modeling` (read in step 1): challenge a term that conflicts with the glossary, sharpen a fuzzy term into a canonical one, probe a boundary with a concrete scenario, check the code against what you are told, write each settled term to the glossary the moment it settles, and offer an ADR only when its three tests hold. Done when every term settled in the interview has its glossary row and every offered ADR is written or declined.

6. **Close the interview.** Read the answers back as one list (question → answer → branches closed) and ask the user to confirm that nothing is left assumed. In SHAPED mode, write each answer back into the document it came from (the table in "The three modes") and stop there. Done when the frontier is empty, the user has confirmed, and, in SHAPED mode, every answer is written back.

7. **Propose 2–3 approaches.** Each with its trade-offs; lead with the one you recommend and say why. Done when the user has picked one.

8. **Present the design, section by section.** Scale each section to its complexity: a few sentences when it is plain, up to 300 words when it is not. Ask after each section whether it holds, and go back to it when it does not. Cover the architecture, the components, the data flow, error handling and testing (the design rules below). Then, for each design skill the feature needs, read its `SKILL.md` by path, apply it, and present what it produces as one more section of this spec, never as a file of its own:

   | Skill | Read when the feature | Spec section |
   |---|---|---|
   | `product/skills/data-model-plan/SKILL.md` | adds or changes stored data | `## Data model` |
   | `product/skills/experience-plan/SKILL.md` | adds or changes a screen or a journey | `## Experience`, with its `### Rendering plan` |
   | `product/skills/api-surface-plan/SKILL.md` | adds or changes an endpoint; after the data model | `## API surface` |
   | `product/skills/integration-plan/SKILL.md` | depends on a service outside the system | `## Integrations` |

   A section the feature does not need is left out, never written empty. Done when the user has approved every section.

9. **Write the spec and get it approved.** Write the spec (Output format), commit it on the current branch, then self-review it: no placeholder, no section contradicting another, a scope one implementation plan can hold, every acceptance criterion checkable by a tester, every behaviour in the design covered by a criterion, and no requirement that reads two ways (pick one and say so). Fix what you find inline. Then ask the user to review it: "Spec written and committed to `<path>`. Review it and tell me what to change before the implementation plan is written." Apply changes and repeat the self-review until the user approves. Done when the user has approved the committed spec.

10. **Write the implementation plan, then close out.** Read `product/skills/writing-plans/SKILL.md` and follow it, with the approved spec as its input and its `## Acceptance criteria` as the basis of the plan's `TD` and `Q` tasks. In NEW mode, commit the plan and stop. In SYSTEM mode, run the system plan's own `## Close-out — every feature`: it commits the plan with the system plan's edits (`As built`, the later features' briefs and prompts, `**Status:**`, and your row's `State` set to `specced (plan <NNN>)`), and only then, in a follow-up commit `docs: delete F<n>'s prompt (<system plan>)`, deletes your feature's prompt block. Done when the plan is committed and, in SYSTEM mode, every close-out step has run.

## On hold

The user can stop at any round ("put this on hold", "park it"). Write the answers so far into the spec draft at its `docs/specs/` path, with `**Status:** on hold` in the header and the open question that stopped it. In SYSTEM mode, run the on-hold half of the system plan's `## Close-out — every feature`: the dated `**On hold (YYYY-MM-DD):** <reason> — spec draft <path>` line on the feature's task block, its `State` set to `on hold`, the `**Status:**` line rewritten, the prompt block kept, and everything committed together. In NEW mode, commit the draft and say where it is. Pasting the prompt again, or naming the draft, resumes from it.

## Design rules

- **Small, well-bounded units.** Each unit has one purpose, a defined interface, and can be understood and tested without reading its internals. For each one, say what it does, how it is used and what it depends on. A unit you cannot describe that way needs better boundaries.
- **Scope and patterns follow `CLAUDE.md`:** "Simplicity (KISS)" for what stays out, and the read-2–3-existing-files rule ("Backend code rules") for matching the codebase. The design-specific part: where existing code stands in the way of the work (a file grown too large, a tangled responsibility), include a targeted improvement in the design, and leave unrelated refactoring out.

## Output format

`docs/specs/NNN-<feature>-design.md`, resolved against the project the session is working in, never this skills-library checkout or a global config directory unless the user asks for a global copy. `NNN` is zero-padded and scoped to `docs/specs/`: the highest existing prefix plus one, `001` when the folder is empty or absent. A user preference for the spec location wins.

```markdown
# Booking cancellation Design

**Date:** 2026-11-20 · **Written by:** `/product:plan-feature`
**System plan:** docs/plans/021-gym-system-system.md F3

## Goal
## Architecture
## Components
## Data flow
## Error handling
## Testing
## Acceptance criteria
- **AC1** — A member cancels their own booking more than 24 h before the session; the seat is released and the booking shows as cancelled.
- **AC2** — A member cancelling inside 24 h is told no refund applies before confirming.
## Data model
## Experience
### Rendering plan
## API surface
## Decisions from the interview
- Who can cancel a booking → the member and staff; a member cancels a booking staff made for them → closes *ownership*, opens *staff audit trail*
- Refund on late cancellation → none inside 24 h → closes *refund policy*
## Prototype
```

- **`**System plan:**`** names the system plan and the feature id, in SYSTEM mode only.
- **`## Acceptance criteria`** holds `AC1…ACn`, each one condition a tester can mark met or not met, in the user's words. The plan's `TD` and `Q` tasks cite them as `<spec path> AC<k>`; an id is never renumbered once the plan cites it.
- **The design sections** (`## Data model`, `## Experience`, `## API surface`, `## Integrations`) appear only when step 8 read their skill; the example has no integration.
- `## Decisions from the interview` holds one line per answer, in step 6's read-back order. `## Prototype` holds the chosen variant and why, when a prototype was made; leave the heading out otherwise.
- **A draft on hold** adds `**Status:** on hold — <the open question>` under the date line.

**Branch boundary:** commit the spec and the plan on the current branch, even on `main`; neither is implementation. Writing them creates no branch and no worktree. Plan Queue runs the plan later, in its own worktree.

## Showing something visual

The interview is text by default. When the user asks to *see* a screen ("mock that up", "show me the layouts side by side"), they type `/design:prototype` when the `design` plugin is enabled; without it, use the Artifact tool for the mockup or diagram. A question *about* a UI topic ("what does personality mean here?") is answered in text.

## When to use

- You paste a feature prompt from a system plan: `/product:plan-feature F3 of docs/plans/021-gym-system-system.md — …`.
- You describe one feature and want it decided, specced and planned before code: "I want to add X", "plan this feature".
- A spec, design or plan has open questions and you want every one closed: "grill me on this", "what am I missing?".

## When NOT to use

- The ask is a whole system or spans several capabilities: `/product:plan-system`.
- The question has a factual answer in the repo, the docs or a tool: look it up.
