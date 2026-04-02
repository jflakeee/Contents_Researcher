"""
Instagram HTML 파서

Playwright로 가져온 Instagram 공개 프로필/게시글 HTML에서
게시글과 댓글 데이터를 추출한다.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from shared.constants import SOURCE_INSTAGRAM
from shared.types import Comment, ContentItem

logger = logging.getLogger(__name__)


def parse_profile_posts(html: str, page_url: str) -> List[Dict[str, str]]:
    """프로필 페이지에서 게시글 링크 목록 추출

    Args:
        html: Instagram 프로필 페이지 HTML
        page_url: 프로필 페이지 URL

    Returns:
        [{"url": "...", "source_id": "...", "thumbnail": "..."}] 형태
    """
    posts = []

    # Instagram 게시글 링크 패턴: /p/{shortcode}/
    shortcodes = re.findall(r'/p/([A-Za-z0-9_-]+)/', html)
    seen = set()

    for shortcode in shortcodes:
        if shortcode in seen:
            continue
        seen.add(shortcode)

        posts.append({
            "url": f"https://www.instagram.com/p/{shortcode}/",
            "source_id": shortcode,
        })

    logger.info("Instagram 프로필 게시글 목록: %d건", len(posts))
    return posts


def parse_post_detail(html: str, url: str, source_id: str) -> ContentItem:
    """게시글 상세 페이지에서 데이터 추출

    Args:
        html: 게시글 상세 페이지 HTML
        url: 게시글 URL
        source_id: 게시글 shortcode

    Returns:
        파싱된 ContentItem
    """
    metadata: Dict[str, Any] = {}

    # meta 태그에서 데이터 추출
    title = _extract_meta(html, "og:title") or ""
    description = _extract_meta(html, "og:description") or ""
    image_url = _extract_meta(html, "og:image") or ""

    if image_url:
        metadata["image_url"] = image_url

    # JSON-LD 스크립트에서 상세 데이터 추출 시도
    json_data = _extract_json_ld(html)
    if json_data:
        # 좋아요, 댓글 수 등 추출
        interaction_stats = json_data.get("interactionStatistic", [])
        for stat in interaction_stats if isinstance(interaction_stats, list) else []:
            stat_type = stat.get("interactionType", "")
            count = int(stat.get("userInteractionCount", 0))
            if "Like" in stat_type:
                metadata["like_count_from_meta"] = count
            elif "Comment" in stat_type:
                metadata["comment_count_from_meta"] = count

    # 캡션을 제목으로 사용 (첫 줄)
    caption = description
    if "\n" in caption:
        title_line = caption.split("\n")[0].strip()
    else:
        title_line = caption[:100] if len(caption) > 100 else caption

    # 작성자 추출
    author_match = re.search(r'(@[\w.]+)', title)
    if author_match:
        metadata["author"] = author_match.group(1)

    return ContentItem(
        source=SOURCE_INSTAGRAM,
        source_url=url,
        source_id=source_id,
        title=title_line or f"Instagram 게시글 ({source_id})",
        body=caption,
        metadata=metadata,
        collected_at=datetime.now(tz=timezone.utc),
    )


def parse_comments_from_html(html: str) -> List[Comment]:
    """게시글 페이지에서 댓글 추출

    Instagram은 댓글이 동적 로딩되므로 Playwright에서
    스크롤/클릭 후 전달된 HTML을 파싱한다.

    Args:
        html: 댓글이 로드된 게시글 페이지 HTML

    Returns:
        Comment 목록
    """
    comments = []

    # Instagram 댓글은 복잡한 DOM 구조를 가짐
    # 일반적인 패턴: <span> 내부에 댓글 텍스트
    # Playwright visible text에서 추출하는 것이 더 안정적

    # 간단한 패턴 매칭 (실제 구조에 맞게 조정 필요)
    comment_pattern = re.compile(
        r'<span[^>]*>([^<]{10,500})</span>',
        re.DOTALL,
    )

    matches = comment_pattern.findall(html)
    for match in matches:
        body = match.strip()
        # 너무 짧거나 메타 텍스트 필터링
        if len(body) < 5:
            continue
        if any(skip in body for skip in ["팔로워", "팔로잉", "게시물", "로그인"]):
            continue

        comments.append(Comment(
            author="",
            body=body,
        ))

    logger.info("Instagram 댓글 파싱: %d건", len(comments))
    return comments


def _extract_meta(html: str, property_name: str) -> Optional[str]:
    """HTML에서 meta 태그 content 추출

    Args:
        html: HTML 문자열
        property_name: meta property 이름

    Returns:
        content 값 또는 None
    """
    pattern = rf'<meta[^>]*property="{property_name}"[^>]*content="([^"]*)"'
    match = re.search(pattern, html)
    if match:
        return match.group(1)

    # 속성 순서가 다른 경우
    pattern = rf'<meta[^>]*content="([^"]*)"[^>]*property="{property_name}"'
    match = re.search(pattern, html)
    if match:
        return match.group(1)

    return None


def _extract_json_ld(html: str) -> Optional[Dict[str, Any]]:
    """HTML에서 JSON-LD 데이터 추출

    Args:
        html: HTML 문자열

    Returns:
        파싱된 JSON 데이터 또는 None
    """
    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match.strip())
            return data
        except json.JSONDecodeError:
            continue

    return None
