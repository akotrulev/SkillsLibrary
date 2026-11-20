---
name: interop
description: Use when C# desktop code crosses a boundary (CsWinRT, HWND, COM, P/Invoke via LibraryImport, XAML Islands, WinUI in WPF/WinForms). Triggers "call a Win32 API". Not for the C++ lane (cpp-winrt).
disable-model-invocation: true
---

# Windows — Interop

How C# desktop code crosses into native code safely: **WinRT through CsWinRT, Win32 through source-generated `LibraryImport` P/Invokes, COM through `ComWrappers`-friendly patterns, window handles from the right place, and XAML hosting only where a lane needs it.** Audit rows: section X of `desktop-windows:standards-audit` (N/A without P/Invoke, COM or C++ projects). The C++/WinRT lane is `desktop-windows:cpp-winrt`.

## Version lane

| Concern | Primary | Rule |
|---|---|---|
| CsWinRT | **2.3.1** (`Microsoft.Windows.CsWinRT`, pulled in by the TFM and the Windows App SDK) | **CsWinRT 3.0 is a preview: not adopted** (plan §4.2); a project on it is a finding |
| P/Invoke | `[LibraryImport]` (.NET 7+; .NET 10 primary) with `AllowUnsafeBlocks` | `[DllImport]` only where the generator cannot express the signature, with a recorded reason (`SYSLIB1054` flags it) |
| Win32 signatures | `Microsoft.Windows.CsWin32` source generator | Generate from `NativeMethods.txt`; hand-written signatures only for what it lacks |
| TFM | `net10.0-windows10.0.26100.0` (11 STS supported) | The OS part of the TFM is what makes WinRT projections available (`A5`) |
| Native AOT | Supported with `LibraryImport`, CsWinRT and `x:Bind`; not with runtime IL stubs or reflection-based COM | `PublishAot` makes a `DllImport` with non-blittable types a warning to fix |
| Windows App SDK | 2.6.x (`desktop-windows:project-setup`) | Never add it to a WPF/WinForms app as a side effect (`A6`) |

## Prefer the managed route first

In order, before any P/Invoke: (1) a .NET BCL API; (2) a WinRT API through the TFM projection; (3) a Windows App SDK API; (4) a CsWin32-generated Win32 call; (5) a hand-written `LibraryImport`. Where installed, `winapp find-api "<what you need>"` searches Windows APIs and the Windows App SDK for the match; never required.

## WinRT through CsWinRT

- A TFM with the OS suffix gives the `Windows.*` projections: `net10.0-windows10.0.26100.0`. The **lowest supported OS** is `TargetPlatformMinVersion` (never raised silently); an API newer than it needs a runtime guard: `ApiInformation.IsMethodPresent` / `OperatingSystem.IsWindowsVersionAtLeast`.
- **Packaged-only APIs** (share target, `ApplicationData.Current`, background tasks, toast with identity) throw or return empty without package identity. Check `AppModel.HasPackageIdentity` (or call `GetCurrentPackageFullName`) and take the unpackaged route (`offline-and-storage`).
- **WinRT objects from other threads:** a `DispatcherQueue` / UI-affine object is touched only on its thread. A `COMException` with `RPC_E_WRONG_THREAD` is the symptom.
- **Do not reference two CsWinRT versions.** One `Microsoft.Windows.CsWinRT` in the dependency graph, from the Windows App SDK; a transitive older one is fixed with a central package version (`B2`).
- **Dispose** `IClosable` WinRT objects (`using`) and release COM RCWs you create with `Marshal.ReleaseComObject` only where you own the count.

## Window handles

Many Windows App SDK and Win32 APIs want an `HWND`. Take it from the owning window; never `GetForegroundWindow()` and never `Process.MainWindowHandle`:

| Lane | Get the handle |
|---|---|
| WinUI | `WinRT.Interop.WindowNative.GetWindowHandle(window)`; the new pickers take `AppWindow.Id` instead |
| WPF | `new WindowInteropHelper(window).EnsureHandle()` (after `SourceInitialized`) |
| WinForms | `form.Handle` (creates it); use `IsHandleCreated` when you must not force creation |

- **Wrap the handle in a typed value at the edge** (`WindowHandle`), pass it down; a view model never holds an `HWND`.
- The handle is valid only while the window lives: do not cache it past close.
- Legacy WinRT pickers and dialogs in desktop apps need `WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd)`; a missing call fails with an invalid-window-handle `COMException`.

## P/Invoke with `LibraryImport`

```csharp
internal static partial class NativeMethods
{
    [LibraryImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static partial bool FlashWindow(nint hwnd, [MarshalAs(UnmanagedType.Bool)] bool invert);

    [LibraryImport("user32.dll", EntryPoint = "GetWindowTextW", StringMarshalling = StringMarshalling.Utf16, SetLastError = true)]
    internal static partial int GetWindowText(nint hwnd, [Out] char[] text, int maxCount);
}
```

- **`static partial` methods** with `[LibraryImport]`; the generator writes the marshalling at compile time (AOT- and trim-safe). Enable `AllowUnsafeBlocks` in the project.
- **Always name the Unicode entry point** (`…W`) and set `StringMarshalling.Utf16`. There is no `CharSet`, no ANSI.
- **`SetLastError = true`** where the API reports via `GetLastError`, then check `Marshal.GetLastPInvokeError()` / throw `new Win32Exception(Marshal.GetLastPInvokeError())` — never ignore a returned failure.
- **Blittable types and `nint`/`SafeHandle`.** Handles you own are `SafeHandle` subclasses (`SafeHandleZeroOrMinusOneIsInvalid`); a raw `nint` you must free is a leak finding. Prefer CsWin32, which emits `SafeHandle`s and correct `BOOL`/`HRESULT` mapping.
- **`HRESULT` returns:** `Marshal.ThrowExceptionForHR(hr)` (or `[PreserveSig]`-free COM) so failure is an exception at the boundary, handled once.
- **No P/Invoke on the UI thread that can block** (file dialogs, network, `WaitFor*`). Run it on the thread pool and return through the dispatcher.
- **Put them in one `NativeMethods` class per library**, internal; no `public` P/Invoke in an app, no struct layout guessed (`[StructLayout(LayoutKind.Sequential)]` with the `cbSize` set).
- **Check the OS availability:** `[SupportedOSPlatform("windows10.0.19041")]` on a wrapper whose API is newer than the floor (`CA1416`).

## COM

- Use the generated interop first: WinRT interfaces come from CsWinRT; Win32 COM interfaces from CsWin32 or `[GeneratedComInterface]` (.NET 8+ COM source generator) which is trim- and AOT-safe. The old `[ComImport]` + RCW route is **not trim-safe**; use it only with a recorded reason.
- **Apartment:** the UI thread is STA. A COM object created on a thread-pool (MTA) thread is marshalled; do not share a raw pointer across threads.
- **Free what you own:** `Marshal.Release` for a raw pointer, `using` for a wrapper; a COM object's lifetime is not the GC's concern.
- Registration-free COM and `regsvr32` need admin: never require it (`J12`). Prefer an in-process managed implementation.

## XAML Islands and hosting WinUI in WPF / WinForms

- **Hosting is a deliberate modernization step**, not a default: it adds the Windows App SDK to a lane that did not have it (`A6`). It needs a recorded reason, the owner's agreement and the `migration` skill's decision guide first.
- WinUI content in a Win32/WPF/WinForms window goes through the Windows App SDK XAML hosting API (`DesktopWindowXamlSource`, `WindowsXamlManager`), one source per island, **disposed with the host**. WPF needs an `HwndHost` around it; WinForms hosts it in a `Control` with a handle.
- **Island rules:** give it a size (the child window starts 0×0), handle keyboard focus in and out, handle DPI changes, and keep **one** island's data source of truth in the host's view models.
- **Not verified for Windows App SDK 2.6 and .NET 10/11:** the exact package, the supported WPF/WinForms wrappers, and whether UWP-era `WindowsXamlHost` applies. Read the current "XAML hosting" page on learn.microsoft.com before writing a line, and say what was checked.
- The reverse direction (WPF in WinUI) is not supported; that is a migration.

## Security at the boundary

- **A native call that takes a path, string or buffer from outside** (activation, clipboard, a file) validates length and shape first (`desktop-shared:security`).
- **No `LoadLibrary` of a bare name** from the working directory: load by full path from the app folder or `System32`, `NativeLibrary.Load` with `DllImportSearchPath.SafeDirectories`/`System32` (`[DefaultDllImportSearchPaths]`).
- **Never `unsafe` for convenience.** `unsafe` blocks cover only the generated or hand-checked span code; each has a bounds check.
- **No `Marshal.GetFunctionPointerForDelegate` without a kept-alive delegate** (a GC'd delegate crashes the native caller).

## Telemetry

A log at each failed native call (API name, `GetLastError` code, never buffers or paths), and an `interop.failures` counter by API. A `COMException` HRESULT is logged as hex.

## Common gotchas

- **`DllImport` without `W`/`CharSet.Unicode`** — mojibake or the ANSI function.
- **`LibraryImport` with `AllowUnsafeBlocks` off** — the generator reports an error.
- **A picker "not initialized with a window"** — pass the HWND or `AppWindow.Id`.
- **`Process.MainWindowHandle` as an owner** — wrong window, or none.
- **`ApplicationData.Current` unpackaged** — throws; check identity.
- **CsWinRT 3.0 preview from a transitive dependency** — pin it back.
- **A `SafeHandle` replaced by `nint`** — a leak on every error path.
- **A delegate passed to native and collected** — a crash minutes later.
- **WinUI added to WPF "just for one control"** — a lane change; it is a migration.
