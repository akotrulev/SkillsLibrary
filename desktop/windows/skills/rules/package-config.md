---
paths:
  - "**/Package.appxmanifest"
  - "**/*.csproj"
  - "**/*.vcxproj"
  - "**/Directory.Build.props"
  - "**/Directory.Packages.props"
  - "**/app.manifest"
  - "**/*.pubxml"
  - "**/nuget.config"
---

<!-- desktop-windows rules v1 (2026-11-15): project, manifest and packaging. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its project files. -->

# Project, manifest and packaging standards (Windows)

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise.

- No secret in a project file, props, manifest, `nuget.config` or the package; no committed `.pfx` with a password or Artifact Signing credential. *blocker*
- The TFM carries the OS part (`net10.0-windows10.0.26100.0`); `TargetPlatformMinVersion` is written explicitly; .NET 8 and 9 are out of support since 2026-11-10 and are a migration finding, never a target. *major*
- Windows App SDK is the 2.x stable channel; no experimental package, no CsWinRT 3.x preview. *blocker for experimental*
- Never raise the TFM, the Windows App SDK major, the C++ standard or the platform list as a side effect of other work. *major*
- Nullable on and `TreatWarningsAsErrors` set once in `Directory.Build.props`; package versions are central (`Directory.Packages.props`). *major*
- `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` is on every WinUI app project. *minor*
- Packaged MSIX unless a reason is recorded (`WindowsPackageType=None` carries it); ClickOnce is not used for WinUI. *major*
- Platforms are `x64;ARM64`, never `Any CPU`, on a packaged project. *minor*
- Capabilities are minimal and each has a recorded reason; `runFullTrust` is the only broad one a desktop app needs; no `allowElevation`, no `requireAdministrator` in `app.manifest`. *blocker for elevation; major otherwise*
- File and protocol associations are declared narrowly and only for a packaged app; manifest strings are localized. *minor*
- `PublishAot` and trimming are decisions: warnings are read, and `{Binding}` reflection paths are gone first. *major*
- Releases are signed (Store, or Azure Artifact Signing) and the update channel is signed; an unpackaged app updates through a signed feed. *blocker*
- C++: `/W4 /WX /permissive-`, `Microsoft.Windows.CppWinRT` as the current stable NuGet, the C++ standard unchanged. *major*
