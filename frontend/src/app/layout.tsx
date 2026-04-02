import type { Metadata } from "next";
import { Noto_Sans_KR } from "next/font/google";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { ThemeProvider } from "@/lib/theme-provider";
import { Sidebar } from "@/components/layout/Sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

/** 한국어 폰트 (Noto Sans KR) */
const notoSansKR = Noto_Sans_KR({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  display: "swap",
});

/** 사이트 메타데이터 */
export const metadata: Metadata = {
  title: "Contents Researcher - 컨텐츠 분석 도구",
  description:
    "다양한 플랫폼의 컨텐츠를 수집하고 분석하는 연구 도구",
};

/**
 * 루트 레이아웃
 * - QueryProvider: React Query 상태 관리
 * - TooltipProvider: shadcn/ui 툴팁 제공
 * - Sidebar + 메인 컨텐츠 영역 2단 레이아웃
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={`${notoSansKR.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="flex h-full min-h-screen">
        <ThemeProvider>
          <QueryProvider>
            <TooltipProvider>
              {/* 사이드바 네비게이션 */}
              <Sidebar />
              {/* 메인 컨텐츠 영역 */}
              <main className="flex-1 overflow-y-auto bg-background p-6">
                {children}
              </main>
            </TooltipProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
