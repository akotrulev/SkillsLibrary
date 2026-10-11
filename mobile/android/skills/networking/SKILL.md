---
name: networking
description: Use when an Android app must call an API — Retrofit 3 + OkHttp (Ktor 3.6 in the KMP lane), kotlinx.serialization, timeout budgets per endpoint class, coroutine cancellation, bounded retries with Retry-After, no retry offline, ProblemDetails, OkHttp Authenticator refresh, WebSocket, Network Security Config. Triggers "request hangs on cell", "retry storm", "refresh token race". Do NOT use for the failure UI (`mobile-android:error-handling`), forms, or Room (`-offline-and-storage`).
---

# Android — Networking

Owns the **request-level half** of resilience: how a call is made, cancelled, timed out, retried, authenticated and categorised, and how a socket lives and dies with the app. The **UI half** (failed region, banner, stale marker) is `mobile-android:error-handling`'s; this skill produces the categorised error it renders. Web analog: [`fe-react:data-fetching`](../../../../frontend/react/skills/data-fetching/SKILL.md) — timeout, ordering and critical-vs-optional rules carry over; RSC, Server Actions and cache tags do not. Sibling: [`mobile-ios:networking`](../../../ios/skills/networking/SKILL.md).

## Version lane

| Concern | Primary | Brownfield / lane |
|---|---|---|
| HTTP client | Retrofit 3 on OkHttp, `suspend` service functions | Retrofit 2.x — same shape; match the project's OkHttp major, check `./gradlew :app:dependencies` before assuming 5.x |
| KMP shared client | Ktor 3.6 with the engine per platform (`OkHttp` on Android) `[KMP]` | [`kotlin-multiplatform`](../kotlin-multiplatform/SKILL.md) |
| Serialization | kotlinx.serialization with Retrofit's first-party `converter-kotlinx-serialization` | Moshi / Gson already present — match, never add a second |
| Cancellation | Structured concurrency; the ViewModel scope cancels with the screen | Same |
| Reachability | `ConnectivityManager.registerDefaultNetworkCallback` → `Flow`, never a ping | Same |
| Cleartext / trust | Network Security Config, `cleartextTrafficPermitted="false"` | Same |

Detect an existing client first (Retrofit, Ktor, a generated OpenAPI client, an in-house wrapper) — **match it; never add a second HTTP layer.**

## When to use

- Writing the API service or a call against it, an upload, a download
- A request hangs on a bad cell link; a retry storm; a duplicate write
- Attaching a token, handling `401`, refreshing once
- Refetching on foreground and on reconnect
- A WebSocket or SSE stream that must close in the background

## When NOT to use

- Failed region, banner, offline indicator, forced-update prompt → `mobile-android:error-handling`
- Persisting responses, an offline write queue, sync → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- Where server data lives → [`architecture`](../architecture/SKILL.md)
- Form submit UX, field errors → [`forms`](../forms/SKILL.md)
- Auth provider setup → `mobile-android:auth0`; token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- FCM token registration → `mobile-android:push-and-deep-links`
- Uploads that outlive the process → `mobile-android:system-integration`
- Another stack → `mobile-ios:networking`, `mobile-react-native:networking`

## One concrete client

One `OkHttpClient` and one Retrofit service per API; budgets, interceptors and the authenticator live in **one module**. Repositories call the service; a ViewModel never does. The service is a Retrofit **interface** (the framework's idiom) — no wrapper interface on top of it.

```kotlin
interface OrdersApi {
    @GET("orders")
    suspend fun orders(@Query("page") page: Int, @Query("q") query: String?): OrdersPageDto

    @POST("orders")
    suspend fun create(
        @Header("Idempotency-Key") key: String,
        @Body body: CreateOrderDto,
    ): OrderDto
}

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun okHttp(authenticator: TokenAuthenticator, tokens: AccessTokenSource, policy: RetryPolicy): OkHttpClient =
        OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .writeTimeout(15, TimeUnit.SECONDS)
            .callTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(BearerInterceptor(tokens))
            .addInterceptor(EndpointBudgetInterceptor)
            .addInterceptor(policy)
            .authenticator(authenticator)
            .build()

    @Provides
    @Singleton
    fun retrofit(client: OkHttpClient, json: Json): Retrofit =
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()

    @Provides
    @Singleton
    fun ordersApi(retrofit: Retrofit): OrdersApi = retrofit.create(OrdersApi::class.java)
}
```

- **The base URL is `BuildConfig` from a Gradle property** — public by design; no secret rides in it. `https` only; a cleartext exception carries a recorded reason ([`mobile-<stack>:security`](../../../_shared/security/SKILL.md) § 2).
- **`Json { ignoreUnknownKeys = true; explicitNulls = false }` is one instance**, configured once; a DTO is a `@Serializable` data class separate from the domain model.
- **A decode failure becomes `ApiError.Drifted`** — never `runCatching { … }.getOrDefault(emptyList())`. A single-object endpoint is never decoded as a list. The UI renders *failed*, not *empty*.
- **Never log a URL with a query secret, a body or a token.** The only logging interceptor is `HttpLoggingInterceptor` at `Level.BASIC` in debug builds, with `redactHeader("Authorization")`; none is planted in release.
- No mutable state in the client; the one mutable thing, the current token, lives in the token source below.

The categorised `ApiError`, `RetryPolicy`, the authenticator, ProblemDetails mapping and the WebSocket wrapper are in [`references/request-policy.md`](references/request-policy.md).

## Timeout budgets — by endpoint class

`OkHttpClient` defaults (10 s connect, 10 s read, **no call timeout**) leave a request on a dying cell link hanging for as long as bytes dribble in. Set all four, and a **per-endpoint call budget**:

| Class | `callTimeout` | Used for |
|---|---|---|
| `Read` | 15 s | `GET` screens and lists |
| `Write` | 30 s | `POST` / `PATCH` / `DELETE` |
| `Upload` | 120 s | multipart, large bodies |

```kotlin
@Target(AnnotationTarget.FUNCTION)
@Retention(AnnotationRetention.RUNTIME)
annotation class Budget(val endpointClass: EndpointClass)

object EndpointBudgetInterceptor : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val invocation = chain.request().tag(Invocation::class.java)
        val endpointClass = invocation?.method()?.getAnnotation(Budget::class.java)?.endpointClass
            ?: EndpointClass.Read
        return chain.withCallTimeout(endpointClass.seconds, TimeUnit.SECONDS).proceed(chain.request())
    }
}
```

- Budgets are **longer than web's** and are set here, never at call sites.
- `SocketTimeoutException` / `InterruptedIOException` from a budget is a **failure** (render the timeout body); `CancellationException` is **not** — the user left. **A `catch (e: Exception)` that swallows `CancellationException` breaks structured concurrency and shows a banner every time the user navigates away** — rethrow it.

## Cancellation — the scope owns the request

```kotlin
@HiltViewModel
class OrdersViewModel @Inject constructor(private val orders: OrdersRepository) : ViewModel() {

    private val query = MutableStateFlow("")

    val uiState: StateFlow<OrdersUiState>
        field = MutableStateFlow<OrdersUiState>(OrdersUiState.Loading)

    init {
        viewModelScope.launch {
            query.debounce(300).distinctUntilChanged().collectLatest { q ->
                uiState.value = OrdersUiState.Loading
                uiState.value = orders.search(q).fold(
                    onSuccess = OrdersUiState::Loaded,
                    onFailure = { OrdersUiState.Failed(it.toApiError()) },
                )
            }
        }
    }
}
```

- **`collectLatest` / `flatMapLatest` cancels the previous request when the key changes**, so a slow answer for a replaced query never overwrites a newer one. Retrofit's `suspend` calls are cancellable — cancelling the coroutine cancels the OkHttp `Call`.
- A repository function is **main-safe** — it switches to an injected `IoDispatcher` when it does blocking work ([`basics`](../basics/SKILL.md)); Retrofit `suspend` functions already are.
- `async` / `coroutineScope` cancel their children; `GlobalScope` and an unowned `CoroutineScope(Dispatchers.IO)` do not — never use them for a request.
- A `Result`-returning repository must rethrow `CancellationException`; `runCatching` swallows it, so wrap with a helper that rethrows (one `suspendRunCatching` in the data module).

## Retries — bounded, polite, never offline

| Situation | Rule |
|---|---|
| Idempotent read failing with `IOException`, `408`, `429`, `502`, `503`, `504` | up to **2** retries, exponential backoff with jitter |
| `429` / `503` with `Retry-After` | wait **exactly that** (seconds or HTTP date), capped; never sooner |
| Write (`POST` / `PATCH`) | retried **only** with an `Idempotency-Key` the server honours; otherwise never |
| `4xx` other than `408` / `429` | never retry |
| **Device offline** (no validated network) | **no retry at all** — fail fast, or queue ([`offline-and-storage`](../offline-and-storage/SKILL.md)) |
| Repeated failures on one endpoint | open a circuit: stop for a cool-down, then one probe |

Retries live in **one** place — the `RetryPolicy` interceptor, [`references/request-policy.md`](references/request-policy.md). `retryOnConnectionFailure(true)` (OkHttp's default) already retries some connection failures; set it deliberately and do not stack a second retry loop in a repository or ViewModel. **An idempotency key is generated once per user intent**, not per attempt.

## Foreground and reconnect

Revalidate on foreground (`repeatOnLifecycle(STARTED)`) and when a `ConnectivityManager` default-network callback `Flow` reports a validated network; pull-to-refresh is the canonical manual refetch and a failed pull marks the list stale. The `Connectivity` class is in [`references/connectivity-and-trust.md`](references/connectivity-and-trust.md).

## Ordering and critical vs optional

- **Key a reload by every parameter it depends on** (`combine(query, filters, page).collectLatest`).
- **Classify each call critical or optional**: `coroutineScope { async … }` for calls critical together (one failure cancels the siblings); `supervisorScope` with `Result`-capturing children the moment one is optional, and render the partial result.
- A dependent call runs after the first one succeeds, not behind a flag that spins when its parent failed.
- **Pagination**: Paging 3 (`androidx.paging`) with a `RemoteMediator` when Room backs the list ([`offline-and-storage`](../offline-and-storage/SKILL.md)), or a hand-written next-page call for a simple list; never fetch all pages up front.
- **Mutations** disable their control while pending, carry the idempotency key, and refresh or patch precisely the state they change.

## Realtime — WebSocket

Pull above; push is a socket the app opens **only while a screen needs it and the app is in `STARTED`.** OkHttp's `WebSocket` (or Ktor's, in the KMP lane) is opened in a `repeatOnLifecycle(STARTED)` block or a `callbackFlow`, closed with `close(1000, …)` when the screen stops, reconnected with jittered backoff only when `isOnline`, and **the data it feeds is revalidated after every reconnect** — messages were missed. A malformed frame is dropped and counted, never crashes the collector. Background delivery is FCM (`mobile-android:push-and-deep-links`), not a held-open socket (Doze closes it). Wrapper in [`references/request-policy.md`](references/request-policy.md).

## Network Security Config

`android:networkSecurityConfig` is the one place cleartext and trust are decided: `cleartextTrafficPermitted="false"`, user CAs only in `<debug-overrides>`, a pin-set with a backup pin, never a trust-all manager. Details and the API 37 `ACCESS_LOCAL_NETWORK` note: [`references/connectivity-and-trust.md`](references/connectivity-and-trust.md).

## Rules

- One client and one Retrofit service per API; match an existing client.
- `https` only; base URL is configuration, not a secret; Network Security Config owns trust.
- A budget on every request by endpoint class; a timeout fails, `CancellationException` is rethrown and silent.
- Cancellation flows from `viewModelScope` / `collectLatest`; no `GlobalScope`, no unowned scope.
- Retries ≤ 2 for reads, jittered, honouring `Retry-After`; none for writes without an idempotency key; none offline; one place.
- Decode failure is `Drifted` and renders as failed.
- `401` triggers exactly one shared refresh (a locked `Authenticator`), then one replay, then re-auth in place.
- Sockets closed when the screen stops.
- No token, body or PII in logs; no logging interceptor in release.

## What NOT to do

- No `runBlocking` or `.execute()` on the main thread; no `Thread.sleep` waiting on a request.
- No `NetworkOnMainThreadException` "fix" with `StrictMode` permissive policies.
- No `catch (e: Exception)` that eats `CancellationException`; no `runCatching` around a suspend call without rethrow.
- No `Gson` / `Moshi` added to a kotlinx.serialization project, or the reverse.
- No `interface ApiClient` wrapping Retrofit with one implementation "for testing" — a fake of the *repository* or a `MockWebServer` is the seam.
- No `usesCleartextTraffic="true"`; no hardcoded LAN URL in a release build type.
- No retry on a `POST` without an idempotency key; no fixed-interval retry without jitter.
- No socket opened in a composable body or left open in the background.

## Generation steps

1. Read the existing client, token handling and DTO style; detect Retrofit / OkHttp / Ktor and the serialization library.
2. Define endpoint classes and budgets; write or extend the OkHttp module, `ApiError`, the DTOs.
3. Put retry, `Retry-After` and the circuit in `RetryPolicy`; add `Connectivity`.
4. Add the `Authenticator` and single-flight refresh ([`references/request-policy.md`](references/request-policy.md)).
5. Write feature calls as service functions behind a repository; load from `collectLatest`; map `ApiError` for [`forms`](../forms/SKILL.md) and `error-handling`.
6. Realtime: open and close the socket with the lifecycle; revalidate on reconnect.
7. Configure Network Security Config; add `MockWebServer` tests.

## Validation

Inside a `Gate: none` plan task, run none of these and report "written, not run"; the plan's gate task runs them.

- Build clean; detekt, ktlint and Android Lint pass.
- With the emulator's network at "100 % loss": a request past its budget fails at the deadline with a timeout; leaving the screen cancels silently.
- Airplane mode: no retry attempts in the log; reconnect refetches.
- A `503` with `Retry-After: 5` retries after 5 s, not sooner; N concurrent `401`s cause exactly one refresh.
- Dev-side tests (`MockWebServer`, `runTest` with a virtual clock for backoff): [`unit-testing`](../unit-testing/SKILL.md).

## Handoffs

- Failed region, banner, stale, forced update → `mobile-android:error-handling`
- Persisted cache, write queue, token storage → [`offline-and-storage`](../offline-and-storage/SKILL.md)
- State ownership → [`architecture`](../architecture/SKILL.md) · field errors → [`forms`](../forms/SKILL.md)
- Cleartext, pinning, secrets → [`mobile-<stack>:security`](../../../_shared/security/SKILL.md)
- API contract tests → `qa-api-typescript` / `qa-api-dotnet` / `qa-api-java` (peer of the backend)
