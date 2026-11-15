# C++/WinRT — unit tests and coverage

The decision is recorded as D16 in `docs/plans/012-desktop-plugins.md`. Sources checked 2026-11-15 on learn.microsoft.com and github.com: Test apps built with the Windows App SDK and WinUI 3 (2026-09-10), the Microsoft Unit Testing Framework for C++ API reference (page dated 2019, in VS 2022/2026 docs), Create and run unit tests with Google Test for C++, Determine code testing coverage, Microsoft.CodeCoverage.Console, the LLVM Source-based Code Coverage page, the OpenCppCoverage README.

## Framework: GoogleTest

| | GoogleTest | Microsoft Unit Testing Framework for C++ |
|---|---|---|
| In VS | Default component of **Desktop development with C++**; **Google Test Project** template; Test Adapter for Google Test in Test Explorer | Default in the same workload; **Native Unit Test Project** |
| Parameterized tests | `TEST_P` + `INSTANTIATE_TEST_SUITE_P` | None in the documented API: `TEST_METHOD` only (no data-driven macro) |
| Runs as | A plain `.exe`: any runner, any coverage tool, CI without VS Test Explorer | A DLL loaded by the VS test host |
| WinRT asserts | None needed for C++/WinRT | The "Windows Runtime asserts" take `T^` (C++/CX hats), not C++/WinRT types |

GoogleTest wins on the house rules: no conditional logic in a test means parameterized tests, and only GoogleTest has them. Cost: one more dependency (the VS component, or vcpkg / NuGet) and a second runner family beside the C# lane's NUnit and MSTest (D8).

## Where tests live

- **Core library** (static `.vcxproj`): logic with no `Microsoft.UI.Xaml` types: parsing, rules, view-model state machines written over plain C++ types, mappers. The app and the test project link it.
- **GoogleTest project** (`CoreTests.vcxproj`): links the core library only. It never references the app project.
- **XAML-bound code** (pages, runtime classes that touch controls) has no verified C++ in-process runner: Microsoft documents the WinUI Unit Test App only as C# MSTest (`[UITestMethod]`; `winapp new --template winui-unittest`). Keep these types thin, forward to the core library, and let the `qa-desktop-<lang>` suite cover them through `AutomationId`.

```cpp
class OrderTotalCase : public testing::TestWithParam<std::tuple<std::vector<int>, int>> {};

TEST_P(OrderTotalCase, Should_SumLines_When_OrderHasLines)
{
    auto const& [lines, expected] = GetParam();

    auto total{ Orders::TotalOf(lines) };

    EXPECT_EQ(total, expected);
}

INSTANTIATE_TEST_SUITE_P(Totals, OrderTotalCase,
    testing::Values(
        std::make_tuple(std::vector<int>{}, 0),
        std::make_tuple(std::vector<int>{ 250 }, 250),
        std::make_tuple(std::vector<int>{ 250, 100 }, 350)));
```

- Names: `Should_X_When_Y`. One logical assertion. Test data from builders. No `Sleep`; wait on a condition.
- A coroutine under test is driven with `.get()` **in the test** (a test thread, never the UI thread) or a `winrt::apartment` set up by the fixture.
- A fake is a plain class implementing your interface; mocks only where a call sequence is the behavior.

## Coverage: what each tool reports

| Tool | Reports | Native C++ | Status |
|---|---|---|---|
| **`Microsoft.CodeCoverage.Console`** (ships with VS under `Common7\IDE\Extensions\Microsoft\CodeCoverage.Console`) | **Blocks and lines**; no branch metric documented | Yes, by static instrumentation (link with `/PROFILE`) | Supported; Visual Studio 2026: Community, Professional, Enterprise (VS 2022: Enterprise only) |
| Visual Studio **Test > Analyze Code Coverage** | Blocks and lines | Yes | Same editions |
| **`clang-cl`** with `-fprofile-instr-generate -fcoverage-mapping`, then `llvm-profdata merge` and `llvm-cov report` | **Branches** (a Branches / Missed Branches / Cover column; `--show-branches=count` per line) | Yes (Windows is a supported platform in the LLVM docs; the `clang-cl` spelling and the `llvm-cov` binaries shipped with VS's Clang component were not verified here) | LLVM, maintained |
| OpenCppCoverage | Line coverage only | Yes | **Archived, "no longer actively maintained"**: not used |

### The floor, per project

1. **Default (MSVC build): ≥ 80% of lines** of the files the change created and the functions it changed. The toolchain reports no branches, so CLAUDE.md § Test code rules sets lines as the floor.
2. **Where the project builds the core library and tests with `clang-cl` and reports with `llvm-cov`: ≥ 80% of branches.** Do not switch toolchains to reach it; do not report lines on a project that has branch data.
3. State the unit in the report: "lines" or "branches".

```powershell
msbuild CoreTests.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true
Microsoft.CodeCoverage.Console collect --settings coverage.config .\x64\Debug\CoreTests.exe
```

`coverage.config` follows the `.runsettings` data-collector format: `ModulePaths` / `IncludeDirectories` for the core library, and exclusions by name for generated code (`Generated Files`, the test sources). Output is `output.coverage`; export to Cobertura through the tool's merge / convert path (the `dotnet-coverage` options; not verified for native results here). Debug build, no optimization, PDBs present: Microsoft's own conditions for usable coverage.

### Exclusions

Only what the selection matrix excludes, by name: generated sources (`Generated Files`, `*.g.cpp`), the test project itself, the IDL implementation stubs that only forward. Never `ExcludeFromCodeCoverage` on code with behavior, never a `#pragma` to move the number.

## Gate commands for a C++ task

```powershell
msbuild App.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true
msbuild CoreTests.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true
.\x64\Debug\CoreTests.exe --gtest_filter=Orders*
Microsoft.CodeCoverage.Console collect --settings coverage.config .\x64\Debug\CoreTests.exe
```

`--gtest_filter` is the narrowest rerun of one suite; the whole `CoreTests.exe` is the whole set.
