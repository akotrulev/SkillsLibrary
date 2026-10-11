# Request policy — the code behind `networking`

Loaded by [`SKILL.md`](../SKILL.md). Samples have no inline comments (CLAUDE.md § Comments).

## The categorised error

```ts
export type ProblemDetails = {
  type?: string;
  title: string;
  status: number;
  detail?: string;
  errors?: Record<string, string[]>;
};

export class AppError extends Error {
  constructor(
    message: string,
    readonly kind: 'network' | 'timeout' | 'http' | 'parse',
    readonly status?: number,
    readonly correlationId?: string,
    readonly retryAfterMs?: number,
    readonly problem?: ProblemDetails,
  ) {
    super(message);
  }

  get retryable(): boolean {
    if (this.kind === 'network' || this.kind === 'timeout') return true;
    return this.status === 408 || this.status === 429 || (this.status !== undefined && this.status >= 502 && this.status <= 504);
  }
}
```

`error.message` is a friendly title or a generic line plus the correlation id — it is **never** the raw body, and the UI never renders anything else ([`error-handling`](../../error-handling/SKILL.md)).

## ProblemDetails → `AppError`

```ts
export async function problemError(response: Response): Promise<AppError> {
  const problem = (await response.json().catch(() => null)) as ProblemDetails | null;
  return new AppError(
    problem?.title ?? 'The request failed.',
    'http',
    response.status,
    response.headers.get('x-correlation-id') ?? undefined,
    parseRetryAfter(response.headers.get('retry-after')),
    problem ?? undefined,
  );
}

export function parseRetryAfter(header: string | null, now = Date.now()): number | undefined {
  if (!header) return undefined;
  const seconds = Number(header);
  if (Number.isFinite(seconds)) return Math.min(seconds * 1000, 120_000);
  const date = Date.parse(header);
  return Number.isNaN(date) ? undefined : Math.min(Math.max(date - now, 0), 120_000);
}
```

The `Retry-After` ceiling (120 s) means a hostile or buggy header cannot park the app. A network failure is wrapped where `fetch` throws a `TypeError` (`kind: 'network'`); `AbortSignal.timeout` rejects with a `TimeoutError` DOMException (`kind: 'timeout'`); a caller abort rejects with `AbortError` and is rethrown untouched.

## Token attach and single-flight refresh

```ts
let refreshing: Promise<string> | null = null;

async function send(path: string, init: RequestInit, signal: AbortSignal, idempotencyKey?: string): Promise<Response> {
  const attempt = async (token: string) =>
    fetch(`${process.env.EXPO_PUBLIC_API_URL}${path}`, {
      ...init,
      signal,
      headers: {
        ...init.headers,
        Authorization: `Bearer ${token}`,
        ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
      },
    });

  const first = await attempt(await getAccessToken());
  if (first.status !== 401) return first;

  refreshing ??= refreshAccessToken().finally(() => {
    refreshing = null;
  });
  return attempt(await refreshing);
}
```

- **One refresh for N concurrent 401s** — the shared promise is the queue; the replay happens **once**. A second 401 after refresh is a session expiry: sign out in place (a modal re-auth, biometric where enrolled), not a loop.
- The module-level `refreshing` is a deliberate in-flight de-duplication, the one permitted module-level mutable; it holds a promise, never data, and is cleared on settle. In tests, inject `getAccessToken` / `refreshAccessToken`.
- Access token in memory; refresh token only in `expo-secure-store` ([`offline-and-storage`](../../offline-and-storage/SKILL.md)). With Auth0, the credentials manager owns refresh — wrap it, do not rebuild it (`auth0-react-native`).

## Timeouts by endpoint class

| Class | Default | Why |
|---|---|---|
| `read` | 15 s | A list or detail GET on a normal link answers in < 2 s; a cell dropout should fail inside half a minute |
| `write` | 30 s | The outcome is indeterminate on expiry — the idempotency key makes the replay safe |
| `upload` | 120 s, plus progress | Resumable or presigned uploads bypass the API server |

Tune from the observability data ([`mobile-<stack>:observability`](../../../../_shared/observability/SKILL.md)), not by feel. An **indeterminate write** (timeout or background mid-request) is not shown as failed or as saved: re-read the resource or replay with the same key — [`error-handling`](../../error-handling/SKILL.md).

## Circuit

Per endpoint class keep a counter of consecutive retryable failures in memory; after 5, short-circuit calls with `AppError('...', 'network')` for 30 s, then allow one probe. Reset on any success and on `onlineManager` going online. In-memory only — it must not survive a restart or mask a fixed server.
