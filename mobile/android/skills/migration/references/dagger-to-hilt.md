# Dagger → Hilt

Hilt is the DI of a **complex Android app** ([`architecture`](../../architecture/SKILL.md)). Move to it when manual or Dagger wiring across features hurts — not by default. **Hilt is Android-only; a shared KMP module uses Koin or Metro** ([`kotlin-multiplatform`](../../kotlin-multiplatform/SKILL.md)).

## Version lane

Hilt Gradle plugin **2.59+ requires AGP 9**; Hilt ≤ 2.58 on AGP 8. Both use **KSP** (`ksp(libs.hilt.compiler)`), never kapt. Do not combine the Hilt move with the AGP move — AGP first.

## Order

1. Add the Hilt plugin and dependencies; annotate the `Application` with `@HiltAndroidApp`. The existing Dagger components keep working beside Hilt's.
2. **Bridge** with an `@EntryPoint` (`@InstallIn(SingletonComponent::class)`) that exposes the existing Dagger component's bindings to Hilt-managed classes, or the reverse, for the duration of the move.
3. Convert component by component, leaves first: `@Component` / `@Subcomponent` → Hilt's generated component; a custom scope → the matching Hilt scope (`@Singleton`, `@ActivityRetainedScoped`, `@ViewModelScoped`).
4. `@Module` classes get `@InstallIn(SingletonComponent::class)` (or the narrower component); `@Provides` and `@Binds` bodies are unchanged.
5. ViewModels: `@HiltViewModel` + `@Inject constructor`; Compose `hiltViewModel()`; Navigation 3 entries use `rememberViewModelStoreNavEntryDecorator()` ([`navigation`](../../navigation/SKILL.md)).
6. Entry points on `Activity` / `Fragment`: `@AndroidEntryPoint`, constructor-less injection removed in favour of fields only where the framework requires them (Activities, Fragments, Services).
7. Delete the old components and the `DaggerAppComponent` call from `Application.onCreate`.

## Traps

- **Qualifiers for dispatchers** (`@IoDispatcher`) move as annotations; the dispatcher is injected, never `Dispatchers.IO` literal.
- Hilt generates the components; a hand-written `Dagger*Component.builder()` left in the tree is a half migration.
- `@Singleton` on everything is the common regression — only process-wide state is singleton.
- Instrumented tests move to `HiltAndroidRule` + `@HiltAndroidTest` + a test application runner; a Robolectric test needs `@HiltAndroidTest` and `HiltTestApplication`.
- A KSP processor mismatch (Hilt on KSP, another library still on kapt) leaves two annotation passes — migrate the others to KSP in [`agp8-to-9`](agp8-to-9.md), not here.

## Verify

- `rg -n "kapt\(|DaggerAppComponent|@Component\b" -g '*.kt' -g '*.kts' -g '*.java'` is empty after the last step.
- The app builds, a Hilt-injected ViewModel survives rotation, and instrumented tests pass with the Hilt runner.
