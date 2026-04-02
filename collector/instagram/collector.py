"""
Instagram 수집기

Playwright sync API를 별도 스레드에서 실행하여
Instagram 공개 프로필/해시태그의 게시글과 댓글을 수집한다.
(asyncio.to_thread로 Python 3.14 Windows 호환)
"""

import asyncio
import logging
import time
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

# 요청 간 딜레이 (초)
REQUEST_DELAY = 3.0

# 수집할 최대 게시글 수
MAX_POSTS = 10

# 브라우저 설치 여부 플래그
_browser_installed = False


def _ensure_browsers_installed() -> None:
    """Playwright 브라우저가 설치되어 있지 않으면 설치"""
    global _browser_installed
    if _browser_installed:
        return
    try:
        import subprocess
        result = subprocess.run(
            ["python", "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            logger.info("Playwright Chromium 브라우저 설치 완료")
        else:
            logger.warning("Playwright 브라우저 설치 실패: %s", result.stderr[:200])
    except Exception as e:
        logger.warning("Playwright 브라우저 설치 시도 실패: %s", e)
    _browser_installed = True


def _collect_sync(
    query: str,
    max_posts: int = MAX_POSTS,
    request_delay: float = REQUEST_DELAY,
) -> List[dict]:
    """Playwright sync API로 Instagram 게시글 수집 (별도 스레드에서 실행)

    Returns:
        [{"url": str, "source_id": str, "html": str}] — 상세 페이지 HTML 목록
    """
    _ensure_browsers_installed()

    from playwright.sync_api import sync_playwright

    results = []

    # URL 결정
    if query.startswith("@"):
        username = query.lstrip("@")
        url = f"https://www.instagram.com/{username}/"
    elif query.startswith("#"):
        hashtag = query.lstrip("#")
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
    else:
        url = f"https://www.instagram.com/explore/tags/{query}/" if query else "https://www.instagram.com/explore/"

    logger.info("[Instagram] Playwright 수집 시작: %s", url)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/16.0 Mobile/15E148 Safari/604.1"
                ),
                viewport={"width": 390, "height": 844},
            )
            page = context.new_page()

            # 프로필/탐색 페이지 로드
            page.goto(url, wait_until="networkidle", timeout=15000)
            time.sleep(request_delay)

            list_html = page.content()

            # 게시글 목록 파싱
            post_list = parse_profile_posts(list_html, url)
            post_list = post_list[:max_posts]
            logger.info("[Instagram] 게시글 목록: %d건", len(post_list))

            # 각 게시글 상세 수집
            for post_info in post_list:
                try:
                    time.sleep(request_delay)
                    page.goto(post_info["url"], wait_until="networkidle", timeout=15000)

                    # 댓글 더보기 시도
                    try:
                        more_btn = page.locator("text=댓글 더 보기")
                        if more_btn.is_visible(timeout=2000):
                            more_btn.click()
                            time.sleep(1)
                    except Exception:
                        pass

                    detail_html = page.content()
                    results.append({
                        "url": post_info["url"],
                        "source_id": post_info["source_id"],
                        "html": detail_html,
                    })
                except Exception as e:
                    logger.warning("[Instagram] 게시글 수집 실패 (%s): %s", post_info["url"], e)

            context.close()
            browser.close()

    except Exception as e:
        logger.error("[Instagram] Playwright 수집 오류: %s", e)

    logger.info("[Instagram] Playwright 수집 완료: %d건", len(results))
    return results


def _collect_comments_sync(
    shortcode: str,
    request_delay: float = REQUEST_DELAY,
) -> str:
    """Playwright sync API로 댓글 수집 (별도 스레드에서 실행)

    Returns:
        상세 페이지 HTML
    """
    _ensure_browsers_installed()

    from playwright.sync_api import sync_playwright

    url = f"https://www.instagram.com/p/{shortcode}/"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                locale="ko-KR",
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=15000)
            time.sleep(request_delay)

            # 댓글 더보기 시도
            try:
                for _ in range(3):
                    more_btn = page.locator("text=댓글 더 보기")
                    if more_btn.is_visible(timeout=1500):
                        more_btn.click()
                        time.sleep(1)
            except Exception:
                pass

            html = page.content()
            context.close()
            browser.close()
            return html

    except Exception as e:
        logger.warning("[Instagram] 댓글 수집 실패 (%s): %s", shortcode, e)
        return ""


class InstagramCollector(BaseCollector):
    """Instagram 수집기

    Playwright sync API를 asyncio.to_thread()로 실행하여
    Python 3.14 Windows에서도 정상 동작.
    """

    source_name = SOURCE_INSTAGRAM

    def __init__(
        self,
        request_delay: float = REQUEST_DELAY,
        max_posts: int = MAX_POSTS,
    ):
        self._request_delay = request_delay
        self._max_posts = max_posts

    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """Instagram 게시글 수집 (Playwright를 별도 스레드에서 실행)"""
        # sync 함수를 별도 스레드에서 실행
        raw_results = await asyncio.to_thread(
            _collect_sync,
            query,
            self._max_posts,
            self._request_delay,
        )

        # HTML → ContentItem 변환
        items = []
        for r in raw_results:
            try:
                item = parse_post_detail(r["html"], r["url"], r["source_id"])
                items.append(item)
            except Exception as e:
                logger.warning("[Instagram] 파싱 실패 (%s): %s", r["url"], e)

        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """게시글 댓글 수집 (Playwright를 별도 스레드에서 실행)"""
        html = await asyncio.to_thread(
            _collect_comments_sync,
            content_id,
            self._request_delay,
        )

        if not html:
            return []

        return parse_comments_from_html(html)
