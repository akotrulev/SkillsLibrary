---
name: ux-writing
description: Use when writing or reviewing UI words (button labels, errors, empty states, toasts) in one voice. Triggers "what should this button say", "write the error message". Not for structure (ui-rules).
disable-model-invocation: true
---

# UX Writing — voice & microcopy

Owns the **words** in a UI and the voice they share. Interface copy is design material, not decoration: it exists to make the product easier to understand and therefore easier to use. This skill supplies the *voice*; the engineering stack owns the *slots* that voice fills — and the two are deliberately split so the copy discipline is written once and reused across stacks (Blazor, React, and the mobile and desktop stacks).

**The slot/voice split — who owns what:**

| The stack skill defines the slot | This skill supplies the voice |
|---|---|
| `ui-rules` — empty-state taxonomy (no-records vs no-filter vs filter-matched-nothing), confirmations by object name, "one name → one concept, one verb per operation" IA | the actual wording of each empty state, confirm button, and label; the rule that a name persists through a flow |
| `error-handling` — error *categorization* (ProblemDetails → friendly message + correlation id), three-state regions | how the friendly message reads: what went wrong + how to fix it, in the interface's voice |
| `component-writer` (a native stack's `ui-components`) — *emits* the button, label and page-title markup | the text those emitted labels carry |

Never duplicate the structural rules back into this skill, and never restate voice rules in those skills — cross-link. `design/visual-identity` carries a design-side *summary* of this discipline (its "writing in design" section); the depth lives here.

## The six rules

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
- The label in a nav, the page or window title (`<PageTitle>` on the web), the breadcrumb segment, and the heading for the same destination all match.
- One concept has one name app-wide (this is the copy face of `ui-rules`' "one name → one concept, one verb per operation" IA rule — same principle, applied to the words).

Renaming for consistency is high-leverage: a single concept called three things ("Client" / "Customer" / "Account") across screens makes the product feel like three products.

### 4. Failure and emptiness are direction, not mood

- **Errors** explain **what went wrong and how to fix it**, in the interface's voice — not a person's. They don't apologize ("Sorry!"), don't blame the user, and are never vague. Structure: *what happened → what to do → (optional) a reference id for support.* `error-handling` categorizes the error and hands you a friendly slot + correlation id; you write the sentence. Example: *"Couldn't upload — the file is over 10 MB. Try a smaller file."* (id shown quietly for support, never as the whole message).
- **Empty states are invitations to act**, and they match the three cases `ui-rules` distinguishes:
  - *Nothing created yet* → invite + primary action: "No projects yet. Create your first project."
  - *A filter matched nothing* → say so + offer to clear: "No results for 'archived'. Clear filters."
  - *Genuinely empty by design* → a calm statement, no false call to action.
  Never leave a blank region — an empty grid is indistinguishable from a broken one.

### 5. Register: conversational, tuned, one job per element

Plain verbs, **sentence case** (not Title Case or ALL CAPS — this overrides the web interface guidelines' *Content & Copy* rule in [`design/ui-code-audit`](../ui-code-audit/SKILL.md), which emits no copy findings; one house voice beats a borrowed style guide, and it holds across every stack), no filler ("please," "simply," "just"), tone matched to the brand and audience. Let each element do exactly one job — a label labels, a hint demonstrates, a tooltip clarifies; nothing quietly does double duty. Be concise: cut every word that doesn't help the person navigate.

- **Front-load the distinguishing word.** People scan; the word that tells them apart comes first — "Pricing", not "Our pricing options"; "To reset your password…", not "In order to reset…". This is the copy face of the IA rule that nav/section labels lead with content, not org structure.
- **Personality lives in low-stakes moments only.** A little voice is welcome in empty states, success toasts, and onboarding; it is out of place in errors, payments, and destructive confirmations, where the user's goal beats brand voice every time.

### 6. Write so it works without sight or position

Copy is read aloud by screen readers and out of visual context — never lean on color, shape, or location a person can't perceive.

- **No visual references.** "Click the green button", "see the panel on the right", "the box below" — a screen-reader user gets nothing from these. Name the thing: "Select **Save changes**".
- **Link and button text describes the destination or effect** so it stands alone in a screen reader's link list — "View pricing", never "Click here" / "Read more" / "Learn more" with no object.
- **Confirmations name the consequence in the buttons**, never "Yes" / "No" (which force the user to re-read the question) — a destructive dialog reads "Delete project" / "Cancel". (Same rule as §4; here it's an accessibility floor, not just clarity.)

## Review checklist

Numbered because audit finding ids cite the numbers: new checks are appended, and none is renumbered or removed (a retired check keeps its number and says *retired*).

1. Every action label is an **active verb phrase** describing the effect ("Save changes"), not "Submit"/"OK"/"New".
2. Each concept has **one name** across nav, titles, breadcrumbs, buttons, and messages.
3. Every action **keeps its name** from trigger to confirmation ("Publish" → "Published").
4. Every error says **what + how to fix**, in the interface's voice, no apology or blame, correlation id demoted.
5. Every empty state matches its **case** (no-records / no-filter-match / by-design) and never leaves a blank region.
6. **Sentence case** throughout; no filler words; tone consistent with the brand; the distinguishing word **front-loaded**.
7. No control label describes the **mechanism** ("webhook") instead of the **user's object** ("notifications").
8. No copy leans on a **visual reference** ("the green button", "the box below"); link/button text describes its **destination or effect**, never "Click here" / "Read more".
9. Destructive confirmations name the **specific object** and its verb ("Delete invoice #4821"), and the buttons carry that verb — **never "Yes" / "No"**.

## Rules

The standards copy must meet are the design rule file `ui-copy.md`, not a list here; it also loads on its own when a session edits a message catalog. Read the project's copy in `.claude/rules/design/`, or the plugin's in `design/rules/` when the project has not installed them (`/design:rules` does). Where it and this skill disagree, the rule file wins. The checklist above stays: it is the form `/design:audit` sweeps as section H, and its check numbers are that audit's finding ids.

Beyond the rule file: do not invent the *structure* here. The slots (which errors, which empty states, which confirmations) come from `ui-rules` / `error-handling`; you fill them.
