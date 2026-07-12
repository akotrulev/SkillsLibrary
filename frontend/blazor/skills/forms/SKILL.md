---
name: fe-blazor-forms
description: Use when the user asks to build or improve a Blazor form (.NET 8/9/10) — `EditForm`, `DataAnnotationsValidator`, `AddValidation()` + `[ValidatableType]` nested validation (net10), `FluentValidationValidator`, async validation, server-side error mapping (ProblemDetails), file uploads, multi-step wizards, accessibility. Triggers: "build a Blazor form for X", "wire FluentValidation in Blazor", "validate nested objects in a Blazor form", "server-side errors on Blazor form", "multi-step wizard in Blazor", "accessible Blazor inputs". Do NOT use for state management (use `frontend/blazor/skills/state-management`), component scaffolding (use `frontend/blazor/skills/generator`), or React (use `frontend/react/skills/forms`).
---

# Blazor Forms

The house pattern: **`EditForm` + `FluentValidation` (default)** or **`DataAnnotationsValidator` (simpler cases)**, validated against a strongly-typed record/class, with server-side errors mapped into the form's `EditContext`, accessibility baked in, and submission state managed cleanly. Applies to .NET 8/9/10; net10 widens what DataAnnotations alone can cover (nested objects via `AddValidation()` + `[ValidatableType]`) — version notes inline.

## When to use

- Any form past a single field
- Replacing scattered ad-hoc validation with a single source of truth
- Wiring server-side validation errors back onto the form
- Multi-step / wizard forms
- File upload forms

## When NOT to use

- State management at large → `frontend/blazor/skills/state-management`
- Component scaffolding → `frontend/blazor/skills/generator`
- React → `frontend/react/skills/forms`
- Auth UI specifics (login / signup) → `auth/auth0-blazor`

## Default stack

- `<EditForm>` (Blazor built-in)
- **FluentValidation** (`FluentValidation.Blazor` or `Blazored.FluentValidation`) — preferred for any non-trivial validation
- DataAnnotations as a fallback for very simple forms
- `<InputText>` / `<InputNumber>` / `<InputSelect>` / `<InputCheckbox>` / `<InputDate>` — Microsoft's typed input components
- `<ValidationSummary>` + `<ValidationMessage For="...">` for surfacing errors

## Minimal recipe (DataAnnotations)

```csharp
public sealed class CreateOrderModel
{
    [Required, EmailAddress, MaxLength(254)]
    public string CustomerEmail { get; set; } = "";

    [Range(1, 100)]
    public int Quantity { get; set; } = 1;

    [MaxLength(500)]
    public string? Notes { get; set; }
}
```

```razor
@page "/orders/new"
@inject ApiClient Api
@inject NavigationManager Nav

<h1>New order</h1>

<EditForm Model="@_model" OnValidSubmit="HandleValidSubmitAsync" @ref="_form">
    <DataAnnotationsValidator />
    <ValidationSummary />

    <div>
        <label for="email">Email</label>
        <InputText id="email" @bind-Value="_model.CustomerEmail" aria-invalid="@_form?.EditContext?.GetValidationMessages(() => _model.CustomerEmail).Any()" />
        <ValidationMessage For="@(() => _model.CustomerEmail)" />
    </div>

    <div>
        <label for="qty">Quantity</label>
        <InputNumber id="qty" @bind-Value="_model.Quantity" />
        <ValidationMessage For="@(() => _model.Quantity)" />
    </div>

    <div>
        <label for="notes">Notes</label>
        <InputTextArea id="notes" @bind-Value="_model.Notes" />
        <ValidationMessage For="@(() => _model.Notes)" />
    </div>

    @if (!string.IsNullOrEmpty(_rootError))
    {
        <p role="alert">@_rootError</p>
    }

    <button type="submit" disabled="@_submitting" aria-busy="@_submitting">
        @(_submitting ? "Saving…" : "Create order")
    </button>
</EditForm>

@code {
    private CreateOrderModel _model = new();
    private EditForm? _form;
    private bool _submitting;
    private string? _rootError;

    private async Task HandleValidSubmitAsync()
    {
        _submitting = true;
        _rootError  = null;
        try
        {
            await Api.CreateOrderAsync(_model);
            Nav.NavigateTo("/orders");
        }
        catch (FieldServerException fx)
        {
            ApplyServerErrors(fx);
        }
        catch (Exception)
        {
            _rootError = "Submission failed. Try again.";
        }
        finally
        {
            _submitting = false;
        }
    }

    private void ApplyServerErrors(FieldServerException fx)
    {
        var ctx = _form!.EditContext!;
        var store = new ValidationMessageStore(ctx);
        foreach (var (field, messages) in fx.Errors)
        {
            var identifier = new FieldIdentifier(_model, field);
            foreach (var m in messages) store.Add(identifier, m);
        }
        ctx.OnFieldChanged += (_, e) => store.Clear(e.FieldIdentifier);
        ctx.NotifyValidationStateChanged();
    }
}
```

## Nested validation with `AddValidation()` + `[ValidatableType]` (net10)

On net8/net9, `DataAnnotationsValidator` only validates top-level properties — nested objects and collections silently pass, which is a classic reason to jump to FluentValidation. net10 closes that gap:

```csharp
// Program.cs
builder.Services.AddValidation();

// Models.cs — models must live in .cs files (source-generator based)
[ValidatableType]                       // root model only; experimental attribute
public sealed class CheckoutModel
{
    public CustomerModel Customer { get; set; } = new();
    public List<OrderLineModel> Lines { get; set; } = [];
}

public sealed class CustomerModel
{
    [Required, EmailAddress] public string Email { get; set; } = "";
}
```

The component keeps the plain `<DataAnnotationsValidator />` — nested and collection members now validate. Class-level `ValidationAttribute`s on a model cover simple cross-field rules.

**When DataAnnotations now suffices (net10):** per-field rules + nested shapes + simple cross-field checks. **Still switch to FluentValidation** (house default on all TFMs) for conditional rules, async rules, RuleSets/wizards, and reusable validator composition. Never mix both on one model.

## FluentValidation (house default for non-trivial)

DataAnnotations runs out of expressiveness fast (conditional, async, per-step RuleSets — and on net8/net9, anything nested). Switch to FluentValidation:

```csharp
public sealed class CreateOrderValidator : AbstractValidator<CreateOrderModel>
{
    public CreateOrderValidator()
    {
        RuleFor(x => x.CustomerEmail).NotEmpty().EmailAddress().MaximumLength(254);
        RuleFor(x => x.Quantity).InclusiveBetween(1, 100);
        RuleFor(x => x.Notes).MaximumLength(500);

        // Cross-field
        RuleFor(x => x.Quantity)
            .LessThanOrEqualTo(10)
            .When(x => x.CustomerEmail.EndsWith("@trial.example"))
            .WithMessage("Trial accounts limited to 10 items");

        // Async
        RuleFor(x => x.CustomerEmail)
            .MustAsync(async (email, ct) => await CheckEmailAllowedAsync(email, ct))
            .WithMessage("This email is on a deny list");
    }
}
```

```razor
<EditForm Model="@_model" OnValidSubmit="HandleValidSubmitAsync">
    <FluentValidationValidator />
    <ValidationSummary />
    @* ... same input pattern ... *@
</EditForm>
```

Register the validator in DI:

```csharp
builder.Services.AddValidatorsFromAssemblyContaining<CreateOrderValidator>();
```

## Server-side errors → form

The library's APIs emit `ProblemDetails` with an `errors` dictionary keyed by field name (matches `qa/api-test-author/generator/dotnet`). Translate that into form messages:

```csharp
public sealed class FieldServerException : Exception
{
    public IReadOnlyDictionary<string, IReadOnlyList<string>> Errors { get; }
    public FieldServerException(IReadOnlyDictionary<string, IReadOnlyList<string>> errors)
        : base("Field validation failed") { Errors = errors; }
}

public class ApiClient(HttpClient http)
{
    public async Task CreateOrderAsync(CreateOrderModel model)
    {
        var res = await http.PostAsJsonAsync("/api/orders", model);
        if (res.IsSuccessStatusCode) return;

        if (res.StatusCode == HttpStatusCode.BadRequest)
        {
            var problem = await res.Content.ReadFromJsonAsync<ProblemDetailsDto>()
                          ?? throw new Exception("Malformed error response");
            if (problem.Errors is { Count: > 0 })
                throw new FieldServerException(problem.Errors);
        }

        res.EnsureSuccessStatusCode();
    }
}
```

Inside the page, push each error into a `ValidationMessageStore` keyed to the right `FieldIdentifier`. The example above (`ApplyServerErrors`) does this. The user sees per-field errors that look identical to client-side validation errors.

## Accessibility — non-negotiable

Every input:

1. `<label for="...">` paired with the input's `id`
2. `aria-invalid` reflects the field's invalid state
3. The error from `<ValidationMessage>` is rendered with `role="alert"` (Blazor's default `<ValidationMessage>` markup doesn't include `role="alert"` — wrap it or use a custom message component)
4. Submit button `disabled` + `aria-busy` while submitting
5. After submission errors, focus moves to the first error (or to a focused summary)

Helper for "move focus to first error":

```razor
@inject IJSRuntime JS

@code {
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        var ctx = _form?.EditContext;
        if (ctx is null) return;
        var hasErrors = ctx.GetValidationMessages().Any();
        if (hasErrors)
        {
            // Move focus to the first input with [aria-invalid='true']
            await JS.InvokeVoidAsync("eval",
                "document.querySelector('input[aria-invalid=\"true\"], textarea[aria-invalid=\"true\"], select[aria-invalid=\"true\"]')?.focus()");
        }
    }
}
```

(Better: a small `focus-first-invalid.js` collocated module — see `frontend/blazor/skills/generator` for the collocated JS pattern.)

## Custom `<ValidationMessage>` with `role="alert"`

Wrap the built-in:

```razor
@* Components/FieldError.razor *@
@typeparam TValue
@if (_errors.Any())
{
    <p role="alert" class="field-error">@string.Join("; ", _errors)</p>
}

@code {
    [Parameter] public Expression<Func<TValue>> For { get; set; } = default!;
    [CascadingParameter] public EditContext? EditContext { get; set; }

    private IEnumerable<string> _errors = Array.Empty<string>();

    protected override void OnParametersSet()
    {
        var id = FieldIdentifier.Create(For);
        _errors = EditContext?.GetValidationMessages(id) ?? Array.Empty<string>();
    }
}
```

Now every field error gets announced to screen readers.

## Multi-step wizards

Two patterns:

1. **One model + one validator + paginated rendering** — model carries all fields; the validator scopes per step via `RuleSet`s
2. **One model per step + a final merged step**

```csharp
public sealed class CheckoutValidator : AbstractValidator<CheckoutModel>
{
    public CheckoutValidator()
    {
        RuleSet("Step1", () => RuleFor(x => x.Email).NotEmpty().EmailAddress());
        RuleSet("Step2", () => RuleFor(x => x.Address).SetValidator(new AddressValidator()));
        RuleSet("Step3", () => RuleFor(x => x.PaymentToken).NotEmpty());
    }
}
```

Validate per step in `OnValidSubmit` of the per-step form; let the user advance only when the step is valid. On the final submit, run the default ruleset to enforce all rules.

## File uploads

`<InputFile>`:

```razor
<InputFile OnChange="HandleFile" multiple accept=".pdf,.png" />

@code {
    private async Task HandleFile(InputFileChangeEventArgs e)
    {
        foreach (var file in e.GetMultipleFiles(maxAllowedFiles: 5))
        {
            if (file.Size > 5 * 1024 * 1024) { /* reject — show error */ continue; }
            await using var stream = file.OpenReadStream(maxAllowedSize: 5 * 1024 * 1024);
            await Api.UploadAsync(file.Name, stream);
        }
    }
}
```

For large files, upload to a signed URL (S3 presigned / Azure Blob SAS) directly from the browser, then submit only the metadata via the form — keeps the server out of the bandwidth path.

## Anti-patterns

- **Mixing DataAnnotations and FluentValidation** in the same model — pick one
- **Manual `Model.Field` checks** inside `OnSubmit` instead of using the validator
- **Submit button without `disabled` during submit** — double-submits + duplicate writes
- **Server errors thrown into a generic banner** when the API gave you a field map
- **Custom inputs that don't bind via `@bind`** — break two-way data flow and EditContext tracking
- **Forms without labels** — accessibility fails immediately
- **`OnSubmit` instead of `OnValidSubmit`** — runs even on invalid forms

## Rules

- `<EditForm>` is mandatory; use `OnValidSubmit` (not `OnSubmit`)
- One validator per model — FluentValidation default; DataAnnotations for trivial forms (on net10 with `AddValidation()` + `[ValidatableType]`, "trivial" includes nested shapes)
- Inputs via the typed `<Input*>` components
- Labels paired with input `id`s
- Errors rendered with `role="alert"` (custom `FieldError` component)
- Submit button `disabled` + `aria-busy` while submitting
- Focus moves to first error on submission failure
- Server `ProblemDetails.errors` mapped into `ValidationMessageStore`
- Wizards split via `RuleSet` (FV) or per-step models
- Large file uploads bypass the server via signed URLs

## What NOT to do

- No `<form>` without `<EditForm>` for any non-trivial form
- No `OnSubmit` when `OnValidSubmit` does what you want
- No DataAnnotations + FluentValidation together
- No raw `<input>` without `<InputText>` / equivalent (loses EditContext binding)
- No submit without `disabled` guard
- No "Something went wrong" banner when the API returned per-field errors
- No file uploads piped through the Blazor Server SignalR channel for large files — use the signed-URL pattern
- No validation logic inside the component instead of the validator
- No `EditForm` without a validator component (`<DataAnnotationsValidator />` or `<FluentValidationValidator />`)

## Generation steps

1. Confirm fields, validation rules, server error shape, and Server vs WASM render mode.
2. Author the model + validator (FluentValidation default).
3. Generate the `<EditForm>` component with `<Input*>` controls, labels, ValidationMessages (or custom `FieldError`).
4. Wire the submit handler with try/catch mapping `FieldServerException` to `ValidationMessageStore`.
5. Add the focus-first-error helper after submit failure.
6. For wizards, structure the model + RuleSets.
7. Smoke locally: valid submit, client-validation fail, server-side fail.

## Handoffs

- State management → `frontend/blazor/skills/state-management`
- Component scaffolding → `frontend/blazor/skills/generator`
- Auth-protected forms → `auth/auth0-blazor`
- API contract → `qa/api-test-author/generator/dotnet`
- React equivalent → `frontend/react/skills/forms`
