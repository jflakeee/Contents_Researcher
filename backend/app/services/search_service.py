"""
콘텐츠 검색 서비스.
DB 쿼리 로직을 캡슐화하여 API 라우터에서 호출한다.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content
from app.schemas.content import (
    ContentDetail,
    ContentSummary,
    PaginatedResponse,
)
from app.schemas.search import SearchRequest

# 정렬 가능한 컬럼 화이트리스트
_SORTABLE_COLUMNS = {
    "collected_at": Content.collected_at,
    "importance_score": Content.importance_score,
    "comment_count": Content.comment_count,
    "like_count": Content.like_count,
    "view_count": Content.view_count,
    "sentiment_score": Content.sentiment_score,
}


class SearchService:
    """콘텐츠 검색, 상세 조회, 트렌딩 기능을 제공한다."""

    @staticmethod
    async def search(
        db: AsyncSession, request: SearchRequest
    ) -> PaginatedResponse[ContentSummary]:
        """검색 조건에 맞는 콘텐츠 목록을 페이지네이션하여 반환한다."""

        # 기본 쿼리 구성
        base_query = select(Content)
        count_query = select(func.count(Content.id))

        # 필터 조건 조합
        filters = []

        # 키워드 검색 (제목 또는 본문에서 ILIKE)
        if request.query:
            keyword_filter = Content.title.like(f"%{request.query}%") | Content.body.like(
                f"%{request.query}%",
            )
            filters.append(keyword_filter)

        # 출처 필터
        if request.sources:
            filters.append(Content.source.in_(request.sources))

        # 감성 필터
        if request.sentiment:
            filters.append(Content.sentiment == request.sentiment)

        # 시작일 필터
        if request.date_from:
            filters.append(
                Content.collected_at >= datetime.combine(
                    request.date_from,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                )
            )

        # 종료일 필터
        if request.date_to:
            filters.append(
                Content.collected_at <= datetime.combine(
                    request.date_to,
                    datetime.max.time(),
                    tzinfo=timezone.utc,
                )
            )

        # 모든 필터 적용
        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        # 총 건수 조회
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 정렬 적용
        sort_column = _SORTABLE_COLUMNS.get(request.sort_by, Content.collected_at)
        if request.sort_order == "asc":
            base_query = base_query.order_by(sort_column.asc())
        else:
            base_query = base_query.order_by(sort_column.desc())

        # 페이지네이션 적용
        offset = (request.page - 1) * request.page_size
        base_query = base_query.offset(offset).limit(request.page_size)

        # 쿼리 실행
        result = await db.execute(base_query)
        contents = result.scalars().all()

        # 응답 생성
        items = [ContentSummary.model_validate(c) for c in contents]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=request.page,
            page_size=request.page_size,
        )

    @staticmethod
    async def get_detail(db: AsyncSession, content_id: int) -> ContentDetail | None:
        """콘텐츠 ID로 상세 정보를 조회한다. 댓글을 함께 로드한다."""
        query = (
            select(Content)
            .where(Content.id == content_id)
            .options(selectinload(Content.comments))
        )
        result = await db.execute(query)
        content = result.scalar_one_or_none()
        if content is None:
            return None
        return ContentDetail.model_validate(content)

    @staticmethod
    async def get_trending(
        db: AsyncSession,
        period: str = "24h",
        source: str | None = None,
        limit: int = 20,
    ) -> list[ContentSummary]:
        """지정 기간 내 중요도 높은 트렌딩 콘텐츠를 반환한다."""

        # 기간 매핑
        period_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "12h": timedelta(hours=12),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = period_map.get(period, timedelta(days=1))
        since = datetime.now(tz=timezone.utc) - delta

        query = select(Content).where(Content.collected_at >= since)

        # 출처 필터
        if source:
            query = query.where(Content.source == source)

        # 중요도 높은 순으로 정렬 (NULL은 뒤로)
        query = query.order_by(Content.importance_score.desc().nulls_last()).limit(limit)

        result = await db.execute(query)
        contents = result.scalars().all()
        return [ContentSummary.model_validate(c) for c in contents]
