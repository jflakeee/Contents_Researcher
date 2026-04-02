"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getTopKeywords, getKeywordTrend } from "@/lib/api";
import type { KeywordStat } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber, getSentimentColor, getSentimentLabel } from "@/lib/utils";
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

/** 기간 옵션 정의 */
const PERIOD_OPTIONS = [
  { value: "1w", label: "1주" },
  { value: "1m", label: "1개월" },
  { value: "3m", label: "3개월" },
];

/** 출처 옵션 정의 */
const SOURCE_OPTIONS = [
  { value: "", label: "전체" },
  { value: "youtube", label: "유튜브" },
  { value: "aggag", label: "아깍" },
  { value: "instagram", label: "인스타그램" },
];

/** 트렌드 차트 색상 배열 */
const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

/**
 * 키워드 트렌드 페이지
 * - 기간/출처 필터로 인기 키워드 조회
 * - 선택한 키워드들의 일별 추이 차트
 * - 인기 키워드 TOP 20 테이블
 */
export default function KeywordsPage() {
  // 필터 상태 관리
  const [period, setPeriod] = useState("1w");
  const [source, setSource] = useState("");
  // 트렌드 차트에 표시할 선택된 키워드 목록
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]);

  // 인기 키워드 TOP 20 조회
  const {
    data: topKeywords,
    isLoading: isLoadingKeywords,
    error: keywordsError,
  } = useQuery({
    queryKey: ["topKeywords", period, source],
    queryFn: () => getTopKeywords(period, source || undefined, 20),
  });

  // 선택된 키워드들의 트렌드 데이터 조회
  const { data: trendData, isLoading: isLoadingTrend } = useQuery({
    queryKey: ["keywordTrend", selectedKeywords, period],
    queryFn: async () => {
      if (selectedKeywords.length === 0) return [];
      // 각 키워드별 트렌드를 병렬로 조회
      const results = await Promise.all(
        selectedKeywords.map((keyword) => getKeywordTrend(keyword, period))
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
    enabled: selectedKeywords.length > 0,
  });

  /**
   * 키워드 행 클릭 시 트렌드 차트 선택/해제 토글
   * - 최대 5개까지 선택 가능
   */
  const handleKeywordToggle = (keyword: string) => {
    setSelectedKeywords((prev) => {
      if (prev.includes(keyword)) {
        return prev.filter((k) => k !== keyword);
      }
      // 최대 5개까지 선택 가능
      if (prev.length >= 5) return prev;
      return [...prev, keyword];
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">키워드 트렌드</h1>

      {/* 필터 영역 */}
      <div className="flex items-center gap-4">
        {/* 기간 선택 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">기간</span>
          <Select value={period} onValueChange={(v) => v && setPeriod(v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PERIOD_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 출처 선택 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">출처</span>
          <Select value={source} onValueChange={(v) => setSource(v ?? "")}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 키워드 트렌드 차트 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">키워드 트렌드 차트</h2>
        <Card>
          <CardContent className="pt-6">
            {selectedKeywords.length === 0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                아래 테이블에서 키워드를 클릭하면 트렌드 차트가 표시됩니다. (최대 5개)
              </p>
            ) : isLoadingTrend ? (
              <Skeleton className="h-64 w-full" />
            ) : trendData && trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip />
                  <Legend />
                  {selectedKeywords.map((keyword, idx) => (
                    <Line
                      key={keyword}
                      type="monotone"
                      dataKey={keyword}
                      stroke={CHART_COLORS[idx % CHART_COLORS.length]}
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

      {/* 인기 키워드 TOP 20 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">인기 키워드 TOP 20</h2>
        {keywordsError && (
          <p className="mb-4 text-sm text-destructive">
            키워드 데이터를 불러올 수 없습니다. API 서버 연결을 확인해주세요.
          </p>
        )}
        <Card>
          <CardContent className="pt-6">
            {isLoadingKeywords ? (
              <div className="space-y-2">
                {Array.from({ length: 10 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : topKeywords && topKeywords.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">순위</TableHead>
                    <TableHead>키워드</TableHead>
                    <TableHead className="w-24 text-right">건수</TableHead>
                    <TableHead className="w-28 text-right">평균 감성</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topKeywords.map((stat: KeywordStat, index: number) => {
                    const isSelected = selectedKeywords.includes(stat.keyword);
                    return (
                      <TableRow
                        key={stat.keyword}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? "bg-accent" : "hover:bg-muted/50"
                        }`}
                        onClick={() => handleKeywordToggle(stat.keyword)}
                      >
                        <TableCell className="font-mono text-center">
                          {index + 1}
                        </TableCell>
                        <TableCell className="font-medium">
                          {isSelected && (
                            <Badge
                              variant="secondary"
                              className="mr-2"
                              style={{
                                backgroundColor:
                                  CHART_COLORS[
                                    selectedKeywords.indexOf(stat.keyword) %
                                      CHART_COLORS.length
                                  ],
                                color: "white",
                              }}
                            >
                              선택
                            </Badge>
                          )}
                          {stat.keyword}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatNumber(stat.count)}
                        </TableCell>
                        <TableCell className="text-right">
                          {stat.avg_sentiment !== null ? (
                            <Badge
                              variant="secondary"
                              className={getSentimentColor(
                                stat.avg_sentiment > 0.1
                                  ? "positive"
                                  : stat.avg_sentiment < -0.1
                                  ? "negative"
                                  : "neutral"
                              )}
                            >
                              {stat.avg_sentiment.toFixed(2)}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">-</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                키워드 데이터가 없습니다.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
