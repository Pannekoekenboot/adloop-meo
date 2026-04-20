import type { NextConfig } from "next";

// Target for the FastAPI backend during `next dev`. The production
// build is a static export served from the same origin as FastAPI,
// so rewrites only run in dev.
const API_TARGET = process.env.ADLOOP_API_URL ?? "http://127.0.0.1:8787";
const isDev = process.env.NODE_ENV !== "production";

const nextConfig: NextConfig = {
  // Produce a fully static bundle in `out/`. The `adloop web` server
  // mounts it at "/" so the UI and /api live on a single origin.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },

  ...(isDev
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${API_TARGET}/api/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
