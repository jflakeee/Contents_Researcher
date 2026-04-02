"""
aggag.com 수집기

Playwright를 사용하여 aggag.com의 전체 게시판에서
게시글과 댓글을 스크래핑한다.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem
from collector.core.base import BaseCollector
from collector.aggag.parser import parse_post_list, parse_post_detail, parse_comments

logger = logging.getLogger(__name__)

# aggag.com 기본 URL
BASE_URL = "https://aggag.com"

# 요청 간 딜레이 (초) — rate limiting
REQUEST_DELAY = 2.0

# 한 번에 수집할 최대 페이지 수
MAX_PAGES = 10

# 페이지당 최대 게시글 수
MAX_POSTS_PER_PAGE = 30


class AggagCollector(BaseCollector):
    """aggag.com 수집기

    Playwright로 동적 페이지를 렌더링하여 게시글과 댓글을 수집한다.
    전체 게시판을 대상으로 수집하며, rate limiting을 적용한다.
    """

    source_name = SOURCE_AGGAG

    def __init__(
        self,
        base_url: str = BASE_URL,
        request_delay: float = REQUEST_DELAY,
        max_pages: int = MAX_PAGES,
        headless: bool = True,
    ):
        """초기화

        Args:
            base_url: aggag.com 기본 URL
            request_delay: 요청 간 딜레이 (초)
            max_pages: 최대 수집 페이지 수
            headless: 브라우저 헤드리스 모드 여부
        """
        self._base_url = base_url
        self._request_delay = request_delay
        self._max_pages = max_pages
        self._headless = headless
        self._browser = None
        self._context = None

    async def _ensure_browser(self):
        """Playwright 브라우저 초기화 (지연 초기화)"""
        if self._browser is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless
            )
            self._context = await self._browser.new_context(
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            logger.info("aggag 수집기: Playwright 브라우저 초기화 완료")

    async def _close_browser(self):
        """브라우저 종료"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if hasattr(self, "_playwright") and self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """aggag.com 게시글 수집

        전체 게시판에서 최신 게시글을 수집한다.
        query 파라미터가 있으면 검색, 없으면 최신 목록에서 수집.

        Args:
            query: 검색 키워드 (빈 문자열이면 최신 목록)
            date_from: 수집 시작일 (참고용, 서버사이드 필터 제한적)
            date_to: 수집 종료일

        Returns:
            수집된 ContentItem 목록
        """
        await self._ensure_browser()
        items: List[ContentItem] = []

        try:
            page = await self._context.new_page()

            # 게시글 목록 수집 (페이지네이션)
            for page_num in range(1, self._max_pages + 1):
                # 검색 또는 최신 목록 URL 구성
                if query:
                    list_url = f"{self._base_url}/search?q={query}&page={page_num}"
                else:
                    list_url = f"{self._base_url}?page={page_num}"

                logger.info("aggag 목록 수집: %s", list_url)

                await page.goto(list_url, wait_until="networkidle")
                html = await page.content()

                # 게시글 목록 파싱
                post_list = parse_post_list(html, self._base_url)
                if not post_list:
                    logger.info("aggag 페이지 %d: 게시글 없음, 수집 종료", page_num)
                    break

                # 각 게시글 상세 수집
                for post_info in post_list:
                    try:
                        await asyncio.sleep(self._request_delay)
                        await page.goto(post_info["url"], wait_until="networkidle")
                        detail_html = await page.content()

                        # 상세 페이지 파싱
                        content_item = parse_post_detail(
                            detail_html,
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

            await page.close()

        except Exception as e:
            logger.error("aggag 수집 중 오류: %s", str(e))
        finally:
            await self._close_browser()

        logger.info("aggag 수집 완료: %d건", len(items))
        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """게시글 댓글 수집

        collect() 과정에서 이미 댓글을 파싱하므로,
        별도 호출 시에는 해당 게시글 페이지를 다시 방문하여 댓글을 추출한다.

        Args:
            content_id: 게시글 ID 또는 URL

        Returns:
            Comment 목록
        """
        await self._ensure_browser()
        comments: List[Comment] = []

        try:
            page = await self._context.new_page()

            # content_id가 URL인 경우와 ID인 경우 모두 처리
            if content_id.startswith("http"):
                url = content_id
            else:
                url = f"{self._base_url}/post/{content_id}"

            await page.goto(url, wait_until="networkidle")
            html = await page.content()
            comments = parse_comments(html)

            await page.close()

        except Exception as e:
            logger.warning(
                "aggag 댓글 수집 실패 (content_id=%s): %s", content_id, str(e)
            )
        finally:
            await self._close_browser()

        return comments
