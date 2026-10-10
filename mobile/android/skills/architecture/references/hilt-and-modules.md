# Hilt and modules — reference

Detail for [`mobile-android-architecture`](../SKILL.md). Hilt Gradle plugin 2.59+ requires AGP 9; AGP 8 stays on ≤ 2.58.

## Setup (KSP)

```kotlin
plugins {
    alias(libs.plugins.hilt)
    alias(libs.plugins.ksp)
}

dependencies {
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)
    implementation(libs.androidx.hilt.navigation.compose)
}
```

`@HiltAndroidApp class App : Application()`; `@AndroidEntryPoint class MainActivity : ComponentActivity()`.

## ViewModel and dispatchers

```kotlin
@HiltViewModel
class OrdersViewModel @Inject constructor(
    private val repository: OrdersRepository,
    private val savedStateHandle: SavedStateHandle,
) : ViewModel()

@Qualifier
annotation class IoDispatcher

@Module
@InstallIn(SingletonComponent::class)
object DispatchersModule {
    @Provides @IoDispatcher
    fun ioDispatcher(): CoroutineDispatcher = Dispatchers.IO
}
```

The one place `Dispatchers.IO` is written. Tests replace the module with `@TestInstallIn` or build the ViewModel by hand with a `StandardTestDispatcher`. Hilt tests that boot a graph are `qa-mobile-android`'s lane; the ViewModel itself is unit-tested with constructor arguments and no Hilt.

## Navigation 3 and Hilt

With Navigation 3 add `rememberViewModelStoreNavEntryDecorator()` to `NavDisplay`, and call `hiltViewModel()` inside the `entry<Key> { }` content — the ViewModel is then scoped to that back stack entry and cleared when the key is popped. Navigation Compose: `hiltViewModel()` in the `composable<Route>` body.

## Manual DI container

```kotlin
class AppContainer(context: Context) {
    private val client = ordersClient(BuildConfigValues.apiBaseUrl)
    val orders = OrdersRepository(client, Dispatchers.IO)
}

class App : Application() {
    val container by lazy { AppContainer(this) }
}
```

`Dispatchers.IO` is named once, in the container. A `ViewModelProvider.Factory` built with `viewModelFactory { initializer { … } }` reads it. The container is the only object with a lifetime longer than a screen.

## Module boundaries

| Module | Holds | May depend on |
|---|---|---|
| `:app` | `Application`, `MainActivity`, `NavDisplay`, DI root | features, core |
| `:feature:<name>` | Screens, ViewModels, the feature's navigation keys | core |
| `:core:data` | Repositories, data sources, models shared by two features | — |
| `:core:ui` | Theme, shared composables (second consumer only) | — |

A feature exposes its keys and one entry function (`fun EntryProviderScope<NavKey>.ordersEntries(...)`); everything else is `internal`. Cross-feature navigation goes through keys the caller imports from a small `:feature:<name>:api` module only when the direct dependency would create a cycle.
