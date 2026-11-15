# Windows App SDK 1.x → 2.x

**Dated.** The current stable is 2.6.x (2.6.5, 2026-11-02). 1.8 left maintenance on 2026-09-24 and 1.7 and older are out of support, so 1.x is a finding. The 2.0 line is serviced to 2027-04-29. 2.0.1 (2026-04-29) was the first SemVer release: the NuGet version equals the SDK version, and breaking changes come only with a major (the next one is 3.0.0).

Read first: the 2.x release notes and the migration guide for the version you are leaving. This reference carries only what the research verified; anything else you find in the notes goes into the move's inventory.

## Steps

1. **Baseline** (the gate in `SKILL.md`), on a branch of work you were given, one project per commit.
2. **Packages.** `Microsoft.WindowsAppSDK` to the 2.x stable version; reference only the sub-packages used (Base, Runtime, WinUI, Widgets, AI …) rather than the metapackage where the project already does. **No experimental package.** `Microsoft.Windows.SDK.BuildTools.WinUIAnalyzer` stays on every app project.
3. **TFM and min version.** Keep `net10.0-windows10.0.26100.0` and the explicit `TargetPlatformMinVersion`; do not raise either here.
4. **Custom `Main`.** `DISABLE_XAML_GENERATED_MAIN` now *renames* the generated entry point (`XamlGeneratedProgram.XamlGeneratedMain()`) instead of removing it (2.3.1). Re-read any project that defines its own `Main` ([`activation-and-notifications`](../../activation-and-notifications/SKILL.md)).
5. **Unpackaged storage.** `Microsoft.Windows.Storage.ApplicationData.GetForUnpackaged()` arrived in 2.2.0 and its registry path was corrected in 2.4.0; an unpackaged app that used it earlier re-checks where its data lives ([`offline-and-storage`](../../offline-and-storage/SKILL.md)). Whether the API is right for the SDK in use is checked against its reference, not assumed.
6. **Pickers.** `Microsoft.Windows.Storage.Pickers` (1.8+) are constructed with `AppWindow.Id` and need no `InitializeWithWindow`; the legacy pickers keep working with an HWND. Move them as a follow-up unless the move breaks them.
7. **Experimental controls.** `TableView`, `Chart` and `InkCanvas` are experimental-only: if a 1.x project used a prerelease of any, it is replaced or removed, never shipped.
8. **Build, run and package** (`winapp run`, or Visual Studio F5), then verify.

## Verify

The package restores from the 2.x stable channel only; a clean packaged install starts; activation, toasts and the pickers each run once; section A of the audit passes (A3).

## Not verified here

The full 1.x → 2.0 breaking-change list, WinUI control behaviour differences, and CsWinRT interactions are not enumerated: they come from the release notes at move time.
