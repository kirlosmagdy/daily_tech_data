// Configure Next.js for static HTML export so Vercel serves pre-built static files.
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default nextConfig;