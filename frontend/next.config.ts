import type { NextConfig } from "next";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

const nextConfig: NextConfig = {
  async rewrites() {
    // 開発時: 本番のCaddy同一オリジン配信(design.md 15.3節)を
    // ローカルでも再現し、backendの/imagesを同一オリジンで参照できるようにする
    if (!apiBaseUrl) return [];
    return [{ source: "/images/:path*", destination: `${apiBaseUrl}/images/:path*` }];
  },
};

export default nextConfig;
