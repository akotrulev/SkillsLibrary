---
paths:
  - "**/*{Test,Tests}.razor"
  - "**/*.{Tests,UnitTests,ComponentTests}/**/*.razor"
---

<!-- fe-blazor rules v1 (2026-11-03): tests. Installed by /fe-blazor:rules; add the folders of this project's bUnit test projects to the paths above. -->

# Blazor test standards (bUnit and plain unit tests)

Severity tags as in the core Blazor rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- bUnit v2: inherit `BunitContext`, render with `Render<T>`, dispose with `DisposeComponentsAsync`; never v1's `TestContext`, `RenderComponent` or `DisposeComponents`. *major*
- bUnit for components with logic; a plain test on the class for non-rendering logic (state containers, validators, mappers, culture helpers with an explicit `CultureInfo`), in the runner the project already uses. *major*
- Select by `data-testid`; assert the smallest proving node (`MarkupMatches`, `TextContent`), never whole-component markup or a class, tag or index selector. *major*
- No snapshot of a markup-only component and no test of the framework (`@bind` binds, `EditForm` submits); a test that is a tautology is deleted. *minor*
- Wait with `WaitForState`/`WaitForAssertion`, never `Thread.Sleep` or `Task.Delay`. *major*
- JS interop in Strict mode; fakes for the direct dependencies registered in `Services`. *minor*
- No faked `NavigationManager` standing in for a journey; E2E belongs to the UI suite. *minor*
- Names state behaviour; one behaviour per test, each assertion expecting one value; no `if`/`for` (use `[Theory]`/`[TestCase]`) and no `try`/`catch`. *major*
- Test data with four or more fields comes from a builder. *minor*
- New code ships with tests covering at least 80% of the branches it wrote (coverlet); only an asserting test counts, and nothing with behaviour is excluded by `[ExcludeFromCodeCoverage]`. *major*
