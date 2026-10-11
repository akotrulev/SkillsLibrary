# Request policy — errors, retry, refresh, ProblemDetails, WebSocket

Everything here lives in the data module beside the OkHttp configuration. Nothing is a public API of a feature.

## `ApiError` — one categorised type

```kotlin
sealed interface ApiError {
    data object Offline : ApiError
    data object TimedOut : ApiError
    data object Unauthorized : ApiError
    data object NotFound : ApiError
    data object Conflict : ApiError
    data class RateLimited(val retryAfter: Duration?) : ApiError
    data class Validation(val fields: Map<String, List<String>>) : ApiError
    data class Server(val status: Int, val correlationId: String?) : ApiError
    data class Drifted(val endpoint: String) : ApiError
    data object Unexpected : ApiError
}

fun Throwable.toApiError(): ApiError = when (this) {
    is HttpException -> toApiError()
    is SocketTimeoutException, is InterruptedIOException -> ApiError.TimedOut
    is UnknownHostException, is ConnectException -> ApiError.Offline
    is SerializationException -> ApiError.Drifted(endpoint = "unknown")
    else -> ApiError.Unexpected
}
```

- `UnknownHostException` is **offline or DNS**, not a server error; the UI tells them apart from `Server`.
- `CancellationException` never reaches this function — it is rethrown first.
- The UI maps each case to a string resource; it never renders `message`.

```kotlin
suspend inline fun <T> suspendRunCatching(block: () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (cancellation: CancellationException) {
        throw cancellation
    } catch (error: Exception) {
        Result.failure(error)
    }
```

## ProblemDetails

```kotlin
@Serializable
data class ProblemDetailsDto(
    val type: String? = null,
    val title: String? = null,
    val status: Int? = null,
    val errors: Map<String, List<String>> = emptyMap(),
    val traceId: String? = null,
)

fun HttpException.toApiError(): ApiError {
    val problem = response()?.errorBody()?.string()?.let { runCatching { json.decodeFromString<ProblemDetailsDto>(it) }.getOrNull() }
    return when (code()) {
        401 -> ApiError.Unauthorized
        404 -> ApiError.NotFound
        409 -> ApiError.Conflict
        422, 400 -> if (problem?.errors?.isNotEmpty() == true) ApiError.Validation(problem.errors) else ApiError.Server(code(), problem?.traceId)
        429 -> ApiError.RateLimited(response()?.headers()?.get("Retry-After")?.let(::parseRetryAfter))
        else -> ApiError.Server(code(), problem?.traceId)
    }
}
```

An error body that is not ProblemDetails degrades to `Server(status)`; it never throws from the mapper. The `traceId` is shown as a "reference" the user can quote, not as text.

## `RetryPolicy` — the one retry loop

```kotlin
class RetryPolicy @Inject constructor(
    private val connectivity: ConnectivityState,
    private val clock: Clock,
    private val sleeper: Sleeper,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        var attempt = 0
        while (true) {
            if (!connectivity.isOnline) throw IOException("offline")
            val outcome = runCatching { chain.proceed(chain.request()) }
            val response = outcome.getOrNull()
            val retryable = isRetryable(chain.request(), response, outcome.exceptionOrNull())
            if (!retryable || attempt >= MAX_RETRIES) return response ?: throw outcome.exceptionOrNull()!!
            val wait = response?.header("Retry-After")?.let(::parseRetryAfter) ?: backoff(attempt)
            response?.close()
            sleeper.sleep(minOf(wait, MAX_WAIT))
            attempt++
        }
    }
}
```

- OkHttp interceptors are **blocking** and run on OkHttp's dispatcher thread for `enqueue`, and on the Retrofit `suspend` adapter's thread — never the main thread. The sleep is on that thread and is interrupted when the call is cancelled.
- `isRetryable`: method is `GET` / `HEAD`, or has an `Idempotency-Key` header; status in `408, 429, 502, 503, 504` or an `IOException` that is not offline.
- `backoff(attempt)` = `min(cap, base * 2^attempt) ± jitter`; `Sleeper` and `Clock` are injected so the test runs on virtual time.
- The circuit is a per-host failure counter in the same class: after N consecutive failures it throws `IOException("circuit open")` for the cool-down, then lets one probe through.

## `TokenAuthenticator` — single-flight refresh

OkHttp calls `Authenticator.authenticate` on a `401`, serially **per call** but concurrently across calls. N parallel `401`s must cause one refresh.

```kotlin
class TokenAuthenticator @Inject constructor(
    private val tokens: TokenStore,
    private val refreshApi: Lazy<AuthApi>,
) : Authenticator {

    private val lock = Any()

    override fun authenticate(route: Route?, response: Response): Request? {
        if (response.responseCount() >= 2) return null
        val failedToken = response.request.header("Authorization")?.removePrefix("Bearer ")
        synchronized(lock) {
            val current = tokens.currentAccessToken()
            if (current != null && current != failedToken) return response.request.withBearer(current)
            val refreshed = runBlocking { tokens.refresh(refreshApi.get()) } ?: return null
            return response.request.withBearer(refreshed)
        }
    }
}
```

- The `synchronized` block plus the **"token changed while I waited"** check is the single-flight: the first caller refreshes, the rest see a new token and replay without refreshing.
- `responseCount() >= 2` stops a loop where the replay also returns `401`; returning `null` surfaces `ApiError.Unauthorized`, and the UI re-authenticates **in place** (a modal, biometric as the common third rung — `mobile-android:error-handling`).
- `runBlocking` is acceptable **only here**: `Authenticator` is a blocking OkHttp contract on an OkHttp thread, never the main thread. A comment is not needed; the class doc states the constraint.
- The refresh uses a **separate** client without this authenticator (a `Lazy<AuthApi>` built on a plain `OkHttpClient`), or it recurses.
- A refresh that is rejected (`invalid_grant`) clears the stored session and emits "signed out" to the session holder — it does not loop.
- The refresh token and access token live in the Keystore-backed store ([`offline-and-storage`](../../offline-and-storage/SKILL.md)), never in `SharedPreferences` or logs.

## WebSocket wrapper

```kotlin
fun OkHttpClient.messages(request: Request): Flow<Frame> = callbackFlow {
    val socket = newWebSocket(request, object : WebSocketListener() {
        override fun onMessage(webSocket: WebSocket, text: String) {
            trySend(Frame.Text(text))
        }
        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            webSocket.close(1000, null)
            close()
        }
        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            close(t)
        }
    })
    awaitClose { socket.close(1000, null) }
}
```

- Collected inside `repeatOnLifecycle(STARTED)`; leaving the screen cancels the collector, which runs `awaitClose` and closes the socket.
- Reconnect = `retryWhen { cause, attempt -> isOnline.first { it }; delay(jittered(attempt)); true }` with a cap; after every (re)connect the owning ViewModel **refetches** the REST state the stream patches.
- Set `pingInterval(30, SECONDS)` on the client used for sockets so a half-open connection is detected.
- Each frame is decoded like a response; a `SerializationException` on one frame is counted and the frame dropped.
- SSE: OkHttp `EventSource` (`okhttp-sse`) with the same lifecycle rules.

## Ktor lane `[KMP]`

Ktor 3.6 `HttpClient(OkHttp)` on Android, `Darwin` on iOS, in `commonMain`: `HttpTimeout` plugin (`requestTimeoutMillis`, `connectTimeoutMillis`, `socketTimeoutMillis`) gives the same three budgets; `HttpRequestRetry` with `retryOnServerErrors(2)` + `exponentialDelay()` is the retry (disable it for writes without a key); `Auth { bearer { refreshTokens { … } } }` is single-flight by construction; `ContentNegotiation { json(json) }`. Same rules, different spelling — see [`kotlin-multiplatform`](../../kotlin-multiplatform/SKILL.md).
