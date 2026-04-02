"""
키워드 트렌드 서비스.
키워드 순위, 시계열 추이, 출처별 통계를 제공한다.
"""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.keyword import KeywordTrend


class TrendService:
    """키워드 트렌드 분석 기능을 제공한다."""

    @staticmethod
    async def get_top_keywords(
        db: AsyncSession,
        period: str = "7d",
        source: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """지정 기간 내 가장 많이 등장한 키워드 순위를 반환한다."""

        # 기간 계산
        period_map = {
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        delta = period_map.get(period, timedelta(days=7))
        since = date.today() - delta

        # 키워드별 등장 횟수 합산 쿼리
        query = (
            select(
                KeywordTrend.keyword,
                func.sum(KeywordTrend.count).label("total_count"),
                func.avg(KeywordTrend.avg_sentiment).label("avg_sentiment"),
            )
            .where(KeywordTrend.date >= since)
            .group_by(KeywordTrend.keyword)
            .order_by(func.sum(KeywordTrend.count).desc())
            .limit(limit)
        )

        # 출처 필터
        if source:
            query = query.where(KeywordTrend.source == source)

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "keyword": row.keyword,
                "total_count": row.total_count,
                "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else None,
            }
            for row in rows
        ]

    @staticmethod
    async def get_keyword_trend(
        db: AsyncSession,
        keyword: str,
        period: str = "30d",
    ) -> list[dict]:
        """특정 키워드의 일별 시계열 데이터를 반환한다."""

        # 기간 계산
        period_map = {
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
            "90d": timedelta(days=90),
        }
        delta = period_map.get(period, timedelta(days=30))
        since = date.today() - delta

        # 날짜별 합산 쿼리
        query = (
            select(
                KeywordTrend.date,
                func.sum(KeywordTrend.count).label("count"),
                func.avg(KeywordTrend.avg_sentiment).label("avg_sentiment"),
            )
            .where(KeywordTrend.keyword == keyword, KeywordTrend.date >= since)
            .group_by(KeywordTrend.date)
            .order_by(KeywordTrend.date.asc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "date": row.date.isoformat(),
                "count": row.count,
                "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else None,
            }
            for row in rows
        ]

    @staticmethod
    async def get_source_stats(db: AsyncSession) -> list[dict]:
        """출처별 콘텐츠 통계를 반환한다."""

        query = (
            select(
                Content.source,
                func.count(Content.id).label("content_count"),
                func.avg(Content.sentiment_score).label("avg_sentiment"),
                func.max(Content.collected_at).label("last_collected_at"),
            )
            .group_by(Content.source)
            .order_by(func.count(Content.id).desc())
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "source": row.source,
                "content_count": row.content_count,
                "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else None,
                "last_collected_at": row.last_collected_at.isoformat() if row.last_collected_at else None,
            }
            for row in rows
        ]
