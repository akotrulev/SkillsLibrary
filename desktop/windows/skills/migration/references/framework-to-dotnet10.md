# .NET Framework → .NET 10 (WPF, WinForms)

C# WinUI cannot target .NET Framework, so a Framework app reaches WinUI only through .NET 10. **Upgrade in place first** (Microsoft's decision guide), as its own move, with the UI lane unchanged.

## Steps

1. **Inventory the blockers** (gate step 3): WCF server, ASMX, `System.Configuration`, `AppDomain` creation, Remoting, COM registration, third-party control vendors without a .NET 10 build, `packages.config`.
2. **SDK-style project.** Convert `*.csproj` to the SDK format (`UseWPF` or `UseWindowsForms`, `TargetFramework`), move to `PackageReference` and central versions, and keep the assembly and file names that installers or registrations depend on.
3. **Target `net10.0-windows`** (with the OS part), build, and fix what the .NET compatibility analyzer and compiler list, project by project, leaves first.
4. **Replace the blockers** one at a time: `System.Configuration` → `Microsoft.Extensions.Configuration`; WCF client → `CoreWCF` client packages or HTTP; the vendor's .NET 10 build or a different control.
5. **Optionally** use the GitHub Copilot app modernization / upgrade agent in Visual Studio 2026 (paid Copilot; VB not fully supported). It is optional (D10): the result is verified by the same build, test and launch.
6. **Stop.** Nullable, host and DI, dark mode, DPI and the Fluent theme are modernization, offered after, in [`wpf`](../../wpf/SKILL.md) / [`winforms`](../../winforms/SKILL.md).

## Verify

Build with warnings as errors, the tests green, the app launches and its primary flow runs; the installer or package still installs side by side with the old version where that matters.
