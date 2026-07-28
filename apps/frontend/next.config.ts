import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,

  // Public environment variables (safe to expose to the browser)
  env: {
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  },

  // Server Components by default — only the consultation feature is client-side
  experimental: {
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },

  // Bundle optimisation
  compiler: {
    removeConsole: process.env.NODE_ENV === "production",
  },
};

export default nextConfig;
