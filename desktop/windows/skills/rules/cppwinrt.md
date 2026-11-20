---
paths:
  - "**/*.cpp"
  - "**/*.h"
  - "**/*.idl"
  - "**/*.vcxproj"
---

<!-- desktop-windows rules v1 (2026-11-15): C++/WinRT. Installed by /desktop-windows:rules; edit the paths above to where this project keeps its C++. Apply to projects with `Microsoft.Windows.CppWinRT` only. -->

# C++/WinRT standards

Severity tags as in the core C# rules. The codebase wins where it consistently does otherwise. A `.vcxproj` with no `winrt::` and no XAML is Win32 or MFC: report it, do not guide it. Never raise the C++ standard, toolset or Windows SDK as a side effect. *major* Recipes: `cpp-winrt`.

## Ownership

- A WinRT object is held as its projected value (`Window window{ nullptr };`); `com_ptr` takes implementation types and COM interfaces only. *major*
- Implementation types are created with `winrt::make` / `make_self`; no raw `new` or `delete`, no owning raw pointer. *major*
- Out-pointers use `put()` on an empty pointer, never `&ptr`; a kernel handle is a `winrt::handle`. *major*
- Dependencies are constructor parameters; no static mutable state. *major*

## Coroutines and threads

- A coroutine or handler that touches `this` after a suspension holds `get_strong()` (or `get_weak()`, promoted before use), taken before the first `co_await`. *blocker*
- Coroutine parameters are by value, never `const&` or a raw `HANDLE` read after a suspension. *major*
- UI-affine objects are touched only after `co_await winrt::resume_foreground(queue)` (or `wil::resume_foreground`), the `false` result on shutdown handled. *blocker*
- The UI thread never waits on an async operation: no `.get()`, `.wait_for()` or `WaitForSingleObject` there. *blocker*
- An event handler captures a strong or weak reference; a strong handler is revoked (`auto_revoke`). *major*

## Errors

- `winrt::hresult_error` is caught once at the boundary and mapped to the failed state. *major*
- Win32 and COM returns are checked (`winrt::check_hresult`). *major*
- No empty `catch`; no `catch (...)` that continues without a state. *major*

## XAML types, build and tests

- A type XAML references is a runtime class in `.idl`, with its `x:Bind` targets and `DependencyProperty` declared there; generated `*.g.h`, `*.g.cpp` and `Generated Files/` are never edited. *major*
- `/W4 /WX /permissive-` on every project. *major*
- Logic is tested with GoogleTest over a XAML-free core library; XAML-bound C++ stays thin and is covered by the E2E suite. The floor: `CLAUDE.md` "Test code rules", in lines. *major*
