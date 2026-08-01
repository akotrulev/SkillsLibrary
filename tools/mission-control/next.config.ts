import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The Agent SDK spawns a child process and reads from disk — it must never be
  // bundled into the server build.
  serverExternalPackages: ["@anthropic-ai/claude-agent-sdk"],
  experimental: {
    // Long-running orchestration: keep server actions/routes from being cut short.
    proxyTimeout: 1000 * 60 * 60,
  },
};

export default nextConfig;
