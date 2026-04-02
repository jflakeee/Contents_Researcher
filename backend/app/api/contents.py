"""
콘텐츠 API 라우터.
콘텐츠 검색, 상세 조회, 트렌딩, 댓글 조회 엔드포인트를 제공한다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.comment import Comment
from app.models.content import Content
from app.schemas.content import (
    CommentSchema,
    ContentDetail,
    ContentSummary,
    PaginatedResponse,
)
from app.schemas.search import SearchRequest
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/v1/contents", tags=["contents"])


@router.get("", response_model=PaginatedResponse[ContentSummary])
async def list_contents(
    query: str | None = Query(default=None, description="검색 키워드"),
    sources: str | None = Query(default=None, description="출처 필터 (쉼표 구분)"),
    sentiment: str | None = Query(default=None, description="감성 필터"),
    date_from: str | None = Query(default=None, description="시작일 (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="종료일 (YYYY-MM-DD)"),
    sort_by: str = Query(default="collected_at", description="정렬 기준"),
    sort_order: str = Query(default="desc", description="정렬 순서"),
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    page_size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ContentSummary]:
    """GET 쿼리 파라미터로 콘텐츠를 검색한다. (프론트엔드 호출용)"""
    from datetime import date as date_type
    request = SearchRequest(
        query=query or None,
        sources=sources.split(",") if sources else None,
        sentiment=sentiment or None,
        date_from=date_type.fromisoformat(date_from) if date_from else None,
        date_to=date_type.fromisoformat(date_to) if date_to else None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return await SearchService.search(db, request)


@router.post("/search", response_model=PaginatedResponse[ContentSummary])
async def search_contents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ContentSummary]:
    """POST JSON body로 콘텐츠를 검색한다."""
    return await SearchService.search(db, request)


@router.get("/trending", response_model=list[ContentSummary])
async def get_trending_contents(
    period: str = Query(default="24h", description="기간 (1h, 6h, 12h, 24h, 7d, 30d)"),
    source: str | None = Query(default=None, description="출처 필터"),
    limit: int = Query(default=20, ge=1, le=100, description="최대 반환 건수"),
    db: AsyncSession = Depends(get_db),
) -> list[ContentSummary]:
    """트렌딩 콘텐츠 목록을 반환한다."""
    return await SearchService.get_trending(db, period=period, source=source, limit=limit)


@router.get("/{content_id}", response_model=ContentDetail)
async def get_content_detail(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> ContentDetail:
    """콘텐츠 상세 정보를 반환한다."""
    detail = await SearchService.get_detail(db, content_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")
    return detail


@router.get("/{content_id}/comments", response_model=list[CommentSchema])
async def get_content_comments(
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[CommentSchema]:
    """특정 콘텐츠의 댓글 목록을 반환한다."""

    # 콘텐츠 존재 여부 확인
    content_result = await db.execute(
        select(Content.id).where(Content.id == content_id)
    )
    if content_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="콘텐츠를 찾을 수 없습니다.")

    # 댓글 조회
    query = (
        select(Comment)
        .where(Comment.content_id == content_id)
        .order_by(Comment.like_count.desc(), Comment.collected_at.desc())
    )
    result = await db.execute(query)
    comments = result.scalars().all()
    return [CommentSchema.model_validate(c) for c in comments]
