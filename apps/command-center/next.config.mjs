/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    return [
      // Proxy direct backend calls during dev so the browser hits :3000.
      { source: "/api/v1/:path*", destination: "http://localhost:8000/v1/:path*" },
    ];
  },
};

export default nextConfig;
