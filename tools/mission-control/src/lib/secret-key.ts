import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { DATA_DIR } from "./config";

/**
 * The encryption key used when `MISSION_CONTROL_SECRET` is not set.
 *
 * `secrets.ts` was written for a deployment where the data directory is a
 * mounted volume and the key must live somewhere the volume is not — hence the
 * environment variable, and hence "no secret configured means credentials
 * cannot be stored at all".
 *
 * That is the right default for a hosted deployment and the wrong one for the
 * goal this file serves: Mission Control should start on any machine, let you
 * paste credentials into the UI, and work — without first teaching you an
 * environment variable. So a key file beside the data is the fallback.
 *
 * Be honest about what it does and does not buy. Encryption at rest with the
 * key stored next to the ciphertext does NOT protect against someone who can
 * read the data directory; it protects against the far more common accident —
 * `settings.json` in a backup, a screen share, a support paste, a synced
 * folder — where the file travels but `0600` file ownership does not. Anyone
 * wanting the stronger property sets `MISSION_CONTROL_SECRET` and gets exactly
 * the old behaviour, because the environment key takes precedence.
 */

const KEY_FILE = path.join(DATA_DIR, ".secret-key");

let cached: Buffer | null = null;

/**
 * Read the local key, creating it on first use.
 *
 * Deliberately synchronous: `secrets.ts` exposes a synchronous API used from
 * several call sites, and this runs once per process. `mode: 0o600` is set at
 * creation rather than chmod'ed after, so the key is never briefly readable.
 */
export function localKey(): Buffer {
  if (cached) return cached;

  try {
    const existing = fs.readFileSync(KEY_FILE);
    // A truncated or hand-edited key would decrypt nothing; regenerate instead
    // of failing every read forever.
    if (existing.length === 32) {
      cached = existing;
      return cached;
    }
  } catch {
    // Missing, unreadable, or a directory — fall through and write a fresh one.
  }

  const key = crypto.randomBytes(32);
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(KEY_FILE, key, { mode: 0o600 });
  cached = key;
  return key;
}

/** Reset the memoized key. Tests only. */
export function resetLocalKeyCache(): void {
  cached = null;
}
