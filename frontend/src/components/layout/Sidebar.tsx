"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

/** 사이드바 메뉴 항목 정의 */
const menuItems = [
  { label: "대시보드", href: "/dashboard", icon: "[D]" },
  { label: "컨텐츠", href: "/contents", icon: "[C]" },
  { label: "키워드", href: "/keywords", icon: "[K]" },
  { label: "스케줄러", href: "/scheduler", icon: "[S]" },
  { label: "설정", href: "/settings", icon: "[G]" },
];

/**
 * 사이드바 네비게이션 컴포넌트
 * - 현재 경로에 따라 활성 메뉴 하이라이트
 * - 모든 주요 페이지 링크 포함
 */
export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r bg-sidebar text-sidebar-foreground">
      {/* 로고 / 제목 영역 */}
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/dashboard" className="text-lg font-bold">
          Contents Researcher
        </Link>
      </div>

      {/* 네비게이션 메뉴 */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {menuItems.map((item) => {
          // 현재 경로가 메뉴 href로 시작하는지 확인
          const isActive = pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <span className="w-8 text-center font-mono text-xs">
                {item.icon}
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* 하단: 테마 토글 + 버전 */}
      <div className="border-t px-4 py-3">
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">v1.0</p>
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
