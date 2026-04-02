"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

/**
 * React Query Provider 컴포넌트
 * - 클라이언트 컴포넌트에서 QueryClientProvider를 래핑
 * - staleTime: 30초 (기본 캐시 유지 시간)
 * - retry: 1회 재시도
 */
export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 30초간 캐시 데이터를 신선한 것으로 간주
            staleTime: 30 * 1000,
            // 실패 시 1회 재시도
            retry: 1,
            // 창 포커스 시 자동 새로고침
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
