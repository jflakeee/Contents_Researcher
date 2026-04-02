"""
검색, 크롤러 트리거, 스케줄 관련 요청 스키마 정의.
"""

from datetime import date

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """콘텐츠 검색 요청 스키마."""

    # 검색 키워드 (제목/본문 대상)
    query: str | None = None

    # 필터링할 출처 목록
    sources: list[str] | None = None

    # 감성 필터 (positive, negative, neutral)
    sentiment: str | None = None

    # 기간 필터 시작일
    date_from: date | None = None

    # 기간 필터 종료일
    date_to: date | None = None

    # 정렬 기준 컬럼
    sort_by: str = "collected_at"

    # 정렬 방향 (asc, desc)
    sort_order: str = "desc"

    # 현재 페이지 번호 (1부터 시작)
    page: int = Field(default=1, ge=1)

    # 페이지당 항목 수
    page_size: int = Field(default=20, ge=1, le=100)


class CrawlerTriggerRequest(BaseModel):
    """크롤러 수동 실행 요청 스키마."""

    # 수집 대상 출처
    source: str

    # 검색 키워드 (옵션)
    query: str | None = None

    # 수집 기간 시작일
    date_from: date | None = None

    # 수집 기간 종료일
    date_to: date | None = None


class ScheduleJobRequest(BaseModel):
    """스케줄 작업 생성/수정 요청 스키마."""

    # 수집 대상 출처
    source: str

    # cron 표현식 (예: "0 */6 * * *")
    cron_expression: str

    # 검색 키워드 (옵션)
    query: str | None = None

    # 스케줄 활성화 여부
    enabled: bool = True
