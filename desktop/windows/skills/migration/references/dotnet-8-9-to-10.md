# .NET 8 / 9 → 10 (or 11)

**Dated.** .NET 8 and 9 have been out of support since 2026-11-10. .NET 10 LTS (10.0.15, end of support 2028-11-14) is primary; .NET 11 STS (GA 2026-11-10, end of support 2028-11-14) is supported. Never target 8 or 9 on new work. CLAUDE.md § Version policy still says "8–9 supported": the plan records the deviation (Q2, D2), and the library-wide fix is a separate plan.

## Steps, per project, leaves first

1. **Baseline** (the gate in `SKILL.md`). Install the SDK pinned by `global.json` and raise `global.json` once, with `rollForward` stated.
2. **TFM.** `net8.0-windows10.0.xxxxx` / `net9.0-windows…` → `net10.0-windows10.0.26100.0` (or `net11.0-windows10.0.26100.0`). The OS part stays on every UI project. Libraries with no Windows API move to `net10.0`.
3. **Packages.** EF Core and the `Microsoft.Extensions.*` packages match the TFM major; move them with the TFM, never ahead of it. CommunityToolkit.Mvvm 8.4.2 and Windows Community Toolkit 8.2 are the library pins; CsWinRT stays 2.3.1 (the 3.0 preview is not adopted).
4. **Breaking changes.** Read the .NET 10 breaking-changes list on learn.microsoft.com for the areas the project uses (BCL, ASP.NET Core if a host is embedded, EF Core, WPF, WinForms). The inventory count from the gate is the work list.
5. **Build with warnings as errors** for the unit just moved; new analyzer warnings are fixed, not suppressed.
6. **CI image and runtime installers.** The build agent and any framework-dependent installer move with the TFM; a self-contained app needs nothing at install.

## Lane notes

- **WPF / WinForms** stay in their lane; .NET 10 brings the Fluent `ThemeMode` (WPF), `SetColorMode` and `ShowAsync` / `ShowDialogAsync` (WinForms). Adopting them is a follow-up, not part of the move.
- **.NET 11** needs x86-64-v2 on x64 and Arm64 LSE on Arm64 (secondary source); say so before choosing it for an app that runs on old hardware. A WinUI app on 11 is supported by the plan, but whether Windows App SDK 2.6 lists the `net11.0-windows` TFM is not verified: check the release notes first.
- **Native AOT** (`PublishAot`) is a separate decision with its warnings read ([`performance`](../../performance/SKILL.md)); never switched on inside this move.

## Verify

`dotnet build -warnaserror`, `dotnet test`, `dotnet list package --outdated --include-transitive` and `--deprecated`; the packaged app installs and launches; section A of the audit passes (A2).
