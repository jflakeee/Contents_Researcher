"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getContent } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  formatDate,
  formatNumber,
  getSentimentColor,
  getSentimentLabel,
} from "@/lib/utils";

/**
 * 컨텐츠 상세 페이지
 * - 기본 정보 (출처, 제목, 원본 링크, 수집일)
 * - 키워드 목록
 * - 감성 분석 결과
 * - 댓글 목록
 */
export default function ContentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const contentId = Number(id);

  // 컨텐츠 상세 데이터 조회
  const { data: content, isLoading, error } = useQuery({
    queryKey: ["content", contentId],
    queryFn: () => getContent(contentId),
    enabled: !isNaN(contentId),
  });

  // 뒤로가기 핸들러
  const handleBack = () => {
    router.back();
  };

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  // 에러 상태
  if (error || !content) {
    return (
      <div className="space-y-4">
        <Button variant="outline" onClick={handleBack}>
          뒤로가기
        </Button>
        <p className="text-sm text-destructive">
          컨텐츠를 불러올 수 없습니다. API 서버 연결을 확인해주세요.
        </p>
      </div>
    );
  }

  // 댓글 감성 통계 계산
  const sentimentCounts = content.comments.reduce(
    (acc, comment) => {
      if (comment.sentiment === "positive") acc.positive++;
      else if (comment.sentiment === "negative") acc.negative++;
      else if (comment.sentiment === "neutral") acc.neutral++;
      else acc.unknown++;
      return acc;
    },
    { positive: 0, negative: 0, neutral: 0, unknown: 0 }
  );

  const totalComments = content.comments.length;

  return (
    <div className="space-y-6">
      {/* 뒤로가기 버튼 */}
      <Button variant="outline" onClick={handleBack}>
        뒤로가기
      </Button>

      {/* 기본 정보 카드 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{content.source}</span>
            <span>|</span>
            <span>{formatDate(content.collected_at)}</span>
          </div>
          <CardTitle className="text-xl">{content.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 원본 링크 */}
          {content.source_url && (
            <a
              href={content.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary underline"
            >
              원본 링크로 이동
            </a>
          )}

          {/* 통계 정보 */}
          <div className="flex gap-4 text-sm text-muted-foreground">
            <span>조회수 {formatNumber(content.view_count)}</span>
            <span>댓글 {formatNumber(content.comment_count)}</span>
            <span>좋아요 {formatNumber(content.like_count)}</span>
            {content.importance_score !== null && (
              <span>중요도 {content.importance_score.toFixed(1)}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 키워드 목록 */}
      {content.keywords.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">키워드</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {content.keywords.map((keyword) => (
                <Badge key={keyword} variant="outline">
                  {keyword}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 감성 분석 결과 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">감성 분석</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 본문 감성 */}
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">본문 감성:</span>
            {content.sentiment ? (
              <>
                <Badge
                  variant="secondary"
                  className={getSentimentColor(content.sentiment)}
                >
                  {getSentimentLabel(content.sentiment)}
                </Badge>
                {content.sentiment_score !== null && (
                  <span className="text-sm text-muted-foreground">
                    (점수: {content.sentiment_score.toFixed(2)})
                  </span>
                )}
              </>
            ) : (
              <span className="text-sm text-muted-foreground">미분석</span>
            )}
          </div>

          {/* 댓글 감성 분포 */}
          {totalComments > 0 && (
            <>
              <Separator />
              <div>
                <p className="mb-2 text-sm font-medium">
                  댓글 감성 분포 (총 {totalComments}건)
                </p>
                <div className="flex gap-4 text-sm">
                  <span className="text-green-600">
                    긍정 {sentimentCounts.positive}건 (
                    {((sentimentCounts.positive / totalComments) * 100).toFixed(
                      1
                    )}
                    %)
                  </span>
                  <span className="text-gray-600">
                    중립 {sentimentCounts.neutral}건 (
                    {((sentimentCounts.neutral / totalComments) * 100).toFixed(1)}
                    %)
                  </span>
                  <span className="text-red-600">
                    부정 {sentimentCounts.negative}건 (
                    {((sentimentCounts.negative / totalComments) * 100).toFixed(1)}
                    %)
                  </span>
                  {sentimentCounts.unknown > 0 && (
                    <span className="text-muted-foreground">
                      미분석 {sentimentCounts.unknown}건
                    </span>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 본문 */}
      {content.body && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">본문</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="whitespace-pre-wrap text-sm leading-relaxed">
              {content.body}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 댓글 목록 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            댓글 ({content.comments.length}건)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {content.comments.length > 0 ? (
            <div className="space-y-4">
              {content.comments.map((comment) => (
                <div
                  key={comment.id}
                  className="rounded-lg border p-4"
                >
                  {/* 댓글 헤더 */}
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {comment.author}
                    </span>
                    <div className="flex items-center gap-2">
                      {comment.sentiment && (
                        <Badge
                          variant="secondary"
                          className={getSentimentColor(comment.sentiment)}
                        >
                          {getSentimentLabel(comment.sentiment)}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        좋아요 {formatNumber(comment.like_count)}
                      </span>
                    </div>
                  </div>
                  {/* 댓글 내용 */}
                  <p className="text-sm text-muted-foreground">
                    {comment.body}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-muted-foreground">
              댓글이 없습니다.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
