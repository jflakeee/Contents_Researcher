"""
Instagram 수집기

Playwright를 사용하여 Instagram 공개 프로필과 해시태그에서
게시글과 댓글을 스크래핑한다.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from shared.constants import SOURCE_INSTAGRAM
from shared.types import Comment, ContentItem
from collector.core.base import BaseCollector
from collector.instagram.parser import (
    parse_profile_posts,
    parse_post_detail,
    parse_comments_from_html,
)

logger = logging.getLogger(__name__)

# 요청 간 딜레이 (초) — Instagram rate limiting 대응
REQUEST_DELAY = 3.0

# 수집할 최대 게시글 수
MAX_POSTS = 30


class InstagramCollector(BaseCollector):
    """Instagram 수집기

    Playwright로 Instagram 공개 페이지를 스크래핑하여
    게시글과 댓글을 수집한다.
    """

    source_name = SOURCE_INSTAGRAM

    def __init__(
        self,
        request_delay: float = REQUEST_DELAY,
        max_posts: int = MAX_POSTS,
        headless: bool = True,
    ):
        """초기화

        Args:
            request_delay: 요청 간 딜레이 (초)
            max_posts: 최대 수집 게시글 수
            headless: 브라우저 헤드리스 모드
        """
        self._request_delay = request_delay
        self._max_posts = max_posts
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
            # 모바일 에뮬레이션 (Instagram 모바일 버전이 더 접근하기 쉬움)
            self._context = await self._browser.new_context(
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/16.0 Mobile/15E148 Safari/604.1"
                ),
                viewport={"width": 390, "height": 844},
            )
            logger.info("Instagram 수집기: Playwright 브라우저 초기화 완료")

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
        """Instagram 게시글 수집

        query가 @로 시작하면 프로필 수집, #으로 시작하면 해시태그 수집.

        Args:
            query: 검색 키워드 (@username 또는 #hashtag)
            date_from: 수집 시작일 (참고용)
            date_to: 수집 종료일

        Returns:
            수집된 ContentItem 목록
        """
        await self._ensure_browser()
        items: List[ContentItem] = []

        try:
            page = await self._context.new_page()

            # 프로필 또는 해시태그 URL 결정
            if query.startswith("@"):
                username = query.lstrip("@")
                url = f"https://www.instagram.com/{username}/"
            elif query.startswith("#"):
                hashtag = query.lstrip("#")
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
            else:
                url = f"https://www.instagram.com/explore/tags/{query}/"

            logger.info("Instagram 수집 시작: %s", url)
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(self._request_delay)

            html = await page.content()

            # 게시글 목록 추출
            post_list = parse_profile_posts(html, url)
            post_list = post_list[: self._max_posts]

            # 각 게시글 상세 수집
            for post_info in post_list:
                try:
                    await asyncio.sleep(self._request_delay)
                    await page.goto(post_info["url"], wait_until="networkidle")
                    detail_html = await page.content()

                    content_item = parse_post_detail(
                        detail_html,
                        post_info["url"],
                        post_info["source_id"],
                    )
                    items.append(content_item)

                except Exception as e:
                    logger.warning(
                        "Instagram 게시글 수집 실패 (%s): %s",
                        post_info["url"],
                        str(e),
                    )

            await page.close()

        except Exception as e:
            logger.error("Instagram 수집 중 오류: %s", str(e))
        finally:
            await self._close_browser()

        logger.info("Instagram 수집 완료: %d건", len(items))
        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """게시글 댓글 수집

        Args:
            content_id: Instagram 게시글 shortcode

        Returns:
            Comment 목록
        """
        await self._ensure_browser()
        comments: List[Comment] = []

        try:
            page = await self._context.new_page()
            url = f"https://www.instagram.com/p/{content_id}/"

            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(self._request_delay)

            # "댓글 더보기" 버튼 클릭하여 댓글 로드
            try:
                load_more = page.locator("text=댓글 더 보기")
                for _ in range(3):  # 최대 3번 더 보기
                    if await load_more.is_visible():
                        await load_more.click()
                        await asyncio.sleep(1.5)
            except Exception:
                pass  # 댓글 더보기 버튼이 없을 수 있음

            html = await page.content()
            comments = parse_comments_from_html(html)

            await page.close()

        except Exception as e:
            logger.warning(
                "Instagram 댓글 수집 실패 (shortcode=%s): %s", content_id, str(e)
            )
        finally:
            await self._close_browser()

        return comments
