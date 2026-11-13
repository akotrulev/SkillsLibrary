---
name: stories
description: Use when turning a scoped requirement or an epic into stories that say what must be built (goal, how we get there, what is included, acceptance criteria as bullets). Triggers "write the stories for X", "add acceptance criteria". Not for scoping (scoping).
---

# Story Writer

A story describes **one feature that must be built**. It says what the goal is, how we plan to get there, what has to be included, and the conditions that must be met before it counts as done. The person who asked for it, the person who builds it and the person who tests it all read the same page and come away with the same picture.

"Authentication" is a story. It includes login, reset password by email and register with confirmation, because the goal (people get into their own account, and only their own) is not reached until all three exist.

## When to use

- The requirements and epics are written and the features under them need describing
- A feature is known by name only ("we need authentication") and nobody has written down what is in it
- Existing stories lack acceptance criteria, or are fragments of one feature spread over several stories

## When NOT to use

- The requirement is still vague → `business-analysis/skills/ba-scoping-writeup` first
- Stories were authored elsewhere and need a review-only readiness audit → `business-analysis/skills/ba-story-quality-review` (this skill *fixes* stories; that one only *finds*)
- The user wants test cases → `qa/manual/test-case-writer`
- The user wants a defect filed → `qa/manual/bug-report-writer`

## Inputs needed

1. **The epics** (`epics.md` from `business-analysis:epics`, ideally) and the requirements document they cover
2. **Who each feature is for**, specifically ("a member with a confirmed account", not "the user")
3. **The business rules with their numbers** (limits, time windows, thresholds) from `requirements.md` §4, and the constraints in §5

## What makes one story

- **One feature a person would name**: "Authentication", "Booking a session", "The monthly invoice". If the title needs an "and" between two unrelated things, it is two stories.
- **One goal.** Everything in the story serves it. Two goals are two stories.
- **Whole.** Every part the goal needs is inside. A part that is no use without another belongs with it: login with no way to register is a fragment, so both sit in Authentication.
- **Never a layer.** "The API" and "the screen" are not stories. Layers and stacks are cut later, at task level, by the planner; a story stays whole.
- **Size follows the goal, not a sprint.** A story is as big as its feature. When a part could be left out and the goal would still be reached, it is a candidate for its own story or for `Not included`.

## Procedure

1. **List the features under each epic.** Every capability in `requirements.md` §4 lands in exactly one story, as an included part or as the whole story.
2. **Write the goal.** One to three sentences: who needs this, what they can do once it is built, and why that matters to them or to the business. A goal that only names the feature ("add authentication") is not a goal yet.
3. **Write how we get there.** The route, in the product's own terms: the approach chosen and what it was chosen over ("an emailed link rather than a code typed in"), what it builds on that already exists, the order the parts come in when one needs another, and any decision already taken with who took it. A reader should finish it knowing the plan, not just the destination. It carries no technology (no table, endpoint, screen, component or library); a constraint the business imposed is cited from `requirements.md` §5. The design is `solution-planner`'s.
4. **List what is included.** One bullet per part: its name, then a line or two saying what it does. Each part is something a person does or something that happens for them. Include the parts people forget because they are not the happy path: the lockout, the expired link, the "send it again".
5. **Write the acceptance criteria as bullets that must be met.** Each one is a condition that is true when the story is done, written so that someone who did not write it can mark it met or not met:
   - One situation per bullet, with what comes of it: what the person ends up with or is told, and the number where there is one. A bullet that walks through several steps ("registers, gets the email, then logs in") is one bullet per step.
   - A validation names the field, the rule and what happens when it is broken.
   - Every included part has criteria for it working **and** for what happens when it cannot (wrong input, expired, refused, already done).
   - What applies to the whole feature (security, accessibility, audit, speed) goes in a closing `Across the feature` group.
   - Numbered `AC1..ACn`, flat within the story, grouped under the part they prove. Plans and tests cite them as `US3 AC7`, so an id is never reused or renumbered; a dropped criterion keeps its id with a line saying why.
   - Not Given / When / Then. Scenarios are written from these bullets by test design.
6. **A number comes from the requirements, never from you.** Where the requirements give none, write `[TBD — <who decides>]` in its place and raise it as an open question.
7. **Say what is not included**, with the reason and where it goes (another story, deferred, refused). Readers assume anything unlisted is in.
8. **Declare dependencies** by story id. "Depends on: US3 (confirmed accounts)" beats finding out mid-build.
9. **Give every story its id and parent epic.** Ids are `US1..USn`, flat across the initiative (never restarted per epic); the parent is its `E` id. Assigned once, never renumbered. A dropped story keeps its id with a line saying why.

## Acceptance criteria — weak and met-or-not

| Weak | What is wrong | Met-or-not |
|---|---|---|
| Login works | Restates the part; nothing to check | A person with a confirmed account who enters their email and password is signed in and lands on their home page |
| The reset link is secure | No rule, no number | A reset link that has been used, or is older than 60 minutes, sets nothing; it says so and offers a new one |
| Passwords are validated | No field rule, no outcome | A password shorter than 12 characters is refused at registration and at reset, and the person is told the minimum |
| The user registers and gets an email and can then log in | Three situations in one bullet | Three bullets: the account is created unconfirmed · the confirmation email arrives within 2 minutes · the link confirms the account |
| Errors are handled gracefully | Unfalsifiable | A wrong email or password gets one message that does not say which of the two was wrong |

## Output format

```markdown
## US<n> — <the feature's name>

**Epic:** E<n>

### Goal
<Who needs this, what they can do once it is built, and why it matters. One to three sentences.>

### How we get there
<The approach in the product's own terms: the route chosen and over what, what it builds on,
the order the parts come in, decisions already taken. A short paragraph or a few bullets.
No technology.>

### What is included
- **<Part>**: <what it does, in a line or two>
- **<Part>**: <what it does>

### Acceptance criteria

**<Part>**
- **AC1** <a condition that is true when the story is done>
- **AC2** <what happens when it cannot be done>

**<Part>**
- **AC3** <…>

**Across the feature**
- **AC<k>** <security / accessibility / audit / speed, with its number>

### Not included
- <what is left out>: <why, and where it goes>

### Depends on
- US<n> (<what it provides>), or none

### Source
<the requirements.md §4 lines and business rules this story realises; never designs or contracts, those are solution-planner's>
```

A complete story in this shape, three parts and sixteen criteria: [`references/example-authentication.md`](references/example-authentication.md). Read it before writing the first story of a set.

## Standards

What every story must meet (the `US<n>` id and parent epic, one whole feature with one goal, no layer stories, the sections in order, an approach that is a plan and not a design, every included part proven by criteria, met-or-not bullets with stable `AC` ids, validations with their violation outcome, no technology, per-story exclusions and dependencies) is the business-analysis rule file `backlog-stories.md`, not a list here. Read the project's copy in `.claude/rules/business-analysis/`, or the plugin's in `business-analysis/skills/rules/` when the project has not installed them (`/business-analysis:rules` does). Where they and this skill disagree, the rule files win.

## Handoffs

- Inside the delivery lane → `requirements-author` (`/dev:refine`) runs this skill as its Step 4 and writes the output to `docs/plans/<NNN>-<initiative>/stories.md`; the `business-analyst` sweep follows when the stories change shared business rules
- Tests next → the test plan for the epic first (`qa-test-planner`, `/qa-<stack>:test-plan`: versions, what is tested, harness, scenarios, Definition of Ready and Done), then one test-case suite per story (`qa-test-case-designer`, `/qa-<stack>:test-cases`). Both start from `qa/manual/requirements-breakdown`, which distills the stories' goals, included parts, rules and validations into the test basis
- Architecture, contracts, task plan → `solution-planner` (`/dev:plan-system`)

Only `qa/manual/requirements-breakdown` ships in this plugin; the other `qa/*` peers and `solution-planner` are invoked separately, never loaded here.
