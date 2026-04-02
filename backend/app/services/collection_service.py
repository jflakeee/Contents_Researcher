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
        query: 검색 키워드 (빈 문자열이면 최신 게시글)
        date_from: 수집 시작일
        date_to: 수집 종료일

    Returns:
        {"source": str, "collected": int, "saved": int, "error": str|None}
    """
    result = {"source": source, "collected": 0, "saved": 0, "error": None}

    try:
        # 1단계: 수집기 생성 및 수집 실행
        collector = _create_collector(source)
        if collector is None:
            result["error"] = f"지원하지 않는 출처: {source}"
            return result

        logger.info("[%s] 수집 시작: query='%s'", source, query)
        collection_result = await collector.run(query, date_from, date_to)

        if not collection_result.success:
            result["error"] = collection_result.error_message
            return result

        # collector.run()은 items를 반환하지 않으므로 직접 수집
        items = await collector.collect(query, date_from, date_to)
        result["collected"] = len(items)

        if not items:
            logger.info("[%s] 수집 결과 0건", source)
            return result

        # 댓글 수집 + 해시 생성
        for item in items:
            try:
                comments = await collector.collect_comments(item.source_id)
                item.comments = comments
                item.comment_count = len(comments)
                hash_text = item.title + (item.body or "")
                item.body_hash = collector.compute_body_hash(hash_text)
            except Exception as e:
                logger.warning("[%s] 댓글 수집 실패 (%s): %s", source, item.source_id, e)

        # 2단계: NLP 분석
        logger.info("[%s] NLP 분석 시작: %d건", source, len(items))
        try:
            from analyzer.pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline()
            await pipeline.analyze(items)
        except Exception as e:
            logger.warning("[%s] NLP 분석 실패 (분석 없이 저장 진행): %s", source, e)

        # 3단계: DB 저장
        saved_count = await _save_to_db(items)
        result["saved"] = saved_count
        logger.info("[%s] 수집 완료: 수집=%d, 저장=%d", source, len(items), saved_count)

        # 4단계: 수집 이력 기록
        await _record_job(source, len(items), saved_count)

    except Exception as e:
        result["error"] = str(e)
        logger.error("[%s] 수집 파이프라인 오류: %s", source, e)
        await _record_job(source, 0, 0, error=str(e))

    return result


def _create_collector(source: str):
    """출처별 수집기 인스턴스 생성"""
    try:
        if source == SOURCE_YOUTUBE:
            from collector.youtube.collector import YouTubeCollector
            from app.config import get_settings
            settings = get_settings()
            if not settings.YOUTUBE_API_KEY:
                logger.warning("YouTube API 키가 설정되지 않았습니다")
                return None
            return YouTubeCollector(api_key=settings.YOUTUBE_API_KEY)

        elif source == SOURCE_AGGAG:
            from collector.aggag.collector import AggagCollector
            return AggagCollector()

        elif source == SOURCE_INSTAGRAM:
            from collector.instagram.collector import InstagramCollector
            return InstagramCollector()

        else:
            logger.warning("지원하지 않는 출처: %s", source)
            return None
    except ImportError as e:
        logger.error("수집기 모듈 로드 실패 (%s): %s", source, e)
        return None


async def _save_to_db(items: list[ContentItem]) -> int:
    """수집/분석된 컨텐츠를 DB에 저장

    Args:
        items: 분석 완료된 ContentItem 목록

    Returns:
        저장된 건수
    """
    from app.db.session import async_session_factory
    from app.models.content import Content
    from app.models.comment import Comment

    if async_session_factory is None:
        logger.error("DB 세션 팩토리가 초기화되지 않았습니다")
        return 0

    saved = 0
    async with async_session_factory() as session:
        for item in items:
            try:
                # 중복 체크 (body_hash)
                if item.body_hash:
                    from sqlalchemy import select
                    existing = await session.execute(
                        select(Content.id).where(Content.body_hash == item.body_hash)
                    )
                    if existing.scalar_one_or_none() is not None:
                        logger.debug("중복 건너뜀: %s", item.title[:30])
                        continue

                # Content 레코드 생성
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

                # Comment 레코드 생성
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
                logger.warning("DB 저장 실패 (%s): %s", item.title[:30], e)

        await session.commit()

    return saved


async def _record_job(
    source: str,
    collected: int,
    saved: int,
    error: Optional[str] = None,
) -> None:
    """수집 작업 이력을 DB에 기록"""
    from app.db.session import async_session_factory
    from app.models.keyword import CollectionJob

    if async_session_factory is None:
        return

    try:
        async with async_session_factory() as session:
            job = CollectionJob(
                source=source,
                status="failed" if error else "completed",
                started_at=datetime.now(tz=timezone.utc),
                completed_at=datetime.now(tz=timezone.utc),
                items_count=saved,
                error_message=error,
                metadata_={"collected": collected, "saved": saved},
            )
            session.add(job)
            await session.commit()
    except Exception as e:
        logger.warning("수집 이력 기록 실패: %s", e)
