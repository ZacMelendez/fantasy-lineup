import type { NextConfig } from "next";

const config: NextConfig = {
  // Produces a minimal self-contained server bundle for the Docker image.
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },
};

export default config;
