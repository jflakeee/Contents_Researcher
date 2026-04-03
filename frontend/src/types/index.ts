// 컨텐츠 요약 타입
export interface ContentSummary {
  id: number;
  source: string;
  source_url: string;
  title: string;
  keywords: string[];
  sentiment: string | null;
  sentiment_score: number | null;
  importance_score: number | null;
  comment_count: number;
  like_count: number;
  collected_at: string;
}

// 댓글 타입
export interface Comment {
  id: number;
  author: string;
  body: string;
  sentiment: string | null;
  sentiment_score: number | null;
  like_count: number;
}

// 컨텐츠 상세 타입 (요약 + 본문 + 댓글)
export interface ContentDetail extends ContentSummary {
  body: string | null;
  view_count: number;
  metadata: Record<string, unknown>;
  comments: Comment[];
}

// 페이지네이션 응답 타입
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 검색 요청 파라미터 타입
export interface SearchRequest {
  query?: string;
  sources?: string[];
  sentiment?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

// 키워드 통계 타입
export interface KeywordStat {
  keyword: string;
  count: number;
  avg_sentiment: number | null;
}

// 키워드 트렌드 포인트 타입
export interface KeywordTrendPoint {
  date: string;
  keyword: string;
  count: number;
}

// 출처별 통계 타입
export interface SourceStat {
  source: string;
  content_count: number;
  avg_sentiment: number | null;
  last_collected_at: string | null;
}

// 수집 작업 타입
export interface CollectionJob {
  id: number;
  source: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items_count: number;
  error_message: string | null;
}

// 스케줄 작업 타입
export interface ScheduleJob {
  id: string;
  source: string;
  cron_expression: string;
  query: string | null;
  enabled: boolean;
  next_run: string | null;
}
