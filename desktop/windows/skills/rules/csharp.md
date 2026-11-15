---
paths:
  - "**/*.cs"
---

<!-- desktop-windows rules v1 (2026-11-15): core C#. Installed by /desktop-windows:rules; edit to fit this project, re-run to compare with the plugin's copy. -->

# C# / Windows code standards

Apply these to every C# file you write, edit or review. The tag after a rule is the severity a review reports: **blocker** ships a crash, a store or signing rejection or a security break, **major** is a design or correctness problem, **minor** is style, **nit** is preference. XAML, WPF, WinForms, C++/WinRT, accessibility, styling, localization, networking, persistence, test and package-config rules are separate files that load with those files.

**The codebase wins.** Where this project consistently does something another way, follow the project and do not flag it. Detect the TFM, the Windows App SDK major, the UI lane (WinUI, WPF, WinForms) and whether the app is packaged before writing: never use an API newer than the target, never flag a .NET 10 project for lacking a .NET 11 API, and never convert a WPF or WinForms app to WinUI as a side effect.

## Simplicity and scope

- Write the simplest thing that meets the requirement, then stop. No `interface` with one implementer and no test fake, no view model that mirrors a record, no wrapper that only forwards, no option nothing sets. An abstraction is earned on the second real need. *major, fix by inlining*
- Cut structure, never correctness: the region states, accessibility, cancellation, the denied path and the tests stay.
- No DI container, messenger or mediator the codebase did not choose; a messenger only between unrelated view models. *major*
- Never raise the TFM, the Windows App SDK major, the C# language version or the platform list as a side effect; that move is its own change (`migration`). *major*

## Safety and types

- Nullable reference types on and warnings as errors; no `null!` to silence a warning, no `#nullable disable`. *major*
- No `.Result`, `.Wait()` or `.GetAwaiter().GetResult()` in production code. *blocker*
- `async void` only on an event handler whose whole body is inside `try`/`catch`; everything else returns `Task`. *major*
- Records and `readonly` members by default; `sealed` classes; a mode is one enum or sealed hierarchy, never several booleans. *minor*
- No static mutable state; constants and `static readonly` immutable values are fine. *major*
- Time comes from an injected `TimeProvider`, never `DateTime.Now` / `UtcNow`. *minor*

## Concurrency and the UI thread

- Nothing blocks the UI thread: no `Thread.Sleep`, `Task.Wait`, lock held across I/O, and no file, network or database work on it. *blocker*
- Background results reach the UI through `DispatcherQueue.TryEnqueue`, batched, and the result is checked (`false` on shutdown). *major*
- Every async method that does I/O takes a `CancellationToken` and passes it on; work a window starts is cancelled when it closes. *major*
- `Task.Run` only for CPU-bound work, and it returns a value rather than touching the UI. *minor*

## State, architecture and dependencies

- View models are `sealed partial` classes on CommunityToolkit.Mvvm (`[ObservableProperty]`, `[RelayCommand]`); one per screen; they never reference a control, a window or the dispatcher. *major*
- Constructor injection only; one Generic Host composition root; no service locator, no `Ioc.Default.GetService` inside a class. *major*
- A data region's state is one sealed type (`Loading`, `Loaded`, `Empty`, `Failed(reason)`, plus `Stale` and `Offline` where cached), switched exhaustively; a failure carries a typed reason, never `Exception.Message`. *major*
- Several windows on the same data share one source of truth, not a copy per window. *major*

## Errors, logging and secrets

- Structured logging through `ILogger` message templates; never interpolation, never a token, a password or personal data in a log. *major; blocker for a secret*
- No empty `catch`, no `catch` that logs and continues without a state, no blanket `catch (Exception)` outside a boundary. *major*
- Unhandled-exception handlers (`Application.UnhandledException`, `TaskScheduler.UnobservedTaskException`, `AppDomain.UnhandledException`) are registered once, log, and do not swallow. *major*
- No secret in code, `appsettings.json`, a resource or the package; tokens live only in `PasswordVault` or DPAPI `CurrentUser`. *blocker*
- Input from outside the process (protocol and file activation, command line, toast arguments, a dropped or pasted item, a WebView2 message, an IPC message) is validated before it routes or opens a path. *blocker*

## Permissions, files and lifecycle

- The app never requires elevation. *blocker*
- Pickers are the Windows App SDK pickers built with `AppWindow.Id`; a `null` result is cancel. *major*
- Closing with unsaved work asks first (`AppWindow.Closing`); relaunch restores state; wake, reactivation and a network change revalidate. *major*

## Comments

- No inline comments, no commented-out code, no `TODO` / `FIXME`; a doc comment only for a contract the name cannot carry, and never one that restates the signature. Generated scaffold comments are removed. *minor; major when the comment exists because the code is unclear*
