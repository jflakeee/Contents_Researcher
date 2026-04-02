"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSchedulerJobs,
  createSchedulerJob,
  deleteSchedulerJob,
  triggerCrawler,
  getCrawlerHistory,
} from "@/lib/api";
import type { ScheduleJob, CollectionJob } from "@/types";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

/** 출처 옵션 정의 */
const SOURCE_OPTIONS = [
  { value: "youtube", label: "유튜브" },
  { value: "aggag", label: "아깍" },
  { value: "instagram", label: "인스타그램" },
];

/**
 * 스케줄러 페이지
 * - 스케줄 목록 테이블 (조회/추가/삭제)
 * - 수동 수집 실행 섹션
 * - 수집 이력 테이블
 */
export default function SchedulerPage() {
  const queryClient = useQueryClient();

  // ─── 스케줄 추가 다이얼로그 상태 ────────────────────────────
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newJobSource, setNewJobSource] = useState("youtube");
  const [newJobCron, setNewJobCron] = useState("");
  const [newJobQuery, setNewJobQuery] = useState("");

  // ─── 수동 수집 상태 ──────────────────────────────────────────
  const [crawlSource, setCrawlSource] = useState("youtube");
  const [crawlQuery, setCrawlQuery] = useState("");

  // ─── 스케줄 목록 조회 ───────────────────────────────────────
  const {
    data: schedulerJobs,
    isLoading: isLoadingJobs,
    error: jobsError,
  } = useQuery({
    queryKey: ["schedulerJobs"],
    queryFn: getSchedulerJobs,
  });

  // ─── 수집 이력 조회 ────────────────────────────────────────
  const {
    data: crawlerHistory,
    isLoading: isLoadingHistory,
    error: historyError,
  } = useQuery({
    queryKey: ["crawlerHistory"],
    queryFn: getCrawlerHistory,
  });

  // ─── 스케줄 생성 뮤테이션 ──────────────────────────────────
  const createMutation = useMutation({
    mutationFn: createSchedulerJob,
    onSuccess: () => {
      // 스케줄 목록 다시 조회
      queryClient.invalidateQueries({ queryKey: ["schedulerJobs"] });
      // 다이얼로그 닫기 및 입력 초기화
      setDialogOpen(false);
      setNewJobCron("");
      setNewJobQuery("");
    },
  });

  // ─── 스케줄 삭제 뮤테이션 ──────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: deleteSchedulerJob,
    onSuccess: () => {
      // 스케줄 목록 다시 조회
      queryClient.invalidateQueries({ queryKey: ["schedulerJobs"] });
    },
  });

  // ─── 수동 수집 뮤테이션 ────────────────────────────────────
  const triggerMutation = useMutation({
    mutationFn: ({ source, query }: { source: string; query?: string }) =>
      triggerCrawler(source, query || undefined),
    onSuccess: () => {
      // 수집 이력 다시 조회
      queryClient.invalidateQueries({ queryKey: ["crawlerHistory"] });
      setCrawlQuery("");
    },
  });

  /** 스케줄 추가 폼 제출 핸들러 */
  const handleCreateJob = () => {
    if (!newJobCron.trim()) return;
    createMutation.mutate({
      source: newJobSource,
      cron_expression: newJobCron.trim(),
      query: newJobQuery.trim() || undefined,
      enabled: true,
    });
  };

  /** 수동 수집 실행 핸들러 */
  const handleTriggerCrawl = () => {
    triggerMutation.mutate({
      source: crawlSource,
      query: crawlQuery.trim() || undefined,
    });
  };

  /** 상태값에 따른 뱃지 색상 반환 */
  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-100 text-blue-800";
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  /** 상태값 한국어 변환 */
  const getStatusLabel = (status: string) => {
    switch (status) {
      case "running":
        return "실행중";
      case "completed":
        return "완료";
      case "failed":
        return "실패";
      case "pending":
        return "대기중";
      default:
        return status;
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">스케줄러</h1>

      {/* 스케줄 목록 섹션 */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">스케줄 목록</h2>

          {/* 스케줄 추가 다이얼로그 */}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger render={<Button />}>스케줄 추가</DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>새 스케줄 추가</DialogTitle>
                <DialogDescription>
                  수집 스케줄을 등록합니다. cron 표현식으로 실행 주기를 설정하세요.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-2">
                {/* 출처 선택 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">출처</label>
                  <Select value={newJobSource} onValueChange={(v) => v && setNewJobSource(v)}>
                    <SelectTrigger className="w-full">
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
                {/* cron 표현식 입력 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">Cron 표현식</label>
                  <Input
                    placeholder="예: 0 */6 * * * (6시간마다)"
                    value={newJobCron}
                    onChange={(e) => setNewJobCron(e.target.value)}
                  />
                </div>
                {/* 검색 키워드 입력 */}
                <div className="space-y-2">
                  <label className="text-sm font-medium">검색 키워드 (선택)</label>
                  <Input
                    placeholder="수집 시 사용할 검색어"
                    value={newJobQuery}
                    onChange={(e) => setNewJobQuery(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleCreateJob}
                  disabled={!newJobCron.trim() || createMutation.isPending}
                >
                  {createMutation.isPending ? "추가 중..." : "추가"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {/* 에러 표시 */}
        {jobsError && (
          <p className="mb-4 text-sm text-destructive">
            스케줄 목록을 불러올 수 없습니다. API 서버 연결을 확인해주세요.
          </p>
        )}

        {/* 스케줄 목록 테이블 */}
        <Card>
          <CardContent className="pt-6">
            {isLoadingJobs ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : schedulerJobs && schedulerJobs.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">출처</TableHead>
                    <TableHead>Cron 표현식</TableHead>
                    <TableHead>검색 키워드</TableHead>
                    <TableHead className="w-40">다음 실행</TableHead>
                    <TableHead className="w-20">상태</TableHead>
                    <TableHead className="w-20">작업</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {schedulerJobs.map((job: ScheduleJob) => (
                    <TableRow key={job.id}>
                      <TableCell className="font-medium">{job.source}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {job.cron_expression}
                      </TableCell>
                      <TableCell>
                        {job.query || (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {job.next_run ? formatDate(job.next_run) : "-"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={
                            job.enabled
                              ? "bg-green-100 text-green-800"
                              : "bg-gray-100 text-gray-800"
                          }
                        >
                          {job.enabled ? "활성" : "비활성"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteMutation.mutate(job.id)}
                          disabled={deleteMutation.isPending}
                        >
                          삭제
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                등록된 스케줄이 없습니다.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      {/* 수동 수집 섹션 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">수동 수집</h2>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-end gap-4">
              {/* 출처 선택 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">출처</label>
                <Select value={crawlSource} onValueChange={(v) => v && setCrawlSource(v)}>
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
              {/* 검색어 입력 */}
              <div className="flex-1 space-y-2">
                <label className="text-sm font-medium">검색어</label>
                <Input
                  placeholder="수집할 검색어를 입력하세요"
                  value={crawlQuery}
                  onChange={(e) => setCrawlQuery(e.target.value)}
                />
              </div>
              {/* 수집 시작 버튼 */}
              <Button
                onClick={handleTriggerCrawl}
                disabled={triggerMutation.isPending}
              >
                {triggerMutation.isPending ? "수집 중..." : "수집 시작"}
              </Button>
            </div>
            {/* 수집 성공 메시지 */}
            {triggerMutation.isSuccess && (
              <p className="mt-3 text-sm text-green-600">
                수집이 시작되었습니다. (작업 ID: {triggerMutation.data?.id})
              </p>
            )}
            {/* 수집 에러 메시지 */}
            {triggerMutation.isError && (
              <p className="mt-3 text-sm text-destructive">
                수집 요청에 실패했습니다. 다시 시도해주세요.
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      {/* 수집 이력 섹션 */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">수집 이력</h2>
        {historyError && (
          <p className="mb-4 text-sm text-destructive">
            수집 이력을 불러올 수 없습니다. API 서버 연결을 확인해주세요.
          </p>
        )}
        <Card>
          <CardContent className="pt-6">
            {isLoadingHistory ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : crawlerHistory && crawlerHistory.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-24">출처</TableHead>
                    <TableHead className="w-20">상태</TableHead>
                    <TableHead className="w-44">시작 시간</TableHead>
                    <TableHead className="w-44">완료 시간</TableHead>
                    <TableHead className="w-24 text-right">수집 건수</TableHead>
                    <TableHead>에러 메시지</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {crawlerHistory.map((job: CollectionJob) => (
                    <TableRow key={job.id}>
                      <TableCell className="font-medium">{job.source}</TableCell>
                      <TableCell>
                        <Badge
                          variant="secondary"
                          className={getStatusBadgeClass(job.status)}
                        >
                          {getStatusLabel(job.status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {job.started_at ? formatDate(job.started_at) : "-"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {job.completed_at ? formatDate(job.completed_at) : "-"}
                      </TableCell>
                      <TableCell className="text-right">{job.items_count}</TableCell>
                      <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                        {job.error_message || "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                수집 이력이 없습니다.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
