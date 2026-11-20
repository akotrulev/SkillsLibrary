---
name: offline-and-storage
description: Use when a Windows app persists data (ApplicationData vs paths, SQLite/EF Core, settings, PasswordVault/DPAPI, migrations, offline cache). Triggers "save settings". Not for HTTP (networking).
disable-model-invocation: true
---

# Windows — Offline and Storage

Where a Windows desktop app keeps its data: **settings and files in the right place for packaged or unpackaged, a local SQLite database with migrations, secrets only in `PasswordVault` or DPAPI, and a cache that is marked stale offline.** Audit rows: section I of `desktop-windows:standards-audit`. Applies to WinUI, WPF and WinForms.

## Version lane

| Concern | Packaged (MSIX, primary) | Unpackaged (`WindowsPackageType=None`, WPF/WinForms default) |
|---|---|---|
| Settings and files | `ApplicationData.Current` (`Windows.Storage`) or the Windows App SDK `Microsoft.Windows.Storage.ApplicationData.GetCurrent()` | **No package identity, so no `ApplicationData.Current`.** Windows App SDK `ApplicationData.GetForUnpackaged(publisher, product)` (since 2.2.0; registry path fixed in 2.4.0), or `Environment.SpecialFolder.LocalApplicationData` + your own folder |
| Uninstall | The package's `LocalState` is removed with the app | Your folder stays: document it, offer "delete my data" |
| Secrets | `PasswordVault` or DPAPI | `PasswordVault` (verify, below) or DPAPI |
| Database | SQLite in `LocalFolder` | SQLite in `%LocalAppData%\<Product>` |
| Runtime | .NET 10 LTS (11 STS supported); EF Core 10 matches the TFM major | .NET 8/9 are out of support: flag |

**Two facts are not verified end to end** (plan §4.6, re-check before relying on them):
- **`PasswordVault` without package identity.** Microsoft's Credential Locker page says the WinRT APIs "can be used in WinUI as well as other desktop apps, such as WPF and WinForms" and lists no packaging requirement; it does not say the unpackaged case was tested. **Rule:** probe it once at startup behind a typed result, and fall back to DPAPI (`ProtectedData`, `DataProtectionScope.CurrentUser`) when `new PasswordVault()` throws. Record which one the app uses.
- **`GetForUnpackaged` semantics** on Windows App SDK 2.6: it exists in the API reference; the general "store and retrieve app data" guide still tells unpackaged apps to use plain file I/O or the registry. If the API is in doubt, use the file path.

## Pick the store by the data

| Data | Store | Never |
|---|---|---|
| A few user preferences | `ApplicationData.LocalSettings` (packaged) or a JSON file in the data folder | the registry for new settings, `appsettings.json`, a `.ini` next to the exe |
| Structured, queryable, growing | SQLite (`Microsoft.Data.Sqlite`, EF Core `Microsoft.EntityFrameworkCore.Sqlite`) | one JSON file rewritten on every change |
| Documents the user owns | A path from a picker (`desktop-windows:platform-integration`) | a hidden app folder |
| Cache | `LocalCacheFolder` (packaged) or `%LocalAppData%\<Product>\Cache` | `LocalFolder` (it is backed up and never evicted) |
| Temporary | `ApplicationData.TemporaryFolder` / `Path.GetTempPath()` with unique names | a fixed temp filename |
| Secret (token, password, key) | `PasswordVault`, or DPAPI-protected bytes | settings, a file, the database in plain text, a log |
| Roaming across devices | the server, or Credential Locker's own roaming | `RoamingSettings` for new code (quota-limited, packaged only) |

Paths are built from the API, never hard-coded: `Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Contoso", "Notes")`. Access them off the UI thread.

## Settings

One typed settings service, constructor-injected; the rest of the app never touches the store:

```csharp
public sealed class SettingsStore(IDataFolder folder)
{
    public async Task<Settings> LoadAsync(CancellationToken ct)
    {
        var path = folder.Resolve("settings.json");
        if (!File.Exists(path)) return Settings.Default;
        await using var stream = File.OpenRead(path);
        return await JsonSerializer.DeserializeAsync(stream, SettingsContext.Default.Settings, ct) ?? Settings.Default;
    }
}
```

- **Version the schema** (`SchemaVersion` in the file); an unknown or corrupt file falls back to defaults, is renamed `settings.json.bad`, and is logged — never crashes startup.
- **Write atomically:** write a temp file in the same folder, then `File.Replace`. A crash mid-write must not leave half a file.
- **Settings hold no secrets** (CLAUDE.md § Desktop code rules).
- **`IDataFolder`** resolves packaged vs unpackaged once; that is the one seam earned by two real implementations (`V5`).

## SQLite and EF Core

- **One connection string, one file** under the data folder. `PRAGMA journal_mode=WAL` and `foreign_keys=ON` at open.
- **EF Core migrations, applied at startup before any query**, behind a loading state with a failed body: `Database.MigrateAsync(ct)` in the host's startup, not in a view model. A migration failure is a *failed* state with a "Back up and reset" choice, never a blank window.
- **Back up before migrating** (copy the file with `VACUUM INTO` or the SQLite backup API), keep the last copy.
- **Never `EnsureCreated()` on a database that will evolve**, and never an in-memory provider as a test substitute: tests use a real SQLite file in a temp folder (CLAUDE.md § Backend code rules).
- **Queries are async, `AsNoTracking()` for reads, and off the UI thread.** A `DbContext` is short-lived: `IDbContextFactory<T>`, one per operation, never a singleton `DbContext` held by a window.
- **Several windows on the same data share one source of truth:** one repository-like service raising change notifications, not one context per window (`C9`).
- **Sensitive columns are encrypted** with a DPAPI-wrapped key, or the database file is encrypted (SQLCipher) when a threat model says so; never store a password hash you do not need.

## Secrets — `PasswordVault` and DPAPI

```csharp
public sealed class TokenStore(ILogger<TokenStore> logger) : ITokenStore
{
    private const string Resource = "Contoso.Notes";

    public void Save(string user, string refreshToken)
    {
        var vault = new PasswordVault();
        vault.Add(new PasswordCredential(Resource, user, refreshToken));
    }

    public string? Load(string user)
    {
        var vault = new PasswordVault();
        try
        {
            var credential = vault.Retrieve(Resource, user);
            credential.RetrievePassword();
            return credential.Password;
        }
        catch (COMException)
        {
            logger.LogInformation("No stored credential for the resource");
            return null;
        }
    }
}
```

- **`PasswordVault` holds short secrets only** (at most 20 credentials per app; not blobs). The access token stays in memory; the refresh token is the vault entry.
- **`FindAllByResource` / `Retrieve` throw `COMException` when nothing is stored:** that is "no credential", handled, not a crash. Call `RetrievePassword()` before reading `Password`.
- **Save only after a successful sign-in and only if the user opted in**; sign-out removes the credential.
- **DPAPI fallback:** `ProtectedData.Protect(bytes, entropy, DataProtectionScope.CurrentUser)` and store the ciphertext file in the data folder. `CurrentUser`, never `LocalMachine`. Add app-specific `entropy`.
- **Never log a secret, never put it in `appsettings.json`, an environment variable baked into the installer, or the binary** (`G11`, `K` rows in `desktop-shared:security`).
- For new sign-in designs, evaluate Windows Hello and passkeys; their desktop APIs are not verified here.

## Offline

- **Every data region has loading, loaded, failed, stale and offline** (CLAUDE.md § Desktop code rules). The local database or cache is what makes `loaded` possible offline: show cached rows with a "Last updated 14:02" label, and the offline `InfoBar` (persistent, user-dismissed).
- **Read-through cache:** show the cache immediately, revalidate in the background (`networking`), replace on success. A failed revalidate keeps the cache and marks it stale.
- **Writes offline** go to an outbox table (`Id`, `Kind`, `Payload`, `CreatedAt`, `Attempts`) drained in order when the network returns; each item carries an idempotency key so a retry cannot double-apply. The user sees "3 changes waiting to sync".
- **Conflicts** are a decision, not a guess: last-writer-wins only when the data allows it; otherwise show both versions and ask.
- **Time is `TimeProvider`**, stored UTC (`B11`).
- **Cache eviction:** a size or age cap, cleaned on startup off the UI thread; user-initiated "Clear cache" in Settings.

## Lifecycle and safety

- **Quitting with unsaved work asks first**, and relaunch restores state (CLAUDE.md § Desktop code rules). Autosave drafts to the data folder.
- **No disk I/O on the UI thread** — `File.ReadAllText` in a click handler is a finding. `await` the async APIs.
- **Close the database and flush on exit:** dispose the factory-created contexts; do not rely on finalizers.
- **A path from outside** (activation, drag-drop, a document's embedded path) is validated: canonicalize with `Path.GetFullPath`, check it stays under the expected root, reject reparse points where it matters.
- **Uninstall:** state what is left behind; provide "Delete all my data" for unpackaged apps.

## Telemetry

Spans around migration and large queries; a log at each fallback decision (vault → DPAPI, corrupt settings → defaults); metrics `storage.migration.duration`, `sync.outbox.pending`, `cache.age`. Never values, keys or paths that carry a user name.

## Common gotchas

- **`ApplicationData.Current` in an unpackaged app** — throws; use the unpackaged route.
- **Settings in `appsettings.json`** — it ships in the install folder, which is read-only for packaged apps.
- **A cache in `LocalFolder`** — backed up, never evicted.
- **`Retrieve` not wrapped** — `COMException` crashes the first launch.
- **`LocalMachine` DPAPI scope** — any user on the box can decrypt.
- **`MigrateAsync` on the UI thread without a state** — the window hangs, a failure is blank.
- **A singleton `DbContext`** — stale tracking, thread-safety bugs.
- **A half-written settings file** — write temp then `File.Replace`.
- **Roaming settings for secrets** — never.
