"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

/**
 * 다크모드 토글 버튼
 * - 라이트 / 다크 / 시스템 3단 토글
 * - hydration mismatch 방지를 위해 마운트 후 렌더링
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // hydration 후에만 렌더링
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
        <span className="text-sm">--</span>
      </Button>
    );
  }

  // 3단 토글: light → dark → system
  const handleToggle = () => {
    if (theme === "light") setTheme("dark");
    else if (theme === "dark") setTheme("system");
    else setTheme("light");
  };

  const icon = theme === "dark" ? "D" : theme === "light" ? "L" : "A";
  const label =
    theme === "dark" ? "다크" : theme === "light" ? "라이트" : "자동";

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleToggle}
      className="h-8 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
      title={`현재: ${label} 모드 (클릭하여 전환)`}
    >
      <span className="font-mono font-bold">[{icon}]</span>
      <span className="hidden sm:inline">{label}</span>
    </Button>
  );
}
