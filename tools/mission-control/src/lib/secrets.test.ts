import { describe, expect, it } from "vitest";
import {
  decryptSecret,
  encryptSecret,
  secretsEnabled,
  tokenHint,
  type SecretRecord,
} from "./secrets";

const KEY = { MISSION_CONTROL_SECRET: "correct horse battery staple" };
const OTHER_KEY = { MISSION_CONTROL_SECRET: "a different passphrase" };
const TOKEN = "github_pat_11ABCDEFG0abcdefghijklmnop";

describe("secretsEnabled", () => {
  it("Should_BeFalse_When_SecretIsAbsentOrBlank", () => {
    expect(secretsEnabled({})).toBe(false);
    expect(secretsEnabled({ MISSION_CONTROL_SECRET: "   " })).toBe(false);
  });

  it("Should_BeTrue_When_SecretIsSet", () => {
    expect(secretsEnabled(KEY)).toBe(true);
  });
});

describe("encryptSecret / decryptSecret", () => {
  it("Should_RoundTripTheToken_When_KeyIsUnchanged", () => {
    expect(decryptSecret(encryptSecret(TOKEN, KEY), KEY)).toBe(TOKEN);
  });

  it("Should_NotStoreThePlaintext_When_Encrypting", () => {
    const record = encryptSecret(TOKEN, KEY);
    expect(JSON.stringify(record)).not.toContain(TOKEN);
    expect(JSON.stringify(record)).not.toContain("github_pat");
  });

  it("Should_UseAFreshNonce_When_EncryptingTheSameValueTwice", () => {
    const a = encryptSecret(TOKEN, KEY);
    const b = encryptSecret(TOKEN, KEY);
    expect(a.iv).not.toBe(b.iv);
    expect(a.ciphertext).not.toBe(b.ciphertext);
  });

  it("Should_FailClosed_When_KeyHasRotated", () => {
    expect(decryptSecret(encryptSecret(TOKEN, KEY), OTHER_KEY)).toBeNull();
  });

  it("Should_FailClosed_When_CiphertextIsTampered", () => {
    const record = encryptSecret(TOKEN, KEY);
    const tampered: SecretRecord = {
      ...record,
      ciphertext: Buffer.from("not the original", "utf8").toString("base64"),
    };
    expect(decryptSecret(tampered, KEY)).toBeNull();
  });

  it("Should_FailClosed_When_AuthTagIsTampered", () => {
    const record = encryptSecret(TOKEN, KEY);
    const tampered: SecretRecord = {
      ...record,
      tag: Buffer.alloc(16).toString("base64"),
    };
    expect(decryptSecret(tampered, KEY)).toBeNull();
  });

  it("Should_ReturnNull_When_NoKeyIsConfigured", () => {
    // Must not throw: the project list renders even with the key missing.
    expect(decryptSecret(encryptSecret(TOKEN, KEY), {})).toBeNull();
  });

  it("Should_Throw_When_EncryptingWithoutAKey", () => {
    expect(() => encryptSecret(TOKEN, {})).toThrow(/MISSION_CONTROL_SECRET/);
  });
});

describe("tokenHint", () => {
  it("Should_RevealOnlyTheLastFour_When_TokenIsLongEnough", () => {
    expect(tokenHint("github_pat_1234abcd")).toBe("…abcd");
  });

  it("Should_RevealNothing_When_TokenIsShort", () => {
    expect(tokenHint("abc")).toBe("…");
  });
});
