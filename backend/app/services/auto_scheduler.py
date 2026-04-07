"""
자동 연속 수집 스케줄러

모든 사이트에서 최근 게시물부터 계속 수집한다.
100건 수집 후 10분 휴식, 이를 무한 반복.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

from app.config import get_settings

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import httpx
from shared.constants import SOURCE_AGGAG, SOURCE_YOUTUBE, SOURCE_INSTAGRAM

logger = logging.getLogger(__name__)

# 서버 시작 후 첫 수집까지 대기 시간 (초)
_INITIAL_DELAY = 15

# 한 사이클 목표 수집 건수
_TARGET_PER_CYCLE = 100

# 휴식 시간 (초) — 10분
_REST_INTERVAL = 10 * 60

# issuelink 수집 설정
_ISSUELINK_BASE = "https://www.issuelink.co.kr"
_ISSUELINK_COMMUNITIES = [
    "all", "theqoo", "fmkorea", "ruliweb", "ppomppu",
    "todayhumor", "instiz", "bobae", "inven", "slr", "clien",
]
_ISSUELINK_HOURS = [3, 6, 12, 24]  # 최근 시간대부터 순회
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


async def _continuous_collection_loop() -> None:
    """모든 사이트에서 연속 수집하는 메인 루프

    1사이클 = issuelink(커뮤니티) + Instagram 수집
    100건 수집 후 10분 휴식, 무한 반복.
    """
    await asyncio.sleep(_INITIAL_DELAY)
    logger.info("[연속수집] 시작 — 100건 수집 후 10분 휴식 반복")

    cycle = 0
    while True:
        cycle += 1
        logger.info("[연속수집] === 사이클 %d 시작 ===", cycle)

        total_collected = 0
        total_saved = 0

        try:
            # 1단계: issuelink (커뮤니티 인기 게시글)
            c, s = await _collect_issuelink()
            total_collected += c
            total_saved += s

            # 2단계: Instagram — 추후 적용 예정
            # c, s = await _collect_instagram()
            # total_collected += c
            # total_saved += s

            # 3단계: YouTube (API 키가 있을 때만)
            settings = get_settings()
            if settings.YOUTUBE_API_KEY:
                c, s = await _collect_youtube()
                total_collected += c
                total_saved += s

        except Exception as e:
            logger.error("[연속수집] 사이클 %d 오류: %s", cycle, e)

        logger.info(
            "[연속수집] === 사이클 %d 완료: 수집=%d, 저장=%d ===",
            cycle, total_collected, total_saved,
        )

        # 10분 휴식
        logger.info("[연속수집] 10분 휴식 후 다음 사이클 시작...")
        await asyncio.sleep(_REST_INTERVAL)


async def _collect_issuelink() -> tuple[int, int]:
    """issuelink.co.kr 커뮤니티 수집

    커뮤니티별 × 시간대별 조합으로 최근 게시물부터 수집.
    중복 제거하여 DB에 저장.

    Returns:
        (수집건수, 저장건수)
    """
    from collector.aggag.parser import parse_post_list
    from app.services.collection_service import _save_to_db, _create_job, _update_job

    job_id = await _create_job(SOURCE_AGGAG, "continuous")
    all_items = []
    seen_ids = set()

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": _USER_AGENT, "Accept-Language": "ko-KR"},
            follow_redirects=True,
        ) as client:

            for community in _ISSUELINK_COMMUNITIES:
                for hours in _ISSUELINK_HOURS:
                    try:
                        if community == "all":
                            url = f"{_ISSUELINK_BASE}/community/listview/all/{hours}/adj/_self/blank/blank/blank"
                        else:
                            url = f"{_ISSUELINK_BASE}/community/filterview/{community}/{hours}/adj/_self/blank/blank/blank"

                        response = await client.get(url)
                        if response.status_code != 200:
                            continue

                        items = parse_post_list(response.text, _ISSUELINK_BASE)
                        new = 0
                        for item in items:
                            if item.source_id not in seen_ids:
                                seen_ids.add(item.source_id)
                                all_items.append(item)
                                new += 1

                        if new > 0:
                            logger.info("[issuelink] %s/%dh: +%d건", community, hours, new)

                        await asyncio.sleep(0.5)

                    except Exception as e:
                        logger.warning("[issuelink] %s/%dh 실패: %s", community, hours, e)

        logger.info("[issuelink] 수집 완료: %d건", len(all_items))

        # NLP 분석
        try:
            from analyzer.pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline()
            for i in range(0, len(all_items), 50):
                await pipeline.analyze(all_items[i:i+50])
        except Exception as e:
            logger.warning("[issuelink] NLP 분석 실패: %s", e)

        # DB 저장
        saved = await _save_to_db(all_items)
        await _update_job(job_id, status="completed", items_count=saved)
        return len(all_items), saved

    except Exception as e:
        logger.error("[issuelink] 수집 오류: %s", e)
        await _update_job(job_id, status="failed", error=str(e))
        return 0, 0


async def _collect_instagram() -> tuple[int, int]:
    """Instagram 수집 (Playwright)

    Returns:
        (수집건수, 저장건수)
    """
    from app.services.collection_service import run_collection

    try:
        result = await asyncio.wait_for(
            run_collection(source=SOURCE_INSTAGRAM, query=""),
            timeout=120.0,
        )
        return result["collected"], result["saved"]
    except asyncio.TimeoutError:
        logger.warning("[Instagram] 수집 타임아웃")
        return 0, 0
    except Exception as e:
        logger.warning("[Instagram] 수집 오류: %s", e)
        return 0, 0


_YOUTUBE_QUERIES = [
    "한국 트렌드", "인기 영상", "이슈 뉴스",
    "리뷰 추천", "꿀팁 정보", "핫이슈 화제",
    "먹방 맛집", "IT 기술", "경제 투자",
    "엔터테인먼트 연예",
]
_youtube_query_idx = 0


async def _collect_youtube() -> tuple[int, int]:
    """YouTube 수집 (API 키 필요)

    매 사이클마다 다른 검색어를 순환하여 다양한 컨텐츠를 수집.
    timeout 발생 시 진행 중인 job을 failed로 마킹한다.

    Returns:
        (수집건수, 저장건수)
    """
    global _youtube_query_idx
    from app.services.collection_service import run_collection

    query = _YOUTUBE_QUERIES[_youtube_query_idx % len(_YOUTUBE_QUERIES)]
    _youtube_query_idx += 1
    logger.info("[YouTube] 수집 키워드: '%s'", query)

    try:
        # YouTube는 댓글 + NLP 분석 시간이 길어 300초로 늘림
        result = await asyncio.wait_for(
            run_collection(source=SOURCE_YOUTUBE, query=query),
            timeout=300.0,
        )
        return result["collected"], result["saved"]
    except asyncio.TimeoutError:
        logger.warning("[YouTube] 수집 타임아웃")
        await _mark_running_jobs_failed(SOURCE_YOUTUBE, "timeout (300s)")
        return 0, 0
    except Exception as e:
        logger.warning("[YouTube] 수집 오류: %s", e)
        await _mark_running_jobs_failed(SOURCE_YOUTUBE, str(e))
        return 0, 0


async def _mark_running_jobs_failed(source: str, reason: str) -> None:
    """해당 출처의 running 상태 job을 모두 failed로 마킹한다."""
    try:
        from app.db.session import async_session_factory
        from app.models.keyword import CollectionJob
        from sqlalchemy import update
        from datetime import datetime, timezone

        if async_session_factory is None:
            return

        async with async_session_factory() as session:
            await session.execute(
                update(CollectionJob)
                .where(CollectionJob.source == source)
                .where(CollectionJob.status == "running")
                .values(
                    status="failed",
                    error_message=reason,
                    completed_at=datetime.now(tz=timezone.utc),
                )
            )
            await session.commit()
    except Exception as e:
        logger.warning("[%s] running job 마킹 실패: %s", source, e)


def start_auto_scheduler() -> None:
    """연속 수집 스케줄러를 시작한다."""
    asyncio.create_task(
        _continuous_collection_loop(),
        name="collector-continuous",
    )
    logger.info("[연속수집] 스케줄러 등록 완료 (100건 수집 → 10분 휴식 → 반복)")


def stop_auto_scheduler() -> None:
    """수집 태스크를 취소한다."""
    cancelled = 0
    for task in asyncio.all_tasks():
        if task.get_name().startswith("collector-"):
            task.cancel()
            cancelled += 1
    logger.info("[연속수집] 스케줄러 종료 (%d개 태스크 취소)", cancelled)
