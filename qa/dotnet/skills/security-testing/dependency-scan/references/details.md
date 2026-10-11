# Deep-dive details — `qa-dotnet:dependency-scan`

Sections moved out of SKILL.md for on-demand loading. Read what the task needs.

## Examples

**End-to-end: a PR SCA gate that fails on a new High CVE via NuGet audit, fixes the fixable transitive one
with a direct pin, and defers the unfixable one with a ticketed suppression.**

```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <NuGetAudit>true</NuGetAudit>
    <NuGetAuditMode>all</NuGetAuditMode>
    <NuGetAuditLevel>high</NuGetAuditLevel>
    <WarningsAsErrors>$(WarningsAsErrors);NU1901;NU1902;NU1903;NU1904</WarningsAsErrors>
  </PropertyGroup>
  <ItemGroup>
    <!-- Real fix: pin the patched transitive version directly (the preferred response). -->
    <PackageReference Include="System.Text.Json" Version="8.0.5" />
    <!-- Deferral: not-yet-fixable transitive CVE, ticketed + dated for re-review. -->
    <!-- JIRA-4211: GHSA-yyyy (high); no upstream patch yet, re-review 2026-09-01. -->
    <NuGetAuditSuppress Include="https://github.com/advisories/GHSA-yyyy-yyyy-yyyy" />
  </ItemGroup>
</Project>
```

Lifecycle for this gate:
1. A dev bumps a package; it pulls in a transitive `System.Text.Json` with a **High** CVE.
2. The PR runs `dotnet restore`; NuGet audit emits `NU1903` (high) → `WarningsAsErrors` turns it into a
   build error → **the build fails**, with the advisory in the uploaded JSON report.
3. The dev adds a **direct `<PackageReference>`** pinning patched `System.Text.Json` (the real fix) → the
   audit passes. A *second*, currently-unfixable transitive CVE is `<NuGetAuditSuppress>`ed with a JIRA
   ticket + re-review date — tracked, not silently muted.
4. Dependabot later raises the parent bump that removes the suppressed CVE; the suppression is deleted at
   its review — the list shrinks, never grows.
