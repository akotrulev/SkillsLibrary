---
name: forms
description: Use when building WinUI forms: input controls, ObservableValidator, NumberBox, focus and tab order, server errors on fields. Triggers "add a form". Not for dialogs (ui-components).
---

# Windows — Forms and Input

How a form is built in WinUI: **the right input control per value, `ObservableValidator` rules that live on the view model, errors shown at the field, a complete tab order, and server errors mapped back to the field that caused them.** Audit rows: section G of `desktop-windows:standards-audit`. Design facts: `design/ui-ux-pro-max --stack winui`.

## Version lane

| Concern | WinUI on WinAppSDK 2.6 (primary) | Note |
|---|---|---|
| Validation | `CommunityToolkit.Mvvm` 8.4.2 `ObservableValidator` + `System.ComponentModel.DataAnnotations` | WinUI has no built-in `INotifyDataErrorInfo` visuals: the form shows errors itself |
| Controls | `TextBox`, `PasswordBox`, `NumberBox`, `ComboBox`, `AutoSuggestBox`, `CheckBox`, `ToggleSwitch`, `RadioButtons`, `CalendarDatePicker`, `DatePicker`, `TimePicker`, `Slider`, `RatingControl`, `ColorPicker`, `TokenizingTextBox` | `TokenizingTextBox`, `SettingsCard` are Community Toolkit; the rest ship in WinUI |
| Experimental | `TableView`, `Chart`, Ink | never in a production form |
| Binding | `x:Bind … Mode=TwoWay` | `UpdateSourceTrigger` is explicit (below) |
| WPF / WinForms | `Binding` + `IDataErrorInfo` / `ErrorProvider` | → `desktop-windows:wpf`, `:winforms` |

## When to use

- Any screen that edits a value: sign-in, settings, create/edit, search filters
- "Validate this field", "show the server's error under the input", "what is the tab order?"

## When NOT to use

- Confirm / destructive dialogs, `InfoBar`, `ContentDialog` → [`ui-components`](../ui-components/SKILL.md)
- State ownership, DI → [`architecture`](../architecture/SKILL.md)
- Sending the form over HTTP, ProblemDetails → `desktop-windows:networking`
- Narrator and labels audit → `desktop-windows:accessibility`; ids → `desktop-windows:test-ids`

---

## Pick the control by the value

| Value | Control | Never |
|---|---|---|
| Short text | `TextBox` with `InputScope`, `PlaceholderText` as a hint only | a placeholder as the label |
| Secret | `PasswordBox` (`PasswordRevealMode="Peek"`) | a `TextBox` with masked text |
| Number | `NumberBox` (`Minimum`, `Maximum`, `SmallChange`, `SpinButtonPlacementMode`, `NumberFormatter`) | a `TextBox` parsed by `int.Parse` |
| Date | `CalendarDatePicker` (one date, a range limit through `MinDate` / `MaxDate`) or `DatePicker` (birth date) | a free-text date |
| Time | `TimePicker` | two `NumberBox`es |
| One of 2–4 | `RadioButtons` | a `ComboBox` |
| One of 5+ | `ComboBox`; searchable: `AutoSuggestBox` | a `ListView` for a form field |
| On/off applied now | `ToggleSwitch` | a `CheckBox` |
| On/off with a Save | `CheckBox` | a `ToggleSwitch` |
| Free choice among many with typing | `AutoSuggestBox`, `TokenizingTextBox` | a custom popup |
| Long text | `TextBox AcceptsReturn="True" TextWrapping="Wrap"` with a bounded height and `ScrollViewer` | a fixed-height box that clips |

- Every input has a **visible `Header`** (or a `TextBlock` + `AutomationProperties.LabeledBy`) and an accessible name. Required fields say so in the header, not by colour alone.
- **`InputScope`** (`Number`, `EmailSmtpAddress`, `Url`, `Search`) for touch and IME; **`IsSpellCheckEnabled="False"`** on ids, codes and emails.
- **`NumberBox` hands back `NaN` when empty:** treat `double.IsNaN` as "no value" in the view model, never save it.
- **Text scaling is never locked** (`IsTextScaleFactorEnabled` stays `true`) and a form reflows at 200 % text.

## Validation — `ObservableValidator` on the view model

```csharp
public sealed partial class ProfileFormViewModel : ObservableValidator
{
    [ObservableProperty]
    [NotifyDataErrorInfo]
    [Required(ErrorMessage = "Enter your name.")]
    [MaxLength(80, ErrorMessage = "Use 80 characters or fewer.")]
    public partial string Name { get; set; } = string.Empty;

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [EmailAddress(ErrorMessage = "Enter a valid email address.")]
    public partial string Email { get; set; } = string.Empty;

    [ObservableProperty]
    [NotifyDataErrorInfo]
    [Range(18, 120, ErrorMessage = "Age must be between 18 and 120.")]
    public partial double Age { get; set; } = 18;

    [RelayCommand(CanExecute = nameof(CanSave))]
    private async Task SaveAsync(CancellationToken ct)
    {
        ValidateAllProperties();
        if (HasErrors) return;
        await _profiles.UpdateAsync(ToRequest(), ct);
    }

    private bool CanSave() => !IsSaving;
}
```

- `[NotifyDataErrorInfo]` validates when the property changes; `ValidateAllProperties()` runs on submit so untouched fields are checked too. **Partial properties** need no preview language version on C# 14; a project still on field-style `[ObservableProperty]` keeps one style per project (`C1`).
- **Rules are data annotations or one `ValidationAttribute` per rule** — never validation in code-behind, never in the control's event handler.
- **Cross-field rules** (`EndDate >= StartDate`) are a `[CustomValidation]` method on the view model or an `ObservableValidator.ValidateProperty` call in the dependent setter.
- **Error text is a user message**, specific and actionable ("Enter a valid email address."), not a code and not `Exception.Message`. Messages come from resources when the app is localized (`desktop-windows:languages`).
- **When to show:** on **lost focus** for the first time, then **live** while the field is invalid; never on first keystroke of an untouched field, never all at once on load. On submit, show all and **move focus to the first invalid field**.
- **Never block typing:** no `BeforeTextChanging` rejection except for a hard format (digits only); the user may paste something and fix it.
- **Never swallow a rule:** a field the user cannot fix (a server-derived value) is read-only text, not an input that always fails.

### Show the error at the field

WinUI inputs do not draw `INotifyDataErrorInfo` errors on their own. Show them with one reusable pattern: a `TextBlock` under the field bound to the first error, an error `Foreground` from a theme brush **plus an icon or text** (never colour alone), and `AutomationProperties.HelpText` / `LiveSetting="Polite"` so Narrator announces it.

```xml
<StackPanel Spacing="4">
    <TextBox Header="Email" Text="{x:Bind ViewModel.Email, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}"
             InputScope="EmailSmtpAddress" IsSpellCheckEnabled="False"
             AutomationProperties.AutomationId="Profile.Form.Email"
             AutomationProperties.LabeledBy="{x:Bind EmailHeader}"/>
    <TextBlock x:Name="EmailError" Foreground="{ThemeResource SystemFillColorCriticalBrush}"
               Text="{x:Bind ViewModel.EmailError, Mode=OneWay}"
               Visibility="{x:Bind ViewModel.HasEmailError, Mode=OneWay}"
               AutomationProperties.LiveSetting="Polite"
               AutomationProperties.AutomationId="Profile.Form.Email.Error"/>
</StackPanel>
```

`EmailError` is a view-model property computed from `GetErrors(nameof(Email))`; keep the mapping in the view model, not in a converter per field. `UpdateSourceTrigger=PropertyChanged` is set only on fields that validate live.

## Server errors map back to the field

A `400` with a ProblemDetails `errors` dictionary (`{"email": ["…"]}`) is the server telling you which field failed (`desktop-windows:networking`).

- **Map by field name** to the view model's error store (`SetServerError(nameof(Email), message)`), clear it when the user edits that field, and **move focus to the first mapped field**.
- **A field the form does not have** (`""` or an unknown key) becomes the form-level message in the `InfoBar`, never dropped.
- **A `409` conflict or a `5xx`** is not a field error: the form stays editable, the user's input is **kept**, and one persistent `InfoBar` explains it (CLAUDE.md § Desktop code rules). A transport failure is told apart from a server failure (offline vs error).
- **Never show the server's raw message** or a stack; use the typed reason's user text.
- **Double submit:** `IsSaving` disables the command (`CanExecute`) and shows a `ProgressRing`; the command takes a `CancellationToken` that a window close cancels.

## Focus and tab order

- **Tab order follows reading order.** Lay the form out in a single column in that order so the default visual order is correct; set `TabIndex` only to repair a layout that cannot be reordered, and set it for the whole form or not at all.
- **`IsTabStop="False"`** on decoration; a custom control that takes focus gets `IsTabStop="True"` and a visible focus rectangle (never remove `FocusVisualPrimaryBrush`).
- **First field focused on load:** `Loaded` → `FocusManager.TryFocusAsync` on the first input, only when the page is a form (never in a list or reader).
- **`Enter` submits** a single-purpose form (`AcceptButton` equivalent: a `KeyboardAccelerator` on the form with `Enter`, or the primary button in a `ContentDialog`); `Esc` cancels. A multi-line `TextBox` keeps `Enter` for new lines.
- **Dialog forms:** `PrimaryButtonText` is the action, named for it ("Save", "Create"), `IsPrimaryButtonEnabled` follows validity, and `Closing` is cancelled while the form is invalid — see `D7`.
- **After a failed submit,** focus goes to the first invalid field and Narrator reads its error; after a success, focus goes somewhere meaningful (the next step or the list), never to nowhere.
- **Access keys** for the primary fields and buttons (`AccessKey="N"`) where the form is dense → `desktop-windows:windows-and-navigation`.

## Three states and unsaved work

- A form that **loads data** (edit) has loading, loaded and failed states like any data region ([`ui-components`](../ui-components/SKILL.md)): a failed load shows the banner and a Retry, not an empty form that would overwrite data on Save.
- **Unsaved changes:** the view model tracks `IsDirty`; closing the window or navigating away with a dirty form asks first (`desktop-windows:windows-and-navigation`).
- **Drafts of long text** may persist locally; never persist a `PasswordBox` value.

## Secrets in forms

`PasswordBox` only; never log or `Debug.WriteLine` field values; clear the secret from the view model after use; no autofill into non-credential fields. Credentials go to `PasswordVault` / DPAPI, never a settings file (`desktop-windows:offline-and-storage`).

## Telemetry

A submit adds a `form.submitted` metric with the form name and outcome (`ok`, `invalid`, `server_error`), a log at the decision, and a span around the save. Never field values.

## Common gotchas

- **`NumberBox` empty → `NaN` saved as a value** — guard it.
- **`Text` bound `TwoWay` with the default trigger** — updates on lost focus only; set `UpdateSourceTrigger=PropertyChanged` where live validation is wanted.
- **Errors shown only by a red border** — add text and the live region.
- **`ValidateAllProperties()` skipped** — untouched required fields submit.
- **`ContentDialog` closes on an invalid primary click** — cancel in `Closing`.
- **Placeholder used as the label** — it disappears and Narrator may not read it.
- **`TabIndex` set on half the form** — the unset half sorts after the set half.
- **Server error dropped when the field is unknown** — surface it in the banner.

## Handoffs

- Dialog and `InfoBar` rules → [`ui-components`](../ui-components/SKILL.md); view-model shape → [`architecture`](../architecture/SKILL.md)
- Windows, access keys, accelerators → `desktop-windows:windows-and-navigation`
- ProblemDetails, retry → `desktop-windows:networking`; localized messages → `desktop-windows:languages`
- Labels, Narrator, High Contrast → `desktop-windows:accessibility`; `AutomationId` → `desktop-windows:test-ids`
- Mac counterpart → `desktop-macos:forms`
