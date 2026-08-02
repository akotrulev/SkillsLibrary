/**
 * The environment handed to agent subprocesses.
 *
 * The SDK's `env` option REPLACES the subprocess environment rather than
 * merging with it, which is what makes containment possible: implementer agents
 * have `Bash`, so anything left in their environment is readable by the agent
 * and can end up echoed into a task log. Git credentials must never be there —
 * they are injected per git command by `git.ts` and belong to the server only.
 *
 * An allowlist rather than a denylist: a new secret added to the server's
 * environment must not become agent-visible by default.
 */

/** Any environment-shaped map; `process.env` satisfies it. */
export type EnvLike = Record<string, string | undefined>;

/** Process plumbing an agent legitimately needs. */
const ALLOWED_NAMES = [
  "PATH",
  "HOME",
  "SHELL",
  "USER",
  "LOGNAME",
  "TERM",
  "TMPDIR",
  "TZ",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  // TLS trust and corporate proxies, or every outbound call fails.
  "NODE_EXTRA_CA_CERTS",
  "SSL_CERT_FILE",
  "SSL_CERT_DIR",
  "HTTP_PROXY",
  "HTTPS_PROXY",
  "NO_PROXY",
  "http_proxy",
  "https_proxy",
  "no_proxy",
];

/** Anthropic auth and Claude Code configuration. */
const ALLOWED_PREFIXES = ["ANTHROPIC_", "CLAUDE_"];

/**
 * Cloud credentials are forwarded only when the SDK is actually configured to
 * authenticate through that cloud — otherwise an unrelated AWS key in the
 * server environment would become agent-readable for no reason.
 */
const CONDITIONAL_PREFIXES: { when: string; prefixes: string[] }[] = [
  { when: "CLAUDE_CODE_USE_BEDROCK", prefixes: ["AWS_"] },
  { when: "CLAUDE_CODE_USE_VERTEX", prefixes: ["GOOGLE_", "GCLOUD_", "CLOUDSDK_"] },
];

/**
 * Never forwarded, even if some future rule above would match them. Belt and
 * braces around the credentials this app itself holds.
 */
const DENIED_NAMES = new Set([
  "MISSION_CONTROL_GIT_TOKEN",
  "MISSION_CONTROL_SECRET",
  "GITHUB_TOKEN",
  "GH_TOKEN",
  "GIT_TOKEN",
  "GIT_ASKPASS",
  "GIT_CONFIG_PARAMETERS",
]);

function isTruthy(value: string | undefined): boolean {
  if (!value) return false;
  const v = value.trim().toLowerCase();
  return v !== "" && v !== "0" && v !== "false";
}

/**
 * Build the environment for an agent subprocess from `source`
 * (defaults to the server's own environment).
 */
export function agentEnv(
  source: EnvLike = process.env,
): Record<string, string> {
  const prefixes = [...ALLOWED_PREFIXES];
  for (const rule of CONDITIONAL_PREFIXES) {
    if (isTruthy(source[rule.when])) prefixes.push(...rule.prefixes);
  }

  const env: Record<string, string> = {};
  for (const [name, value] of Object.entries(source)) {
    if (value === undefined) continue;
    if (DENIED_NAMES.has(name)) continue;

    const allowed =
      ALLOWED_NAMES.includes(name) || prefixes.some((p) => name.startsWith(p));
    if (allowed) env[name] = value;
  }

  return env;
}
