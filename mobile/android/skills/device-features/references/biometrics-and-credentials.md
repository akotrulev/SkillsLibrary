# Biometrics, Credential Manager and local network

## Biometrics — `BiometricPrompt` with a `CryptoObject`

```kotlin
suspend fun FragmentActivity.authenticate(cipher: Cipher, title: String, cancel: String): Cipher? =
    suspendCancellableCoroutine { continuation ->
        val prompt = BiometricPrompt(
            this,
            ContextCompat.getMainExecutor(this),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    continuation.resume(result.cryptoObject?.cipher)
                }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    continuation.resume(null)
                }
            },
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setNegativeButtonText(cancel)
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .build()
        prompt.authenticate(info, BiometricPrompt.CryptoObject(cipher))
        continuation.invokeOnCancellation { prompt.cancelAuthentication() }
    }
```

- **The authentication unlocks a Keystore key** (`setUserAuthenticationRequired(true)`, `setInvalidatedByBiometricEnrollment(true)`) used through the `CryptoObject` — **a callback that just sets `isUnlocked = true` is bypassable** and a security finding ([`mobile-shared-security`](../../../../_shared/security/references/android.md) § 9). Key creation is [`offline-and-storage`](../../offline-and-storage/SKILL.md).
- `BIOMETRIC_STRONG` for sensitive actions; `BIOMETRIC_STRONG or DEVICE_CREDENTIAL` for convenience unlock (and then no `setNegativeButtonText`). Check `BiometricManager.canAuthenticate(…)` first and map `BIOMETRIC_ERROR_NONE_ENROLLED`, `NO_HARDWARE`, `HW_UNAVAILABLE` to **working screens** (enrol prompt, password fallback), not crashes.
- A `KeyPermanentlyInvalidatedException` (enrolment changed) is "re-authenticate with the password and recreate the key" — never a crash or a silent downgrade.
- Biometric **re-auth is the common third rung** of the session ladder (`mobile-android-error-handling`).
- No biometric template or result is stored or logged.

## Credential Manager and passkeys

- One API for sign-in: `CredentialManager.create(context).getCredential(activityContext, GetCredentialRequest(listOf(GetPasswordOption(), GetPublicKeyCredentialOption(requestJson))))`; the result is a `PasswordCredential`, a `PublicKeyCredential` (passkey) or a federated credential. Sign-up saves with `CreatePasswordRequest` / `CreatePublicKeyCredentialRequest`.
- The **challenge and the relying-party id come from the server**; the passkey JSON is passed through unmodified and the response is sent to the server for verification. The app never verifies it.
- Handle `NoCredentialException` (show the normal sign-in form), `GetCredentialCancellationException` (silent — the user cancelled) and `CreateCredentialCancellationException`. These are typed outcomes, not error banners.
- Passkeys on the website need the Digital Asset Links association (`assetlinks.json`, `delegate_permission/common.get_login_creds`) — the same file as App Links, served from the relying-party domain.
- Credential Manager needs an **Activity context** and runs in a coroutine owned by the screen (`viewModelScope` through the caller's launch) — `GlobalScope` is out. One Tap, Google Sign-In and the FIDO2 API are legacy: flag, migrate under `mobile-android-migration`, do not add.
- Form-side autofill and `ContentType` are [`forms`](../../forms/SKILL.md).

## Local network at API 37

Reaching a device on the LAN (a printer, a smart speaker, `NsdManager` discovery, a socket to `192.168.x.x`) needs the `ACCESS_LOCAL_NETWORK` runtime permission when targeting 37. Request it **in context** with the recipe above, say in the pre-prompt which device the app is looking for, and give the denied screen a manual-address alternative. Add it only if the feature exists; the Play policy row is in [`mobile-shared-store-compliance`](../../../../_shared/store-compliance/references/google-play.md) § 5. At targets below 37 nothing changes — **do not raise the target for it** (never up-level as a side effect).
