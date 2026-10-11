# Secrets, backup and storage failures

## Secrets — Keystore and Tink

`androidx.security:security-crypto` is **deprecated** (all APIs, since 1.1.0-beta01; Google points to platform APIs and the Keystore). **Never write `EncryptedSharedPreferences`, `EncryptedFile` or `MasterKey` in new code.**

```kotlin
class SecretStore @Inject constructor(
    @ApplicationContext private val context: Context,
    private val store: DataStore<Preferences>,
) {
    private val aead: Aead by lazy {
        AndroidKeysetManager.Builder()
            .withSharedPref(context, "secret_keyset", "secret_keyset_prefs")
            .withKeyTemplate(KeyTemplates.get("AES256_GCM"))
            .withMasterKeyUri("android-keystore://secret_master_key")
            .build()
            .keysetHandle
            .getPrimitive(RegistryConfiguration.get(), Aead::class.java)
    }

    suspend fun put(name: String, value: String) {
        val sealed = aead.encrypt(value.toByteArray(), name.toByteArray())
        store.edit { it[stringPreferencesKey(name)] = Base64.encodeToString(sealed, Base64.NO_WRAP) }
    }

    suspend fun get(name: String): String? {
        val sealed = store.data.first()[stringPreferencesKey(name)] ?: return null
        return runCatching { aead.decrypt(Base64.decode(sealed, Base64.NO_WRAP), name.toByteArray()).decodeToString() }
            .getOrNull()
    }
}
```

- The **associated data** (the key name) binds each ciphertext to its slot. The keyset is wrapped by a Keystore key (`android-keystore://…`), so the raw keyset never rests in plain text.
- A decrypt failure (key invalidated, restored on another device) returns `null` and the caller treats the user as **signed out** — it never crashes and never loops. Treat an `AEADBadTagException` or `KeyPermanentlyInvalidatedException` as "secret gone".
- Direct Keystore alternative for a single key: `KeyGenParameterSpec` with `AES/GCM/NoPadding`, `setUserAuthenticationRequired(true)` and `setInvalidatedByBiometricEnrollment(true)` for a biometric-gated key, `setIsStrongBoxBacked(true)` where available with a deliberate fallback. Biometric binding with a `CryptoObject` is [`device-features`](../../device-features/SKILL.md).
- Room columns holding secrets are encrypted with the same `Aead` before they reach the DAO, or the whole database uses an encrypted driver with a Keystore-wrapped passphrase — never a hardcoded passphrase.
- Tokens: **access token in memory (and the Keystore-backed store for restart), refresh token only in the Keystore-backed store.** Logout deletes the store, the keyset, the database rows and WebView data.

**Brownfield `EncryptedSharedPreferences`:** flagged (audit row I-series), not rewritten here. The migration reads old, writes new, deletes old, in one release — `mobile-android:migration`.

## Backup and device transfer

`allowBackup` defaults to true. Declare `android:dataExtractionRules` (Android 12+) **and** `android:fullBackupContent` (11 and below): exclude the database, DataStore files, the keyset prefs and anything token-shaped, or set `allowBackup="false"` when the app has no restore need. **Keystore keys never restore to another device**, so an encrypted blob restored without its key is dead — exclude both. Rules and the audit are [`mobile-<stack>:security`](../../../../_shared/security/references/android.md) § 3.

## Storage failures degrade to memory

Full disks, corrupt files and a read-only volume are common. Writes to Room, DataStore or files are wrapped in the **repository**, not the screen: on `SQLiteFullException`, `IOException` or a failed migration the repository keeps the working set **in memory** for the session, reports a `StorageDegraded` state to `uiState`, and raises the banner — the app does not crash and does not silently drop the user's edit. A database that fails to open is **deleted and rebuilt only if it is a cache**; a user-data database is kept, the failure reported, and support given the `traceId` — never auto-wiped. `error-handling` owns the banner and the copy.
