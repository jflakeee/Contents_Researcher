"""
자동 수집 스케줄러

서버 시작 시 백그라운드에서 주기적으로 수집 작업을 실행한다.
APScheduler 대신 asyncio.Task 기반으로 구현하여 외부 의존성 없이 동작.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from shared.constants import (
    SOURCE_YOUTUBE,
    SOURCE_AGGAG,
    SOURCE_INSTAGRAM,
    DEFAULT_SCHEDULES,
)

logger = logging.getLogger(__name__)

# 스케줄러 백그라운드 태스크
_scheduler_task: asyncio.Task | None = None

# 수집 주기 (초 단위) — cron 표현식을 초로 변환한 기본값
_DEFAULT_INTERVALS = {
    SOURCE_YOUTUBE: 6 * 3600,    # 6시간
    SOURCE_AGGAG: 3 * 3600,      # 3시간
    SOURCE_INSTAGRAM: 12 * 3600, # 12시간
}

# 서버 시작 후 첫 수집까지 대기 시간 (초)
_INITIAL_DELAY = 30


async def _collection_loop(source: str, interval: int) -> None:
    """단일 출처의 수집을 반복 실행하는 루프

    Args:
        source: 수집 출처
        interval: 반복 주기 (초)
    """
    # 초기 대기 (서버 완전 기동 후 시작)
    await asyncio.sleep(_INITIAL_DELAY)

    logger.info(
        "[스케줄러] %s 자동 수집 시작 (주기: %d분)",
        source,
        interval // 60,
    )

    while True:
        try:
            from app.services.collection_service import run_collection

            logger.info("[스케줄러] %s 수집 실행 중...", source)

            # 수집 타임아웃 — Playwright 사용 출처는 120초, 나머지 60초
            timeout = 120.0 if source in (SOURCE_INSTAGRAM, SOURCE_AGGAG) else 60.0
            result = await asyncio.wait_for(
                run_collection(source=source, query=""),
                timeout=timeout,
            )

            if result["error"]:
                logger.warning(
                    "[스케줄러] %s 수집 실패: %s",
                    source,
                    result["error"],
                )
            else:
                logger.info(
                    "[스케줄러] %s 수집 완료: 수집=%d, 저장=%d",
                    source,
                    result["collected"],
                    result["saved"],
                )

        except asyncio.TimeoutError:
            logger.warning("[스케줄러] %s 수집 타임아웃 (60초 초과)", source)
        except Exception as e:
            logger.error("[스케줄러] %s 수집 오류: %s", source, e)

        # 다음 수집까지 대기
        logger.info(
            "[스케줄러] %s 다음 수집: %d분 후",
            source,
            interval // 60,
        )
        await asyncio.sleep(interval)


def start_auto_scheduler() -> None:
    """모든 출처의 자동 수집 스케줄러를 시작한다.

    서버 lifespan에서 호출되어 백그라운드 태스크로 실행.
    YouTube는 API 키가 설정된 경우에만 활성화.
    """
    global _scheduler_task
    settings = get_settings()

    tasks = []

    # aggag.com — 항상 활성화
    tasks.append(
        asyncio.create_task(
            _collection_loop(SOURCE_AGGAG, _DEFAULT_INTERVALS[SOURCE_AGGAG]),
            name=f"collector-{SOURCE_AGGAG}",
        )
    )
    logger.info("[스케줄러] aggag.com 수집 등록 (3시간 주기)")

    # YouTube — API 키가 있을 때만
    if settings.YOUTUBE_API_KEY:
        tasks.append(
            asyncio.create_task(
                _collection_loop(SOURCE_YOUTUBE, _DEFAULT_INTERVALS[SOURCE_YOUTUBE]),
                name=f"collector-{SOURCE_YOUTUBE}",
            )
        )
        logger.info("[스케줄러] YouTube 수집 등록 (6시간 주기)")
    else:
        logger.info("[스케줄러] YouTube API 키 미설정 — 수집 비활성화")

    # Instagram — Playwright sync API를 to_thread로 실행
    tasks.append(
        asyncio.create_task(
            _collection_loop(SOURCE_INSTAGRAM, _DEFAULT_INTERVALS[SOURCE_INSTAGRAM]),
            name=f"collector-{SOURCE_INSTAGRAM}",
        )
    )
    logger.info("[스케줄러] Instagram 수집 등록 (12시간 주기, Playwright)")

    logger.info("[스케줄러] 자동 수집 스케줄러 시작 완료 (%d개 출처)", len(tasks))


def stop_auto_scheduler() -> None:
    """모든 수집 태스크를 취소한다."""
    cancelled = 0
    for task in asyncio.all_tasks():
        if task.get_name().startswith("collector-"):
            task.cancel()
            cancelled += 1

    logger.info("[스케줄러] 자동 수집 스케줄러 종료 (%d개 태스크 취소)", cancelled)
