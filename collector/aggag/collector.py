"""
issuelink.co.kr 수집기

httpx로 이슈링크 커뮨니티 목록 페이지를 수집한다.
(Cloudflare 차단 없음, httpx로 충분)
목록 페이지에서 제목/출처/댓글수를 추출하여 DB에 저장.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem
from collector.core.base import BaseCollector
from collector.aggag.parser import parse_post_list

logger = logging.getLogger(__name__)

# issuelink 기본 URL
BASE_URL = "https://www.issuelink.co.kr"

# 목록 페이지 URL 패턴
LIST_URL = "/community/listview/all/{hours}/adj/_self/blank/blank/blank"

# 요청 간 딜레이 (초)
REQUEST_DELAY = 1.0

# 수집할 최대 페이지 수
MAX_PAGES = 1

# 수집 시간 범위 (시간 단위): 3=3시간, 24=24시간
HOURS_RANGE = 24

# HTTP 요청 타임아웃 (초)
REQUEST_TIMEOUT = 15.0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class AggagCollector(BaseCollector):
    """issuelink.co.kr 수집기

    커뮤니티 인기 게시글 목록을 수집한다.
    다양한 커뮤니티(더쿠, 에펨, 보배, 인벤, 뽐뿌 등)의
    인기 게시글을 한 번에 수집할 수 있다.
    """

    source_name = SOURCE_AGGAG

    def __init__(
        self,
        base_url: str = BASE_URL,
        request_delay: float = REQUEST_DELAY,
        max_pages: int = MAX_PAGES,
        hours_range: int = HOURS_RANGE,
    ):
        self._base_url = base_url
        self._request_delay = request_delay
        self._max_pages = max_pages
        self._hours_range = hours_range

    def _create_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 생성"""
        return httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
            follow_redirects=True,
        )

    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """issuelink 커뮤니티 인기 게시글 수집

        Args:
            query: 검색 키워드 (미사용, 목록 기반 수집)
            date_from: 수집 시작일
            date_to: 수집 종료일

        Returns:
            수집된 ContentItem 목록
        """
        all_items: List[ContentItem] = []

        async with self._create_client() as client:
            for page_num in range(1, self._max_pages + 1):
                try:
                    # 목록 URL 구성 (시간 범위 지정)
                    list_path = LIST_URL.format(hours=self._hours_range)
                    list_url = f"{self._base_url}{list_path}"

                    logger.info("[issuelink] 목록 수집: %s", list_url)
                    response = await client.get(list_url)
                    response.raise_for_status()

                    # 목록에서 ContentItem 직접 생성
                    items = parse_post_list(response.text, self._base_url)
                    all_items.extend(items)

                    logger.info("[issuelink] 페이지 %d: %d건", page_num, len(items))

                    if not items:
                        break

                    await asyncio.sleep(self._request_delay)

                except Exception as e:
                    logger.warning("[issuelink] 페이지 %d 수집 실패: %s", page_num, e)
                    break

        logger.info("[issuelink] 수집 완료: %d건", len(all_items))
        return all_items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """댓글 수집 (issuelink 목록에서는 댓글 본문 불가, 빈 목록 반환)"""
        return []
