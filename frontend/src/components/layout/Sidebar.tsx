"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { Button } from "@/components/ui/button";

/** 사이드바 메뉴 항목 정의 */
const menuItems = [
  { label: "대시보드", href: "/dashboard", icon: "D" },
  { label: "컨텐츠", href: "/contents", icon: "C" },
  { label: "키워드", href: "/keywords", icon: "K" },
  { label: "스케줄러", href: "/scheduler", icon: "S" },
  { label: "설정", href: "/settings", icon: "G" },
];

/**
 * 사이드바 네비게이션 컴포넌트
 * - 토글 버튼으로 펼침/접힘 전환
 * - 접힌 상태에서는 아이콘만 표시
 * - 현재 경로에 따라 활성 메뉴 하이라이트
 */
export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r bg-sidebar text-sidebar-foreground transition-all duration-200",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* 로고 / 제목 + 토글 버튼 */}
      <div className="flex h-16 items-center border-b px-3">
        {!collapsed && (
          <Link href="/dashboard" className="flex-1 truncate px-2 text-lg font-bold">
            Contents Researcher
          </Link>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "h-8 w-8 shrink-0 p-0 text-muted-foreground hover:text-foreground",
            collapsed && "mx-auto"
          )}
          title={collapsed ? "메뉴 펼치기" : "메뉴 접기"}
        >
          <span className="font-mono text-sm">{collapsed ? ">>" : "<<"}</span>
        </Button>
      </div>

      {/* 네비게이션 메뉴 */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {menuItems.map((item) => {
          const isActive = pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                collapsed ? "justify-center" : "gap-3",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              <span className="w-6 text-center font-mono text-xs font-bold">
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* 하단: 테마 토글 + 버전 */}
      <div className="border-t px-2 py-3">
        <div className={cn(
          "flex items-center",
          collapsed ? "justify-center" : "justify-between px-2"
        )}>
          {!collapsed && <p className="text-xs text-muted-foreground">v1.0</p>}
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
