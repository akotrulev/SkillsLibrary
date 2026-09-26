---
name: fe-blazor-languages
description: Use when a Blazor app (.NET 8/9/10) must support multiple languages — `IStringLocalizer<T>` + `.resx`, the two culture pipelines (Server = `RequestLocalization` + culture cookie; WASM = startup culture, satellite assemblies), the cookie-based culture switch, `@bind:culture`, RTL. Triggers: "add multi-language support", "let users switch language", "why are my WASM dates in the wrong culture". Do NOT use for display-format policy (`ui-rules`) or i18n test assertions (qa `language-testing`).
---

# Blazor — Localization & Globalization

Owns the **mechanics** of running a Blazor UI in multiple languages and cultures: resource files and `IStringLocalizer`, how the *current culture* is established (which differs radically by render mode), letting a user switch language, and culture-correct formatting of numbers/dates/money. It does **not** decide the app's canonical display formats — that policy (one date/money/percent format app-wide, timezone labeled, through shared helpers) is [`ui-rules`](../ui-rules/SKILL.md)'; this skill makes those helpers *culture-aware*.

**Two words that are not the same:** **globalization** = formatting values for a culture (`CurrentCulture`, always active, even in a single-language app); **localization** = swapping *text* per culture (`IStringLocalizer` + `.resx`). You can need one without the other.

**Version rule:** `IStringLocalizer`/`.resx`, `RequestLocalizationOptions`, the cookie switch, and `@bind:culture` are **identical across net8/9/10**. The render-mode split (Server vs WASM culture pipeline) is a net8+ Blazor-Web-App reality, unchanged through net10. Nothing here is net10-only; the net10 docs refresh clarified the guidance but added no new API. Apply the same recipe to all three TFMs.

## When to use

- Standing up multi-language support (resource files, localizer injection, `@Loc["Key"]`)
- Establishing the current culture correctly for Server, WASM, or a mixed Blazor Web App
- A language switcher users can operate, persisted across visits
- Culture-correct number/date/currency display and input parsing
- Right-to-left layout enablement

## When NOT to use

- The app's canonical format-per-data-type policy, humanized enums, GUID→name → [`ui-rules`](../ui-rules/SKILL.md) (localization supplies the culture; ui-rules owns the policy)
- RTL styling mechanics (logical properties, mirrored icons) beyond setting `dir` → [`styling`](../styling/SKILL.md) + [`responsive-design`](../responsive-design/SKILL.md)
- Validation-message wording/voice → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md); the *plumbing* of localized validation messages is here + [`forms`](../forms/SKILL.md)
- Asserting translations/culture behavior in tests → the qa **`language-testing`** peer (locale-pinned assertions, pseudo-loc, RTL) — a peer, not loaded here

## The shared half: resources + `IStringLocalizer`

Same in every render mode. Register once, key text to `.resx`, inject the localizer.

```csharp
builder.Services.AddLocalization();   // resources under /Resources by convention
```
```razor
@inject IStringLocalizer<Home> Loc
<h1>@Loc["Greeting"]</h1>          @* falls back to the key if no resource matches *@
<p>@Loc["ItemCount", count]</p>    @* composite-format args flow through *@
```

- **Resource layout:** `Resources/Pages/Home.en.resx`, `Home.fr.resx`, … keyed by the component's type. The `RootNamespace`/folder must line up or the localizer silently returns keys.
- **`.resx` per culture** compiles into **satellite assemblies** (`fr/App.resources.dll`) — the unit WASM downloads on demand and Server loads in-process.
- **Never hardcode UI strings** once localization is on — a literal in markup is invisible to translation. Keys are stable identifiers, not English sentences.
- Localize **`DataAnnotations`/FluentValidation messages** through the same localizer so form errors translate — see [`forms`](../forms/SKILL.md).

## The split half: establishing `CurrentCulture` — Server vs WASM

This is where Blazor localization actually gets hard. The render mode decides the pipeline.

```
Which render mode serves this component?
  Interactive Server / static SSR (culture lives on the server, per request/circuit)
    → RequestLocalizationOptions middleware + a culture cookie
  WASM (culture lives in the browser, set before the app boots)
    → set CultureInfo at startup (autostart=false) + satellite assemblies + ICU data
  Blazor Web App with BOTH  → use the cookie approach so server and client agree
```

### Interactive Server / static SSR

Culture is a **per-request/per-circuit** value on the server. Wire the middleware and read culture from a cookie:

```csharp
var cultures = new[] { "en", "fr", "de", "ar" };
app.UseRequestLocalization(new RequestLocalizationOptions()
    .SetDefaultCulture("en")
    .AddSupportedCultures(cultures)
    .AddSupportedUICultures(cultures));
// CookieRequestCultureProvider is included by default and read first.
```

- Put `UseRequestLocalization` **before** the Blazor endpoints so the circuit inherits the resolved culture.
- The default provider order is **cookie → `Accept-Language` → default**. The cookie is what a switcher writes.

### WASM

Culture is set **once, in the browser, before the app runs** — you can't change it mid-run without a reload. Stop autostart, set the culture, then start:

```html
<!-- index.html / App: prevent autostart so we can pick culture first -->
<script src="_framework/blazor.webassembly.js" autostart="false"></script>
```
```csharp
// Program.cs — read the persisted choice, set BOTH before RunAsync
var culture = await GetPersistedCultureAsync(host);   // e.g. from localStorage
CultureInfo.DefaultThreadCurrentCulture   = new CultureInfo(culture);
CultureInfo.DefaultThreadCurrentUICulture = new CultureInfo(culture);
await host.RunAsync();
```

- **ICU data:** full globalization needs the ICU dataset. `<BlazorWebAssemblyLoadAllGlobalizationData>true</BlazorWebAssemblyLoadAllGlobalizationData>` ships the complete set (large — measure against [`performance`](../performance/SKILL.md) budgets) or use a custom ICU shard for only the cultures you support.
- **`<InvariantGlobalization>` must be `false`** — if it's true (sometimes set for size), every culture collapses to invariant and formatting/localization silently no-op.
- Satellite assemblies are lazy-loaded per selected culture; only the active culture's `.dll` downloads.

## Switching language at runtime — the cookie pattern (works for both)

The robust, render-mode-agnostic switch: write a culture cookie, then **force a full reload** so the server middleware (SSR/Server) re-resolves and WASM re-boots with the new culture. A SPA-smooth in-place swap is not reliable across the Blazor Web App boundary — the reload is the feature, not a workaround.

```csharp
// A minimal endpoint the switcher posts to (Server/SSR); sets the culture cookie, redirects back.
app.MapPost("/culture/set", (string culture, string redirectUri, HttpContext ctx) =>
{
    ctx.Response.Cookies.Append(
        CookieRequestCultureProvider.DefaultCookieName,
        CookieRequestCultureProvider.MakeCookieValue(new RequestCulture(culture)));
    return Results.LocalRedirect(redirectUri);
});
```

- On **WASM-only**, persist to `localStorage` instead and `forceLoad`-navigate to re-run `Program.cs`.
- Persist the choice so returning users keep their language; default from `Accept-Language` on first visit.

## Culture-aware formatting — free once culture is set

Once `CurrentCulture` is correct, `@item.Price.ToString("C")`, `date.ToString("d")`, and number/percent formatting follow the culture automatically — **don't** hand-format with hardcoded separators.

- **Input parsing:** `<input @bind="value" @bind:culture="CultureInfo.CurrentCulture" />` so typed dates/decimals parse in the user's culture; `<input type="date"/number">` use the browser locale — keep them consistent with the app culture.
- **Money:** currency *code* is data, not culture — a French user still sees USD as USD; culture controls symbol placement/separators, not which currency. Keep the amount-as-minor-units discipline from [`data-fetching`](../data-fetching/SKILL.md)/`ui-rules`.
- Route all display formatting through the **shared helpers** [`ui-rules`](../ui-rules/SKILL.md) mandates; this skill just guarantees those helpers see the right `CurrentCulture`.

## RTL

- Set `dir="rtl"` on `<html>` for RTL cultures (Arabic, Hebrew) — derive it from the culture, don't hardcode.
- The layout must already use **logical CSS properties** (`margin-inline-start`, not `margin-left`) so it mirrors automatically — that mechanics work lives in [`styling`](../styling/SKILL.md)/[`responsive-design`](../responsive-design/SKILL.md); this skill owns *deciding* `dir` from culture.
- Mirror directional icons (chevrons, back arrows); leave logos/brand marks unmirrored.

## Rules

- **Distinguish globalization (formatting, always on) from localization (text swap, `IStringLocalizer`).**
- **`.resx` keyed to component type**, keys are stable ids, never hardcode UI strings under localization.
- **Culture pipeline by render mode:** Server/SSR → `RequestLocalizationOptions` + cookie; WASM → set `CultureInfo` at startup with `autostart=false` + satellite assemblies; mixed Web App → cookie for both.
- **WASM needs ICU data** (`BlazorWebAssemblyLoadAllGlobalizationData` or a shard) and **`InvariantGlobalization=false`** — else formatting silently no-ops.
- **Language switch = write culture cookie + full reload**, persisted for return visits.
- **Formatting flows from `CurrentCulture`** — never hand-roll separators; parse inputs with `@bind:culture`.
- **Localize validation messages** through the same localizer ([`forms`](../forms/SKILL.md)).
- **`dir` derives from culture**; logical-property mirroring is `styling`'s job.

## What NOT to do

- No hardcoded UI strings once localization is enabled — invisible to translators.
- No `InvariantGlobalization=true` on a localized WASM app — kills all culture behavior.
- No assuming WASM culture can change without a reload — it's set at boot.
- No `RequestLocalization` placed after the Blazor endpoints — the circuit misses the culture.
- No hand-formatted dates/money with fixed separators — breaks in every other culture.
- No `.resx` folder/namespace mismatch — the localizer silently returns raw keys (looks "untranslated").
- No shipping the full ICU dataset without checking the WASM size budget ([`performance`](../performance/SKILL.md)).
- No RTL via `left/right` CSS — use logical properties so one stylesheet serves both directions.

## Validation

Inside a `Gate: none` plan task, run none of these checks and report "written, not run"; the plan's gate task runs them.

- Switch language in the UI → text, dates, numbers, and currency all change; the choice survives a reload/return visit.
- WASM: dates/decimals render in the selected culture (proves ICU data shipped + `InvariantGlobalization=false`).
- Server/SSR: the culture cookie drives the first render (no English flash before a client swap).
- A missing resource key falls back to the key (visible), not a crash — then gets translated.
- Form validation messages appear in the active language.
- An RTL culture flips layout direction with no broken alignment (logical properties held).
- WASM published size stays within budget with the chosen ICU strategy.

## Handoffs

- Canonical format-per-type policy, humanized enums, GUID→name → [`ui-rules`](../ui-rules/SKILL.md)
- Localized validation-message plumbing → [`forms`](../forms/SKILL.md); their wording/voice → [`design/ux-writing`](../../../../design/ux-writing/SKILL.md)
- RTL/logical-property styling, mirrored components → [`styling`](../styling/SKILL.md) + [`responsive-design`](../responsive-design/SKILL.md)
- WASM ICU-data size trade-off → [`performance`](../performance/SKILL.md)
- Which render mode a surface uses (drives the culture pipeline) → [`project-setup`](../project-setup/SKILL.md)
- Locale-pinned test assertions, pseudo-localization, RTL testing → the qa **`language-testing`** peer (invoke separately)
