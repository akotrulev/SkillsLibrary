# React Native — Session expiry, OTA skew and app resume

The failures where **the app changed underneath the user**: the session ended, the JS bundle on disk is older than the server expects, or the app slept for an hour. All three recover in place; all three destroy unsaved work when handled with a sign-out or reload reflex.

*Deep dive for [`mobile-react-native-error-handling`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).*

---

## Session expiry — recover in place, never discard work

`networking` owns the mechanics (single-flight refresh, replay once — `networking/references/request-policy.md`); this file owns **what the UI does when that fails**. The default — an interceptor that navigates to the login route — unmounts the form the user is typing into.

```
401 → 1. Silent refresh (single-flight)       → ok → 2. Replay once → user saw nothing
                                              → fail → 3. Re-authenticate IN PLACE (modal) → replay → done
                                                       → declined → 4. Scoped failed state + banner
                                                                       (sign out only from a surface with nothing to lose)
```

1. **One refresh for N concurrent 401s.** Ten failing queries share one promise; parallel refreshes revoke a rotated token family.
2. **Replay exactly once**, marked. A replay that 401s again goes straight to rung 3 — never back into the ladder.
3. **Re-auth in place is a modal, not a redirect.** Present the sign-in as a modal route or sheet over the mounted screen so the form, filters and scroll position survive. **Biometric re-auth is often the right rung 3** when a refresh token exists in `expo-secure-store` behind `requireAuthentication`: one Face ID / fingerprint prompt, then replay. On success dismiss and replay the pending requests.
4. **Sign out only from a clean surface.** A dirty form (`formState.isDirty`), a pending mutation or an editor with content ⇒ do not navigate; keep the modal affordance. For long forms persist a draft through the guarded storage wrapper (it may be unavailable — see [`writes-and-dependencies.md`](writes-and-dependencies.md)).

```tsx
export function useReauthModal() {
  const router = useRouter();
  return useCallback(async (): Promise<boolean> => {
    router.push('/reauth');
    return reauthResult.wait();
  }, [router]);
}
```

`reauthResult` is a single-use promise the modal resolves with `true` on success and `false` on dismissal; the ladder awaits it and replays or falls to rung 4. Tokens stay in Keychain / Keystore-backed storage only; the modal never logs them.

- **403 is not 401.** Permission-denied renders in the scoped region with **no retry**, no refresh and no re-auth. Conflating them logs the user out for tapping an admin control.
- **Only your own API triggers the ladder.** A 401 from a third-party host never signs the user out.
- **Warn before the deadline.** If the backend has a hard session limit, surface "signing out in 2 minutes — stay signed in?" from the session's real expiry, not from HTTP idleness (a user typing a long form is not idle).
- **Return the user to where they were.** After a sign-out, route back to the exact route and params, not the home tab. Treat the return target as untrusted input and validate it against the route table.
- **Sign-out clears every store** (`offline-and-storage` I9) — and the Query cache, so the next user never sees the last user's data.

## OTA update skew — the bundle that outlived its server

`expo-updates` downloads a new JS bundle in the background; it applies at the **next cold start** unless the app reloads. A server deployed with a breaking contract change meets clients still running the old bundle, and a native build can lag behind the JS that runs on it. Detect, prompt, reload **once**.

```tsx
import * as Updates from 'expo-updates';
import { useCallback, useRef } from 'react';

export function useOtaRestart(hasUnsavedWork: boolean) {
  const { isUpdatePending } = Updates.useUpdates();
  const reloading = useRef(false);

  const restart = useCallback(async () => {
    if (hasUnsavedWork || reloading.current) return;
    reloading.current = true;
    await Updates.reloadAsync();
  }, [hasUnsavedWork]);

  return { isUpdatePending, restart };
}
```

The root layout raises one banner entry keyed `ota.pending` while `isUpdatePending` is true ("A new version is ready" with a **Restart** action bound to `restart`); the action is disabled, with the reason shown, while work is unsaved.

- **One guarded `Updates.reloadAsync()`**, and it runs only from the user's tap on the prompt (the ref stops a double tap), or automatically only while the current view is already broken (a contract mismatch rendered as the failed body) **and** nothing is dirty. An unguarded reload against a bad bundle is a reload loop. `Updates.reloadAsync()` is also the single reload path — no second `DevSettings.reload`.
- **Never reload over unsaved work.** Dirty form, pending mutation, an upload in flight ⇒ the prompt waits; it is a banner entry with the dedupe key `ota.pending`, so it stays one.
- **Server-driven skew** (the API answers `426` or a `min-client` header): treat it as the same prompt when a pending update exists; when none exists, show a failed body that says to update from the store, not a retry button.
- **Check, then fetch.** On resume call `Updates.checkForUpdateAsync()`, then `fetchUpdateAsync()` when `isAvailable`; `useUpdates()` reflects both — do not hand-roll state.
- **Never in development.** `Updates.isEnabled` is false in dev builds and Expo Go; guard on it.
- **Native builds lag JS.** An OTA update is only applied to a compatible native runtime (`runtimeVersion` policy — `mobile-shared-release`); a store build whose runtime is older than the server's floor needs the **forced-update path** (MASVS-CODE-2): a server-side minimum version, a blocking screen with a store link, and no other action.
- **Report it.** The prompt shown, accepted and dismissed are events for the crash reporter, tagged with the update id so a JS error symbolicates against the right bundle (`mobile-shared-observability`).

## App resume — revalidate, never show yesterday as current

The web's stale-tab restore becomes **foreground resume**: the OS may have suspended the process for hours, killed sockets, or restored it cold from process death.

- **Foreground + reconnect revalidate** through `focusManager` on `AppState` and `onlineManager` on NetInfo (`networking`). Leave `refetchOnWindowFocus` and `refetchOnReconnect` on; tune `staleTime`.
- **A resumed screen with data older than `staleTime` renders the stale marker until the refetch lands**, never the old numbers as current. A failed revalidation keeps the data and the marker.
- **Session first.** On resume, if the access token has expired, the first revalidation runs the 401 ladder; the user returns to a working screen or to the in-place re-auth, not to a wall of failed regions.
- **Android process death** restores navigation state and drafts; any region restoring from a persisted cache renders as stale until it revalidates.
- **A resumed connection** (socket, SSE) reconnects with jitter and revalidates the queries it feeds; its status ("reconnecting…") is legible, and live data is dimmed, never shown as current.
- **Deep link on resume** is untrusted input; validate it before it routes, and never let it skip the ladder.
