---
name: cpp-winrt
description: Use when writing or reviewing a C++/WinRT WinUI app (com_ptr, coroutines, get_strong, dispatcher resume, hresult_error, IDL, tests). Triggers "vcxproj", "winrt::". Not for C# (interop).
disable-model-invocation: true
---

# Windows — C++/WinRT

How a C++/WinRT WinUI app owns objects, survives suspension points, reaches the UI thread, fails, declares XAML types and is tested: **projected types are the smart pointers, implementation types are made with `winrt::make`, a coroutine that outlives the call holds its `this`, the UI thread is reached by awaiting its queue, and an exception is caught once at the boundary.** Audit rows: `[C++]` rows in sections B, C, N, S and X of `desktop-windows:standards-audit`. The C# lane is `desktop-windows:basics`; C# native calls are `desktop-windows:interop`.

## Version lane

| Concern | Primary | Rule |
|---|---|---|
| Projection | `Microsoft.Windows.CppWinRT` NuGet **3.0.260818.1** (plan §4.2) | The package is the build support: `cppwinrt.exe`, `midl` wiring, XAML codegen. A `.vcxproj` without it is not a C++/WinRT project; `<CppWinRTEnabled>` is obsolete |
| Language | The package sets `/std:c++17`, `/bigobj` and `/await` | **Never raise the standard, the toolset or the SDK as a side effect.** Set `/permissive-` (the package does not) |
| Windows App SDK | 2.6.x, packaged MSIX (`desktop-windows:project-setup`) | Same lane rules as C#: no experimental channel, no 1.x |
| IDE / build | Visual Studio 2026, workload **WinUI application development** with **C++ WinUI app development tools**; Developer Mode on | `winapp` CLI 0.8.0 (preview) builds `.vcxproj` with VS's MSBuild: every recipe has the `msbuild` fallback |
| Tests | **GoogleTest** (D16) | Not the Microsoft C++ framework; not C# MSTest for C++ logic |
| Coverage | `Microsoft.CodeCoverage.Console` (native, static instrumentation): **lines**; `clang-cl` + `llvm-cov`: branches | Floor is 80% of lines unless the toolchain reports branches (`references/testing-and-coverage.md`) |

Detect the lane (`desktop-windows:concepts`): a `.vcxproj` with `Microsoft.Windows.CppWinRT`, `*.idl`, `winrt/` includes, `App.xaml` + `App.xaml.h`. A `.vcxproj` with no `winrt::` and no XAML is Win32/MFC: report it, do not guide it.

## Ownership

| You hold | Use | Never |
|---|---|---|
| A WinRT object (`Window`, `Uri`, a runtime class you consume) | The **projected type as a value**: `Window window{ nullptr };` The projected type is already a reference-counted smart pointer | `com_ptr<Window>`: a projected type in `com_ptr` fails to compile (`Release` is not a member) |
| A COM interface or one of your **implementation** types | `winrt::com_ptr<T>`; get an out-pointer with `put()` / `put_void()` | A raw owning pointer; `get()` stored past the `com_ptr` |
| A new implementation type | `winrt::make<Impl>(…)` (returns the projected type) or `winrt::make_self<Impl>()` (returns `com_ptr<Impl>`) | `new Impl`, a stack `Impl x;` returned as a projected type (a dangling pointer), `delete` |
| A kernel handle | `winrt::handle` by value | A raw `HANDLE` in a coroutine parameter |

```cpp
winrt::com_ptr<IDXGIFactory2> factory;
winrt::check_hresult(CreateDXGIFactory2(0, __uuidof(IDXGIFactory2), factory.put_void()));

auto viewModel{ winrt::make<winrt::Orders::implementation::OrdersViewModel>(std::move(client)) };
```

- `put()` / `put_void()` release the previous target: use them on an empty pointer, never `&ptr`.
- `attach` / `detach` are for hand-off at an ABI edge only; the reference you detach is the caller's to release.
- Weak references are on by default for your types and pay-for-play. They break cycles (a handler that holds the object that holds the source); outside XAML you rarely need them. Opt out with `no_weak_ref` only with a reason.
- Constructor injection only: dependencies are parameters of the implementation constructor (`make` forwards them). No static mutable state, no service locator, no `extern` globals holding services.

## Coroutines and lifetime

A coroutine runs synchronously to its first suspension point; after it, the caller's stack is gone. Everything it touches must be owned by the coroutine.

```cpp
winrt::fire_and_forget OrdersPage::Refresh_Click(IInspectable const&, RoutedEventArgs const&)
{
    auto lifetime{ get_strong() };
    auto queue{ DispatcherQueue() };

    OrdersState state{ OrdersState::Loading() };
    try
    {
        co_await winrt::resume_background();
        state = OrdersState::Loaded(co_await m_client.LoadOrdersAsync(m_cancel.Token()));
    }
    catch (winrt::hresult_error const& error)
    {
        state = OrdersState::Failed(error.code());
    }

    co_await wil::resume_foreground(queue);
    Render(std::move(state));
}
```

- **`this`:** call `get_strong()` **before the first suspension point** and hold it for the coroutine's life. Weak alternative: `auto weak{ get_weak() };`, then after every resume `if (auto strong{ weak.get() }) { … } else { co_return; }`. `get_strong` / `get_weak` exist only on types deriving `winrt::implements` (every runtime class and XAML page does); a plain C++ class uses `std::shared_ptr` / `std::weak_ptr`.
- **Parameters by value** (or owned handles): a `const&` parameter dangles after the first suspension. The unnamed `IInspectable const&` sender above is safe because it is never read. A `winrt::handle` passes by value, never as `HANDLE`.
- **Handlers:** an `async` event handler returns `winrt::fire_and_forget`. Register with `{ get_strong(), &Page::OnEvent }` or `{ get_weak(), &Page::OnEvent }`; a lambda captures `[weak_this{ get_weak() }]` or `[strong_this{ get_strong() }]`, never a bare `[this]` or `[&]` when the source can outlive the object. A strong capture holds a cycle with the source: **revoke** (`winrt::auto_revoke` revoker member, or the token) when the page unloads. `[this]` is fine only when the receiver owns the source (a page and its own button).
- **Cancellation:** a window's work is cancelled when it closes. Hold the `IAsyncAction` and `Cancel()` it, or poll `co_await winrt::get_cancellation_token()`. A cancellation is observed only at the next `co_await`; long loops poll the token. Cancellation does not flow to nested operations unless `cancellation_token.callback(…)` forwards it.
- **One waiter:** an async object is either `co_await`ed or has a `Completed` handler, never both; `get()` and `wait_for()` are waiters too.
- **Never block the UI thread:** `.get()` or `wait_for()` on an `IAsync*` from the UI thread is the C++ form of `.Result` (`B8`, `X17`). Await.
- **No `co_await` inside a `catch` block** (the language forbids it): record the failure in a local, leave the `try`, then await (as above).
- **Awaiting a `winrt::` async type restores the calling context** (apartment); awaiting `resume_background`, a duration or a kernel signal resumes on the thread pool. Put WinRT calls **after** `resume_background` so one hop does the work.

## The UI thread

- Background work reaches the UI only through the dispatcher queue: `co_await wil::resume_foreground(queue);` or `co_await winrt::resume_foreground(queue);` (also written `co_await queue;`). **Both always queue, even when already on the thread**, so the stack unwinds (C++/WinRT 2.0).
- Take the queue **once** (`auto queue{ DispatcherQueue() };`, the object's own `DispatcherQueue` property) before the hop; do not read a XAML property from the background thread to find it.
- **Shutdown differs:** `winrt::resume_foreground` / `co_await queue` returns `false` when the queue is shutting down (you stay on the calling thread); `wil::resume_foreground` throws `hresult_error` `0x800701ab` (`ERROR_NO_TASK_QUEUE`). Pick one per project and handle its shutdown case at the boundary.
- `wil::resume_foreground` needs `#include <wil/cppwinrt_helpers.h>` **after** the `winrt/Microsoft.UI.Dispatching.h` (or `Windows.System.h`) header, and keeps a reference to the dispatcher object: hold it in a local, not a temporary that dies before the resume.
- A XAML object touched off its thread throws `winrt::hresult_wrong_thread`. `apartment_context` returns to the caller's context; it is not a UI guarantee when the caller is unknown, so use the queue.

## Errors

- **Expected failures are return values**, not exceptions: a missing optional file, a user cancel, an offline response are `std::optional`, an enum or a result type. Microsoft's rule: throw only on an unexpected runtime error; everything else is handled near its source.
- **`winrt::hresult_error` is caught once, at the boundary:** the event handler, the coroutine root, or a `noexcept` ABI entry. It maps to the failed state of the region and the one persistent `InfoBar` (`desktop-windows:error-handling`). Read `error.code()` (an `hresult`), not `to_abi()` (which pushes COM thread-local state).
- **Check what the OS returns:** `winrt::check_hresult`, `check_bool`, `check_win32`, `check_nt`, `check_pointer` turn an error return into an exception at the call; an ignored `HRESULT` is a finding (`X19`).
- **No empty `catch (...)`**; a catch that logs and continues hides a bug. The projection converts `E_OUTOFMEMORY` to `std::bad_alloc`; do not catch it.
- **Unhandled exceptions fail fast on purpose.** `fire_and_forget` terminates through `RoFailFastWithErrorContext`, which keeps the stowed exception; a bare `noexcept` that lets a C++ exception escape loses it (`std::terminate`). Triage: `winapp run --debug-output` prints the original error and stack.
- A `noexcept` ABI method that awaits wraps its projection calls in a `fire_and_forget` lambda with **no captures** (parameters passed in); a synchronous one is `HRESULT abi() noexcept try { … } catch (...) { winrt::terminate(); }`.

## IDL and XAML types

- A type that XAML references (a page, a view model bound by `x:Bind`, a control, a converter) **must be a runtime class declared in IDL**, even in the same project. `midl.exe` then `cppwinrt.exe` generate the projected type and an implementation stub under `Generated Files\sources`; copy the stub into the project, then implement it. **`Generated Files` is never edited and never committed.**
- A plain C++ type that only your code uses stays a plain class: no IDL, no runtime class (the simplest thing, `desktop-windows:architecture`).

```idl
namespace Orders
{
    [default_interface]
    runtimeclass OrdersViewModel : Microsoft.UI.Xaml.Data.INotifyPropertyChanged
    {
        OrdersViewModel(Orders.IOrdersClient client);
        Windows.Foundation.Collections.IObservableVector<Orders.OrderRow> Rows{ get; };
        Boolean IsLoading{ get; };
    }
}
```

- Declaring a constructor in the IDL makes the class activatable; without one it is not.
- Three namespaces: `winrt::Orders` (projected, a smart pointer), `winrt::Orders::implementation` (a real C++ object: never construct it directly), `winrt::Orders::factory_implementation`. `make<T>`, `make_self<T>`, `com_ptr<T>` and `get_self<T>` take the **implementation** type; `weak_ref<T>` and `agile_ref<T>` take either.
- `x:Bind` over `{Binding}` (same rule as C#, `desktop-windows:ui-components`).
- **Optimized** (`<CppWinRTOptimized>true</CppWinRTOptimized>`) is on in new projects: `make` and uniform construction skip the factory. Leave it on.
- Project layout, derived controls, cross-IDL `import`, arrays across the ABI: `references/project-and-idl.md`.

## WIL

WIL is where `wil::resume_foreground` comes from; use the platform first, WIL where it removes boilerplate (`wil::unique_*` RAII for resources `winrt::handle` does not cover). Its result macros are a second error style next to `winrt::check_*`: one style per project, recorded. No version is pinned here; never add WIL to call one function (`references/project-and-idl.md`).

## Build, warnings and analysis

- **`/W4 /WX /permissive-` on every project.** Microsoft leaves `/WX` "to taste" because the `cppwinrt.exe` stubs warn until implemented: implement the stub before committing, never turn the flag off. Exclude `Generated Files` by name, not by `#pragma warning`.
- **`/analyze`** with the C++ Core Guidelines ruleset (`EnableMicrosoftCodeAnalysis`, `CppCoreCheckRules.ruleset`); clang-tidy where configured; SAL on Win32 boundaries.
- Build `msbuild App.vcxproj /p:Configuration=Debug /p:Platform=x64 /p:TreatWarningAsError=true`; run with identity `winapp run .\App.vcxproj`; package `winapp pack .\App.vcxproj -c Release --arch x64 --cert .\devcert.pfx` (fallbacks and prerequisites: `references/project-and-idl.md`). Platforms `x64;ARM64` (`B6`).

## Tests and coverage

- **GoogleTest** (D16), in a test project over a **plain C++ core library**: the logic that does not touch `Microsoft.UI.Xaml` types lives in a static library both the app and the tests link. Tests are `TEST_P` parameterized (no `if` or loop drives an assertion), named for behavior, with fakes of your own interfaces.
- Code that needs the XAML runtime has **no verified C++ in-process runner**: Microsoft's WinUI unit test template (`winapp new --template winui-unittest`) is a C# MSTest project. Keep such code thin (the runtime class forwards to the core library) and cover it with the E2E suite (`qa-desktop-<lang>`, `AutomationId` contract in `desktop-windows:test-ids`).
- **Floor:** ≥ 80% of lines of the files you wrote, because the default tool reports blocks and lines, not branches; ≥ 80% of branches when the project builds with `clang-cl` and reports with `llvm-cov`. The tool, the commands and the exclusions are in `references/testing-and-coverage.md`.

## Telemetry

Logs at decision points through the project's logging (not `OutputDebugString`), a span per outbound call, an `hresult` as hex, never a path or token; the boundary `catch` logs the code once.

## Common gotchas

- **`[this]` capture in a handler, then a crash on close** — `get_strong` / `get_weak` at registration, revoke on unload.
- **`const&` coroutine parameter read after an await** — pass by value.
- **`MyRuntimeClass x;` returned as a projected type** — an implementation on the stack; `make<>` it.
- **`com_ptr<Windows::Foundation::Uri>`** — a projected type; use the value.
- **XAML property read on a background thread** — `resume_foreground` first; `hresult_wrong_thread`.
- **`.get()` on the UI thread** — a freeze; await.
- **Raising `/std:c++20` "for coroutines"** — the package already enables `/await`; a standard change is a decision, not a fix.
