"""
issuelink.co.kr HTML 파서

이슈링크 커뮤니티 목록 페이지에서 게시글 데이터를 추출한다.
(상세 페이지는 원본 사이트로 리다이렉트되므로 목록에서 수집)
URL 패턴: /community/go/{source}/{id}
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem

logger = logging.getLogger(__name__)

# issuelink 기본 URL
BASE_URL = "https://www.issuelink.co.kr"


def parse_post_list(html: str, base_url: str = BASE_URL) -> List[ContentItem]:
    """커뮤니티 목록 페이지에서 게시글 데이터 추출

    issuelink는 상세 페이지가 원본 사이트로 리다이렉트되므로
    목록 페이지에서 제목, 출처, 댓글수를 직접 추출하여 ContentItem을 생성한다.

    Args:
        html: 목록 페이지 HTML
        base_url: 기본 URL

    Returns:
        ContentItem 목록
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []
    seen = set()

    for a_tag in soup.select('a[href*="/community/go/"]'):
        href = a_tag.get("href", "")
        if not href:
            continue

        # 출처/ID 추출: /community/go/{source}/{id}
        m = re.search(r'/community/go/(\w+)/(\d+)', href)
        if not m:
            continue

        origin_source = m.group(1)  # theqoo, fmkorea, bobae 등
        post_id = m.group(2)
        unique_key = f"{origin_source}/{post_id}"

        if unique_key in seen:
            continue
        seen.add(unique_key)

        # 제목 추출 (a 태그 텍스트에서 [댓글수] 제거)
        raw_text = a_tag.get_text(strip=True)
        # [숫자] 패턴 제거하여 순수 제목 추출
        title = re.sub(r'\s*\[\d+\]\s*$', '', raw_text).strip()

        # 댓글 수 추출
        comment_count = 0
        cmt_match = re.search(r'\[(\d+)\]', raw_text)
        if cmt_match:
            comment_count = int(cmt_match.group(1))

        if not title:
            continue

        # 원본 URL 구성
        if href.startswith("/"):
            full_url = base_url.rstrip("/") + href
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = base_url.rstrip("/") + "/" + href

        items.append(ContentItem(
            source=SOURCE_AGGAG,
            source_url=full_url,
            source_id=unique_key,
            title=title,
            body=None,
            comment_count=comment_count,
            metadata={
                "origin_source": origin_source,
                "origin_id": post_id,
            },
            collected_at=datetime.now(tz=timezone.utc),
        ))

    logger.info("issuelink 게시글 파싱: %d건", len(items))
    return items


def parse_comments(html: str) -> List[Comment]:
    """댓글 추출 (issuelink 목록에서는 댓글 본문을 가져올 수 없음)

    Args:
        html: HTML 문자열

    Returns:
        빈 Comment 목록
    """
    return []
