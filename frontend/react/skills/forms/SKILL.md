---
name: fe-react-forms
description: Use when building or fixing a form — React Hook Form + Zod (default), the React 19 Server-Actions lane (`<form action>` + `useActionState` + `useOptimistic`), async/server validation, ProblemDetails→field-error mapping, wizards, uploads, a11y. Triggers "build a form for X", "validate with Zod", "server errors aren't landing on the fields", "my input loses focus on every keystroke". Not for state management (`state-management`) or fetch mechanics (`data-fetching`).
---

# React — Forms

House pattern: **React Hook Form (RHF) + Zod** validated against a strongly-typed schema, with a **React 19 Server-Actions lane** for App Router mutations, server errors mapped onto the right fields, accessibility baked in, and submission state managed cleanly. React forms are full of foot-guns; this cuts the recipe to two paths that scale from one-field forms to multi-step wizards.

**Version rule:** `useActionState` (React 19; supersedes React 18's `useFormState`) + `useOptimistic` + Server Actions are the primary App Router lane. On React 18 / a Vite SPA (no Server Actions), use the **RHF + fetch/`useMutation`** lane throughout. Detect the React/Next major and pick the lane.

## When to use

- Any form past a single field
- Replacing scattered ad-hoc validation with one schema as the source of truth
- Wiring server-side validation errors back onto the fields
- Multi-step / wizard forms; file uploads; optimistic submit

## When NOT to use

- A single search input or filter — `useState` (or URL state) is fine, no library
- State management at large → [`state-management`](../state-management/SKILL.md)
- The fetch/mutation mechanics + caching/revalidation → [`data-fetching`](../data-fetching/SKILL.md)
- Broad accessibility audit → [`accessibility`](../accessibility/SKILL.md)
- Component scaffolding → [`component-writer`](../component-writer/SKILL.md)
- Auth UI (login/signup) → `auth/auth0-react`

## Which lane?

```
Next.js App Router + the mutation is a plain server write (create/update/delete)?
  → Server Actions lane: <form action={fn}> + useActionState — no client fetch, no API route, lightest path.
Rich client-side interactivity (live cross-field rules, dynamic arrays, wizard, 3rd-party controls)?
  → RHF + Zod lane: full control, instant client validation.
Both? Use RHF for the client UX and submit *to* a Server Action — they compose.
Vite SPA (no server)?
  → RHF + Zod, submit via a TanStack Query useMutation.
```

## Shared foundation — the Zod schema

One schema per form; the TypeScript type is **inferred** from it (never hand-maintained in parallel):

```ts
// features/orders/order.schema.ts
import { z } from 'zod';

export const CreateOrderSchema = z.object({
  customerEmail: z.string().email('Enter a valid email'),
  quantity: z.coerce.number().int().min(1, 'At least 1 item').max(100, 'Max 100 items'),
  notes: z.string().max(500).optional(),
});
export type CreateOrderInput = z.infer<typeof CreateOrderSchema>;
```

The **same schema validates on the client (RHF resolver) and on the server (Server Action / API)** — one source of truth, no drift.

## RHF + Zod lane (default for rich client forms)

```tsx
'use client';
import { useForm, type SubmitHandler } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CreateOrderSchema, type CreateOrderInput } from '@/features/orders/order.schema';

export function OrderForm({ onSubmit }: { onSubmit: (d: CreateOrderInput) => Promise<void> }) {
  const { register, handleSubmit, formState: { errors, isSubmitting, isSubmitSuccessful }, setError, reset } =
    useForm<CreateOrderInput>({
      resolver: zodResolver(CreateOrderSchema),
      defaultValues: { customerEmail: '', quantity: 1, notes: '' },
      mode: 'onBlur',                                   // feedback without per-keystroke noise
    });

  const submit: SubmitHandler<CreateOrderInput> = async (data) => {
    try {
      await onSubmit(data);
      reset();
    } catch (e) {
      if (e instanceof FieldServerError) {
        for (const [field, messages] of Object.entries(e.errors))
          setError(field as keyof CreateOrderInput, { type: 'server', message: messages.join(', ') });
      } else {
        setError('root', { type: 'server', message: 'Submission failed. Try again.' });
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} noValidate aria-busy={isSubmitting} data-testid="OrderForm">
      <div>
        <label htmlFor="email">Email</label>
        <input id="email" type="email" data-testid="OrderForm.Email"
          aria-invalid={!!errors.customerEmail}
          aria-describedby={errors.customerEmail ? 'email-err' : undefined}
          {...register('customerEmail')} />
        {errors.customerEmail && <p id="email-err" role="alert">{errors.customerEmail.message}</p>}
      </div>
      {/* quantity, notes — same pattern */}
      {errors.root && <p role="alert">{errors.root.message}</p>}
      <button type="submit" disabled={isSubmitting} data-testid="OrderForm.Submit">
        {isSubmitting ? 'Saving…' : 'Create order'}
      </button>
      {isSubmitSuccessful && <p role="status">Saved.</p>}
    </form>
  );
}
```

RHF is **uncontrolled by default** — it registers inputs and reads via `ref`, so it does **not** re-render the whole form on every keystroke. That's the point; don't replace it with `useState`-per-field.

## Server Actions lane (App Router primary)

```tsx
// features/orders/OrderForm.tsx
'use client';
import { useActionState } from 'react';           // React 19 (React 18: useFormState from react-dom)
import { useFormStatus } from 'react-dom';
import { createOrder, type FormState } from './actions';

const initial: FormState = { errors: {} };

export function OrderForm() {
  const [state, action] = useActionState(createOrder, initial);
  return (
    <form action={action} data-testid="OrderForm">
      <div>
        <label htmlFor="email">Email</label>
        <input id="email" name="customerEmail" type="email"
          aria-invalid={!!state.errors.customerEmail}
          aria-describedby={state.errors.customerEmail ? 'email-err' : undefined} />
        {state.errors.customerEmail && <p id="email-err" role="alert">{state.errors.customerEmail}</p>}
      </div>
      {state.errors.root && <p role="alert">{state.errors.root}</p>}
      <SubmitButton />
    </form>
  );
}

function SubmitButton() {
  const { pending } = useFormStatus();             // must be a child of <form> — reads the enclosing action's state
  return <button type="submit" disabled={pending} data-testid="OrderForm.Submit">
    {pending ? 'Saving…' : 'Create order'}</button>;
}
```

```ts
// features/orders/actions.ts
'use server';
import { revalidateTag } from 'next/cache';
import { redirect } from 'next/navigation';
import { CreateOrderSchema } from './order.schema';

export type FormState = { errors: Partial<Record<'customerEmail' | 'quantity' | 'notes' | 'root', string>> };

export async function createOrder(_prev: FormState, formData: FormData): Promise<FormState> {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData)); // SAME schema, server side
  if (!parsed.success) {
    const f = parsed.error.flatten().fieldErrors;
    return { errors: { customerEmail: f.customerEmail?.[0], quantity: f.quantity?.[0], notes: f.notes?.[0] } };
  }
  try { await db.orders.create(parsed.data); }
  catch { return { errors: { root: 'Submission failed. Try again.' } }; }
  revalidateTag('orders');                           // reflect the write — see data-fetching
  redirect('/orders');
}
```

The action validates with the **same Zod schema**, persists, revalidates the affected cache tag, and redirects — no client fetch, no API route, no client store. `useActionState` carries server field errors back into `state`; `useFormStatus` gives the pending state to any child button. For **rich UX + a Server Action**, keep RHF on the client and call the action inside `handleSubmit` — you get instant client validation *and* the server as the authority.

### Optimistic submit — `useOptimistic`

For actions where the result is predictable (add a to-do, toggle a like), show the change immediately and let it reconcile when the action resolves (auto-reverts on failure):

```tsx
'use client';
const [optimisticItems, addOptimistic] = useOptimistic(items, (state, next: Item) => [...state, next]);
// in the form action handler: addOptimistic(draft); await createItem(draft);
```

## Server-side errors — one shape

Server APIs emit RFC-7807 `ProblemDetails` with an `errors` map keyed by field. Extract it uniformly and map onto fields (RHF `setError`, or the action's returned `state.errors`):

```ts
export class FieldServerError extends Error {
  constructor(public errors: Record<string, string[]>) { super('Field errors'); }
}
// in the client data call: if (res.status === 400) { const p = await res.json(); if (p.errors) throw new FieldServerError(p.errors); }
```

Per-field server errors then look identical to client validation errors — never dump them into a generic banner when the API gave you a field map.

## Accessibility — non-negotiable

Every input: (1) `<label htmlFor>` matched to `id` (or a documented `aria-label`); (2) `aria-invalid` when in error; (3) `aria-describedby` pointing at the error message `id`; (4) the error message rendered with `role="alert"` so it's announced; (5) submit `disabled` while submitting + `aria-busy` on the form; (6) on submission failure, **focus moves to the first invalid field** (`setFocus` in RHF, or a focusing effect in the actions lane). Without these the form fails screen-reader users — [`accessibility`](../accessibility/SKILL.md) and [`code-review`](../code-review/SKILL.md) check them.

## Controlled inputs — `Controller`

RHF stays uncontrolled except when wrapping a **3rd-party component that expects `value`/`onChange`** (combobox, MUI Select, date picker) or when you must transform between schema type and UI value (currency ↔ minor units). Then use `Controller`:

```tsx
<Controller control={control} name="currency"
  render={({ field, fieldState }) => (
    <CurrencySelect value={field.value} onChange={field.onChange} onBlur={field.onBlur}
      error={fieldState.error?.message} />
  )} />
```

MUI's `TextField` binds cleanly via `register` for simple inputs; its `Select`/`Autocomplete`/`DatePicker` go through `Controller`.

## Async validation

When a rule needs the server (uniqueness), debounce it (`mode: 'onBlur'` + a debounced network check) so it fires per blur, not per keystroke — via a Zod `.refine(async …)` or an RHF `validate` function. Never block the whole form on every keystroke's round-trip.

## Multi-step wizards

Prefer **one schema per step + a merged final schema** — each step validates independently; the final submit uses the merge:

```ts
const FullSchema = Step1Schema.merge(Step2Schema).merge(Step3Schema);
```

Hold accumulated state in a parent (or a scoped store); validate per step; call the action/API once with the full payload. Let the user advance only when the current step is valid.

## File uploads

`<input type="file" multiple accept=".pdf,.png">` — RHF handles the `FileList`; validate with Zod (`z.instanceof(FileList)` + a `.refine` for size/MIME). For large files, request a **signed URL server-side** (S3 presigned / Azure Blob SAS) and upload straight from the browser, submitting only metadata through the form — keeps the server out of the bandwidth path.

## Rules

- **RHF + Zod** by default; **Server Actions + `useActionState`** for App Router server writes; both compose.
- **One Zod schema per form**, type inferred, used on **both** client and server.
- **`mode: 'onBlur'`** — feedback without per-keystroke noise; async rules debounced.
- Every input: `<label htmlFor>` + `aria-invalid` + `aria-describedby` + `role="alert"`; submit `disabled` while pending + `aria-busy`; focus to first error on failure.
- **Server `ProblemDetails.errors` mapped per field** (`setError` / `state.errors`); a `root` error only for non-field failures.
- **Uncontrolled by default**; `Controller` for 3rd-party controls; MUI `Select`/`Autocomplete`/`DatePicker` via `Controller`.
- **Multi-step:** schema-per-step + merged final; accumulated state in a parent/store.
- **Large uploads bypass the server** via signed URLs.
- Every form + interactive control carries a `data-testid` per [`test-ids`](../test-ids/SKILL.md).

## What NOT to do

- No `useState`-per-field for any form past one or two inputs (re-renders the whole form).
- No `<input>` without a `<label>` (or documented `aria-label`); no error without `role="alert"`.
- No "Something went wrong" banner when the API returned per-field errors.
- No validation logic duplicated in the schema and in handlers; no form state in Redux/Zustand.
- No submit without a `disabled`/`pending` guard (double-submits + duplicate writes).
- No validate-on-every-keystroke; no async rule firing per keystroke.
- No React-18 `useFormState` in a React 19 project (use `useActionState`); no Server Actions in a Vite SPA.
- No file input without size/MIME guards; no large upload piped through the app server.

## Generation steps

1. Confirm fields, rules, server error shape (likely ProblemDetails), and the lane (App Router Server Action vs RHF/SPA).
2. Author the Zod schema; export the inferred type.
3. Generate the form — RHF + `zodResolver`, or `<form action>` + `useActionState`, or both composed.
4. Wire the accessibility attributes per the checklist; add focus-to-first-error.
5. Wire submit — map `ProblemDetails` to `setError`/`state.errors`; revalidate/redirect in the action.
6. Multi-step → schema-per-step + parent state; optimistic → `useOptimistic`.
7. Smoke locally: valid submit, client-validation fail, server-side fail; confirm screen-reader announcement.

## Handoffs

- State management at large → [`state-management`](../state-management/SKILL.md)
- Fetch/mutation mechanics, caching, revalidation → [`data-fetching`](../data-fetching/SKILL.md)
- Accessibility deep dive → [`accessibility`](../accessibility/SKILL.md)
- Component scaffolding → [`component-writer`](../component-writer/SKILL.md)
- Auth-protected forms → `auth/auth0-react`
- API contract (ProblemDetails fields must match) → `qa/typescript/skills/api-test-author` (peer)
- Blazor forms → `frontend/blazor/skills/forms`
