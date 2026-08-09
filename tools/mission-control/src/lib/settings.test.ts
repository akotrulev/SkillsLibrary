import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * These tests pin the one rule the settings layer exists to enforce:
 * **the host is the base, a configured value overrides it** — and the
 * write-only property that keeps a stored credential from coming back out.
 *
 * `config.ts` reads its paths at module load, so the data directory is pointed
 * at a temp dir before the modules under test are imported.
 */

let dataDir: string;

beforeEach(async () => {
  dataDir = await fs.mkdtemp(path.join(os.tmpdir(), "mc-settings-"));
  process.env.MISSION_CONTROL_DATA_DIR = dataDir;
  vi.resetModules();
});

afterEach(async () => {
  delete process.env.MISSION_CONTROL_DATA_DIR;
  delete process.env.MISSION_CONTROL_SECRET;
  delete process.env.ANTHROPIC_API_KEY;
  delete process.env.CLAUDE_CODE_OAUTH_TOKEN;
  await fs.rm(dataDir, { recursive: true, force: true });
});

async function load() {
  return import("./settings");
}

describe("credential storage", () => {
  it("stores a credential without a passphrase configured", async () => {
    const { setCredential, configuredCredential } = await load();

    await setCredential("anthropic", "sk-ant-secret-value");

    expect((await configuredCredential("anthropic"))?.value).toBe("sk-ant-secret-value");
  });

  it("never writes the value in plaintext", async () => {
    const { setCredential } = await load();

    await setCredential("github", "ghp_plaintext_would_be_a_bug");

    const raw = await fs.readFile(path.join(dataDir, "settings.json"), "utf8");
    expect(raw).not.toContain("ghp_plaintext_would_be_a_bug");
  });

  it("keeps only a last-four hint in the client view", async () => {
    const { setCredential, settingsView } = await load();

    await setCredential("github", "ghp_abcdefgh1234");
    const view = await settingsView();

    expect(view.github.hint).toBe("…1234");
    expect(JSON.stringify(view)).not.toContain("ghp_abcdefgh1234");
  });

  it("clears back to the host when set to null", async () => {
    const { setCredential, configuredCredential } = await load();

    await setCredential("anthropic", "sk-ant-value");
    await setCredential("anthropic", null);

    expect(await configuredCredential("anthropic")).toBeUndefined();
  });

  it("reports a stored credential it can no longer decrypt", async () => {
    process.env.MISSION_CONTROL_SECRET = "first-passphrase";
    const first = await load();
    await first.setCredential("github", "ghp_written_under_old_key");

    // Rotate the passphrase and reload: the ciphertext is now unreadable.
    process.env.MISSION_CONTROL_SECRET = "second-passphrase";
    vi.resetModules();
    const second = await load();
    const view = await second.settingsView();

    expect(view.github.undecryptable).toBe(true);
  });
});

describe("agent environment precedence", () => {
  it("overrides the host credential with the configured one", async () => {
    process.env.ANTHROPIC_API_KEY = "host-key";
    const { setCredential, agentEnvWithSettings } = await load();

    await setCredential("anthropic", "configured-key", "ANTHROPIC_API_KEY");

    expect((await agentEnvWithSettings()).ANTHROPIC_API_KEY).toBe("configured-key");
  });

  it("passes the host credential through when nothing is configured", async () => {
    process.env.ANTHROPIC_API_KEY = "host-key";
    const { agentEnvWithSettings } = await load();

    expect((await agentEnvWithSettings()).ANTHROPIC_API_KEY).toBe("host-key");
  });

  it("clears sibling variables so the host value cannot win by resolution order", async () => {
    // The SDK checks ANTHROPIC_API_KEY before the OAuth token, so a host API key
    // would silently beat a configured OAuth token if it were left in place.
    process.env.ANTHROPIC_API_KEY = "host-key";
    const { setCredential, agentEnvWithSettings } = await load();

    await setCredential("anthropic", "configured-oauth", "CLAUDE_CODE_OAUTH_TOKEN");
    const env = await agentEnvWithSettings();

    expect(env.CLAUDE_CODE_OAUTH_TOKEN).toBe("configured-oauth");
    expect(env.ANTHROPIC_API_KEY).toBeUndefined();
  });

  it("still withholds the server's git token from agents", async () => {
    process.env.MISSION_CONTROL_GIT_TOKEN = "ghp_server_only";
    const { agentEnvWithSettings } = await load();

    const env = await agentEnvWithSettings();
    expect(env.MISSION_CONTROL_GIT_TOKEN).toBeUndefined();
    delete process.env.MISSION_CONTROL_GIT_TOKEN;
  });

  it("does not put the configured git token in the agent environment", async () => {
    const { setCredential, agentEnvWithSettings } = await load();

    await setCredential("github", "ghp_configured");
    const env = await agentEnvWithSettings();

    expect(JSON.stringify(env)).not.toContain("ghp_configured");
  });
});

describe("preferences", () => {
  it("falls back to the environment defaults when unset", async () => {
    const { runtimeConfig } = await load();
    const config = await runtimeConfig();

    expect(config.plannerModel).toBeTruthy();
    expect(config.maxParallel).toBeGreaterThanOrEqual(1);
  });

  it("clamps an out-of-range parallelism rather than accepting it", async () => {
    const { setPreferences, runtimeConfig } = await load();

    await setPreferences({ maxParallel: 500 });
    expect((await runtimeConfig()).maxParallel).toBe(16);

    await setPreferences({ maxParallel: 0 });
    expect((await runtimeConfig()).maxParallel).toBe(1);
  });

  it("treats undefined as leave-alone and null as clear", async () => {
    const { setPreferences, runtimeConfig } = await load();

    await setPreferences({ plannerModel: "claude-custom" });
    await setPreferences({ maxParallel: 4 });
    expect((await runtimeConfig()).plannerModel).toBe("claude-custom");

    await setPreferences({ plannerModel: null });
    expect((await runtimeConfig()).plannerModel).not.toBe("claude-custom");
    expect((await runtimeConfig()).maxParallel).toBe(4);
  });
});
