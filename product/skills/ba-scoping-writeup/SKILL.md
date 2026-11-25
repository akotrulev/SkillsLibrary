---
name: scoping
description: Use when writing a system plan's §2 (vision and scope) from a vague business problem or stakeholder request. Triggers "help me scope this system". Not for epics (epics).
disable-model-invocation: true
user-invocable: false
---

# Vision and scope — the system plan's §2

Turns an ambiguous business request into **§2 of a system plan, `## 2. Vision and scope`**, and
nothing else: the ask, the product in plain words, the problem, the actors, what the system must do, constraints, success, scope,
assumptions and risks, separated and labelled so the skeleton (§3), the epics (§4) and every feature
session can be checked against them. `solution-planner` loads it for `/product:plan-system`; the file
around it is defined by `product/skills/solution-blueprint/references/system-plan-format.md`.

## Inputs needed

Ask only what is missing, in rounds of at most four questions (the harness's question tool where it
has one), each with two to four concrete options, the recommended one first, and what will be assumed
if unanswered. `solution-planner` folds these into its own interview rounds:

1. **The ask in the stakeholder's own words** (pasted verbatim where possible)
2. **Who is asking** (role and team), **who decides scope**, and who is affected
3. **What problem this solves** (the why, not the what)
4. **Known constraints**: deadlines, budget, compliance, systems that must be kept
5. **What is explicitly out of scope**, where known
6. **How we will know it worked**: a metric, a KPI or a qualitative signal

If nobody can answer "why" or "how will we know it worked", that is the first risk and the first open
question. Never invent a number to fill the gap, and never refuse to proceed: the rest of §2 is still
written.

## Eliciting the inputs

When a stakeholder can be asked, drive the discovery from this question bank rather than waiting for a
brief:

| Missing | Ask |
|---|---|
| The why | "Walk me through the last time this problem cost you something." Then five whys until the answer is a business outcome, not a feature |
| Users | "Who touches this on a bad day? Who complains when it breaks?" |
| Scope | "If we shipped only one part this quarter, which? What would you happily never get?" |
| Success | "Six months from now, what number or behaviour proves this worked?" Push for baseline → target |
| Constraints | "What is fixed: date, budget, compliance, systems we must keep?" |
| Quality targets | "On the busiest day, how many people use it at once, and how long may they wait? How long may it be down? How long must we keep the data? Which accessibility level?" A target nobody can state is an open question, never a guess |
| Risks | "What is the way this most plausibly fails or gets cancelled?" |

Walk the current workflow end to end before discussing the future one, and ask for the last concrete
instance, never the general case: "usually" hides the edge cases that become open questions.

## Procedure

1. **The product in plain words, first.** Three to five sentences anyone outside the team could read:
   what a person gets and what it is not. Then the journeys, one row each: who, what they do, what they
   end up with, in their words; `solution-planner` fills each row's features once the feature list
   exists. Then the kinds of choice the decision-maker wants put to them (what people see, who and what
   is in, the risk and cost they carry); the feature sessions decide how it works inside and list those
   calls in each spec. No code identifier, library, protocol or decision id in this subsection.
2. **Separate observation from inference.** Quote the stakeholder verbatim; attribute each constraint
   to whoever stated it; put every inference in Assumptions.
3. **The problem before any solution wording.** "Add a CSV export button" is a solution; the problem
   is the workflow it unblocks.
4. **Actors, not a stakeholder list.** Every actor has a goal, and one is named the decision-maker who
   approves scope.
5. **What it must do, as outcomes, never mechanism.** What an actor gets, business rules with their
   numbers, and quality targets with their number and who stated it. No stack, table, endpoint, screen
   or component: those are §3's or a feature spec's.
6. **Scope in three columns**: in, out (refused) and deferred (a follow-up commitment).
7. **Success is measurable or explicitly qualitative**, with a baseline → target where one exists.
8. **Risks on two axes**, likelihood and impact, each with a mitigation.
9. **Open questions are unknowns, not risks.** Each goes to the system plan's `## Open questions`
   table, naming its options, what it blocks and who can answer it.

## Output format

Ten subsections, in this order, none dropped; an empty one says why. Open questions live in the plan's `## Open questions` table.

````markdown
## 2. Vision and scope

### The ask, verbatim
> <what the stakeholder said, quoted, never paraphrased> — <who, where, when>

### The product, in plain words
<three to five sentences: what a person gets, and what it is not>

| Journey | Who | Does | Ends up with | Features |
|---|---|---|---|---|
| J1 | <actor> | <what they do, in their words> | <what they see or have afterwards> | <F ids> |

**The decision-maker is asked:** <the kinds of choice put to them>. **Feature sessions decide:** how it
works inside, listed in each spec's engineering calls for review.

### Problem and why now
<one paragraph: the problem in the business's terms, and what not doing it costs>

### Actors
| Actor | What they are trying to get done | Role |
|---|---|---|
| <role or name> | <goal> | decision-maker / primary user / contributor / informed |

### What it must do
- <capability, as an outcome an actor gets>
- <business rule, with its number: limit, window, threshold>
- Quality target: <what is measured> — <its number> — stated by <who>

### Constraints
- <regulatory / contractual / "must reuse X" / deadline> — stated by <who>

### Success
- <measure with baseline → target, or a qualitative signal and who judges it>

### Scope
| In scope | Out of scope (refused) | Deferred (follow-up) |
|---|---|---|

### Assumptions
1. <every inference made because the stakeholder did not say, one line each>

### Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| | L/M/H | L/M/H | |
````

A quality target nobody stated is written `Quality target: <what is measured> — [TBD - <who decides>]`
with an open question beside it. In an existing repo, a capability the code already has is §1's row
with no gap, not a line here.

## Standards

What §2 must and must never contain is the product rule file `system-plans.md`, not a list here. Read
the project's copy in `.claude/rules/product/`, or the plugin's in `product/skills/rules/` when the
project has not installed them (`/product:rules` does). Where they and this skill disagree, the rule
file wins.
