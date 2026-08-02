import { describe, expect, it } from "vitest";
import { agentEnv } from "./agent-env";

describe("agentEnv", () => {
  it("Should_ExcludeGitCredentials_When_TheyArePresent", () => {
    const env = agentEnv({
      PATH: "/usr/bin",
      MISSION_CONTROL_GIT_TOKEN: "ghp_secret",
      GITHUB_TOKEN: "ghp_secret",
      GH_TOKEN: "ghp_secret",
      GIT_TOKEN: "ghp_secret",
    });
    expect(env.MISSION_CONTROL_GIT_TOKEN).toBeUndefined();
    expect(env.GITHUB_TOKEN).toBeUndefined();
    expect(env.GH_TOKEN).toBeUndefined();
    expect(env.GIT_TOKEN).toBeUndefined();
    expect(Object.values(env)).not.toContain("ghp_secret");
  });

  it("Should_ExcludeTheEncryptionKey_When_ItIsSet", () => {
    const env = agentEnv({ PATH: "/usr/bin", MISSION_CONTROL_SECRET: "key" });
    expect(env.MISSION_CONTROL_SECRET).toBeUndefined();
  });

  it("Should_ForwardAnthropicAuth_When_Present", () => {
    const env = agentEnv({
      ANTHROPIC_API_KEY: "sk-ant-x",
      CLAUDE_CODE_MAX_OUTPUT_TOKENS: "8192",
    });
    expect(env.ANTHROPIC_API_KEY).toBe("sk-ant-x");
    expect(env.CLAUDE_CODE_MAX_OUTPUT_TOKENS).toBe("8192");
  });

  it("Should_ForwardProcessPlumbing_When_Present", () => {
    const env = agentEnv({ PATH: "/usr/bin", HOME: "/root", LANG: "en_US.UTF-8" });
    expect(env).toMatchObject({ PATH: "/usr/bin", HOME: "/root", LANG: "en_US.UTF-8" });
  });

  it("Should_DropUnknownVariables_When_NotAllowlisted", () => {
    // An allowlist means a newly-added server secret is excluded by default.
    const env = agentEnv({ PATH: "/usr/bin", SOME_FUTURE_SECRET: "oops" });
    expect(env.SOME_FUTURE_SECRET).toBeUndefined();
  });

  it("Should_WithholdAwsCredentials_When_BedrockIsNotEnabled", () => {
    const env = agentEnv({ PATH: "/usr/bin", AWS_SECRET_ACCESS_KEY: "aws-secret" });
    expect(env.AWS_SECRET_ACCESS_KEY).toBeUndefined();
  });

  it("Should_ForwardAwsCredentials_When_BedrockIsEnabled", () => {
    const env = agentEnv({
      PATH: "/usr/bin",
      CLAUDE_CODE_USE_BEDROCK: "1",
      AWS_SECRET_ACCESS_KEY: "aws-secret",
    });
    expect(env.AWS_SECRET_ACCESS_KEY).toBe("aws-secret");
  });

  it("Should_WithholdAwsCredentials_When_BedrockFlagIsFalsy", () => {
    for (const flag of ["0", "false", "", " "]) {
      const env = agentEnv({
        CLAUDE_CODE_USE_BEDROCK: flag,
        AWS_SECRET_ACCESS_KEY: "aws-secret",
      });
      expect(env.AWS_SECRET_ACCESS_KEY, `flag=${JSON.stringify(flag)}`).toBeUndefined();
    }
  });

  it("Should_ForwardVertexCredentials_When_VertexIsEnabled", () => {
    const env = agentEnv({
      CLAUDE_CODE_USE_VERTEX: "true",
      GOOGLE_APPLICATION_CREDENTIALS: "/creds.json",
    });
    expect(env.GOOGLE_APPLICATION_CREDENTIALS).toBe("/creds.json");
  });

  it("Should_ForwardProxyAndTlsSettings_When_Present", () => {
    const env = agentEnv({
      HTTPS_PROXY: "http://proxy:8080",
      NODE_EXTRA_CA_CERTS: "/certs/ca.pem",
    });
    expect(env.HTTPS_PROXY).toBe("http://proxy:8080");
    expect(env.NODE_EXTRA_CA_CERTS).toBe("/certs/ca.pem");
  });

  it("Should_SkipUndefinedValues_When_BuildingTheEnvironment", () => {
    const env = agentEnv({ PATH: "/usr/bin", HOME: undefined });
    expect("HOME" in env).toBe(false);
  });
});
