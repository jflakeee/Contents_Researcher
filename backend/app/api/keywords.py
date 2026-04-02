"""
키워드 API 라우터.
키워드 순위 및 시계열 트렌드 엔드포인트를 제공한다.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.trend_service import TrendService

router = APIRouter(prefix="/api/v1/keywords", tags=["keywords"])

# === 출처별 통계 (프론트엔드 대시보드에서 사용) ===
# /api/v1/sources/stats 경로지만 같은 라우터에서 제공
sources_router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@sources_router.get("/stats")
async def get_source_stats(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """출처별 수집 통계를 반환한다."""
    return await TrendService.get_source_stats(db)


@router.get("/top")
async def get_top_keywords(
    period: str = Query(default="7d", description="기간 (1d, 7d, 30d, 90d)"),
    source: str | None = Query(default=None, description="출처 필터"),
    limit: int = Query(default=20, ge=1, le=100, description="최대 반환 건수"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """지정 기간 내 인기 키워드 순위를 반환한다."""
    return await TrendService.get_top_keywords(db, period=period, source=source, limit=limit)


@router.get("/trend")
async def get_keyword_trend(
    keyword: str = Query(description="조회할 키워드"),
    period: str = Query(default="30d", description="기간 (7d, 30d, 90d)"),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """특정 키워드의 일별 시계열 데이터를 반환한다."""
    return await TrendService.get_keyword_trend(db, keyword=keyword, period=period)
