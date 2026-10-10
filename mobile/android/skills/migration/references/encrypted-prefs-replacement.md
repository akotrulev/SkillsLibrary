# `EncryptedSharedPreferences` → DataStore + Tink / Keystore

`androidx.security:security-crypto` (`EncryptedSharedPreferences`, `EncryptedFile`, `MasterKey`) is **deprecated**. Existing use is flagged and migrated; new code never writes it. Target design: [`keystore-and-secrets`](../../offline-and-storage/references/keystore-and-secrets.md) — an **Android Keystore key**, or a **Tink `Aead` with a Keystore-wrapped keyset**, over **DataStore** for non-secret values. Rules: [`mobile-shared-security`](../../../../_shared/security/references/android.md).

## Procedure — read old, write new, delete old

1. Add the new store beside the old (DataStore file + a `SecretStore` over Tink `Aead`); do not remove `security-crypto` yet.
2. **Migrate per key, once, on first read after the upgrade:** read the old value from `EncryptedSharedPreferences`; if present, write it to the new store; confirm the write by reading it back; then `remove(key)` from the old store. All inside one `suspend` function on an injected IO dispatcher.
3. Non-secret values (flags, last-seen ids) go to plain DataStore with `SharedPreferencesMigration`; **secrets** (refresh tokens, API keys the user entered) go to the encrypted store.
4. **Never wipe on failure.** If the old store cannot be decrypted (Keystore key invalidated after a restore, a corrupted file), the safe outcome is *"user signs in again"* — handled as a normal unauthenticated state — never a crash and never a silent empty token that the server then rejects in a loop.
5. Keep the old read path for **at least one release** that users commonly skip across, then delete it with `security-crypto` in a later commit.
6. Backup: confirm the new files are excluded or included deliberately in `data_extraction_rules.xml` / `backup_rules.xml` — an encrypted file restored to another device cannot be decrypted there.

## Traps

- A Keystore key is **not** exportable; do not attempt to carry key material to the new scheme — carry the plaintext through memory only, for the one migration step, and never log it.
- A new Keystore key needs the right authentication requirements (`setUserAuthenticationRequired` only when the product wants a prompt); changing them later invalidates the key.
- Tink keysets need a stable `Aead` primitive and a Keystore master key URI; a second keyset per run is the usual bug.
- Do not convert an `EncryptedFile` of large data to DataStore — it is for small values; large blobs stay in files with an `Aead` stream.

## Verify

- `rg -n "EncryptedSharedPreferences|MasterKey|security-crypto|EncryptedFile" -g '*.kt' -g '*.kts' -g 'libs.versions.toml'` finds only the migration's temporary read path, with a dated removal.
- An upgrade install from the previous production build keeps the user signed in; a device with the key wiped shows the sign-in screen, not a crash.
