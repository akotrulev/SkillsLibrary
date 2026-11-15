# C++/WinRT — project shape, IDL, WIL and the build

Detail for `desktop-windows:cpp-winrt`. Sources checked 2026-11-15 on learn.microsoft.com: Introduction to C++/WinRT (2026-09-21), Author APIs with C++/WinRT, Using WinApp CLI with WinUI (2026-11-09), the WIL `cppwinrt_helpers.h` header.

## Project shape

| Piece | What it is | Rule |
|---|---|---|
| `App.vcxproj` | The app, from VS's **WinUI Blank App (Packaged)** C++ template | One app project; libraries and tests are separate projects |
| `Microsoft.Windows.CppWinRT` | NuGet build support: MSBuild properties and targets, `cppwinrt.exe`, XAML codegen | Present in every C++/WinRT project; sets `/std:c++17`, `/bigobj`, `/await` |
| `*.idl` | One IDL per XAML page / runtime class; `App.idl`, `MainPage.idl`, view models | `midl.exe` produces one `.winmd` per project; VS merges them under the root namespace |
| `Generated Files\` | `winrt\` projection headers, `sources\` stubs, `module.g.cpp` | Never edited, never committed (`.gitignore`) |
| `pch.h` / `pch.cpp` | Precompiled header with the `winrt/` includes | Add a projection header to `pch.h` before using its namespace; a missing `#include <winrt/...>` is the usual "not a member" error |
| `Package.appxmanifest` | MSIX identity and capabilities | Same rules as C# (`desktop-windows:project-setup`) |
| Core library (static `.vcxproj`) | Logic with no `Microsoft.UI.Xaml` types | The app and the GoogleTest project both link it |

The C++ properties the rules fix: `WarningLevel` Level4, `TreatWarningAsError` true, `ConformanceMode` true (`/permissive-`), `LanguageStandard` as the template set it (read it; never raise it), `CppWinRTOptimized` true.

## Authoring a runtime class for XAML

1. Add the runtime class to the page's IDL (or a new IDL). Declare a constructor to make it activatable.
2. Build once. The stub implementation appears in `Generated Files\sources\<Type>.h` and `.cpp`.
3. Copy the stub into the project, add it to the `.vcxproj`, then implement. A stub with unimplemented members warns under `/W4`: implement before committing.
4. Create the object with `winrt::make<implementation::Type>(args)` (projected result) or `winrt::make_self<implementation::Type>()` (a `com_ptr` to the implementation, when you need members that are not in the IDL).
5. `INotifyPropertyChanged`: the implementation owns a `winrt::event<Microsoft::UI::Xaml::Data::PropertyChangedEventHandler>` and raises it on the UI thread.

```idl
namespace Orders
{
    runtimeclass OrderRow
    {
        String Number{ get; };
        Decimal Total{ get; };
    }
}
```

- The implementation and the projection share a name: inside `winrt::Orders::implementation` `OrderRow` is the implementation, outside it is the projection. Qualify (`implementation::OrderRow`, `Orders::OrderRow`) when both are in view.
- A runtime class derived from a XAML control (`runtimeclass MyButton : Microsoft.UI.Xaml.Controls.Button`) has a `factory_implementation`; copy it from the generated stub, do not hand-write.
- A base constructor with no default needs an overload in the derived IDL that forwards the argument (as an automation peer takes its owner).
- Two IDLs that reference each other need `import`; keep the dependency one-way where you can.
- Returning an array across the ABI: `IInspectable` boxed through `PropertyValue::CreateInt32Array`, unboxed by the caller.

## Win32 and COM from C++

- Win32 handle: `winrt::handle` (kernel), `wil::unique_*` for the rest. A function returning `BOOL` / `HANDLE`: `winrt::check_bool(...)`; `HRESULT`: `winrt::check_hresult(...)`; `GetLastError` codes: `check_win32`. Never discard the return.
- A window handle: from `window.as<IWindowNative>()` / the `WindowNative` interop for the owning window; never `GetForegroundWindow()` (same rule as C#, `desktop-windows:interop`, `X5`).
- A COM interface pointer: `com_ptr`, filled by `put_void()` or `capture(...)` (which calls `check_hresult`).
- A message pump that needs the dispatcher on the current thread: `CreateDispatcherQueueController` with `DQTYPE_THREAD_CURRENT` and `DQTAT_COM_STA`, ownership transferred with `take_ownership_from_abi`.

## WIL

`Microsoft.Windows.ImplementationLibrary` is a NuGet package of headers. What this skill uses from it: `wil::resume_foreground` (`wil/cppwinrt_helpers.h`, included after the `winrt/` namespace header; supports `Windows.System`, `Microsoft.UI.Dispatching`, `Microsoft.System` queues and `CoreDispatcher`; always schedules; throws `0x800701ab` if the queue is gone) and `wil::unique_*` RAII types. No WIL version is pinned here; read the project's package reference.

## Build and run, with the non-`winapp` fallback

| Task | `winapp` 0.8.0 (preview) | Fallback |
|---|---|---|
| Build | `msbuild App.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true` | same (this is what `winapp run` calls, with VS's MSBuild) |
| Run with identity | `winapp run .\App.vcxproj` (or `winapp run .`); `--debug-output` for stowed exceptions; `--arch arm64` | Deploy from VS (F5) |
| Package and sign | `winapp pack .\App.vcxproj -c Release --arch x64 --cert .\devcert.pfx` | VS Package and Publish; `MakeAppx` and `signtool` |
| Analyze | `msbuild … /p:EnableMicrosoftCodeAnalysis=true /p:RunCodeAnalysis=true` with `CppCoreCheckRules.ruleset` | VS Code Analysis |

`winapp` needs Developer Mode, and VS or Build Tools with **Desktop development with C++** and **C++ WinUI app development tools**. `winapp pack` refuses an unpackaged project.

## Not verified here

- The exact property names VS writes for `ConformanceMode` and `WarningLevel` in the 2026 template: read the generated `.vcxproj`.
- Whether the WinUI C++ template's `Generated Files` folder name changed in the 3.0 package.
- WIL's current package version and its `cppwinrt.h` error-mapping header behavior.
- The `IWindowNative` route to an `HWND` from a WinUI `Window` in C++ (written from the documented interop shape).
- A C++ in-process XAML test runner: none found in Microsoft's documentation.
