---
paths:
  - "**/*.cpp"
  - "**/*.h"
  - "**/*.idl"
  - "**/*.vcxproj"
---

<!-- desktop-windows rules v1 (2026-11-15): C++/WinRT. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its C++. Apply to projects with `Microsoft.Windows.CppWinRT` only. -->

# C++/WinRT standards

Severity tags as in the core C# rules: **blocker**, **major**, **minor**, **nit**. The codebase wins where it consistently does otherwise. A `.vcxproj` with no `winrt::` and no XAML is Win32 or MFC: report it, do not guide it. Never raise the C++ standard, the toolset or the Windows SDK as a side effect. *major*

## Ownership

- A WinRT object is held as its projected value (`Window window{ nullptr };`); `com_ptr` takes implementation types and COM interfaces only, and `com_ptr<Projected>` does not compile. *major*
- Implementation types are created with `winrt::make` / `make_self`; no raw `new` or `delete`, no stack implementation returned as a projected type, no owning raw pointer. *major*
- Out-pointers use `put()` / `put_void()` on an empty pointer, never `&ptr`; `attach` / `detach` only at an ABI edge. *major*
- A kernel handle is a `winrt::handle`. *major*
- Dependencies are constructor parameters; no static mutable state, no service locator, no `extern` global holding a service. *major*

## Coroutines and threads

- A coroutine or handler that touches `this` after a suspension holds `get_strong()` (or `get_weak()`, promoted before use), taken before the first `co_await`; `get_strong()` exists only on `winrt::implements` types. *blocker*
- Coroutine parameters are by value or by handle, never `const&` or a raw `HANDLE` read after the first suspension. *major*
- UI-affine objects (XAML properties, `Window`) are touched only after `co_await winrt::resume_foreground(queue)` (or `wil::resume_foreground`), the queue obtained on the UI thread; `resume_foreground` always queues and returns `false` on shutdown, so the result is handled. *blocker*
- The UI thread never waits on an async operation: no `.get()`, `.wait_for()` or `WaitForSingleObject` there. *blocker*
- Work leaves the UI thread once (`resume_background`) and returns once per result. *major*
- An event handler captures a strong or weak reference, or the receiver owns the source; a strong handler is revoked (`event_token` / `auto_revoke`). *major*

## Errors

- `winrt::hresult_error` is caught once at the boundary and mapped to the failed state; expected failures are return values, not exceptions. *major*
- Win32 and COM returns are checked (`winrt::check_hresult`, `check_bool`, `check_win32`). *major*
- No empty `catch`, and no `catch (...)` that continues without a state. *major*

## XAML types and IDL

- A type XAML references is a runtime class in `.idl`; implement the generated stubs before the build (`/WX` fails on them); generated `*.g.h`, `*.g.cpp` and `Generated Files/` are never edited. *major*
- Page and control metadata (`x:Bind` targets, `DependencyProperty`) is declared in IDL, not only in the header. *major*

## Build and tests

- `/W4 /WX /permissive-` on every project; `Microsoft.Windows.CppWinRT` is the current stable NuGet, not an experimental version. *major*
- Logic is tested with GoogleTest over a XAML-free core library; XAML-bound C++ stays thin and is covered by the E2E suite. New code reaches 80% of lines (`Microsoft.CodeCoverage.Console` reports lines; `llvm-cov` reports branches where present), designed branch by branch, with asserting tests. *major*
- Comments follow the core rules: no inline comments. *minor*
