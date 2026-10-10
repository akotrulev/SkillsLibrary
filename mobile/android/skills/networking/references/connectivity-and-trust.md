# Connectivity and Network Security Config

## Foreground and reconnect

The app revalidates when it returns to the foreground and when the network returns — `error-handling` shows it, networking triggers it:

```kotlin
@Singleton
class Connectivity @Inject constructor(@ApplicationContext context: Context) {
    private val manager = context.getSystemService<ConnectivityManager>()

    val isOnline: Flow<Boolean> = callbackFlow {
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) {
                trySend(capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED))
            }
            override fun onLost(network: Network) {
                trySend(false)
            }
        }
        manager.registerDefaultNetworkCallback(callback)
        awaitClose { manager.unregisterNetworkCallback(callback) }
    }.distinctUntilChanged()
}
```

A screen revalidates with `LifecycleResumeEffect` / `repeatOnLifecycle(Lifecycle.State.STARTED)` and when `isOnline` flips to `true`; both call the same load. Pull-to-refresh (`PullToRefreshBox`) is the canonical manual refetch — a failed pull keeps the list and marks it stale. Needs `ACCESS_NETWORK_STATE` only.

## Network Security Config

`android:networkSecurityConfig` is the single place cleartext and trust are decided ([`mobile-shared-security`](../../../../_shared/security/references/android.md) § 2): `cleartextTrafficPermitted="false"` in `<base-config>`, one `<domain-config>` per exception with an owner, user CAs only in `<debug-overrides>`, a `<pin-set expiration>` carrying a **backup pin**. A `localhost` / `10.0.2.2` cleartext exception lives in the **debug** source set's manifest or config only. At API 37, reaching a LAN device needs the `ACCESS_LOCAL_NETWORK` runtime permission ([`device-features`](../../device-features/SKILL.md)). Never a trust-all `X509TrustManager` or `HostnameVerifier { _, _ -> true }`.
