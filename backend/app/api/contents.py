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


@router.post("/search", response_model=PaginatedResponse[ContentSummary])
async def search_contents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ContentSummary]:
    """검색 조건에 맞는 콘텐츠 목록을 반환한다."""
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
