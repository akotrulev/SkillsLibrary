# React Native — Write failures, third-party failures and a full disk

Three surfaces where the failure is **not a read**: a write that costs work (and may have half-happened), a third-party SDK that fails on its own schedule, and the device itself running out of room.

*Deep dive for [`mobile-react-native:error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Mutation failures — backgrounding mid-write is routine

A failed read costs information; a failed **write** costs work and may have succeeded anyway. On a phone the **indeterminate outcome is the common case**: the user switches app, the OS suspends the process, the link drops between request and response.

- **Pending is the double-submit guard.** Disable the control while `isPending`; guard the keyboard's return key too. A second tap on "Pay" is a duplicate charge, not a wrinkle.
- **Idempotency key per user intent, not per attempt** — generated once when the user starts the action, kept across retries and across a process restart if the write is queued (`networking`; `offline-and-storage` I10). It is what makes a timed-out write safe to replay.
- **An unknown outcome is its own state.** A timeout, or a write interrupted by backgrounding or reconnect, renders "We couldn't confirm whether this saved", then **refetches the resource or replays with the same key** — never a definite failure and never a definite success. Reconcile on resume before showing the screen as current.
- **A rolled-back optimistic update is announced.** The row reverts and a banner says what did not happen ("Couldn't move the ticket — it's back in Review"). The form keeps what the user typed; never clear it on a failed submit.
- **409 / 412 is a decision, not a retry.** "This was updated elsewhere" with *Reload theirs* or *Overwrite* (a re-issued `If-Match`). Never auto-retry a conflict.
- **422 belongs on the fields** (`forms`, `setError`), not in the banner.
- **Bulk writes report per item** — "12 of 15 archived", the three named and retryable.
- **Mutations never auto-retry from the query client** (`networking`); replay is the offline queue's decision, in order, with its keys.

```tsx
const archive = useMutation({
  mutationFn: (input: ArchiveInput) => archiveOrders(input, { idempotencyKey }),
  onError: (error) => notify.error(toAppError(error), { region: 'Orders' }),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
});

<Pressable
  accessibilityRole="button"
  accessibilityState={{ disabled: archive.isPending, busy: archive.isPending }}
  disabled={archive.isPending}
  onPress={() => archive.mutate(selection)}
  testID="Orders.Archive"
>
```

`idempotencyKey` comes from a `useRef` created when the flow begins. `notify.error` is the **one** raise-point for mutations when no global `MutationCache.onError` exists — never both.

## Third-party dependencies — fail without taking the screen with them

Maps, payment sheets, push, analytics, crash reporters, feature flags, chat widgets and embedded web views each ship someone else's native and JS code and fail independently. The split teams get backwards is **which failures the user hears about**.

| Dependency | If it fails | User-visible? |
|---|---|---|
| Analytics, tags, attribution | Nothing — the app is unaffected | **No.** Log it; no banner for a failed beacon |
| Feature-flag provider | Evaluate to **defaults** and render | **No**, but the defaults are deliberate and the failure alarms the team |
| Map, chart, rich embed, `WebView` | That region shows its failed body | **Yes**, scoped to the region |
| Payment sheet, sign-in provider, push registration | The flow cannot complete | **Yes**, prominently, with a stated fallback |
| A native module that fails to **link** (missing in the binary, Expo Go, wrong build) | **A crash at import, not a degraded region** | Prevented, not handled — see below |

- **Each third party gets its own boundary and its own timeout.** A widget throwing in render degrades its region; a script or SDK call that never returns must not leave a region loading forever.
- **A flag provider never blocks first render.** Start from bootstrapped or cached values; decide fail-open or fail-closed per flag (a kill-switch fails closed, a rollout flag fails to its default).
- **A native module that fails to link is a crash.** `requireNativeModule` / `import` of a missing module throws at load, before any boundary exists. Guard optional modules at one place (`try { require(...) } catch` in an adapter that reports once and returns a no-op or `unavailable` result), prefer config plugins and development builds so the module is in the binary, and make the unavailable result a **failed body** for that feature, never an app crash. Never in a test body — the adapter is where the catch lives and it logs what it caught.
- **A permission denied is not a failure** — it is the working denied screen (`device-features`).
- **A third party's 401 or 5xx is never your session's problem** — it never starts the 401 ladder and never reaches the route boundary if it can be helped.
- **Load heavy embeds lazily** (a static preview that mounts the real map on interaction) so the failure is cheap and the startup is faster ([`performance`](../../performance/SKILL.md)).

## Storage is full — degrade to memory, say it once

`offline-and-storage` makes a write that cannot complete (disk full, quota, a cache the OS purged under pressure) **throw a typed error at one repository boundary**. This skill owns what happens next.

```ts
export class StorageFullError extends Error {}

export async function writeOrDegrade(write: () => Promise<void>, memory: Map<string, string>, key: string, value: string, notify: (message: string) => void): Promise<void> {
  try {
    await write();
  } catch (error) {
    if (!(error instanceof StorageFullError)) throw error;
    memory.set(key, value);
    notify('Your device is low on storage, so changes may not be kept after you close the app.');
  }
}
```

- **Only the typed error degrades**; anything else rethrows to the boundary and the crash reporter. No blanket catch that swallows a bug.
- **Fall back to memory for the session**, so the app keeps working; the value is lost on process death, and the notice says so.
- **One notice per session** (dedupe key `storage.full`), a banner entry with a close control — not one per failed write.
- **Never degrade a secret to memory silently into a weaker store.** A failed secure-store write for a token keeps the token in memory only, and the next launch signs in again; it never falls back to MMKV or AsyncStorage.
- **Caches are disposable.** The OS may wipe caches under pressure; a missing cached file or database row is a refetch, not an error banner.
- **Persisted drafts and the mutation queue** that cannot be written tell the user their changes are not safe to leave behind, and keep them in memory while the screen is open.
