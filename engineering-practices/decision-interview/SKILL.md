---
name: decision-interview
description: Use when a design or plan has a shape and every open decision must be closed, one question at a time. Triggers "grill me on this", "poke holes in this plan". Not for a fresh idea (design).
---

# Decision Interview

Drive a design that already has a shape to a decision on every branch of it. Nothing is left silently assumed, and nothing is built until the user confirms the tree is closed.

## When to use

- The user has a design, spec draft or plan and wants it stress-tested before implementation
- A plan carries open questions that are really chains of linked decisions
- The user says "grill me", "interview me", or "what am I missing?" about something they have already shaped

## When NOT to use

- The ask is loose, or spans several capabilities, and there is no design yet — send the user to `/dev:refine` (`requirements-author`), which writes what is being built, for whom, and what is out
- The user wants approaches proposed and a design written from an idea — that is `/dev:design`; come here afterwards if branches remain open
- The question has a factual answer in the repo, the docs or a tool — look it up instead of asking

## The design tree

Treat the design as a tree: every decision branches into the decisions that hang off it. A branch is **open** until the user has answered the decision at its root. A branch is **blocked** while a decision above it is open, because asking it now means guessing the answer to the one above.

Build the first tree from what the user gave you plus what the project already says (files, docs, recent commits). Redraw it after every answer.

## The loop

1. **Pick one question.** Take the open, unblocked branch whose answer unblocks the most others. Ask only that question, one per message, never batched.
2. **Recommend an answer.** State the question, then your recommended answer with the reason in one line. Word the question so that "yes" accepts the recommendation. Prefer a multiple-choice shape when the options are finite.
3. **Wait.** The decision is the user's. Do not continue on an assumed answer.
4. **Restate.** Repeat the answer in one line together with the branch it closes and the branches it opens or unblocks ("Single tenant → closes *isolation model*; opens *per-tenant config*").
5. **Redraw and repeat** until no branch is open.

A contradiction between a new answer and an earlier one is itself a branch: ask which one stands.

## Facts are your job

Look up what the environment can tell you before asking: read the file, the config, the existing code, the doc. Ask the user only for choices, priorities, constraints and anything that exists only in their head. When a fact is missing and cannot be found, ask for it as a question like any other.

## Ending

The interview ends only when no branch is open. Then:

1. Read the resolved answers back as one list: question, answer, the branches it closed.
2. Ask the user to confirm that nothing is left assumed. Do not act before they do.
3. Hand the list on:
   - a design in progress → `/dev:design`'s approval gate
   - a plan with open questions → its `## Answered questions`, each as a dated entry

This skill writes no code, no spec and no plan; it produces decisions.

## Common mistakes

- Batching several questions into one message — the answers to later ones depend on earlier ones
- Asking a question whose answer sits in the repo
- Moving on without restating the answer and the branch it closes
- Declaring the tree closed while a restated answer still opened a branch
- Turning the interview into approach proposals — that is `/dev:design`
- Acting on the result before the user confirms the tree is closed

## Provenance

`mattpocock/skills@a496f5513d4a4cf889bc48e189e579f4b0bdf6aa` (`grilling`, `grill-me`) — MIT, adapted. The design-tree framing and the recommend-an-answer habit come from upstream. The one-question-at-a-time loop, the restatement step, the single-session rule and the hand-offs are the library's own.
