---
name: design-ai-experience
description: Use when designing how an AI or agent feature behaves on screen — streaming and tool-call visibility, stop/interrupt, approval-with-context, confidence display, correction, AI labelling, and the AI-specific states. Triggers "design the chat/assistant UI", "how should the agent show what it's doing", "show a confidence score?". Not for the transport (a stack's `realtime`/`data-fetching`), prompt/model work (`ai-development`), or testing an LLM feature (qa `ai-feature-testing`).
---

# AI experience — designing what the agent shows

Owns the **on-screen behaviour of AI and agent features**: what the user sees while a model is working, what they can stop, what they must approve, how sure the system claims to be, and how a wrong answer gets corrected. A CRUD screen's contract is *request → response → state*; an AI surface's is *intent → autonomous work of unknown length → a result that may be wrong* — and almost every pattern below exists because that second contract breaks assumptions the first one let you make.

The current framing from the field is worth stating plainly, because it decides what this skill optimizes for: as more interaction is mediated by assistants and agents, **the interface becomes the accountability layer between the user's intent and the system's autonomous action**. Its job is no longer only to be usable. It is to keep a person in a position to judge, correct, and stop something that is acting on their behalf.

**What this skill owns:** the patterns — progress, visibility, control, approval, uncertainty, correction, disclosure, and the AI-specific states. **What it does not own:** the transport that delivers them (a stack's `realtime` / `data-fetching` — SSE, WebSocket, streamed responses, resumable runs), the prompt/model/tool design behind them (`ai-development/claude-api`), and proving the feature works (qa `ai-feature-testing`). Design the pattern here; build it there.

**Corpus authority.** The facts this skill decides with come from the vendored [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) corpus — **it is the source of truth, and where it and this skill disagree on a fact, the corpus wins.** The AI-surface patterns below are this skill's own; the corpus supplies the general UX guidelines they sit on — streaming feedback, interruptibility, loading and empty states, focus behavior:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/design/ui-ux-pro-max/scripts/search.py" "<observable outcome>" --domain ux
```

## 1. Show the work, while it happens

The single highest-value improvement reported across agent products: **stream tool inputs and outputs inline as they occur**, rather than presenting a finished summary. A user watching a run knows whether it is going well, and can stop it when it is not.

- **A spinner is wrong for anything an agent does.** A multi-second model call gets streamed tokens; a multi-minute agent run gets a **visible timeline of steps** — the tool being called, its input, its result, in order, as they land.
- **Name the step in the user's language**, not the tool's identifier — "Searching the invoice archive", not `invoice_search(q=...)`. The raw call belongs behind a disclosure for the user who wants it.
- **A step that is still running looks different from one that finished** — and a failed step stays visible with its error rather than disappearing into a retry.
- **Long work reports progress against something real** — items processed, files scanned, steps completed of a known total. Where no total exists, say what is happening now, and never fake a percentage.
- **The transcript is the record.** When the run ends, the steps remain inspectable — collapsed by default, expandable. A result whose derivation vanished cannot be judged.

## 2. Keep the user in control

Users must feel they are driving even when the agent is doing the work — and the feeling has to be backed by controls that exist.

- **Stop is always available and always immediate.** Every streaming response and every long-running agent has a visible stop/interrupt control from the first moment, not after a threshold. Stopping leaves the partial work visible and usable, never discarded.
- **Nothing irreversible happens without an approval step** — sends, payments, deletes, external writes, anything touching another person. See §3.
- **The user can steer mid-run** where the medium allows: correct a wrong assumption, add a constraint, redirect. An agent that cannot be redirected must at least be stoppable and restartable with the correction.
- **Autonomy is a visible setting, not an implicit mode.** If the product has ask-every-time / ask-on-risk / run-freely, the current level is on screen, and changing it is one action.

## 3. Approvals carry their context

Approval requests that include the agent's accumulated context produce faster **and more accurate** human decisions than terse approve/deny prompts. A bare "Allow this action?" trains the user to click yes.

- **Show what will happen, to what, and why** — the concrete action, the specific target ("Delete invoice #4821", never "Delete item"), and the reasoning or evidence that led here.
- **Show what changes and what it costs** — the diff, the recipient, the amount, the irreversibility.
- **Offer more than two answers** where they exist: approve · approve-and-don't-ask-for-this-again · edit-then-approve · reject-with-a-reason. A reject that captures *why* is the highest-quality signal the product will ever get.
- **Batch approvals stay itemized.** Approving twelve actions at once still shows the twelve; "approve all" is a control on a visible list, never a summary standing in for one.

## 4. Say how sure it is

Opacity, inconsistency, hallucination, and lack of control are the named trust-killers. Uncertainty display is the direct answer to the first and third.

- **Signal confidence where the user must decide whether to verify** — a score, a band, or the alternatives considered ("Poison oak (80%)", with the runners-up). Calibrated hedging in the response ("I'm not certain — verify X") does the same job in conversational surfaces.
- **Cite the source, and make it reachable.** A claim with a link the user can open is checkable; the same claim without one is a request for faith.
- **Distinguish what the system knows from what it inferred.** A retrieved fact and a generated one look identical on screen unless the design makes them differ.
- **Never manufacture precision.** A percentage the model cannot support is worse than no number — it converts uncertainty into false confidence, which is the failure mode the pattern exists to prevent.

## 5. Every output is correctable

Users who know they can correct an AI are measurably more willing to engage with it — the affordance drives adoption, not just quality.

- **Edit, reject, regenerate, and flag are visible on every AI output**, not hidden in a hover menu or a feedback dialog.
- **Editing is direct.** The user changes the output in place; they do not re-prompt to get a comma moved.
- **A rejection goes somewhere.** It changes what happens next in the session, and it reaches the team as signal.
- **The user's correction survives.** A regenerate does not silently discard the edit the user just made.

## 6. Disclose that it is AI

**78%** of consumers say explicit labelling of AI-generated content matters to their trust; **31%** trust a brand *less* when they detect undisclosed AI output. Disclosure is a trust asset, not a disclaimer.

- **Label AI-generated and AI-assisted content** where a reasonable person would otherwise assume a human or a database produced it.
- **Label consistently and quietly** — one treatment, used everywhere, not a banner on one surface and nothing on another.
- **Say what the AI can see.** If the assistant reads the user's documents, messages, or screen, that is stated at the point of use, not only in a policy (`design/ethical-patterns` owns the consent mechanics).
- **Do not disguise an AI as a person** — no invented human name and avatar for a bot, no implied human review that does not happen.

## 7. The states an AI surface needs

Beyond the three-state region every data surface has (`ux-patterns`, the stack's `error-handling`), an AI surface has its own:

| State | What it must do |
|---|---|
| **Idle / first run** | Say what this assistant is *for* and show two or three real starting actions. A blank prompt box is the AI equivalent of an empty grid with no call to action |
| **Working** | §1 — streamed output or a visible step timeline, with stop always present |
| **Partial** | A stopped or interrupted run keeps what it produced, marked as incomplete, with resume or discard |
| **Low confidence** | The answer, plus the hedge and the check-this path — never suppressed into silence |
| **Refusal** | Say what will not be done and *why*, in one sentence, and offer the nearest thing that will be. A refusal is a designed response, not an error |
| **Failure** | The model or tool failed: what failed, what survived, retry scoped to the failed step — not the whole run |
| **No answer** | The system genuinely doesn't know. Say so plainly; do not fabricate, and do not return an empty state that reads as a bug |

## 8. Earn the feature

The named risk for 2026 is **AI fatigue** — on the user's side as much as the practitioner's — driven by low-value features shipped because the capability existed.

- **An AI feature needs a user job**, stated the way any other feature's is. "Summarize this" is not a job; "so the reviewer can triage fifty of these an hour" is.
- **Prefer the deterministic path where one exists.** A filter beats a model that guesses a filter — faster, cheaper, explainable, testable.
- **Latency and cost are UX.** A four-second answer to something a query answers in 40 ms is a downgrade the interface has to justify.
- **Measure the correction rate.** If users routinely edit or reject the output, the feature is generating work rather than removing it.

## Review checklist

- **Work is visible while it happens** — streamed tokens or an inline step timeline in the user's language; no bare spinner on an agent run.
- **Stop is present from the first moment** and preserves partial work.
- **Nothing irreversible executes without an approval that carries context** — the specific target, the change, the cost, the reasoning.
- **Uncertainty is expressed** where the user must decide whether to verify; sources are cited and reachable; no manufactured precision.
- **Every output can be edited, rejected, regenerated, and flagged**, in place.
- **AI-generated content is labelled** consistently; what the assistant can see is stated at the point of use; no AI wearing a human identity.
- **All seven AI states** (§7) are designed, including refusal and no-answer.
- **The feature has a stated user job**, and a deterministic alternative was considered and rejected for a reason.

## What NOT to do

- No spinner for a long agent run; no summary that hides which tools ran; no step that vanishes when it fails.
- No approve/deny with no context; no "approve all" that hides the list.
- No confidence number the model cannot support; no citation that doesn't resolve.
- No feedback buried in a menu; no regenerate that eats the user's edit.
- No undisclosed AI output, no bot with a fabricated human identity, no implied human review.
- No AI feature whose only justification is that the capability was available.

## Related

- A stack's `realtime` / `data-fetching` ([React](../../frontend/react/skills/realtime/SKILL.md)) — **the transport**: SSE/WebSocket, streamed rendering, resumable runs. This skill decides what streams; that one moves it.
- A stack's `error-handling` — the three-state region these AI states extend, and the persistent failure notification they reuse.
- [`design/ux-patterns`](../ux-patterns/SKILL.md) — the surface the assistant lives on (panel, page, or command palette), and the §9 responsiveness budget, which an AI feature meets differently: acknowledge in 100 ms even when the answer takes a minute.
- [`design/ux-writing`](../ux-writing/SKILL.md) — the assistant's voice, its refusals, and its error sentences.
- [`design/ethical-patterns`](../ethical-patterns/SKILL.md) — consent and disclosure mechanics for what the AI reads.
- [`design/accessible-by-design`](../accessible-by-design/SKILL.md) — streamed output is a live-region and cognitive-load problem; a step timeline that never stops moving is unusable for some readers.
- `ai-development/claude-api` — the model, prompt, and tool design behind the surface. qa `ai-feature-testing` — proving it works. Both peers, invoked separately.
- [`design-ui-ux-pro-max`](../ui-ux-pro-max/SKILL.md) — the general UX guideline corpus these AI-surface patterns sit on.
