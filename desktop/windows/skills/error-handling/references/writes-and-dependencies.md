# Writes, quit and relaunch — the desktop mutation path

Read when a screen saves, deletes or syncs, or when the app can quit with work in flight. The rules are those of `../SKILL.md` § Desktop deltas; this file is the how.

## A write is three steps, and quitting can land between any two

| Step | Rule |
|---|---|
| Intent recorded | The change is written to local storage (a row in a pending-operations table, or a draft file) **before** the request leaves, with a client-generated id (`Guid.CreateVersion7()`) |
| Request sent | With the same id as an idempotency key (`Idempotency-Key` header, or the id in the body) so a replay cannot duplicate |
| Outcome recorded | On success the pending row is removed; on a definite failure it is marked failed with `FailureKind`; on an **indeterminate** outcome (timeout, connection lost after send, quit) it stays pending |

On relaunch the app reads the pending rows **before** it shows data as final:

1. Ask the server for the operation by id (`GET /operations/{id}`, or `GET` the resource) → applied: drop the row; not applied: replay with the same id; unknown: keep and surface.
2. Show what is unresolved in the window banner: "We could not confirm your last change", with Retry and Discard. Never drop it silently.
3. A replay that gets a conflict (`409` / `412`) opens the conflict path of the feature, never a silent overwrite.

## Autosave

- Debounce, then write to a **temporary file in the same directory** and replace atomically (`File.Replace` or `File.Move(temp, final, overwrite: true)` on the same volume). A crash leaves the old file or the new one, never half of each.
- The document model marks itself dirty on the first change and clean on a confirmed write; the title shows the state.
- A write failure (`IOException`, `UnauthorizedAccessException`) is `FailureKind.Storage`: keep the dirty flag, keep the data in memory, raise the banner, offer *Save as…* with the file picker.

## Quit and close

```csharp
private async void OnClosing(AppWindow sender, AppWindowClosingEventArgs args)
{
    if (!viewModel.HasUnsavedWork)
    {
        return;
    }

    args.Cancel = true;
    var choice = await dialogs.AskSaveAsync(Content.XamlRoot);
    if (choice == SaveChoice.Cancel)
    {
        return;
    }

    if (choice == SaveChoice.Save && !await viewModel.SaveAsync())
    {
        return;
    }

    viewModel.DiscardDirtyMarker();
    sender.Destroy();
}
```

- `async void` is allowed here because it is an event handler; the whole body is guarded by the early returns and `SaveAsync` maps its own failures. A save that fails keeps the window open.
- Only the first closing window with unsaved work asks; a system shutdown (`AppInstance`/`Windows` end-session) saves a draft silently and lets the process end: there is no time to ask.
- An update (Velopack or Store) checks `HasUnsavedWork` for every window and **defers the restart** until the work is saved or the user chooses.

## Multi-window consistency

- One service owns the data (`OrdersStore`), exposes an `ObservableCollection` change feed or an event, and every window's view model subscribes. A write goes through the service.
- Window-local state (selection, scroll, filters) stays in the window's view model.
- A window closing unsubscribes (`Unloaded` / `AppWindow.Closing`), or the service keeps a dead window alive (`desktop-windows:performance`, leaks).

## Dependency failures

- **WebView2 missing:** check `CoreWebView2Environment.GetAvailableBrowserVersionString()` once at region creation inside a `try`/`catch (WebView2RuntimeNotFoundException)` that sets the region Failed with an install action (the Evergreen bootstrapper link). The check is an I/O helper, so the `catch` names the one exception and logs it.
- **COM unregistered:** catch `COMException` where the object is created, map `0x80040154` to the region's Failed state, log the CLSID. Never register a COM server from the app (needs admin).
- **Windows AI API unavailable:** run the readiness check before use (`desktop-windows:platform-integration`); the feature hides or explains, never throws.
- **A helper service:** every call has a timeout and a cancel; a dead helper is Failed with Retry, and the retry reconnects.

## Revalidate once

Wake, activation and network change can fire together. Funnel them through one method that skips a refresh if one started less than a few seconds ago or is running, so a laptop waking up does not send four identical requests.
