/** @type {import('next').NextConfig} */
// Static export for GitHub Pages. Set NEXT_PUBLIC_BASE_PATH="/<repo-name>" when
// deploying to https://<user>.github.io/<repo-name>/ (the CI workflow does this).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig = {
  output: "export",
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
  images: { unoptimized: true },
  trailingSlash: true,
  reactStrictMode: true,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

module.exports = nextConfig;
