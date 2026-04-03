"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getSourceStats,
  getTopKeywords,
  getKeywordTrend,
  getTrendingContents,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatDate,
  formatNumber,
  getSentimentColor,
  getSentimentLabel,
  getSourceIcon,
} from "@/lib/utils";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

/**
 * 대시보드 페이지
 * - 출처별 수집 현황 카드
 * - 키워드 트렌드 차트
 * - 최근 수집 컨텐츠 테이블
 */
export default function DashboardPage() {
  // 출처별 통계 조회
  const {
    data: sourceStats,
    isLoading: isLoadingStats,
    error: statsError,
  } = useQuery({
    queryKey: ["sourceStats"],
    queryFn: getSourceStats,
  });

  // 인기 키워드 조회 (트렌드 차트용)
  const { data: topKeywords, isLoading: isLoadingKeywords } = useQuery({
    queryKey: ["topKeywords", "1w"],
    queryFn: () => getTopKeywords("1w", undefined, 5),
  });

  // 상위 키워드 트렌드 데이터 조회
  const topKeywordNames = topKeywords?.slice(0, 3).map((k) => k.keyword) ?? [];
  const { data: trendData, isLoading: isLoadingTrend } = useQuery({
    queryKey: ["keywordTrend", topKeywordNames],
    queryFn: async () => {
      if (topKeywordNames.length === 0) return [];
      // 각 키워드별 트렌드를 병렬로 조회
      const results = await Promise.all(
        topKeywordNames.map((keyword) => getKeywordTrend(keyword, "1w"))
      );
      // 날짜 기준으로 데이터 병합
      const mergedMap = new Map<string, Record<string, unknown>>();
      results.forEach((points) => {
        points.forEach((point) => {
          const existing = mergedMap.get(point.date) || { date: point.date };
          existing[point.keyword] = point.count;
          mergedMap.set(point.date, existing);
        });
      });
      return Array.from(mergedMap.values()).sort((a, b) =>
        String(a.date).localeCompare(String(b.date))
      );
    },
    enabled: topKeywordNames.length > 0,
  });

  // 최근 트렌딩 컨텐츠 조회 (getTrendingContents API 사용)
  const { data: recentContents, isLoading: isLoadingContents } = useQuery({
    queryKey: ["trendingContents"],
    queryFn: () => getTrendingContents(undefined, undefined, 10),
  });

  // 트렌드 차트 색상 배열
  const chartColors = [
    "var(--chart-1)",
    "var(--chart-2)",
    "var(--chart-3)",
    "var(--chart-4)",
    "var(--chart-5)",
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* 출처별 수집 현황 카드 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">출처별 수집 현황</h2>
        {statsError && (
          <p className="text-sm text-destructive">
            데이터를 불러올 수 없습니다. API 서버 연결을 확인해주세요.
          </p>
        )}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {isLoadingStats
            ? // 로딩 스켈레톤
              Array.from({ length: 4 }).map((_, i) => (
                <Card key={i}>
                  <CardHeader className="pb-2">
                    <Skeleton className="h-4 w-20" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-8 w-16" />
                    <Skeleton className="mt-2 h-3 w-32" />
                  </CardContent>
                </Card>
              ))
            : (
                <>
                  {/* 전체 수집 현황 카드 */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        전체
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {formatNumber(
                          sourceStats?.reduce((sum, s) => sum + (s.content_count ?? 0), 0) ?? 0
                        )}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        총 {sourceStats?.length ?? 0}개 출처
                      </p>
                    </CardContent>
                  </Card>
                  {/* 출처별 카드 */}
                  {sourceStats?.map((stat) => (
                    <Card key={stat.source}>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                          {getSourceIcon(stat.source)} {stat.source}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">
                          {formatNumber(stat.content_count)}
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          평균 감성{" "}
                          {stat.avg_sentiment !== null
                            ? stat.avg_sentiment?.toFixed(2)
                            : "-"}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </>
              )}
          {!isLoadingStats && !statsError && sourceStats?.length === 0 && (
            <p className="col-span-full text-sm text-muted-foreground">
              수집된 데이터가 없습니다.
            </p>
          )}
        </div>
      </section>

      {/* 키워드 트렌드 차트 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">키워드 트렌드 (최근 1주)</h2>
        <Card>
          <CardContent className="pt-6">
            {isLoadingKeywords || isLoadingTrend ? (
              <Skeleton className="h-64 w-full" />
            ) : trendData && trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Legend />
                  {topKeywordNames.map((keyword, idx) => (
                    <Line
                      key={keyword}
                      type="monotone"
                      dataKey={keyword}
                      stroke={chartColors[idx % chartColors.length]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="py-12 text-center text-sm text-muted-foreground">
                트렌드 데이터가 없습니다.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      {/* 최근 수집 컨텐츠 테이블 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">최근 수집 컨텐츠</h2>
        <Card>
          <CardContent className="pt-6">
            {isLoadingContents ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : recentContents && recentContents.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">출처</TableHead>
                    <TableHead>제목</TableHead>
                    <TableHead className="w-20">감성</TableHead>
                    <TableHead className="w-20 text-right">댓글</TableHead>
                    <TableHead className="w-20 text-right">좋아요</TableHead>
                    <TableHead className="w-40">수집일</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentContents.map((content) => (
                    <TableRow key={content.id}>
                      <TableCell className="font-mono text-xs">
                        {getSourceIcon(content.source)}
                      </TableCell>
                      <TableCell className="max-w-xs truncate font-medium">
                        <Link
                          href={`/contents/${content.id}`}
                          className="hover:text-primary hover:underline"
                        >
                          {content.title}
                        </Link>
                      </TableCell>
                      <TableCell>
                        {content.sentiment ? (
                          <Badge
                            variant="secondary"
                            className={getSentimentColor(content.sentiment)}
                          >
                            {getSentimentLabel(content.sentiment)}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(content.comment_count)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatNumber(content.like_count)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(content.collected_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                수집된 컨텐츠가 없습니다.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
