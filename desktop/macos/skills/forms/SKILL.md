---
name: forms
description: Use when building a Mac SwiftUI form (Settings, inspectors, FocusState, key-view loop, validation). Triggers "build a preferences pane". Not for the request (networking).
disable-model-invocation: true
---

# macOS — Forms

A Mac form is a draft value, a pure validator, a focus order and a submit that can fail per field. It lives in a `Settings` pane, an inspector, a sheet or a document window, and it is **keyboard first**: Tab walks every field, Return commits, Escape cancels. Audit rows are section G of `desktop-macos:standards-audit`.

## Version lane

| Concern | Primary | Notes |
|---|---|---|
| `Form`, `Section`, `LabeledContent`, `@FocusState`, `.onSubmit` | macOS 13+ (`.formStyle(.grouped)`) | — |
| `@Observable` draft in `@State`, bound with `@Bindable` | macOS 14+ | macOS 13: value-type draft in `@State` |
| `.inspector`, `focusable(interactions:)` | macOS 14+ | — |
| Text-field styles `.squareBorder` / `.roundedBorder` **[mac27SDK]** | Soft-deprecated: `.bordered` + `textInputBorderShape(_:)` | Older SDK keeps the old names |
| `controlSize`, `buttonSizing` inside sheets and popovers **[mac27SDK]** | Reset on the 27 SDK: re-apply in the presented content | — |
| AppKit forms | `NSTextField` + `autorecalculatesKeyViewLoop` | → [`appkit`](../appkit/SKILL.md) |

Design facts: `design/ui-ux-pro-max` `--stack swiftui`; HIG "Text fields", "Settings". The corpus wins.

## When to use

- A Settings pane, an inspector form, a sheet with inputs
- Tab order wrong, Return or Escape doing nothing useful
- Validation, a server `422` shown on a field
- Autofill, password manager or passkey sign-in

## When NOT to use

- A single search field → `.searchable`
- The request, timeouts, ProblemDetails → `networking`
- Where the draft model lives → [`architecture`](../architecture/SKILL.md)
- The settings window itself → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- A load/failed region around the form → [`ui-components`](../ui-components/SKILL.md)
- Pickers for files → `sandbox-and-permissions`; document-backed forms → [`documents`](../documents/SKILL.md)
- Another platform → `mobile-ios:forms`, `desktop-windows:forms`

## The shape: draft, validator, submit

```swift
struct AccountDraft: Equatable {
    var email = ""
    var displayName = ""
}

struct AccountErrors: Equatable {
    var email: String?
    var displayName: String?
    var isEmpty: Bool { email == nil && displayName == nil }
}

func validate(_ draft: AccountDraft) -> AccountErrors {
    AccountErrors(
        email: draft.email.contains("@") ? nil : "Enter a valid email address",
        displayName: draft.displayName.isEmpty ? "Enter a name" : nil
    )
}
```

One validator is the source of truth. Validate on submit and on leaving a field, never per keystroke for a field the user has not left. The draft is a value; only a successful submit writes to the model or the store.

```swift
struct AccountForm: View {
    enum Field: Hashable { case email, displayName }

    @State private var draft = AccountDraft()
    @State private var errors = AccountErrors()
    @State private var isSubmitting = false
    @FocusState private var focus: Field?
    let submit: (AccountDraft) async throws -> Void

    var body: some View {
        Form {
            TextField("Email", text: $draft.email)
                .textContentType(.username)
                .focused($focus, equals: .email)
                .accessibilityIdentifier("Account.Email")
            if let message = errors.email {
                Text(message).foregroundStyle(.red).accessibilityIdentifier("Account.Email.Error")
            }
            TextField("Name", text: $draft.displayName)
                .focused($focus, equals: .displayName)
                .accessibilityIdentifier("Account.DisplayName")
            Button("Save", action: save)
                .keyboardShortcut(.defaultAction)
                .disabled(isSubmitting)
                .accessibilityIdentifier("Account.Save")
        }
        .formStyle(.grouped)
        .onSubmit(save)
        .defaultFocus($focus, .email)
    }
}
```

`save` runs the validator, moves `focus` to the first invalid field, and awaits `submit` guarded by `isSubmitting` (no double submit). An error line also carries a symbol or the word "error" — never red alone.

## Keyboard and the key-view loop

| Rule | How |
|---|---|
| Tab visits every field in reading order | The SwiftUI order is view order; fix with `.focused` + `defaultFocus`, not tag hacks |
| Return commits, Escape cancels | `.keyboardShortcut(.defaultAction)` / `.cancelAction` on the buttons; `.onSubmit` for fields |
| First field is focused when the form opens | `.defaultFocus` |
| Full Keyboard Access reaches every control, including pickers and checkboxes | `focusable(interactions:)` on a custom control; never a clickable `Text` |
| AppKit hosts | `window.autorecalculatesKeyViewLoop = true` |

There is no on-screen keyboard to dodge; the Mac has no keyboard toolbar placement. Frequent form commands belong in the menu bar (`menus-and-commands`).

## Settings and inspector forms

- **Settings** apply immediately, with no Save button: `@AppStorage` or a settings model written on change. A setting that needs confirmation (a destructive reset) asks in a sheet.
- Panes are `Form { … }.formStyle(.grouped)` inside tabs (`TabView`), one concern per pane, labels via `LabeledContent`.
- An **inspector** edits the selection: no selection shows an empty state, not a disabled form of blanks; edits write through the model, with undo registered (`documents`).
- A **sheet** form has Cancel (Escape) and a default action (Return) and sets `controlSize` again on the 27 SDK.

## Validation and server errors

A server `422` / ProblemDetails maps field names to the same `AccountErrors`; an unknown field becomes a form-level message in the form's own banner (the persistent inline banner of the desktop rules), never a modal alert. Wire shape and retries are `networking`'s. A failed submit keeps the draft.

## Autofill and passkeys

`textContentType(.username)`, `.password`, `.newPassword`, `.oneTimeCode`, `.emailAddress` on the matching fields; the Passwords app and iCloud Keychain fill from them. Passkey sign-in uses `AuthenticationServices` (`auth0-macos` for the Auth0 flow). Tokens never enter the draft or a log.

## Accessibility

Every field has a visible label (not a placeholder) and the control carries it as its accessibility label; error text is read after the field (`accessibilityElement(children: .combine)` where it groups). Hit areas meet the Mac minimum 20 × 20 pt. Tests locate fields by `accessibilityIdentifier`, PascalCase dot-separated (`test-ids`).

## Common gotchas

- **A placeholder as the only label**: disappears while typing; use a label.
- **Validation per keystroke on an untouched field**: shouts at the user.
- **A Settings pane with a Save button**: Mac settings apply on change.
- **A modal alert for a server error**: use the inline banner.
- **A custom `onTapGesture` row that edits**: unreachable by keyboard.
- **A removed `.roundedBorder`**: on the 27 SDK use `.bordered` and `textInputBorderShape`.
- **Sheet controls the wrong size**: re-apply `controlSize` inside the sheet.

## Handoffs

- Draft model placement → [`architecture`](../architecture/SKILL.md)
- Settings window → [`windows-and-scenes`](../windows-and-scenes/SKILL.md)
- Request and error shape → `networking`; the error banner → `error-handling`
- AppKit field controllers → [`appkit`](../appkit/SKILL.md)
- iOS counterpart → `mobile-ios:forms`
