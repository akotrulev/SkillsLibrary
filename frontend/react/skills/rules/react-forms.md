---
paths:
  - "**/*Form*.{tsx,jsx}"
  - "**/forms/**/*.{ts,tsx}"
---

<!-- fe-react rules v1 (2026-11-03): forms. Installed by /fe-react:rules; edit the paths above to where this app keeps its forms and their schemas. -->

# React form standards

Severity tags as in the core React rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- React Hook Form + Zod by default; App Router server writes use a Server Action with `useActionState` (React 19; never `useFormState` there, and no Server Action in a Vite SPA). No `useState` per field past two inputs, no form state in a global store. *major*
- One Zod schema per form, its type inferred, used on client and server; no validation duplicated in handlers. *major*
- Validate `onBlur`; async rules are debounced, never per keystroke. Uncontrolled by default, `Controller` for third-party inputs. *minor*
- Every input has `<label htmlFor>`, `aria-invalid` and `aria-describedby`; its error has `role="alert"`; a failed submit focuses the first error. A placeholder is not a label. *major*
- Server `ProblemDetails.errors` map onto their fields (`setError` / `state.errors`); a root error only for a failure no field owns. A 422 is never a toast or a "Something went wrong" banner. *major*
- Submit is disabled and `aria-busy` while pending; a failed submit never clears the user's input. *major*
- The form renders only fields the write path persists; a primary key is read-only; a status changes through an explicit action, never an editable `<select>`; a full replace carries a concurrency token. *major*
- Multi-step: a schema per step plus a merged final schema, state held in the parent. *minor*
- File inputs guard size and MIME type; large uploads go straight to storage through a signed URL. *major*
