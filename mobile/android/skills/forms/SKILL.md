---
name: mobile-android-forms
description: Use when building or fixing a Compose form — text-field state, validation timing, KeyboardOptions and KeyboardActions field order, autofill ContentType and Credential Manager, IME insets, submit state, server errors mapped onto fields. Triggers "build a sign-up form", "keyboard hides the field", "autofill not offered", "server errors don't land on fields". Do NOT use for the request (`mobile-android-networking`), state ownership (`-architecture`) or XML forms (`-views-interop`).
---

# Android — Forms

A form is **a draft, a validator and a submit**, all behind the screen ViewModel's one `uiState`. This skill owns field state, validation timing, keyboard and autofill behaviour and how a server rejection lands on a field. The request is [`networking`](../networking/SKILL.md)'s; where the draft lives is [`architecture`](../architecture/SKILL.md)'s. Web analog: [`fe-react-forms`](../../../../frontend/react/skills/forms/SKILL.md) — field-level errors, server errors mapped back, a pending submit that cannot double-fire all carry over; React Hook Form and Zod do not.

## Version lane

| Concern | Primary (Compose BOM 2026.09, Kotlin 2.4) | Brownfield |
|---|---|---|
| Text field state | `TextFieldState` with `BasicTextField` / Material 3 `OutlinedTextField(state = …)` — the state-based API | Value-based `TextField(value, onValueChange)` — correct on older BOMs and in existing screens |
| Autofill | `Modifier.semantics { contentType = ContentType.Username }` | `Modifier.semantics { contentType … }` unavailable below the autofill API of the BOM in use — then `AutofillTree` / Views `autofillHints` |
| Sign-in | Credential Manager 1.6 (passwords + passkeys) | Same; Google Sign-In / One Tap are legacy |
| IME | `enableEdgeToEdge()` + `Modifier.imePadding()` / `WindowInsets.ime` | Same (edge-to-edge is enforced at target 35) |

Confirm the BOM and whether the screen already uses `TextFieldState` before choosing; **match the screen — never mix both APIs in one form.** The state-based API's availability on a given material3 version is re-checked against the release notes before it is written as fact.

## When to use

- A sign-up, sign-in, checkout, profile or search form
- "The keyboard covers the field", "Next should go to the next field", "autofill isn't offered"
- Field-level validation and a server `422` that must mark the offending field
- A wizard whose draft survives rotation and process death

## When NOT to use

- The HTTP call, retries, timeouts → [`networking`](../networking/SKILL.md)
- Where the draft is owned, `SavedStateHandle` → [`architecture`](../architecture/SKILL.md)
- Failure banner and the failed region → `mobile-android-error-handling`
- Stateless composable structure, previews → [`ui-components`](../ui-components/SKILL.md)
- XML `TextInputLayout` forms → [`views-interop`](../views-interop/SKILL.md)
- Passkey and Credential Manager *wiring* → [`device-features`](../device-features/SKILL.md)
- Another stack → `mobile-ios-forms`, `mobile-react-native-forms`

## Inputs needed

- Value-based or state-based text fields already in the project
- Field list, which are required, and the server's validation error shape
- Whether the form signs in (autofill, Credential Manager) or collects a secret

## The shape: draft, validator, submit

The draft is plain immutable data in `uiState`; the validator is a pure function; the ViewModel runs it and owns submit. The composable renders and sends calls up — it never validates.

```kotlin
data class SignUpUiState(
    val email: String = "",
    val password: String = "",
    val errors: Map<SignUpField, FieldError> = emptyMap(),
    val submit: SubmitState = SubmitState.Idle,
)

enum class SignUpField { Email, Password }

sealed interface SubmitState {
    data object Idle : SubmitState
    data object Pending : SubmitState
    data object Done : SubmitState
    data class Failed(val reason: FormFailure) : SubmitState
}

fun validate(state: SignUpUiState): Map<SignUpField, FieldError> = buildMap {
    if (!state.email.contains('@')) put(SignUpField.Email, FieldError.Invalid)
    if (state.password.length < 12) put(SignUpField.Password, FieldError.TooShort(minimum = 12))
}
```

```kotlin
@HiltViewModel
class SignUpViewModel @Inject constructor(
    private val accounts: AccountsRepository,
    private val savedState: SavedStateHandle,
) : ViewModel() {

    val uiState: StateFlow<SignUpUiState>
        field = MutableStateFlow(SignUpUiState(email = savedState.get<String>(EMAIL).orEmpty()))

    fun onEmailChanged(email: String) {
        savedState[EMAIL] = email
        uiState.update { it.copy(email = email, errors = it.errors - SignUpField.Email) }
    }

    fun onSubmit() {
        val current = uiState.value
        if (current.submit is SubmitState.Pending) return
        val errors = validate(current)
        if (errors.isNotEmpty()) {
            uiState.update { it.copy(errors = errors) }
            return
        }
        viewModelScope.launch {
            uiState.update { it.copy(submit = SubmitState.Pending) }
            val outcome = accounts.signUp(current.email, current.password)
            uiState.update { it.copy(submit = outcome.toSubmitState(), errors = outcome.fieldErrors()) }
        }
    }

    private companion object {
        const val EMAIL = "email"
    }
}
```

- **The outcome is a field of `uiState`** (`SubmitState.Done`), consumed by the UI and cleared — never a `Channel` or `SharedFlow` event (decision D26; [`architecture`](../architecture/SKILL.md)). Navigation after success happens in a `LaunchedEffect(state.submit)` that calls the navigator once and then `onSubmitHandled()`.
- **Never put a password in `SavedStateHandle`, `rememberSaveable` or logs** — they survive in the saved-state bundle. A secret field restores empty after process death; the e-mail restores.
- The ViewModel guards `Pending` itself — a disabled button alone is not a double-submit guard.
- Validation rules are one pure function in one file with unit tests ([`unit-testing`](../unit-testing/SKILL.md)); a regex and a length live there, never in a composable.

## The composable

```kotlin
@Composable
fun SignUpScreen(viewModel: SignUpViewModel = hiltViewModel(), onSignedUp: () -> Unit) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    LaunchedEffect(state.submit) {
        if (state.submit is SubmitState.Done) {
            onSignedUp()
            viewModel.onSubmitHandled()
        }
    }
    SignUpContent(
        state = state,
        onEmailChanged = viewModel::onEmailChanged,
        onPasswordChanged = viewModel::onPasswordChanged,
        onSubmit = viewModel::onSubmit,
    )
}

@Composable
fun SignUpContent(
    state: SignUpUiState,
    onEmailChanged: (String) -> Unit,
    onPasswordChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val passwordFocus = remember { FocusRequester() }
    Column(
        modifier = modifier
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        OutlinedTextField(
            value = state.email,
            onValueChange = onEmailChanged,
            label = { Text(stringResource(R.string.email)) },
            isError = SignUpField.Email in state.errors,
            supportingText = { state.errors[SignUpField.Email]?.let { Text(it.message()) } },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
            keyboardActions = KeyboardActions(onNext = { passwordFocus.requestFocus() }),
            modifier = Modifier
                .fillMaxWidth()
                .semantics { contentType = ContentType.EmailAddress }
                .testTag("SignUp.Email"),
        )
        OutlinedTextField(
            value = state.password,
            onValueChange = onPasswordChanged,
            label = { Text(stringResource(R.string.password)) },
            isError = SignUpField.Password in state.errors,
            supportingText = { state.errors[SignUpField.Password]?.let { Text(it.message()) } },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { onSubmit() }),
            modifier = Modifier
                .fillMaxWidth()
                .focusRequester(passwordFocus)
                .semantics { contentType = ContentType.NewPassword }
                .testTag("SignUp.Password"),
        )
        Button(
            onClick = onSubmit,
            enabled = state.submit !is SubmitState.Pending,
            modifier = Modifier.fillMaxWidth().testTag("SignUp.Submit"),
        ) {
            if (state.submit is SubmitState.Pending) CircularProgressIndicator(Modifier.size(20.dp)) else Text(stringResource(R.string.sign_up))
        }
    }
}
```

- `SignUpContent` is stateless and previewable; the screen function is the only one touching the ViewModel ([`ui-components`](../ui-components/SKILL.md)).
- **Test ids** are static PascalCase `Modifier.testTag("SignUp.Email")` — never the label ([`test-ids`](../test-ids/SKILL.md)).
- **A field never shows `error.message` from a framework or server** — a `FieldError` maps to a string resource.

## Keyboard, focus and the IME

- `KeyboardOptions(keyboardType, imeAction, capitalization, autoCorrectEnabled)` per field: `Email` / `Number` / `Phone` / `Password` types; `ImeAction.Next` between fields, `Done` / `Send` / `Search` on the last. `Next` is wired with `KeyboardActions` and a `FocusRequester` (or `LocalFocusManager.moveFocus(FocusDirection.Down)`), because Compose does not infer the order.
- `autoCorrectEnabled = false` and `KeyboardType.Password` (or `VisualTransformation`) for a secret; a secret never offers suggestions.
- **The IME must not hide the focused field**: edge-to-edge activity (`enableEdgeToEdge()`, `android:windowSoftInputMode="adjustResize"` where Views remain) plus `Modifier.imePadding()` on the scrolling container, and `Modifier.bringIntoViewRequester` for a field deep in a long form. Test with the keyboard open in landscape and at 200 % font scale.
- A scrolling form is `verticalScroll` on a short, bounded `Column`; a long or unbounded one is a `LazyColumn` ([`ui-components`](../ui-components/SKILL.md)).
- Dismiss the keyboard on submit (`LocalSoftwareKeyboardController.current?.hide()`) and on scroll.

## Validation timing

Errors raise on focus loss or submit, clear on edit, and are text plus `isError` — never colour alone; async checks are debounced with `collectLatest`. The full table is in [`references/validation-autofill-wizards.md`](references/validation-autofill-wizards.md).

## Server errors land on the field

Parse the response in [`networking`](../networking/SKILL.md) into a typed `ApiError.Validation(fields: Map<String, List<String>>)` (ProblemDetails `errors`); the ViewModel maps wire names to `SignUpField` and writes them to `uiState.errors`. An unmapped field name becomes a **form-level** error above the button — never dropped. A `409` (taken, stale version) marks its field or the form; a `5xx` / timeout leaves the form **editable with its values intact** and raises the failure banner (`mobile-android-error-handling`); a double tap during `Pending` is ignored; the idempotency key is created once per draft.

## Autofill and sign-in

`ContentType` on every autofillable field; sign-in goes through Credential Manager 1.6 (wiring in [`device-features`](../device-features/SKILL.md)). Details in [`references/validation-autofill-wizards.md`](references/validation-autofill-wizards.md).

## Wizards

One ViewModel, one draft, a `step` in `uiState`; secrets never restore. See [`references/validation-autofill-wizards.md`](references/validation-autofill-wizards.md).

## Rules

- One draft in `uiState`, one pure validator, one submit guarded in the ViewModel.
- `TextFieldState` or value-based fields — match the screen, never both.
- Keyboard type and `ImeAction` set per field; `Next` wired with `FocusRequester`.
- `imePadding()` plus edge-to-edge so the IME never covers the focused field.
- Errors appear on focus loss or submit, clear on edit, are text plus `isError`.
- Server field errors map onto fields; unmapped ones show at form level.
- `ContentType` on autofillable fields; sign-in through Credential Manager.
- Secrets are never in `SavedStateHandle`, `rememberSaveable`, logs or analytics.
- Every field and the submit button carry a static `testTag`.

## What NOT to do

- No `TextField` whose `value` is a `remember { mutableStateOf("") }` copy of ViewModel state — it desynchronises.
- No validation inside `onValueChange` that raises errors before the user leaves the field.
- No `error.message`, `localizedMessage` or HTTP status text in `supportingText`.
- No submit button whose only guard is `enabled = …` — the ViewModel guards too.
- No `Channel` / `SharedFlow` event to say "submitted" or "show error" (D26).
- No `rememberSaveable` password; no `GlobalScope` for Credential Manager; no Google One Tap in new code.
- No `android:windowSoftInputMode="adjustPan"` as the fix for a covered field in a Compose screen.
- No regex or length rule inline in a composable.

## Generation steps

1. Read an existing form, the ViewModel style, and whether fields are value- or state-based; detect the BOM.
2. Write the `uiState` draft, `FieldError` cases and the pure `validate`.
3. Write the ViewModel (submit guard, `SavedStateHandle` for non-secrets) and the stateless content composable.
4. Set `KeyboardOptions`, `KeyboardActions`, focus order, `ContentType`, `imePadding()`.
5. Map the server `Validation` error onto fields in the ViewModel.
6. Add `testTag`s and a preview per state (empty, errors, pending).
7. Write validator and ViewModel unit tests with a fake repository.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean; detekt, ktlint and Android Lint (compose-lints) pass.
- On a device with the IME open in landscape and font scale 200 %: the focused field and its error stay visible; `Next` walks the fields in order; `Done` submits.
- A `422` marks the named field; a timeout keeps the typed values and shows the banner; rotation and process death keep the e-mail and drop the password.
- TalkBack reads label, value and error together; autofill offers a saved credential.
- Dev-side tests (validator, ViewModel with a fake, Compose UI test v2): [`unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- Request, budgets, ProblemDetails parsing → [`networking`](../networking/SKILL.md)
- Draft persistence, secrets storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Credential Manager, passkeys, biometrics → [`device-features`](../device-features/SKILL.md)
- Failure banner, failed region → `mobile-android-error-handling`
- Labels, 48 dp, TalkBack → `mobile-android-accessibility`
- Test ids → [`test-ids`](../test-ids/SKILL.md)
