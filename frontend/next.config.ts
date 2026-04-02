import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API 프록시: 프론트엔드에서 /api/v1/** 요청을 백엔드로 전달
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
