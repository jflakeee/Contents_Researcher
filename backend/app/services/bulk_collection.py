"""
대량 수집 서비스

지정 기간(한달~1주 전)의 게시글을 최대한 수집한다.
issuelink.co.kr의 시간대/커뮤니티별 조합으로 다양한 게시글을 확보.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import httpx
from collector.aggag.parser import parse_post_list
from shared.constants import SOURCE_AGGAG

logger = logging.getLogger(__name__)

BASE_URL = "https://www.issuelink.co.kr"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 수집 대상 커뮤니티
COMMUNITIES = ["all", "theqoo", "fmkorea", "ruliweb", "ppomppu", "todayhumor", "instiz", "bobae", "inven", "slr", "clien"]

# 시간대 (168h=1주 ~ 720h=한달, 24시간 단위로 세분화)
TIME_RANGES = list(range(168, 721, 24))  # 168, 192, 216, ..., 720


async def bulk_collect_and_save() -> dict:
    """한달 전 ~ 1주 전 게시글을 대량 수집하여 DB에 저장

    Returns:
        {"total_collected": int, "total_saved": int, "duplicates_skipped": int}
    """
    from app.services.collection_service import _save_to_db, _create_job, _update_job

    # 수집 작업 생성
    job_id = await _create_job(SOURCE_AGGAG, "bulk: 1month~1week")

    all_items = []
    seen_ids = set()

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR"},
        follow_redirects=True,
    ) as client:

        # 커뮤니티별 × 시간대별 조합으로 수집
        for community in COMMUNITIES:
            for hours in TIME_RANGES:
                try:
                    if community == "all":
                        url = f"{BASE_URL}/community/listview/all/{hours}/adj/_self/blank/blank/blank"
                    else:
                        url = f"{BASE_URL}/community/filterview/{community}/{hours}/adj/_self/blank/blank/blank"

                    response = await client.get(url)
                    if response.status_code != 200:
                        continue

                    items = parse_post_list(response.text, BASE_URL)

                    new_count = 0
                    for item in items:
                        if item.source_id not in seen_ids:
                            seen_ids.add(item.source_id)
                            all_items.append(item)
                            new_count += 1

                    if new_count > 0:
                        logger.info(
                            "[대량수집] %s/%dh: +%d건 (누적 %d건)",
                            community, hours, new_count, len(all_items),
                        )

                    # rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning("[대량수집] %s/%dh 실패: %s", community, hours, e)

        logger.info("[대량수집] 수집 완료: 총 %d건 (중복 제거)", len(all_items))

    # NLP 분석
    try:
        from analyzer.pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline()
        # 배치 분석 (50건씩)
        for i in range(0, len(all_items), 50):
            batch = all_items[i:i+50]
            await pipeline.analyze(batch)
            logger.info("[대량수집] NLP 분석: %d/%d건", min(i+50, len(all_items)), len(all_items))
    except Exception as e:
        logger.warning("[대량수집] NLP 분석 실패: %s", e)

    # DB 저장
    saved = await _save_to_db(all_items)
    duplicates = len(all_items) - saved

    # 작업 완료 업데이트
    await _update_job(job_id, status="completed", items_count=saved)

    result = {
        "total_collected": len(all_items),
        "total_saved": saved,
        "duplicates_skipped": duplicates,
    }
    logger.info("[대량수집] 최종: 수집=%d, 저장=%d, 중복=%d", result["total_collected"], result["total_saved"], result["duplicates_skipped"])
    return result
