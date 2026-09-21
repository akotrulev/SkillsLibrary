# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan is complete, matches the spec, and has proper task decomposition.

**Dispatch after:** The complete plan is written.

```
Task tool (general-purpose):
  description: "Review plan document"
  prompt: |
    You are a plan document reviewer. Verify this plan is complete and ready for implementation.

    **Plan to review:** [PLAN_FILE_PATH]
    **Spec for reference:** [SPEC_FILE_PATH]
    **The format the plan must be in:** engineering-practices/writing-plans/references/plan-format.md

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Grounding | `## 1. What already exists, and what is missing` exists; every row traces to a task and every task back to a row |
    | Completeness | TODOs, placeholders, "similar to <id>", incomplete tasks |
    | Spec Alignment | Plan covers spec requirements, no major scope creep |
    | Task Decomposition | Tasks have clear boundaries; the bullets are concrete and checkable |
    | Deliverables | Every task states one deliverable, and it is a result rather than an activity |
    | Stack & agent | Every task names exactly one stack and exactly one agent, and they match |
    | Budget | Every task carries a `Budget:` with itemized drivers; the task table agrees |
    | Gate | Exactly one task carries the gate, it is the last runnable one, its commands are the project's own and in run order, and it is told to fix what it finds. Every other task says `Gate: none` and names what not to run |
    | Order | Read top to bottom: could each task actually be started at its position? Every `Depends on` points backwards |
    | Prompts | One block per task that has not landed, each with its reading list (sections, not artifacts), its traps and its gate line. Each `Blocked on <id>` placeholder is matched by a bullet on that task |
    | Buildability | Could an engineer follow this plan without getting stuck? |

    ## Calibration

    **Only flag issues that would cause real problems during implementation.**
    An implementer building the wrong thing or getting stuck is an issue.
    Minor wording, stylistic preferences, and "nice to have" suggestions are not.

    Approve unless there are serious gaps — missing requirements from the spec,
    contradictory steps, placeholder content, or tasks so vague they can't be acted on.

    ## Output Format

    ## Plan Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [<task id> / <section>]: [specific issue] - [why it matters for implementation]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
