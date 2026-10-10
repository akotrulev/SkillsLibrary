---
name: mobile-ios-forms
description: Use when building or fixing a SwiftUI form — Form and sections, @FocusState field order, validation timing, textContentType for autofill and passkeys, keyboard toolbar, submit state, server errors mapped onto fields. Triggers "build a sign-up form", "keyboard hides the field", "autofill not offered", "server errors don't land on fields". Do NOT use for the request itself (`mobile-ios-networking`), state ownership (`-architecture`) or UIKit forms (`-uikit`).
---

# iOS — Forms

A SwiftUI form is a value (the draft), a validator (a pure function over it), a focus order, and a submit that can fail per field. House rules from the web (`fe-react-forms`) that carry over: **one validator is the source of truth, errors appear on the field that caused them, submit is guarded against double taps, a server rejection lands on the right field.** Rules that do not carry over: Zod, RHF, Server Actions, `aria-*`.

## Version lane

| Concern | iOS 17+ (primary) | `[iOS16]` | `[UIKit]` |
|---|---|---|---|
| Draft model | `@Observable` draft held in `@State`, bound with `@Bindable` | `@State` value-type draft, or `ObservableObject` where the codebase has it | Existing delegate / target-action style — [`uikit`](../uikit/SKILL.md) |
| Focus | `@FocusState` with an enum | Same | `becomeFirstResponder` chain |
| Submit | `.onSubmit` + `.submitLabel` | Same | `textFieldShouldReturn` |
| Autofill / passkeys | `textContentType` (`.username`, `.password`, `.newPassword`, `.oneTimeCode`, `.emailAddress`) | Same | Same on `UITextField.textContentType` |
| Keyboard toolbar | `ToolbarItemGroup(placement: .keyboard)` | Same | `inputAccessoryView` |

Design facts (field heights, labels, keyboard behaviour): `design/ui-ux-pro-max` `--stack swiftui`.

## When to use

- A screen with more than one input, or any input that is validated
- Autofill, password manager or passkey sign-in not appearing
- The keyboard covers the field or Return does nothing useful
- A server `422` / ProblemDetails must show on specific fields
- A multi-step flow (a wizard) with a draft across steps

## When NOT to use

- A single search field or filter — `@State` and `.searchable`, no form machinery
- Building the request, retries, timeouts → [`networking`](../networking/SKILL.md)
- Where the draft model lives, `@Bindable` vs `@Environment` → [`architecture`](../architecture/SKILL.md)
- A load / failed region around a form's data → [`ui-components`](../ui-components/SKILL.md); the failure banner → `mobile-ios-error-handling`
- Photos, camera, files picked inside a form → [`device-features`](../device-features/SKILL.md)
- UIKit form screens → [`uikit`](../uikit/SKILL.md)
- Another stack → `mobile-react-native-forms`, `mobile-android-forms`

## Inputs needed

- Deployment target, and whether forms in the codebase use `@Observable`, `ObservableObject` or UIKit
- The field list with each rule (required, format, range, cross-field) and which are server-checked
- Where the draft is submitted and what error shape the server returns

## The shape: draft, validator, submit

```swift
struct SignUpDraft: Equatable {
    var email = ""
    var password = ""
    var acceptedTerms = false
}

enum SignUpField: String, CaseIterable, Hashable {
    case email, password
    init?(serverName: String) { self.init(rawValue: serverName) }
}

struct SignUpErrors: Equatable {
    var fields: [SignUpField: String] = [:]
    var form: String?
    var isEmpty: Bool { fields.isEmpty && form == nil }
}

enum SignUpValidator {
    static func validate(_ draft: SignUpDraft) -> SignUpErrors {
        var errors = SignUpErrors()
        if !draft.email.contains("@") { errors.fields[.email] = String(localized: "Enter a valid email") }
        if draft.password.count < 12 { errors.fields[.password] = String(localized: "At least 12 characters") }
        if !draft.acceptedTerms { errors.form = String(localized: "Accept the terms to continue") }
        return errors
    }
}
```

- **The validator is a pure function over the draft** — no view, no network — so a Swift Testing test calls it directly (`mobile-ios-unit-testing`).
- **Messages are localized at creation** (`String(localized:)`, String Catalog — `mobile-ios-languages`), never a raw server string.
- Field-level errors are keyed by an enum, not a string, so the focus enum and the error map share one vocabulary.

## The view

```swift
struct SignUpView: View {
    @State private var draft = SignUpDraft()
    @State private var errors = SignUpErrors()
    @State private var isSubmitting = false
    @FocusState private var focus: SignUpField?
    let submit: (SignUpDraft) async throws -> Void

    var body: some View {
        Form {
            Section {
                TextField("Email", text: $draft.email)
                    .textContentType(.username)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .submitLabel(.next)
                    .focused($focus, equals: .email)
                    .onSubmit { focus = .password }
                    .accessibilityIdentifier("SignUp.Email")
                FieldError(errors.fields[.email])

                SecureField("Password", text: $draft.password)
                    .textContentType(.newPassword)
                    .submitLabel(.go)
                    .focused($focus, equals: .password)
                    .onSubmit { Task { await send() } }
                    .accessibilityIdentifier("SignUp.Password")
                FieldError(errors.fields[.password])
            }
            Section {
                Toggle("I accept the terms", isOn: $draft.acceptedTerms)
                    .accessibilityIdentifier("SignUp.Terms")
                FieldError(errors.form)
            }
            Section {
                Button(isSubmitting ? "Creating…" : "Create account") { Task { await send() } }
                    .disabled(isSubmitting)
                    .accessibilityIdentifier("SignUp.Submit")
            }
        }
        .scrollDismissesKeyboard(.interactively)
        .toolbar {
            ToolbarItemGroup(placement: .keyboard) {
                Spacer()
                Button("Done") { focus = nil }
                    .accessibilityIdentifier("SignUp.KeyboardDone")
            }
        }
    }

    private func send() async {
        guard !isSubmitting else { return }
        errors = SignUpValidator.validate(draft)
        guard errors.isEmpty else {
            focus = SignUpField.allCases.first { errors.fields[$0] != nil }
            return
        }
        isSubmitting = true
        defer { isSubmitting = false }
        do { try await submit(draft) }
        catch { errors = (error as? SubmitFailure ?? .unexpected).errors() }
    }
}

struct FieldError: View {
    let message: String?
    init(_ message: String?) { self.message = message }
    var body: some View {
        if let message {
            Text(message)
                .font(.footnote)
                .foregroundStyle(.red)
                .accessibilityIdentifier("FieldError")
        }
    }
}
```

- **`Form` and `Section`, not a `ScrollView` of stacks** — the system gives grouped styling, Dynamic Type, and keyboard avoidance. A custom layout re-implements all three.
- **Error text sits beside its field and is not colour alone** — the message is text; `mobile-ios-accessibility` adds the VoiceOver wiring so the error is read with the field.
- **`.submitLabel` + `.onSubmit` chain the fields**; the last field's Return submits. `@FocusState` moves focus to the first invalid field after a failed submit.
- **`isSubmitting` guards re-entry** at the top of `send()`, not only through `.disabled` — Return on the keyboard bypasses a disabled button.
- **Test ids** on every control and on the error text — static, PascalCase dot-separated, never the label ([`mobile-ios-test-ids`](../test-ids/SKILL.md)).
- `SecureField` and `UITextContentType.oneTimeCode` keep input out of the keyboard cache and the pasteboard history; never disable secure entry to "help" a UI test ([`mobile-shared-security`](../../../_shared/security/SKILL.md)).

## Validation timing

| Rule type | When it runs | Why |
|---|---|---|
| Format (email, length) | On leaving the field (`onChange(of: focus)` for the field just left) and on submit | Per-keystroke errors punish a user mid-word |
| Required | On submit only | An untouched field is not yet wrong |
| Cross-field (confirm password, date range) | On the change of the second field and on submit | Both values exist |
| Server-only (taken username) | On submit, mapped back to the field | Do not build a debounced live check unless the product needs it |

A field that was invalid and is now valid clears its error on the next change — an error that outlives its cause trains users to ignore errors.

## Server errors land on the field

The networking layer returns a categorised error carrying field names ([`networking`](../networking/SKILL.md) — ProblemDetails `errors`). The form maps field names to its enum; an unknown field goes to the form-level slot, never dropped, and the whole message is never `localizedDescription`.

```swift
enum SubmitFailure: Error {
    case invalid([String: [String]])
    case network
    case unexpected

    func errors() -> SignUpErrors {
        var result = SignUpErrors()
        switch self {
        case .invalid(let byField):
            for (name, messages) in byField {
                guard let field = SignUpField(serverName: name) else {
                    result.form = String(localized: "Check your details and try again")
                    continue
                }
                result.fields[field] = messages.first
            }
        case .network:
            result.form = String(localized: "You appear to be offline. Try again when connected.")
        case .unexpected:
            result.form = String(localized: "Something went wrong. Try again.")
        }
        return result
    }
}
```

An indeterminate outcome (the app was backgrounded mid-submit, the response never arrived) is the common mobile case: the submit carries an idempotency key made **once per draft**, not per tap, so a retry cannot create twice ([`networking`](../networking/SKILL.md)).

## Autofill, passkeys and the keyboard

| Field | `textContentType` | Keyboard |
|---|---|---|
| Sign-in email / username | `.username` | `.emailAddress` |
| Sign-in password | `.password` | default, `SecureField` |
| New password | `.newPassword` (offers a strong password) | `SecureField` |
| One-time code | `.oneTimeCode` (the SMS code appears above the keyboard) | `.numberPad` |
| Name, address, phone | `.givenName`, `.postalCode`, `.telephoneNumber` … | per field |

- **Associated Domains** `webcredentials:` is what lets password autofill and passkeys offer saved credentials for your domain; passkey creation itself is `auth-auth0-ios`'s lane.
- Set `.textInputAutocapitalization(.never)` and `.autocorrectionDisabled()` on emails, usernames and codes.
- `.scrollDismissesKeyboard(.interactively)` lets the user drag the keyboard away; a `.keyboard` toolbar `Done` button is the way out of a `.numberPad`, which has no Return.
- Numeric fields use `TextField(value:format:)` with `.keyboardType(.decimalPad)` rather than parsing strings by hand; the `FormatStyle` also handles the user's locale separators.

## Wizards and drafts

A multi-step flow holds **one draft** above the steps (`@State` in the owning view, `@Bindable` into each step) — not a draft per step copied forward. Each step validates its own slice of the validator; the final step validates the whole. Back navigation never discards entered values. Whether to persist an in-progress draft across a process kill is `offline-and-storage`'s (SwiftData or `SceneStorage` for small drafts); **a password, a card number or a token is never written into a draft** that persists.

## Rules

- One pure validator per form; the view renders its result.
- Errors beside the field, as text, localized; cleared when the cause is fixed.
- `@FocusState` order matches the visual order; Return moves on or submits; focus lands on the first invalid field.
- Submit guards re-entry in code, disables the control, shows progress, and carries one idempotency key per draft.
- Server field errors map to the enum; unknown fields go to a form-level message.
- `textContentType` on every credential, address and code field; `SecureField` for secrets.
- Every control and error text has an `accessibilityIdentifier`.

## What NOT to do

- No validation inside `body` that allocates or calls the network; no `Task` per keystroke.
- No `ScrollView` + `VStack` imitating `Form`; no per-platform imitation of Material text fields.
- No `.disabled(!isValid)` as the only feedback — the user sees a dead button and no reason.
- No `localizedDescription` or a raw server string shown as an error.
- No secrets in a persisted draft, `@AppStorage` or `UserDefaults`.
- No `UIKit` `UITextField` wrapper where `TextField` + `textContentType` does the job.
- No `Thread.sleep`-style delay to "let the keyboard settle".

## Generation steps

1. Read an existing form and the draft convention; detect target and Observation style.
2. List fields, rules and which come from the server; write the draft, the field enum and the validator.
3. Write the view with `Form`, `@FocusState`, `textContentType`, submit labels and the guarded `send()`.
4. Map the networking error onto the field enum; add the idempotency key.
5. Add test ids; add the audit-relevant states to `#Preview` (empty, invalid, submitting, server error).
6. Add validator tests with Swift Testing.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build with warnings as errors; run the project's `swift-format` / SwiftLint configuration.
- On a device or simulator: Return walks the fields in order and the last one submits; the password manager offers a credential on the sign-in form; an invalid submit focuses the first invalid field; Dynamic Type at the largest accessibility size keeps every field reachable.
- A double tap on submit sends one request.
- Dev-side tests: the validator and the error mapper as Swift Testing cases ([`mobile-ios-unit-testing`](../unit-testing/SKILL.md)).

## Handoffs

- The request, retries, ProblemDetails → [`networking`](../networking/SKILL.md)
- Draft persistence → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Failure banner and offline copy → `mobile-ios-error-handling`
- VoiceOver for errors → `mobile-ios-accessibility`
- Passkeys and sign-in → `auth-auth0-ios`
- E2E journeys → `qa-mobile-ios` (peer)
