"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { searchContents, getSourceStats } from "@/lib/api";
import type { SearchRequest } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  formatDate,
  formatNumber,
  getSentimentColor,
  getSentimentLabel,
  getSourceIcon,
} from "@/lib/utils";

/**
 * 컨텐츠 검색 페이지
 * - 검색바 + 필터 패널
 * - 검색 결과 카드 목록
 * - 페이지네이션
 */
export default function ContentsPage() {
  const router = useRouter();

  // 검색 조건 상태
  const [searchParams, setSearchParams] = useState<SearchRequest>({
    query: "",
    page: 1,
    page_size: 12,
    sort_by: "collected_at",
    sort_order: "desc",
  });

  // 검색어 입력 상태 (실시간 반영 방지)
  const [queryInput, setQueryInput] = useState("");

  // 출처 목록 조회 (필터 옵션용)
  const { data: sourceStats } = useQuery({
    queryKey: ["sourceStats"],
    queryFn: getSourceStats,
  });

  // 컨텐츠 검색 결과 조회
  const {
    data: searchResult,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["contents", searchParams],
    queryFn: () => searchContents(searchParams),
  });

  // 검색 실행
  const handleSearch = useCallback(() => {
    setSearchParams((prev) => ({
      ...prev,
      query: queryInput || undefined,
      page: 1,
    }));
  }, [queryInput]);

  // Enter 키 검색
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        handleSearch();
      }
    },
    [handleSearch]
  );

  // 출처 필터 변경
  const handleSourceChange = useCallback((value: string | null) => {
    setSearchParams((prev) => ({
      ...prev,
      sources: !value || value === "all" ? undefined : [value],
      page: 1,
    }));
  }, []);

  // 감성 필터 변경
  const handleSentimentChange = useCallback((value: string | null) => {
    setSearchParams((prev) => ({
      ...prev,
      sentiment: !value || value === "all" ? undefined : value,
      page: 1,
    }));
  }, []);

  // 정렬 변경
  const handleSortChange = useCallback((value: string | null) => {
    setSearchParams((prev) => ({
      ...prev,
      sort_by: value ?? "collected_at",
      page: 1,
    }));
  }, []);

  // 페이지 변경
  const handlePageChange = useCallback((page: number) => {
    setSearchParams((prev) => ({ ...prev, page }));
  }, []);

  // 컨텐츠 카드 클릭 시 상세 페이지 이동
  const handleContentClick = useCallback(
    (id: number) => {
      router.push(`/contents/${id}`);
    },
    [router]
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">컨텐츠 검색</h1>

      {/* 검색바 + 필터 패널 */}
      <div className="space-y-4">
        {/* 검색바 */}
        <div className="flex gap-2">
          <Input
            placeholder="검색어를 입력하세요..."
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1"
          />
          <Button onClick={handleSearch}>검색</Button>
        </div>

        {/* 필터 패널 */}
        <div className="flex flex-wrap gap-3">
          {/* 출처 필터 */}
          <Select onValueChange={handleSourceChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="출처 선택" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">전체 출처</SelectItem>
              {sourceStats?.map((stat) => (
                <SelectItem key={stat.source} value={stat.source}>
                  {getSourceIcon(stat.source)} {stat.source}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 감성 필터 */}
          <Select onValueChange={handleSentimentChange}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="감성 선택" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">전체 감성</SelectItem>
              <SelectItem value="positive">긍정</SelectItem>
              <SelectItem value="neutral">중립</SelectItem>
              <SelectItem value="negative">부정</SelectItem>
            </SelectContent>
          </Select>

          {/* 날짜 범위 필터 */}
          <Input
            type="date"
            className="w-40"
            onChange={(e) =>
              setSearchParams((prev) => ({
                ...prev,
                date_from: e.target.value || undefined,
                page: 1,
              }))
            }
            placeholder="시작일"
          />
          <Input
            type="date"
            className="w-40"
            onChange={(e) =>
              setSearchParams((prev) => ({
                ...prev,
                date_to: e.target.value || undefined,
                page: 1,
              }))
            }
            placeholder="종료일"
          />

          {/* 정렬 */}
          <Select onValueChange={handleSortChange} defaultValue="collected_at">
            <SelectTrigger className="w-40">
              <SelectValue placeholder="정렬 기준" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="collected_at">수집일순</SelectItem>
              <SelectItem value="importance_score">중요도순</SelectItem>
              <SelectItem value="comment_count">댓글수순</SelectItem>
              <SelectItem value="like_count">좋아요순</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 에러 상태 */}
      {error && (
        <p className="text-sm text-destructive">
          데이터를 불러올 수 없습니다. API 서버 연결을 확인해주세요.
        </p>
      )}

      {/* 검색 결과 */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="space-y-3 pt-6">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-3 w-48" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : searchResult && searchResult.items.length > 0 ? (
        <>
          {/* 결과 수 표시 */}
          <p className="text-sm text-muted-foreground">
            총 {formatNumber(searchResult.total)}건의 결과
          </p>

          {/* 카드 목록 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {searchResult.items.map((content) => (
              <Card
                key={content.id}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => handleContentClick(content.id)}
              >
                <CardContent className="space-y-3 pt-6">
                  {/* 출처 + 날짜 */}
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {getSourceIcon(content.source)} {content.source}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDate(content.collected_at)}
                    </span>
                  </div>

                  {/* 제목 */}
                  <h3 className="line-clamp-2 text-sm font-semibold">
                    {content.title}
                  </h3>

                  {/* 키워드 뱃지 */}
                  <div className="flex flex-wrap gap-1">
                    {content.keywords.slice(0, 5).map((keyword) => (
                      <Badge key={keyword} variant="outline" className="text-xs">
                        {keyword}
                      </Badge>
                    ))}
                  </div>

                  {/* 감성 + 통계 */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {content.sentiment && (
                        <Badge
                          variant="secondary"
                          className={getSentimentColor(content.sentiment)}
                        >
                          {getSentimentLabel(content.sentiment)}
                        </Badge>
                      )}
                      {content.importance_score !== null && (
                        <span className="text-muted-foreground">
                          중요도 {content.importance_score.toFixed(1)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-muted-foreground">
                      <span>댓글 {formatNumber(content.comment_count)}</span>
                      <span>좋아요 {formatNumber(content.like_count)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* 페이지네이션 (이전/다음 + 페이지 번호) */}
          {searchResult.total_pages > 1 && (
            <div className="flex items-center justify-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={searchResult.page <= 1}
                onClick={() => handlePageChange(searchResult.page - 1)}
              >
                이전
              </Button>
              {/* 페이지 번호 버튼 */}
              {(() => {
                const maxVisible = 5;
                const total = searchResult.total_pages;
                const current = searchResult.page;
                let start = Math.max(1, current - Math.floor(maxVisible / 2));
                const end = Math.min(total, start + maxVisible - 1);
                start = Math.max(1, end - maxVisible + 1);
                const pages: number[] = [];
                for (let i = start; i <= end; i++) pages.push(i);
                return pages.map((num) => (
                  <Button
                    key={num}
                    variant={num === current ? "default" : "outline"}
                    size="sm"
                    onClick={() => handlePageChange(num)}
                  >
                    {num}
                  </Button>
                ));
              })()}
              <Button
                variant="outline"
                size="sm"
                disabled={searchResult.page >= searchResult.total_pages}
                onClick={() => handlePageChange(searchResult.page + 1)}
              >
                다음
              </Button>
            </div>
          )}
        </>
      ) : (
        !error && (
          <div className="flex flex-col items-center justify-center py-16">
            <p className="text-lg font-medium text-muted-foreground">
              검색 결과가 없습니다.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              다른 검색어나 필터 조건을 시도해 보세요.
            </p>
          </div>
        )
      )}
    </div>
  );
}
