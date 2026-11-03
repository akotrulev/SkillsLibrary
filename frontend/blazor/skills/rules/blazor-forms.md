---
paths:
  - "**/*.razor"
---

<!-- fe-blazor rules v1 (2026-11-03): forms and edits. Installed by /fe-blazor:rules; edit to fit this project. -->

# Blazor form and edit standards

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- `<EditForm>` with one validator component (FluentValidation by default, DataAnnotations for trivial forms, never both) and `OnValidSubmit`, not `OnSubmit`. *major*
- Validation lives in the validator, never in the component or a manual check in the submit handler. *major*
- Typed `<Input*>` components, never a raw `<input>`; a custom input binds through `@bind-Value`. *major*
- Every field has a paired `<label>` and a `<ValidationMessage For>`; on a failed submit, focus moves to the first error. *major*
- Submit is `disabled` with `aria-busy` while submitting. *major*
- Server `ProblemDetails.errors` map into the `ValidationMessageStore`; never a generic banner when the API returned field errors. *major*
- A form shows only fields the write path persists (form, DTO and mapper match); primary keys are read-only. *major*
- State changes through explicit transition actions, never an editable `Status` field. *major*
- A full PUT carries a concurrency token (`If-Match`). *major*
- Large uploads go to storage via a signed URL, never through the SignalR channel. *major*
