import type {
  ContentSummary,
  ContentDetail,
  PaginatedResponse,
  SearchRequest,
  KeywordStat,
  KeywordTrendPoint,
  SourceStat,
  CollectionJob,
  ScheduleJob,
} from "@/types";

// API 기본 URL (환경변수 또는 기본값)
const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * 공통 fetch 래퍼
 * - JSON 응답 자동 파싱
 * - 에러 시 예외 발생
 */
async function fetchAPI<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => "");
    throw new Error(
      `API 요청 실패: ${res.status} ${res.statusText} - ${errorBody}`
    );
  }

  // DELETE 등 본문이 없는 응답 처리
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/**
 * 쿼리 파라미터 문자열 생성 유틸
 * - undefined/null 값은 제외
 * - 배열은 콤마로 구분
 */
function buildQuery(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      if (value.length > 0) {
        searchParams.set(key, value.join(","));
      }
    } else {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

// ─── 컨텐츠 API ─────────────────────────────────────────────

/** 컨텐츠 검색 */
export async function searchContents(
  request: SearchRequest
): Promise<PaginatedResponse<ContentSummary>> {
  const query = buildQuery({
    query: request.query,
    sources: request.sources,
    sentiment: request.sentiment,
    date_from: request.date_from,
    date_to: request.date_to,
    sort_by: request.sort_by,
    sort_order: request.sort_order,
    page: request.page,
    page_size: request.page_size,
  });
  return fetchAPI<PaginatedResponse<ContentSummary>>(
    `/api/v1/contents${query}`
  );
}

/** 컨텐츠 상세 조회 */
export async function getContent(id: number): Promise<ContentDetail> {
  return fetchAPI<ContentDetail>(`/api/v1/contents/${id}`);
}

/** 트렌딩 컨텐츠 조회 */
export async function getTrendingContents(
  period?: string,
  source?: string,
  limit?: number
): Promise<ContentSummary[]> {
  const query = buildQuery({ period, source, limit });
  return fetchAPI<ContentSummary[]>(
    `/api/v1/contents/trending${query}`
  );
}

// ─── 키워드 API ─────────────────────────────────────────────

/** 인기 키워드 조회 */
export async function getTopKeywords(
  period?: string,
  source?: string,
  limit?: number
): Promise<KeywordStat[]> {
  const query = buildQuery({ period, source, limit });
  return fetchAPI<KeywordStat[]>(`/api/v1/keywords/top${query}`);
}

/** 키워드 트렌드 조회 */
export async function getKeywordTrend(
  keyword: string,
  period?: string
): Promise<KeywordTrendPoint[]> {
  const query = buildQuery({ keyword, period });
  return fetchAPI<KeywordTrendPoint[]>(
    `/api/v1/keywords/trend${query}`
  );
}

// ─── 출처 API ───────────────────────────────────────────────

/** 출처별 통계 조회 */
export async function getSourceStats(): Promise<SourceStat[]> {
  return fetchAPI<SourceStat[]>(`/api/v1/sources/stats`);
}

// ─── 크롤러 API ─────────────────────────────────────────────

/** 크롤러 수동 실행 */
export async function triggerCrawler(
  source: string,
  query?: string,
  dateFrom?: string,
  dateTo?: string
): Promise<{ job_id: number }> {
  return fetchAPI<{ job_id: number }>(`/api/v1/crawler/trigger`, {
    method: "POST",
    body: JSON.stringify({
      source,
      query,
      date_from: dateFrom,
      date_to: dateTo,
    }),
  });
}

/** 크롤러 현재 상태 조회 */
export async function getCrawlerStatus(): Promise<CollectionJob[]> {
  return fetchAPI<CollectionJob[]>(`/api/v1/crawler/status`);
}

/** 크롤러 수집 이력 조회 */
export async function getCrawlerHistory(): Promise<CollectionJob[]> {
  return fetchAPI<CollectionJob[]>(`/api/v1/crawler/history`);
}

// ─── 스케줄러 API ────────────────────────────────────────────

/** 스케줄러 작업 목록 조회 */
export async function getSchedulerJobs(): Promise<ScheduleJob[]> {
  return fetchAPI<ScheduleJob[]>(`/api/v1/scheduler/jobs`);
}

/** 스케줄러 작업 생성 */
export async function createSchedulerJob(data: {
  source: string;
  cron_expression: string;
  query?: string;
  enabled?: boolean;
}): Promise<ScheduleJob> {
  return fetchAPI<ScheduleJob>(`/api/v1/scheduler/jobs`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** 스케줄러 작업 삭제 */
export async function deleteSchedulerJob(id: string): Promise<void> {
  return fetchAPI<void>(`/api/v1/scheduler/jobs/${id}`, {
    method: "DELETE",
  });
}
