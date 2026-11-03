---
name: conventions-review
description: Use when reviewing Blazor code (lifecycle bugs, missing dispose, prerender double-fetch, render modes, JS interop). Triggers "review this Blazor page". Not for writing code (component-writer).
---

# Blazor Design Patterns — Reviewer

Reviews Blazor code (.NET 8/9/10 — Static SSR / Server / WASM / Interactive Auto) against the fe-blazor rule files and produces a findings table. It does **not** rewrite: it points to the fix and hands off to `component-writer`.

## The checklist is the rule files

Every check, and the severity it reports, lives in one place: the fe-blazor rule files `blazor.md` (core), `blazor-markup.md`, `blazor-forms.md`, `blazor-ui.md`, `blazor-styles.md`, `blazor-js.md`, `blazor-tests.md` and `blazor-config.md`.

1. **The project's copies first**: `.claude/rules/fe-blazor/` at the project root. The team may have edited them, and its edits win.
2. **Otherwise the plugin's copies**: `frontend/blazor/skills/rules/` (under `${CLAUDE_PLUGIN_ROOT}` in an installed plugin). Say in the report that the project has no installed rules and that `/fe-blazor:rules` installs them.

Read `blazor.md`, plus each other file whose `paths:` match a file under review, in full before the first finding. A rule loaded on its own by the session is not enough: a review needs every file that applies, not just the ones the session happened to open. Never review from memory of the rules, and never add a check the files do not contain; propose it as a rule change instead.

## Version policy

Identify the project's `TargetFramework` before flagging. Manual `PersistentComponentState` boilerplate is a finding only on net10 (where `[PersistentState]` replaces it); on net8/net9 it's the correct pattern. Same for `NotFoundPage`, `AddValidation()`, and `ReconnectModal` — never flag a down-level project for not using a net10-only API. For tests, detect the bUnit major: v1 patterns are a finding, the TFM is not. The rule files' "the codebase wins" line applies: a convention the project follows consistently is not a finding.

## When to use

- A `.razor` / `.razor.cs` / `.razor.css` / `.razor.js` diff submitted
- Pre-merge gate on PRs touching `Components/` / `Pages/` / `App.razor`
- "Why does this page fetch twice?" / "Why does my event not re-render?"
- Audit JS interop / dispose hygiene

## When NOT to use

- Conceptual lookup → `frontend/blazor/skills/basics`
- Generating new code → `frontend/blazor/skills/component-writer`
- Non-Blazor .NET review → the `backend/dotnet` dev stack's reviewer, if installed
- Auth wiring review → `auth/auth0-blazor` + general code review

## Procedure

1. Read the rule files, then each changed file end to end.
2. Identify the **render mode** and **hosting model** of each component first — half the bugs depend on it.
3. Walk the rules in this order: render modes and prerender, component contract and lifecycle (dispose, `EventCallback`), state, JS interop, then the rest. Most blockers and majors live there.
4. Per finding: file and line, the rule broken, a one-sentence fix. The severity is the tag on the rule, never a new judgment.
5. Do not rewrite. Hand off to `frontend/blazor/skills/component-writer`.

## Output format

```
| Severity | Location                              | Issue                                                              | Suggested fix                                                              |
|----------|---------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------|
| blocker  | App/Pages/Orders.razor.cs:14         | `CartState` registered as Singleton in Blazor Server                 | Switch to `AddScoped<CartState>()` — Server scopes per SignalR connection   |
| major    | App/Pages/Orders.razor:22            | `OnInitializedAsync` calls `Http.GetFromJsonAsync` without persisting | Wrap with `PersistentComponentState` to avoid double-fetch on Interactive Auto |
| major    | Components/Cart.razor:18             | Subscribes to `Cart.Changed` without `IDisposable`                   | Implement `IDisposable` and unsubscribe in `Dispose`                       |
| major    | Components/InputCurrency.razor:9     | `[Parameter] public Action<long> OnChange` — should be EventCallback  | Change to `[Parameter] EventCallback<long> OnChange`                        |
```

End with one line: `Rules: project .claude/rules/fe-blazor/ | plugin copy (not installed)`.

## Handoffs

- Rewrite → `frontend/blazor/skills/component-writer`
- Conceptual lookup → `frontend/blazor/skills/basics`
- Non-Blazor .NET review → the `backend/dotnet` dev stack's reviewer, if installed
- Auth0 wiring review → `auth/auth0-blazor`
- A rule is missing or wrong → edit the project's `.claude/rules/fe-blazor/`; for every project, the plugin's `frontend/blazor/skills/rules/`
