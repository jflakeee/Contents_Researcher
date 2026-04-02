# =============================================================================
# Contents Researcher 프론트엔드 Dockerfile
# =============================================================================
# 멀티스테이지 빌드: 의존성 → 빌드 → 실행
# =============================================================================

FROM node:20-alpine AS base
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app

# --- 의존성 설치 ---
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile

# --- 빌드 ---
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Docker 환경에서 API 호스트를 backend 컨테이너로 설정
ENV API_HOST=backend

RUN pnpm build

# --- 실행 ---
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV API_HOST=backend

# standalone 출력 복사
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
