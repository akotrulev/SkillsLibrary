/**
 * Plain JS on purpose.
 *
 * A `next.config.ts` has to be compiled at startup, so `next start` pulls in
 * TypeScript at runtime — in a production image built with `--omit=dev` that
 * turns every container boot into a package install (and fails with no
 * network). JS keeps the runtime stage dependency-free.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  // The Agent SDK spawns a child process and reads from disk — it must never be
  // bundled into the server build.
  serverExternalPackages: ["@anthropic-ai/claude-agent-sdk"],
  experimental: {
    // Long-running orchestration: keep server actions/routes from being cut short.
    proxyTimeout: 1000 * 60 * 60,
  },
};

export default nextConfig;
