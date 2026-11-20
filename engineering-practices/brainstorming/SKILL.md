---
name: feature
description: Use when describing a new feature or closing a plan's open questions. Triggers "I want to add X", "grill me on this". Not for a loose multi-capability ask (requirements-author).
---

# Feature: interview, then spec

You describe a feature, or hand over a document with open questions. This skill interviews you in rounds until every decision is closed, records the project's language and hard-to-reverse decisions as they settle, and, for a new feature, turns the answers into an approved spec that `dev:plan-feature` plans.

**Which front door.** The library has two, and they do not overlap:

| | `/dev:feature` (this skill) | `/dev:refine` (`requirements-author`) |
|---|---|---|
| The input | **One feature** whose requirements are clear enough to decide, or a spec, design or plan with open questions | A loose ask: the *what* is still open, or it spans several capabilities |
| The question | *How* should we build it, and what is still undecided | *What* are we building, for whom, and what is out |
| The output | `docs/specs/NNN-<feature>-design.md` → `/dev:plan-feature`, or the answers written back into the document | `docs/plans/<NNN>-<initiative>/{requirements,epics,stories}.md` → `/dev:plan-system` (`solution-planner`) |

When the ask turns out to be several capabilities, or the requirements keep moving, stop and delegate to the `requirements-author` agent, or tell the user to type `/dev:refine`. A whole initiative's task list is the `solution-planner` agent's, typed as `/dev:plan-system`.

**No implementation before an approved design.** Write no code, scaffold nothing and start no implementation skill until the user has approved a design, however small the change: a todo list, a one-function utility and a config change each get a design of a few sentences. A step-by-step agent that runs its own design gate (the `fe-blazor` build, the `qa-*` orchestrators) already satisfies this.

## The two modes

Pick the mode from the input before the first question.

| Mode | Input | Runs | Output |
|---|---|---|---|
| **NEW** | You describe a feature | steps 1–9 | the spec, then `dev:plan-feature` |
| **SHAPED** | A spec, a design or a plan with open questions | steps 1–6 | each answer written back into the document it came from: a plan's `## Answered questions (YYYY-MM-DD)` as `**O<n> — <question>: <answer>.**` (plan-format §2), a spec's `## Decisions from the interview` |

## Procedure

1. **Orient.** Read the files, the docs and the recent commits that the feature touches. When they exist, read `docs/business-model/glossary.md` and the titles in `docs/adr/`. Read `${CLAUDE_PLUGIN_ROOT}/engineering-practices/domain-modeling/SKILL.md`: step 5 applies it in every round. Then draw the **decision tree**: every decision the feature needs, each branching into the decisions that depend on it. A decision is **open** until you answer it, and **blocked** while a decision above it is open. Before the first round, check the scope: a request naming several independent subsystems goes to `requirements-author` now, before any question is spent on it. Done when every decision you can see is on the tree, marked open or blocked.

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

6. **Close the interview.** Read the answers back as one list (question → answer → branches closed) and ask the user to confirm that nothing is left assumed. In SHAPED mode, write each answer back into the document it came from (the table in "The two modes") and stop there. Done when the frontier is empty, the user has confirmed, and, in SHAPED mode, every answer is written back.

7. **Propose 2–3 approaches.** Each with its trade-offs; lead with the one you recommend and say why. Done when the user has picked one.

8. **Present the design, section by section.** Scale each section to its complexity: a few sentences when it is plain, up to 300 words when it is not. Ask after each section whether it holds, and go back to it when it does not. Cover the architecture, the components, the data flow, error handling and testing (the design rules below). Done when the user has approved every section.

9. **Write the spec, review it, and hand on.** Write the spec (Output format), commit it on the current branch, then self-review it: no placeholder, no section contradicting another, a scope one implementation plan can hold, and no requirement that reads two ways (pick one and say so). Fix what you find inline. Then ask the user to review it: "Spec written and committed to `<path>`. Review it and tell me what to change before the implementation plan is written." Apply changes and repeat the self-review until the user approves. Then invoke `dev:plan-feature`, the only skill this one hands to. Done when the user has approved the committed spec and `dev:plan-feature` is invoked.

## Design rules

- **Small, well-bounded units.** Each unit has one purpose, a defined interface, and can be understood and tested without reading its internals. For each one, say what it does, how it is used and what it depends on. A unit you cannot describe that way needs better boundaries.
- **YAGNI.** Take out every feature the stated need does not ask for.
- **In an existing codebase, follow its patterns.** Where existing code stands in the way of the work (a file grown too large, a tangled responsibility), include a targeted improvement in the design. Leave unrelated refactoring out.

## Output format

`docs/specs/NNN-<feature>-design.md`, resolved against the project the session is working in, never this skills-library checkout or a global config directory unless the user asks for a global copy. `NNN` is zero-padded and scoped to `docs/specs/`: the highest existing prefix plus one, `001` when the folder is empty or absent. A user preference for the spec location wins.

```markdown
# Booking cancellation Design

**Date:** 2026-11-20 · **Written by:** `dev:feature`

## Goal
## Architecture
## Components
## Data flow
## Error handling
## Testing
## Decisions from the interview
- Who can cancel a booking → the member and staff; a member cancels a booking staff made for them → closes *ownership*, opens *staff audit trail*
- Refund on late cancellation → none inside 24 h → closes *refund policy*
## Prototype
```

`## Decisions from the interview` holds one line per answer, in step 6's read-back order. `## Prototype` holds the chosen variant and why, when a prototype was made; leave the heading out otherwise.

**Branch boundary:** commit the spec on the current branch, even on `main`; a spec is not implementation. Writing it creates no branch and no worktree. Plan Queue runs the plan later, in its own worktree.

## Showing something visual

The interview is text by default. When the user asks to *see* a screen ("mock that up", "show me the layouts side by side"), they type `/design:prototype` when the `design` plugin is enabled; without it, use the Artifact tool for the mockup or diagram. A question *about* a UI topic ("what does personality mean here?") is answered in text.

## When to use

- You describe one feature and want it decided and specced before code: "I want to add X", "let's build X".
- A spec, design or plan has open questions and you want every one closed: "grill me on this", "what am I missing?".

## When NOT to use

- The ask is loose or spans several capabilities: delegate to the `requirements-author` agent, or type `/dev:refine`.
- The design is approved and needs a task list: `dev:plan-feature`.
- The question has a factual answer in the repo, the docs or a tool: look it up.
