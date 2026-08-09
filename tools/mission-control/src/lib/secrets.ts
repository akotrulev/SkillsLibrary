import crypto from "node:crypto";
import type { EnvLike } from "./agent-env";
import { localKey } from "./secret-key";

/**
 * Symmetric encryption for credentials kept in `.data/projects.json`.
 *
 * That file sits on a docker volume, so a token must not be readable there.
 * AES-256-GCM gives confidentiality plus tamper detection: a truncated or
 * edited record fails to decrypt rather than yielding garbage.
 *
 * The key is derived from `MISSION_CONTROL_SECRET` when it is set, which keeps
 * it off the volume entirely. When it is not set the key comes from
 * `secret-key.ts` — generated once, `0600`, beside the data. Credentials are
 * never silently downgraded to plaintext storage in either mode; the weaker
 * mode is weaker about *where the key lives*, not about whether one is used.
 */

export interface SecretRecord {
  /** Base64 AES-256-GCM ciphertext. */
  ciphertext: string;
  /** Base64 96-bit nonce, fresh per encryption. */
  iv: string;
  /** Base64 128-bit auth tag. */
  tag: string;
}

const ALGORITHM = "aes-256-gcm";
const IV_BYTES = 12;

/**
 * Whether an explicit passphrase is configured in the environment.
 *
 * This is the *stronger* mode — the key lives somewhere the data directory is
 * not. It is no longer the only mode; see `secretStorageAvailable`.
 */
export function secretsEnabled(env: EnvLike = process.env): boolean {
  return Boolean(env.MISSION_CONTROL_SECRET?.trim());
}

/**
 * Whether credentials can be stored at all. Always true now: without a
 * passphrase, `secret-key.ts` generates one beside the data. Kept as a function
 * rather than inlined `true` because the answer becomes interesting again the
 * moment the data directory is read-only.
 */
export function secretStorageAvailable(env: EnvLike = process.env): boolean {
  if (secretsEnabled(env)) return true;
  try {
    localKey();
    return true;
  } catch {
    return false;
  }
}

function deriveKey(env: EnvLike = process.env): Buffer {
  const secret = env.MISSION_CONTROL_SECRET?.trim();
  // The secret is a passphrase of arbitrary length; the cipher needs 32 bytes.
  if (secret) return crypto.createHash("sha256").update(secret, "utf8").digest();
  return localKey();
}

export function encryptSecret(
  plaintext: string,
  env: EnvLike = process.env,
): SecretRecord {
  const iv = crypto.randomBytes(IV_BYTES);
  const cipher = crypto.createCipheriv(ALGORITHM, deriveKey(env), iv);
  const ciphertext = Buffer.concat([
    cipher.update(plaintext, "utf8"),
    cipher.final(),
  ]);
  return {
    ciphertext: ciphertext.toString("base64"),
    iv: iv.toString("base64"),
    tag: cipher.getAuthTag().toString("base64"),
  };
}

/**
 * Decrypt a stored record. Returns null when the record cannot be recovered —
 * a rotated or lost `MISSION_CONTROL_SECRET`, or a tampered record. Callers
 * treat null as "no token, ask the user to re-enter it"; it must never throw,
 * because that would take the whole project list down with it.
 */
export function decryptSecret(
  record: SecretRecord,
  env: EnvLike = process.env,
): string | null {
  try {
    const decipher = crypto.createDecipheriv(
      ALGORITHM,
      deriveKey(env),
      Buffer.from(record.iv, "base64"),
    );
    decipher.setAuthTag(Buffer.from(record.tag, "base64"));
    return Buffer.concat([
      decipher.update(Buffer.from(record.ciphertext, "base64")),
      decipher.final(),
    ]).toString("utf8");
  } catch {
    return null;
  }
}

/**
 * A non-reversible label for a token, enough to tell two apart in the UI.
 * Short tokens are masked entirely rather than revealing most of themselves.
 */
export function tokenHint(token: string): string {
  const trimmed = token.trim();
  return trimmed.length >= 8 ? `…${trimmed.slice(-4)}` : "…";
}
