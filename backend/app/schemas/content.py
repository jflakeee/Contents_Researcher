"""
콘텐츠 관련 Pydantic v2 스키마 정의.
API 응답 직렬화 및 요청 유효성 검사에 사용한다.
"""

import math
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class CommentSchema(BaseModel):
    """댓글 응답 스키마."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    author: str | None = None
    body: str
    sentiment: str | None = None
    sentiment_score: float | None = None
    like_count: int = 0


class ContentSummary(BaseModel):
    """콘텐츠 요약 응답 스키마 (목록 조회용)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_url: str
    title: str
    keywords: list[str] | None = None
    content_type: str | None = None
    sentiment: str | None = None
    sentiment_score: float | None = None
    importance_score: float | None = None
    comment_count: int = 0
    like_count: int = 0
    collected_at: datetime


class ContentDetail(ContentSummary):
    """콘텐츠 상세 응답 스키마 (단건 조회용)."""

    body: str | None = None
    view_count: int = 0
    metadata: dict | None = Field(None, alias="metadata_")
    comments: list[CommentSchema] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedResponse(BaseModel, Generic[T]):
    """페이지네이션 응답 래퍼."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        """총 건수와 페이지 정보로 PaginatedResponse를 생성한다."""
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
