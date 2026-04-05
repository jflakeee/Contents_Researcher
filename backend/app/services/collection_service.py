"""
수집 실행 서비스

수집기 실행 → NLP 분석 → DB 저장 전체 파이프라인을 관리한다.
스케줄러에서 호출되거나 API trigger로 호출된다.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

# 프로젝트 루트를 PYTHONPATH에 추가 (shared, collector, analyzer 접근용)
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.types import ContentItem
from shared.constants import SOURCE_YOUTUBE, SOURCE_AGGAG, SOURCE_INSTAGRAM

logger = logging.getLogger(__name__)


async def run_collection(
    source: str,
    query: str = "",
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> dict:
    """수집 → 분석 → DB 저장 전체 파이프라인 실행

    Args:
        source: 수집 출처 (youtube, aggag, instagram)
        query: 검색 키워드
        date_from: 수집 시작일
        date_to: 수집 종료일

    Returns:
        {"source": str, "collected": int, "saved": int, "job_id": int|None, "error": str|None}
    """
    result = {"source": source, "collected": 0, "saved": 0, "job_id": None, "error": None}

    # 수집 시작 — DB에 running 상태로 job 생성
    job_id = await _create_job(source, query)
    result["job_id"] = job_id

    try:
        # 1단계: 수집기 생성
        collector = _create_collector(source)
        if collector is None:
            result["error"] = f"collector not available: {source} (API key missing or module error)"
            await _update_job(job_id, status="failed", error=result["error"])
            return result

        logger.info("[%s] 수집 시작: query='%s'", source, query)

        # 2단계: 컨텐츠 수집
        items = await collector.collect(query, date_from, date_to)
        result["collected"] = len(items)

        # 수집 건수 실시간 업데이트
        await _update_job(job_id, items_count=len(items))

        if not items:
            logger.info("[%s] 수집 결과 0건", source)
            await _update_job(job_id, status="completed", items_count=0)
            return result

        # 3단계: 댓글 수집 + 해시 생성
        for item in items:
            try:
                comments = await collector.collect_comments(item.source_id)
                item.comments = comments
                item.comment_count = len(comments)
                hash_text = item.title + (item.body or "")
                item.body_hash = collector.compute_body_hash(hash_text)
            except Exception as e:
                logger.warning("[%s] 댓글 수집 실패 (%s): %s", source, item.source_id, e)

        # 4단계: NLP 분석
        logger.info("[%s] NLP 분석 시작: %d건", source, len(items))
        try:
            from analyzer.pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline()
            await pipeline.analyze(items)
        except Exception as e:
            logger.warning("[%s] NLP 분석 실패 (분석 없이 저장 진행): %s", source, e)

        # 5단계: DB 저장
        saved_count = await _save_to_db(items)
        result["saved"] = saved_count

        # 완료 상태 업데이트
        await _update_job(job_id, status="completed", items_count=saved_count)
        logger.info("[%s] 수집 완료: 수집=%d, 저장=%d", source, len(items), saved_count)

    except Exception as e:
        result["error"] = str(e)
        logger.error("[%s] 수집 파이프라인 오류: %s", source, e)
        await _update_job(job_id, status="failed", error=str(e))

    return result


async def _create_job(source: str, query: str = "") -> Optional[int]:
    """수집 작업을 running 상태로 DB에 생성하고 ID를 반환"""
    from app.db.session import async_session_factory
    from app.models.keyword import CollectionJob

    if async_session_factory is None:
        return None

    try:
        async with async_session_factory() as session:
            job = CollectionJob(
                source=source,
                status="running",
                started_at=datetime.now(tz=timezone.utc),
                items_count=0,
                metadata_={"query": query},
            )
            session.add(job)
            await session.flush()
            job_id = job.id
            await session.commit()
            return job_id
    except Exception as e:
        logger.warning("수집 job 생성 실패: %s", e)
        return None


async def _update_job(
    job_id: Optional[int],
    status: Optional[str] = None,
    items_count: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """수집 작업 상태를 실시간 업데이트"""
    if job_id is None:
        return

    from app.db.session import async_session_factory
    from app.models.keyword import CollectionJob
    from sqlalchemy import update

    if async_session_factory is None:
        return

    try:
        values = {}
        if status is not None:
            values["status"] = status
        if items_count is not None:
            values["items_count"] = items_count
        if error is not None:
            values["error_message"] = error
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.now(tz=timezone.utc)

        if values:
            async with async_session_factory() as session:
                await session.execute(
                    update(CollectionJob)
                    .where(CollectionJob.id == job_id)
                    .values(**values)
                )
                await session.commit()
    except Exception as e:
        logger.warning("수집 job 업데이트 실패 (id=%s): %s", job_id, e)


def _create_collector(source: str):
    """출처별 수집기 인스턴스 생성"""
    try:
        if source == SOURCE_YOUTUBE:
            from collector.youtube.collector import YouTubeCollector
            from app.config import get_settings
            settings = get_settings()
            if not settings.YOUTUBE_API_KEY:
                logger.warning("YouTube API key not configured")
                return None
            return YouTubeCollector(api_key=settings.YOUTUBE_API_KEY)

        elif source == SOURCE_AGGAG:
            from collector.aggag.collector import AggagCollector
            return AggagCollector()

        elif source == SOURCE_INSTAGRAM:
            from collector.instagram.collector import InstagramCollector
            return InstagramCollector()

        else:
            logger.warning("unsupported source: %s", source)
            return None
    except ImportError as e:
        logger.error("collector module load failed (%s): %s", source, e)
        return None


async def _save_to_db(items: list[ContentItem]) -> int:
    """수집/분석된 컨텐츠를 DB에 저장"""
    from app.db.session import async_session_factory
    from app.models.content import Content
    from app.models.comment import Comment

    if async_session_factory is None:
        logger.error("DB session factory not initialized")
        return 0

    saved = 0
    async with async_session_factory() as session:
        for item in items:
            try:
                from sqlalchemy import select

                # 중복 체크 1: source_url 기준
                url_exists = await session.execute(
                    select(Content.id).where(Content.source_url == item.source_url)
                )
                if url_exists.scalar_one_or_none() is not None:
                    continue

                # 중복 체크 2: body_hash 기준 (본문이 있는 경우)
                if item.body_hash:
                    hash_exists = await session.execute(
                        select(Content.id).where(Content.body_hash == item.body_hash)
                    )
                    if hash_exists.scalar_one_or_none() is not None:
                        continue

                content = Content(
                    collected_at=item.collected_at,
                    source=item.source,
                    source_url=item.source_url,
                    title=item.title,
                    body=item.body,
                    body_hash=item.body_hash,
                    keywords=item.keywords,
                    sentiment=item.sentiment,
                    sentiment_score=item.sentiment_score,
                    importance_score=item.importance_score,
                    comment_count=item.comment_count,
                    like_count=item.like_count,
                    view_count=item.view_count,
                    metadata_=item.metadata,
                )
                session.add(content)
                await session.flush()

                for c in item.comments:
                    comment = Comment(
                        content_id=content.id,
                        collected_at=item.collected_at,
                        author=c.author,
                        body=c.body,
                        sentiment=c.sentiment,
                        sentiment_score=c.sentiment_score,
                        like_count=c.like_count,
                    )
                    session.add(comment)

                saved += 1

            except Exception as e:
                logger.warning("DB save failed (%s): %s", item.title[:30], e)

        await session.commit()

    return saved
