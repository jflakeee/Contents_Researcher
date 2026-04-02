import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker standalone 출력 활성화
  output: "standalone",
  // API 프록시: 프론트엔드에서 /api/v1/** 요청을 백엔드로 전달
  // Docker 환경에서는 backend 컨테이너명 사용, 로컬에서는 localhost
  async rewrites() {
    const apiHost = process.env.API_HOST || "localhost";
    return [
      {
        source: "/api/v1/:path*",
        destination: `http://${apiHost}:8000/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
