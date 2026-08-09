import fs from "node:fs/promises";
import path from "node:path";
import { agentEnv } from "./agent-env";
import {
  DEFAULT_MAX_PARALLEL,
  DATA_DIR,
  IMPLEMENTER_MODEL,
  PLANNER_MODEL,
} from "./config";
import { detectHostConfig, type HostConfig } from "./host-config";
import {
  decryptSecret,
  encryptSecret,
  secretsEnabled,
  secretStorageAvailable,
  tokenHint,
  type SecretRecord,
} from "./secrets";

/**
 * Instance-wide configuration, editable from the UI.
 *
 * The point of this module is that Mission Control can be dropped on any
 * machine — a laptop, a VM, a homelab box — and made to work from the browser,
 * without the operator being expected to know which environment variable the
 * Agent SDK reads.
 *
 * **The precedence rule is one line and everything else follows from it:**
 * what the host already provides is the base, and an explicitly configured
 * value overrides it. Never the reverse. That ordering is what makes the same
 * build behave sensibly in both deployments — on a developer laptop the host
 * already has a Claude login and a `gh` credential helper, so the settings page
 * stays empty and nothing needs saying; on a bare VM nothing is detected, so
 * every value comes from here.
 *
 * Credentials are stored encrypted (`secrets.ts`) and are **write-only across
 * the API**: they go in through PUT and no route ever returns one. Clients get
 * a `CredentialState` — where the value comes from, a last-four hint, and
 * whether it is usable.
 */

export type CredentialKind = "anthropic" | "github";

interface StoredCredential {
  cipher: SecretRecord;
  hint: string;
  /**
   * Which environment variable this value should become for the child process.
   * Stored rather than inferred so an API key and an OAuth token can both live
   * in the `anthropic` slot without a second field to keep in sync.
   */
  envName: string;
  updatedAt: string;
}

interface StoredSettings {
  schemaVersion: 1;
  credentials: Partial<Record<CredentialKind, StoredCredential>>;
  /** Empty string is not a value — an unset model means "use the default". */
  plannerModel?: string;
  implementerModel?: string;
  maxParallel?: number;
  /** For an Anthropic-compatible gateway or proxy. */
  anthropicBaseUrl?: string;
  updatedAt: string;
}

/** The environment variable each credential becomes, and what may be chosen. */
export const ANTHROPIC_ENV_NAMES = [
  "ANTHROPIC_API_KEY",
  "CLAUDE_CODE_OAUTH_TOKEN",
  "ANTHROPIC_AUTH_TOKEN",
] as const;

export type AnthropicEnvName = (typeof ANTHROPIC_ENV_NAMES)[number];

const FILE = path.join(DATA_DIR, "settings.json");

const EMPTY: StoredSettings = {
  schemaVersion: 1,
  credentials: {},
  updatedAt: new Date(0).toISOString(),
};

let cache: StoredSettings | null = null;
let chain: Promise<unknown> = Promise.resolve();

/** Serialise writes so two saves cannot lose each other. */
function serialise<T>(fn: () => Promise<T>): Promise<T> {
  const next = chain.then(fn, fn);
  chain = next.catch(() => undefined);
  return next;
}

async function read(): Promise<StoredSettings> {
  if (cache) return cache;
  try {
    const parsed = JSON.parse(await fs.readFile(FILE, "utf8")) as StoredSettings;
    // A settings file from a future version is not worth guessing at, and
    // falling back to defaults is safe here: nothing is lost, the operator is
    // simply asked again.
    cache = parsed.schemaVersion === 1 ? { ...EMPTY, ...parsed } : EMPTY;
  } catch {
    cache = EMPTY;
  }
  return cache;
}

async function write(next: StoredSettings): Promise<void> {
  await fs.mkdir(DATA_DIR, { recursive: true });
  // 0600: the file holds ciphertext, but the hints and model choices are still
  // nobody else's business on a shared machine.
  await fs.writeFile(FILE, JSON.stringify(next, null, 2), { encoding: "utf8", mode: 0o600 });
  cache = next;
}

/** Drop the in-memory copy. Tests, and any future out-of-process editing. */
export function invalidateSettingsCache(): void {
  cache = null;
}

// ---------------------------------------------------------------------------
// Reading — resolved values, server-side only
// ---------------------------------------------------------------------------

/**
 * The configured credential for `kind`, or undefined.
 *
 * Returns null-ish rather than throwing when the stored value cannot be
 * decrypted (a rotated `MISSION_CONTROL_SECRET`, a replaced key file): the
 * caller falls back to the host, and the UI is told to ask for it again.
 */
export async function configuredCredential(
  kind: CredentialKind,
): Promise<{ value: string; envName: string } | undefined> {
  const stored = (await read()).credentials[kind];
  if (!stored) return undefined;
  const value = decryptSecret(stored.cipher);
  return value ? { value, envName: stored.envName } : undefined;
}

/**
 * The environment for an agent subprocess: the allowlisted host environment
 * with configured credentials layered on top.
 *
 * The overlay is applied *after* `agentEnv()` precisely because it must win —
 * that is the precedence rule. Note the consequence, which is inherent and not
 * introduced here: the agent runs with the credential that pays for it, so an
 * agent with `Bash` can read it. The boundary that matters is who can reach
 * Mission Control at all, not this environment.
 */
export async function agentEnvWithSettings(): Promise<Record<string, string>> {
  const env = agentEnv();
  const settings = await read();

  const anthropic = await configuredCredential("anthropic");
  if (anthropic) {
    // Clear the sibling variables so a leftover host value cannot win by being
    // earlier in the SDK's own resolution order.
    for (const name of ANTHROPIC_ENV_NAMES) delete env[name];
    env[anthropic.envName] = anthropic.value;
  }

  if (settings.anthropicBaseUrl) env.ANTHROPIC_BASE_URL = settings.anthropicBaseUrl;

  return env;
}

/** The git credential configured here, if any. Server-side only. */
export async function configuredGitToken(): Promise<string | undefined> {
  return (await configuredCredential("github"))?.value;
}

/** Model and concurrency choices, with the env-var defaults underneath. */
export async function runtimeConfig(): Promise<{
  plannerModel: string;
  implementerModel: string;
  maxParallel: number;
}> {
  const settings = await read();
  return {
    plannerModel: settings.plannerModel?.trim() || PLANNER_MODEL,
    implementerModel: settings.implementerModel?.trim() || IMPLEMENTER_MODEL,
    maxParallel: settings.maxParallel ?? DEFAULT_MAX_PARALLEL,
  };
}

// ---------------------------------------------------------------------------
// Writing
// ---------------------------------------------------------------------------

export async function setCredential(
  kind: CredentialKind,
  value: string | null,
  envName?: string,
): Promise<void> {
  await serialise(async () => {
    const current = await read();
    const credentials = { ...current.credentials };

    if (value === null) {
      delete credentials[kind];
    } else {
      const trimmed = value.trim();
      if (!trimmed) throw new Error("The value is empty.");
      credentials[kind] = {
        cipher: encryptSecret(trimmed),
        hint: tokenHint(trimmed),
        envName:
          kind === "anthropic"
            ? ((envName as AnthropicEnvName) ?? "ANTHROPIC_API_KEY")
            : "MISSION_CONTROL_GIT_TOKEN",
        updatedAt: new Date().toISOString(),
      };
    }

    await write({ ...current, credentials, updatedAt: new Date().toISOString() });
  });
}

export async function setPreferences(input: {
  plannerModel?: string | null;
  implementerModel?: string | null;
  maxParallel?: number | null;
  anthropicBaseUrl?: string | null;
}): Promise<void> {
  await serialise(async () => {
    const current = await read();
    const next: StoredSettings = { ...current, updatedAt: new Date().toISOString() };

    // null clears, undefined leaves alone — so a partial PUT is really partial.
    if (input.plannerModel !== undefined)
      next.plannerModel = input.plannerModel?.trim() || undefined;
    if (input.implementerModel !== undefined)
      next.implementerModel = input.implementerModel?.trim() || undefined;
    if (input.anthropicBaseUrl !== undefined)
      next.anthropicBaseUrl = input.anthropicBaseUrl?.trim() || undefined;
    if (input.maxParallel !== undefined)
      next.maxParallel =
        input.maxParallel === null ? undefined : clampParallel(input.maxParallel);

    await write(next);
  });
}

/** One agent per task is the floor; the ceiling stops a typo saturating the box. */
function clampParallel(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_MAX_PARALLEL;
  return Math.min(16, Math.max(1, Math.floor(value)));
}

// ---------------------------------------------------------------------------
// The client-safe view
// ---------------------------------------------------------------------------

export interface CredentialState {
  /** Where the value that will actually be used comes from. */
  source: "configured" | "host" | "none";
  /** Last-four label for a configured value; never the value. */
  hint?: string;
  /** Which environment variable a configured value becomes. */
  envName?: string;
  /** True when something is stored but the key can no longer decrypt it. */
  undecryptable: boolean;
  /** What the host offers underneath, shown even when overridden. */
  host: HostConfig["anthropic"];
}

export interface SettingsView {
  anthropic: CredentialState;
  github: CredentialState;
  gitIdentity: HostConfig["gitIdentity"];
  plannerModel: string;
  implementerModel: string;
  maxParallel: number;
  anthropicBaseUrl?: string;
  /** True when the key comes from the environment rather than the data dir. */
  strongKeyStorage: boolean;
  storageAvailable: boolean;
  host: { platform: string; homeDir: string; detectedAt: string };
}

async function credentialState(
  kind: CredentialKind,
  host: HostConfig["anthropic"],
): Promise<CredentialState> {
  const stored = (await read()).credentials[kind];
  if (!stored) {
    return {
      source: host.status === "absent" ? "none" : "host",
      undecryptable: false,
      host,
    };
  }

  const usable = decryptSecret(stored.cipher) !== null;
  return {
    source: usable ? "configured" : host.status === "absent" ? "none" : "host",
    hint: stored.hint,
    envName: stored.envName,
    undecryptable: !usable,
    host,
  };
}

/** Everything the settings UI needs, and nothing it must not have. */
export async function settingsView(): Promise<SettingsView> {
  const [host, config] = await Promise.all([detectHostConfig(), runtimeConfig()]);
  const [anthropic, github] = await Promise.all([
    credentialState("anthropic", host.anthropic),
    credentialState("github", host.github),
  ]);
  const stored = await read();

  return {
    anthropic,
    github,
    gitIdentity: host.gitIdentity,
    plannerModel: config.plannerModel,
    implementerModel: config.implementerModel,
    maxParallel: config.maxParallel,
    anthropicBaseUrl: stored.anthropicBaseUrl,
    strongKeyStorage: secretsEnabled(),
    storageAvailable: secretStorageAvailable(),
    host: { platform: host.platform, homeDir: host.homeDir, detectedAt: host.detectedAt },
  };
}
