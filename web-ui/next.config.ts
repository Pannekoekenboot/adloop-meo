import type { NextConfig } from "next";

// Target for the FastAPI backend. In dev: `adloop web` on :8787.
// In production, the Next build is exported and served from the same
// origin by FastAPI, so rewrites don't run — the relative /api paths
// reach FastAPI directly.
const API_TARGET = process.env.ADLOOP_API_URL ?? "http://127.0.0.1:8787";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_TARGET}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
