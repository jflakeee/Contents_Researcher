"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

/**
 * 다크모드 테마 Provider
 * - attribute="class": html에 .dark 클래스 토글
 * - defaultTheme="system": 시스템 설정 따름
 * - enableSystem: OS 다크모드 감지
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}
