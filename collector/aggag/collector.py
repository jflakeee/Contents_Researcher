"""
aggag.com 수집기

httpx + BeautifulSoup을 사용하여 aggag.com의 전체 게시판에서
게시글과 댓글을 수집한다.
(Playwright 대신 httpx 사용 — Python 3.14 Windows 호환)
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem
from collector.core.base import BaseCollector
from collector.aggag.parser import parse_post_list, parse_post_detail, parse_comments

logger = logging.getLogger(__name__)

# aagag.com 기본 URL
BASE_URL = "https://aagag.com"

# 요청 간 딜레이 (초) — rate limiting
REQUEST_DELAY = 1.0

# 한 번에 수집할 최대 페이지 수
MAX_PAGES = 1

# 페이지당 상세 수집할 최대 게시글 수
MAX_DETAIL_PER_PAGE = 10

# HTTP 요청 타임아웃 (초)
REQUEST_TIMEOUT = 15.0

# User-Agent 헤더
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class AggagCollector(BaseCollector):
    """aggag.com 수집기

    httpx로 HTTP 요청을 보내고 BeautifulSoup으로 HTML을 파싱하여
    게시글과 댓글을 수집한다.
    전체 게시판을 대상으로 수집하며, rate limiting을 적용한다.
    """

    source_name = SOURCE_AGGAG

    def __init__(
        self,
        base_url: str = BASE_URL,
        request_delay: float = REQUEST_DELAY,
        max_pages: int = MAX_PAGES,
    ):
        """초기화

        Args:
            base_url: aggag.com 기본 URL
            request_delay: 요청 간 딜레이 (초)
            max_pages: 최대 수집 페이지 수
        """
        self._base_url = base_url
        self._request_delay = request_delay
        self._max_pages = max_pages

    def _create_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 생성"""
        return httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            },
            follow_redirects=True,
        )

    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """aggag.com 게시글 수집

        Args:
            query: 검색 키워드 (빈 문자열이면 최신 목록)
            date_from: 수집 시작일
            date_to: 수집 종료일

        Returns:
            수집된 ContentItem 목록
        """
        items: List[ContentItem] = []

        async with self._create_client() as client:
            # 게시글 목록 수집 (페이지네이션)
            for page_num in range(1, self._max_pages + 1):
                try:
                    # 검색 또는 최신 목록 URL 구성
                    if query:
                        list_url = f"{self._base_url}/issue/?search={query}&page={page_num}"
                    else:
                        list_url = f"{self._base_url}/issue/?page={page_num}"

                    logger.info("aggag 목록 수집: %s", list_url)

                    response = await client.get(list_url)
                    response.raise_for_status()
                    html = response.text

                    # 게시글 목록 파싱
                    post_list = parse_post_list(html, self._base_url)
                    if not post_list:
                        logger.info("aggag 페이지 %d: 게시글 없음, 수집 종료", page_num)
                        break

                    # 각 게시글 상세 수집 (최대 MAX_DETAIL_PER_PAGE건)
                    for post_info in post_list[:MAX_DETAIL_PER_PAGE]:
                        try:
                            await asyncio.sleep(self._request_delay)
                            detail_resp = await client.get(post_info["url"])
                            detail_resp.raise_for_status()

                            content_item = parse_post_detail(
                                detail_resp.text,
                                post_info["url"],
                                post_info["source_id"],
                            )
                            items.append(content_item)

                        except Exception as e:
                            logger.warning(
                                "aggag 게시글 수집 실패 (%s): %s",
                                post_info["url"],
                                str(e),
                            )

                    # 페이지 간 딜레이
                    await asyncio.sleep(self._request_delay)

                except Exception as e:
                    logger.warning("aggag 페이지 %d 수집 실패: %s", page_num, str(e))
                    break

        logger.info("aggag 수집 완료: %d건", len(items))
        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """게시글 댓글 수집

        Args:
            content_id: 게시글 ID 또는 URL

        Returns:
            Comment 목록
        """
        # content_id가 URL인 경우와 ID인 경우 모두 처리
        if content_id.startswith("http"):
            url = content_id
        else:
            url = f"{self._base_url}/post/{content_id}"

        try:
            async with self._create_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                return parse_comments(response.text)
        except Exception as e:
            logger.warning("aggag 댓글 수집 실패 (content_id=%s): %s", content_id, str(e))
            return []
