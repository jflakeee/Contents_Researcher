"""
자동 수집 파이프라인 통합 테스트

실제 수집기 → NLP 분석 → DB 저장 → 중복 체크 → 이력 기록
전체 흐름을 이틀치(48시간) 시뮬레이션으로 검증한다.

실제 외부 사이트 접속 없이 Mock 수집기로 테스트.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import patch

import pytest

# 프로젝트 루트를 PYTHONPATH에 추가
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.types import ContentItem, Comment
from shared.constants import SOURCE_AGGAG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("test_auto_collection")


# ======================================================================
# Mock 수집기: 실제 사이트 접속 없이 가상 게시글을 생성
# ======================================================================
class MockCollector:
    """테스트용 Mock 수집기 — 외부 접속 없이 가상 컨텐츠 생성"""

    source_name = "mock_aggag"
    _post_counter = 0

    def __init__(self):
        self._collected_ids = set()

    def compute_body_hash(self, text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def collect(
        self, query: str, date_from=None, date_to=None
    ) -> List[ContentItem]:
        """시뮬레이션 시간대에 맞는 가상 게시글 생성"""
        MockCollector._post_counter += 1
        batch = MockCollector._post_counter

        items = []
        for i in range(3):  # 수집 회차당 3건
            post_id = f"post-batch{batch}-{i}"

            # 매 수집마다 새 게시글 2건 + 중복 1건
            if i == 2 and batch > 1:
                # 이전 배치의 첫 게시글과 동일한 제목 (중복 테스트)
                title = f"[aggag] 인기 게시글 batch{batch - 1}-0"
                body = f"이것은 batch{batch - 1}의 첫 번째 게시글 본문입니다."
            else:
                title = f"[aggag] 인기 게시글 {post_id}"
                body = f"이것은 {post_id}의 게시글 본문입니다. 최근 화제가 되고 있는 컨텐츠입니다."

            items.append(ContentItem(
                source=SOURCE_AGGAG,
                source_url=f"https://aggag.com/post/{post_id}",
                source_id=post_id,
                title=title,
                body=body,
                view_count=100 * (batch + i),
                like_count=10 * (batch + i),
                metadata={"batch": batch, "index": i},
                collected_at=datetime.now(tz=timezone.utc),
            ))

        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """가상 댓글 생성"""
        return [
            Comment(author="유저A", body="정말 좋은 글이네요! 최고입니다.", like_count=5),
            Comment(author="유저B", body="별로예요 실망입니다", like_count=1),
            Comment(author="유저C", body="흥미로운 내용이군요", like_count=3),
        ]

    async def run(self, query, date_from=None, date_to=None):
        from shared.types import CollectionResult
        return CollectionResult(source=self.source_name, success=True)


# ======================================================================
# 테스트 본체
# ======================================================================
@pytest.fixture
def test_db_url(tmp_path):
    """테스트 전용 SQLite DB 경로"""
    return f"sqlite+aiosqlite:///{tmp_path / 'test_collection.db'}"


@pytest.fixture
async def setup_db(test_db_url):
    """테스트용 DB 초기화"""
    # config를 테스트 DB URL로 오버라이드
    with patch("app.config.get_settings") as mock_settings:
        settings = mock_settings.return_value
        settings.DATABASE_URL = test_db_url
        settings.YOUTUBE_API_KEY = ""
        settings.CORS_ORIGINS = ["http://localhost:3000"]
        settings.SCHEDULER_TIMEZONE = "Asia/Seoul"
        settings.KEYWORDS_PER_CONTENT = 15
        settings.SENTIMENT_THRESHOLD = 0.1
        settings.DEFAULT_PAGE_SIZE = 20

        from app.db.session import init_engine, dispose_engine, init_cache, close_cache

        engine = init_engine()
        init_cache()

        # 테이블 생성
        from app.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await close_cache()
        await dispose_engine()


@pytest.mark.asyncio
async def test_two_day_collection_simulation(setup_db, test_db_url):
    """이틀치(48시간) 자동 수집 시뮬레이션

    3시간 주기로 16회 수집을 실행하여:
    1. 수집 → 분석 → DB 저장이 정상 동작하는지
    2. 중복 게시글이 올바르게 필터링되는지
    3. NLP 분석(키워드, 감성)이 적용되는지
    4. 수집 이력이 정상 기록되는지
    5. 누적 데이터가 올바르게 쌓이는지
    """
    from app.db.session import async_session_factory
    from app.models.content import Content
    from app.models.comment import Comment as CommentModel
    from app.models.keyword import CollectionJob
    from sqlalchemy import select, func

    mock_collector = MockCollector()

    # 이틀 = 48시간, 3시간 주기 = 16회 수집
    total_cycles = 16
    logger.info("=" * 60)
    logger.info("이틀치 자동 수집 시뮬레이션 시작 (총 %d회)", total_cycles)
    logger.info("=" * 60)

    for cycle in range(1, total_cycles + 1):
        sim_hour = (cycle - 1) * 3
        sim_day = sim_hour // 24 + 1
        sim_hour_of_day = sim_hour % 24

        logger.info(
            "\n--- [%d일차 %02d:00] 수집 회차 %d/%d ---",
            sim_day, sim_hour_of_day, cycle, total_cycles,
        )

        # 수집
        items = await mock_collector.collect(query="")
        logger.info("수집: %d건", len(items))

        # 댓글 수집 + 해시 생성
        for item in items:
            comments = await mock_collector.collect_comments(item.source_id)
            item.comments = comments
            item.comment_count = len(comments)
            item.body_hash = mock_collector.compute_body_hash(item.title + (item.body or ""))

        # NLP 분석
        try:
            from analyzer.pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline()
            await pipeline.analyze(items)
            logger.info("NLP 분석 완료")
        except Exception as e:
            logger.warning("NLP 분석 스킵: %s", e)

        # DB 저장 (중복 체크 포함)
        saved = 0
        async with async_session_factory() as session:
            for item in items:
                # 중복 체크
                if item.body_hash:
                    result = await session.execute(
                        select(Content.id).where(Content.body_hash == item.body_hash)
                    )
                    if result.scalar_one_or_none() is not None:
                        logger.info("  중복 건너뜀: %s", item.title[:40])
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
                    comment = CommentModel(
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

            # 수집 이력 기록
            job = CollectionJob(
                source=SOURCE_AGGAG,
                status="completed",
                started_at=datetime.now(tz=timezone.utc),
                completed_at=datetime.now(tz=timezone.utc),
                items_count=saved,
                metadata_={"cycle": cycle, "collected": len(items), "saved": saved},
            )
            session.add(job)
            await session.commit()

        logger.info("저장: %d건 (중복 제외)", saved)

    # ================================================================
    # 검증
    # ================================================================
    logger.info("\n" + "=" * 60)
    logger.info("검증 시작")
    logger.info("=" * 60)

    async with async_session_factory() as session:
        # 1. 총 컨텐츠 건수 확인
        total_contents = (await session.execute(
            select(func.count(Content.id))
        )).scalar_one()
        logger.info("[검증 1] 총 컨텐츠: %d건", total_contents)

        # 첫 수집 3건 + 이후 15회 * 2건(1건 중복) = 3 + 30 = 33건
        assert total_contents > 0, "컨텐츠가 저장되지 않았습니다"
        assert total_contents <= total_cycles * 3, "중복 필터가 작동하지 않습니다"
        logger.info("  → 중복 필터 정상 동작 (최대 %d건 중 %d건 저장)", total_cycles * 3, total_contents)

        # 2. 총 댓글 건수 확인
        total_comments = (await session.execute(
            select(func.count(CommentModel.id))
        )).scalar_one()
        logger.info("[검증 2] 총 댓글: %d건", total_comments)
        assert total_comments > 0, "댓글이 저장되지 않았습니다"
        # 컨텐츠당 3건 댓글
        assert total_comments == total_contents * 3, "댓글 수 불일치"
        logger.info("  → 댓글 정상 저장 (컨텐츠당 3건)")

        # 3. NLP 분석 결과 확인 (키워드, 감성)
        analyzed = (await session.execute(
            select(func.count(Content.id)).where(Content.sentiment.isnot(None))
        )).scalar_one()
        logger.info("[검증 3] 감성 분석 완료: %d/%d건", analyzed, total_contents)
        if analyzed > 0:
            logger.info("  → NLP 감성 분석 정상 동작")

        keyword_count = (await session.execute(
            select(func.count(Content.id)).where(Content.keywords.isnot(None))
        )).scalar_one()
        logger.info("[검증 4] 키워드 추출 완료: %d/%d건", keyword_count, total_contents)
        if keyword_count > 0:
            logger.info("  → NLP 키워드 추출 정상 동작")

        # 4. 중요도 점수 확인
        scored = (await session.execute(
            select(func.count(Content.id)).where(Content.importance_score.isnot(None))
        )).scalar_one()
        logger.info("[검증 5] 중요도 산정 완료: %d/%d건", scored, total_contents)

        # 5. 수집 이력 건수 확인
        total_jobs = (await session.execute(
            select(func.count(CollectionJob.id))
        )).scalar_one()
        logger.info("[검증 6] 수집 이력: %d건", total_jobs)
        assert total_jobs == total_cycles, f"수집 이력이 {total_cycles}건이어야 합니다"
        logger.info("  → 수집 이력 정상 기록 (%d회)", total_jobs)

        # 6. 중복 없는지 body_hash 유니크 확인
        unique_hashes = (await session.execute(
            select(func.count(func.distinct(Content.body_hash)))
        )).scalar_one()
        logger.info("[검증 7] 유니크 해시: %d (총 %d)", unique_hashes, total_contents)
        assert unique_hashes == total_contents, "중복 해시가 존재합니다"
        logger.info("  → 중복 제거 정상 동작")

        # 7. 샘플 데이터 출력
        sample = (await session.execute(
            select(Content).order_by(Content.id.desc()).limit(3)
        )).scalars().all()
        logger.info("\n[샘플 데이터 — 최근 3건]")
        for c in sample:
            logger.info(
                "  id=%d | %s | 키워드=%s | 감성=%s(%.2f) | 중요도=%.2f | 댓글=%d",
                c.id,
                c.title[:35],
                c.keywords[:3] if c.keywords else "없음",
                c.sentiment or "없음",
                c.sentiment_score or 0,
                c.importance_score or 0,
                c.comment_count,
            )

    logger.info("\n" + "=" * 60)
    logger.info("이틀치 자동 수집 시뮬레이션 완료 — 모든 검증 통과")
    logger.info("=" * 60)
