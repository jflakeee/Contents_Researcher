"""
Instagram 수집기

httpx를 사용하여 Instagram 공개 프로필과 해시태그에서
게시글과 댓글을 수집한다.
(Playwright 대신 httpx 사용 — Python 3.14 Windows 호환)
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

import httpx

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
MAX_POSTS = 20

# HTTP 요청 타임아웃 (초)
REQUEST_TIMEOUT = 15.0

# User-Agent (모바일 브라우저 에뮬레이션)
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.0 Mobile/15E148 Safari/604.1"
)


class InstagramCollector(BaseCollector):
    """Instagram 수집기

    httpx로 Instagram 공개 페이지를 요청하고 HTML을 파싱하여
    게시글과 댓글을 수집한다.
    """

    source_name = SOURCE_INSTAGRAM

    def __init__(
        self,
        request_delay: float = REQUEST_DELAY,
        max_posts: int = MAX_POSTS,
    ):
        """초기화

        Args:
            request_delay: 요청 간 딜레이 (초)
            max_posts: 최대 수집 게시글 수
        """
        self._request_delay = request_delay
        self._max_posts = max_posts

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
        """Instagram 게시글 수집

        query가 @로 시작하면 프로필 수집, #으로 시작하면 해시태그 수집.

        Args:
            query: 검색 키워드 (@username 또는 #hashtag)
            date_from: 수집 시작일
            date_to: 수집 종료일

        Returns:
            수집된 ContentItem 목록
        """
        items: List[ContentItem] = []

        # 프로필 또는 해시태그 URL 결정
        if query.startswith("@"):
            username = query.lstrip("@")
            url = f"https://www.instagram.com/{username}/"
        elif query.startswith("#"):
            hashtag = query.lstrip("#")
            url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        else:
            url = f"https://www.instagram.com/explore/tags/{query}/" if query else "https://www.instagram.com/explore/"

        logger.info("Instagram 수집 시작: %s", url)

        try:
            async with self._create_client() as client:
                # 프로필/해시태그 페이지 요청
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

                # 게시글 목록 추출
                post_list = parse_profile_posts(html, url)
                post_list = post_list[: self._max_posts]

                # 각 게시글 상세 수집
                for post_info in post_list:
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
                            "Instagram 게시글 수집 실패 (%s): %s",
                            post_info["url"],
                            str(e),
                        )

        except Exception as e:
            logger.error("Instagram 수집 중 오류: %s", str(e))

        logger.info("Instagram 수집 완료: %d건", len(items))
        return items

    async def collect_comments(self, content_id: str) -> List[Comment]:
        """게시글 댓글 수집

        Args:
            content_id: Instagram 게시글 shortcode

        Returns:
            Comment 목록
        """
        url = f"https://www.instagram.com/p/{content_id}/"

        try:
            async with self._create_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                return parse_comments_from_html(response.text)
        except Exception as e:
            logger.warning(
                "Instagram 댓글 수집 실패 (shortcode=%s): %s", content_id, str(e)
            )
            return []
