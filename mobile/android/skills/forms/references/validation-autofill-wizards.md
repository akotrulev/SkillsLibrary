# Validation timing, autofill and wizards

## Validation timing

| When | Rule |
|---|---|
| On every keystroke | Only to **clear** that field's error; never to raise one on a field the user has not left |
| On leaving a field (focus lost) | Validate that field once; `onFocusChanged { if (!it.isFocused && touched) … }` with a `touched` bit in state |
| On submit | Validate everything, focus the **first** invalid field (`FocusRequester`) and announce it |
| Asynchronous (username taken) | After focus loss, debounced in the ViewModel with `collectLatest` so a stale answer never lands; shown as a hint, re-checked by the server on submit |

An error is text plus `isError = true` — **never colour alone**; the `supportingText` is read by TalkBack with the field. Error text is a string resource built from a `FieldError` case.

## Autofill, passkeys and Credential Manager

- Declare `ContentType` on every field that has one (`Username`, `EmailAddress`, `Password`, `NewPassword`, `NewUsername`, `PostalCode`, `CreditCardNumber`) so the system autofill service and password managers offer values. Pair the screen with the Digital Asset Links association for the app's domain when credentials are shared with the website.
- **Sign-in is Credential Manager** (`CredentialManager.getCredential` with `GetPasswordOption` + `GetPublicKeyCredentialOption`) so a passkey, a saved password and federated sign-in share one sheet; **sign-up** saves with `CreatePasswordRequest` / `CreatePublicKeyCredentialRequest`. The call needs an `Activity` context and runs from a coroutine in the ViewModel's caller scope, not `GlobalScope`. Wiring and failure cases are [`device-features`](../../device-features/SKILL.md).
- Mark a sensitive field so it is not offered for autofill from other apps' data when that is wrong (`Modifier.semantics { contentType = … }` omitted, `importantForAutofill` on Views); never disable autofill on a password field to "improve security".

## Wizards and drafts

A multi-step form is **one ViewModel with one draft** and a `step` in `uiState`, not N ViewModels; the draft survives rotation (ViewModel) and process death (`SavedStateHandle` for the non-secret parts, or a Room/DataStore draft for a long form — [`offline-and-storage`](../../offline-and-storage/SKILL.md)). Back goes to the previous step and keeps its values; leaving with unsaved input asks first (`BackHandler` / predictive back with `PredictiveBackHandler`). Validation runs per step on Next and once more on the final submit.
