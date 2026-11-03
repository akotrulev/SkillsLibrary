---
paths:
  - "**/messages/*.json"
  - "**/locales/**/*.json"
  - "**/*.xcstrings"
  - "**/res/values*/strings.xml"
---

<!-- design rules v1 (2026-11-03): UI copy in message catalogs. Installed by /design:rules; add this app's catalogs (.resx, i18n/*.json, .po) to the paths above. -->

# UI copy standards

Apply these to the source-language strings a user reads. Severity tags as in `design-tokens.md`: **blocker**, **major**, **minor**, **nit**. Catalog mechanics (plurals, placeholders, formatting) are the stack's own rules; this file is the voice. The codebase wins where it consistently does otherwise.

- Name things from the user's side: what people control and recognise (notifications, members, your plan), never system vocabulary (webhook, principal, entity, payload, null, exception). *minor*
- An action label is an active verb phrase naming its effect ("Save changes", "Send invite"), never "Submit", "OK", "Proceed" or a noun ("New"). *minor*
- One concept has one name across nav, titles, breadcrumbs, buttons and messages, and an action keeps its name from trigger to result ("Publish" → "Published"). *minor*
- An error says what happened and what to do, in the interface's voice: no apology, no blame, no bare "Something went wrong", never raw exception text or a status code as the message; a reference id sits quietly after. *major*
- Each empty state fits its case: nothing yet invites the first action; a filter that matched nothing says so and offers to clear it; empty by design is a calm statement. Never one generic "No data". *minor*
- Sentence case, never Title Case or ALL CAPS; no filler ("please", "simply", "just"); the distinguishing word first. *minor*
- Personality only in low-stakes moments (empty states, success toasts, onboarding), never in errors, payments or destructive confirmations. *minor*
- No visual or positional reference ("the green button", "the box below"); link and button text names its destination or effect and stands alone, never "Click here" or a bare "Read more". *major*
- A destructive confirmation names the object and the verb ("Delete invoice #4821"), and its buttons carry the verb, never "Yes" / "No". *major*
- One job per string: a label labels, a hint demonstrates ("Enter an email address like name@company.com"), a tooltip clarifies. *nit*
