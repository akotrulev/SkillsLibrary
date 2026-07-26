---
name: design-ux-writing
description: Use when writing or reviewing the words inside a UI — button labels, error and empty-state copy, confirmations, toasts, form hints, nav names — in one consistent, active, user-side voice. The stack defines the structural slots; this supplies the voice. Triggers "what should this button say", "write the error message", "microcopy for this flow", "our UI wording is inconsistent". Not for empty-state/confirmation STRUCTURE (the stack's `ui-rules`).
---

# UX Writing — voice & microcopy

Owns the **words** in a UI and the voice they share. Interface copy is design material, not decoration: it exists to make the product easier to understand and therefore easier to use. This skill supplies the *voice*; the engineering stack owns the *slots* that voice fills — and the two are deliberately split so the copy discipline is written once and reused across stacks (Blazor, React).

**The slot/voice split — who owns what:**

| The stack skill defines the slot | This skill supplies the voice |
|---|---|
| `ui-rules` — empty-state taxonomy (no-records vs no-filter vs filter-matched-nothing), confirmations by object name, "one name → one concept, one verb per operation" IA | the actual wording of each empty state, confirm button, and label; the rule that a name persists through a flow |
| `error-resilience` — error *categorization* (ProblemDetails → friendly message + correlation id), three-state regions | how the friendly message reads: what went wrong + how to fix it, in the interface's voice |
| `generator` — *emits* the button/label/`<PageTitle>` markup | the text those emitted labels carry |

Never duplicate the structural rules back into this skill, and never restate voice rules in those skills — cross-link. `design/visual-identity` carries a design-side *summary* of this discipline (its "writing in design" section); the depth lives here.

## When to use

- Choosing what a button, link, menu item, tab, or toggle says
- Writing an error message, empty state, confirmation, toast, or form hint
- Renaming labels so one concept has one name across the whole product
- Reviewing existing copy for voice, tone, and consistency

## When NOT to use

- The visual/aesthetic direction of the page → [`design/visual-identity`](../visual-identity/SKILL.md)
- The *structure* of empty states/confirmations + IA rules → the stack's `ui-rules` ([Blazor](../../frontend/blazor/skills/ui-rules/SKILL.md) · [React](../../frontend/react/skills/ui-rules/SKILL.md))
- Error → message *mapping/categorization* mechanics → the stack's `error-resilience` ([Blazor](../../frontend/blazor/skills/error-handling/SKILL.md) · [React](../../frontend/react/skills/error-handling/SKILL.md))
- Translating copy / locale-formatting / pseudo-localization → qa `language-testing` + a localization skill

## The five rules

### 1. Write from the user's side of the screen

Name things by what people control and recognize, never by how the system is built. A person manages **notifications**, not *webhook config*; **members**, not *principals*; **your plan**, not *the subscription entity*. Describe what a thing does in plain terms rather than selling it. Being specific always beats being clever — "Delete 3 invoices" over "Proceed."

| System-side (avoid) | User-side (use) |
|---|---|
| "Submit" | "Save changes" / "Send invite" / "Publish" |
| "Invalid input" | "Enter an email address like name@company.com" |
| "Operation failed" | "Couldn't save — check your connection and try again" |
| "No data" | "No invoices yet. Create your first one." |
| "Authentication error (401)" | "Your session expired. Sign in to continue." |

### 2. Active voice, and a control says what it does

A control names the action that happens when it's used: **"Save changes," not "Submit."** The label describes the effect, not the mechanism. Verbs, not nouns, for actions ("Add member," not "New member" on a button).

### 3. A name persists through the whole flow

The vocabulary of an interface is the signposting people use to learn their way around, so an action keeps **one name from trigger to result**:

- A **"Publish"** button produces a **"Published"** toast — never a "Post" button that yields a "Your content is now live" message.
- The label in a nav, the page `<PageTitle>`, the breadcrumb segment, and the heading for the same destination all match.
- One concept has one name app-wide (this is the copy face of `ui-rules`' "one name → one concept, one verb per operation" IA rule — same principle, applied to the words).

Renaming for consistency is high-leverage: a single concept called three things ("Client" / "Customer" / "Account") across screens makes the product feel like three products.

### 4. Failure and emptiness are direction, not mood

- **Errors** explain **what went wrong and how to fix it**, in the interface's voice — not a person's. They don't apologize ("Sorry!"), don't blame the user, and are never vague. Structure: *what happened → what to do → (optional) a reference id for support.* `error-resilience` categorizes the error and hands you a friendly slot + correlation id; you write the sentence. Example: *"Couldn't upload — the file is over 10 MB. Try a smaller file."* (id shown quietly for support, never as the whole message).
- **Empty states are invitations to act**, and they match the three cases `ui-rules` distinguishes:
  - *Nothing created yet* → invite + primary action: "No projects yet. Create your first project."
  - *A filter matched nothing* → say so + offer to clear: "No results for 'archived'. Clear filters."
  - *Genuinely empty by design* → a calm statement, no false call to action.
  Never leave a blank region — an empty grid is indistinguishable from a broken one.

### 5. Register: conversational, tuned, one job per element

Plain verbs, **sentence case** (not Title Case or ALL CAPS), no filler ("please," "simply," "just"), tone matched to the brand and audience. Let each element do exactly one job — a label labels, a hint demonstrates, a tooltip clarifies; nothing quietly does double duty. Be concise: cut every word that doesn't help the person navigate.

- **Front-load the distinguishing word.** People scan; the word that tells them apart comes first — "Pricing", not "Our pricing options"; "To reset your password…", not "In order to reset…". This is the copy face of the IA rule that nav/section labels lead with content, not org structure.
- **Personality lives in low-stakes moments only.** A little voice is welcome in empty states, success toasts, and onboarding; it is out of place in errors, payments, and destructive confirmations, where the user's goal beats brand voice every time.

### 6. Write so it works without sight or position

Copy is read aloud by screen readers and out of visual context — never lean on color, shape, or location a person can't perceive.

- **No visual references.** "Click the green button", "see the panel on the right", "the box below" — a screen-reader user gets nothing from these. Name the thing: "Select **Save changes**".
- **Link and button text describes the destination or effect** so it stands alone in a screen reader's link list — "View pricing", never "Click here" / "Read more" / "Learn more" with no object.
- **Confirmations name the consequence in the buttons**, never "Yes" / "No" (which force the user to re-read the question) — a destructive dialog reads "Delete project" / "Cancel". (Same rule as §4; here it's an accessibility floor, not just clarity.)

## Voice consistency checklist (use for review)

- Every action label is an **active verb phrase** describing the effect ("Save changes"), not "Submit"/"OK"/"New".
- Each concept has **one name** across nav, titles, breadcrumbs, buttons, and messages.
- Every action **keeps its name** from trigger to confirmation ("Publish" → "Published").
- Every error says **what + how to fix**, in the interface's voice, no apology or blame, correlation id demoted.
- Every empty state matches its **case** (no-records / no-filter-match / by-design) and never leaves a blank region.
- **Sentence case** throughout; no filler words; tone consistent with the brand; the distinguishing word **front-loaded**.
- No control label describes the **mechanism** ("webhook") instead of the **user's object** ("notifications").
- No copy leans on a **visual reference** ("the green button", "the box below"); link/button text describes its **destination or effect**, never "Click here" / "Read more".
- Destructive confirmations name the **specific object** and its verb ("Delete invoice #4821"), and the buttons carry that verb — **never "Yes" / "No"**.

## What NOT to do

- No "Submit"/"OK"/"Proceed"/"Click here" — say what happens.
- No system vocabulary in user-facing copy (entity/principal/payload/null/exception).
- No apology or blame in errors, no vague "Something went wrong" with no next step, no raw exception text (that leak is `error-resilience`'s rule; the voice is yours).
- No blank empty state, and no single generic empty message for all three empty cases.
- No name drift — a concept called different things on different screens, or an action that changes its name mid-flow.
- No Title Case / ALL CAPS labels, no filler ("please simply just").
- Do not invent the *structure* here — the slots (which errors, which empty states, which confirmations) come from `ui-rules` / `error-resilience`; you fill them.

## Handoffs

- Visual/aesthetic direction (this discipline's design-side summary) → [`design/visual-identity`](../visual-identity/SKILL.md)
- Empty-state/confirmation **structure**, IA "one verb per operation" rule → stack `ui-rules` ([Blazor](../../frontend/blazor/skills/ui-rules/SKILL.md) · [React](../../frontend/react/skills/ui-rules/SKILL.md))
- Error **categorization/mapping**, three-state regions, correlation id → stack `error-resilience` ([Blazor](../../frontend/blazor/skills/error-handling/SKILL.md) · [React](../../frontend/react/skills/error-handling/SKILL.md))
- The markup that *carries* these labels (buttons, `<PageTitle>`, real anchors) → stack `generator`
- Translation, locale formatting, pseudo-localization → qa `language-testing` + a localization skill
