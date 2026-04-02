"""
aggag.com HTML 파서

Playwright로 가져온 HTML에서 게시글과 댓글 데이터를 추출한다.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem

logger = logging.getLogger(__name__)


def parse_post_list(html: str, base_url: str) -> List[Dict[str, str]]:
    """게시글 목록 페이지에서 게시글 링크와 제목 추출

    Args:
        html: 게시글 목록 페이지 HTML
        base_url: aggag.com 기본 URL

    Returns:
        [{"url": "...", "title": "...", "source_id": "..."}] 형태의 목록
    """
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    # 게시글 목록 항목 탐색
    # aggag.com의 실제 HTML 구조에 맞게 셀렉터 조정 필요
    for article in soup.select("article, .post-item, .board-item, tr.list-item"):
        link_tag = article.select_one("a[href]")
        if not link_tag:
            continue

        href = link_tag.get("href", "")
        title = link_tag.get_text(strip=True)

        # 상대 경로를 절대 경로로 변환
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        elif not href.startswith("http"):
            href = base_url.rstrip("/") + "/" + href

        # 게시글 ID 추출 (URL에서)
        source_id = _extract_post_id(href)

        if title and href:
            posts.append({
                "url": href,
                "title": title,
                "source_id": source_id,
            })

    logger.info("aggag 게시글 목록 파싱: %d건", len(posts))
    return posts


def parse_post_detail(html: str, url: str, source_id: str) -> ContentItem:
    """게시글 상세 페이지에서 컨텐츠 데이터 추출

    Args:
        html: 게시글 상세 페이지 HTML
        url: 게시글 URL
        source_id: 게시글 고유 ID

    Returns:
        파싱된 ContentItem
    """
    soup = BeautifulSoup(html, "html.parser")

    # 제목 추출
    title = _extract_text(soup, [
        "h1.post-title",
        "h1.article-title",
        ".board-title h1",
        "h1",
    ])

    # 본문 추출
    body = _extract_text(soup, [
        ".post-content",
        ".article-body",
        ".board-content",
        ".content-area",
        "article",
    ])

    # 조회수 추출
    view_count = _extract_number(soup, [
        ".view-count",
        ".hit-count",
        ".views",
    ])

    # 좋아요 수 추출
    like_count = _extract_number(soup, [
        ".like-count",
        ".recommend-count",
        ".likes",
    ])

    # 작성일 추출
    date_text = _extract_text(soup, [
        ".post-date",
        ".article-date",
        "time",
        ".date",
    ])

    # 메타데이터
    metadata: Dict[str, Any] = {}
    if date_text:
        metadata["original_date"] = date_text

    # 작성자 추출
    author = _extract_text(soup, [
        ".post-author",
        ".article-author",
        ".nickname",
        ".writer",
    ])
    if author:
        metadata["author"] = author

    return ContentItem(
        source=SOURCE_AGGAG,
        source_url=url,
        source_id=source_id,
        title=title or "제목 없음",
        body=body,
        view_count=view_count,
        like_count=like_count,
        metadata=metadata,
        collected_at=datetime.now(tz=timezone.utc),
    )


def parse_comments(html: str) -> List[Comment]:
    """게시글 페이지에서 댓글 추출

    Args:
        html: 게시글 상세 페이지 HTML

    Returns:
        Comment 목록
    """
    soup = BeautifulSoup(html, "html.parser")
    comments = []

    # 댓글 목록 탐색
    for comment_el in soup.select(
        ".comment-item, .reply-item, .comment-list li, .cmt-item"
    ):
        author = _extract_text(comment_el, [
            ".comment-author",
            ".reply-author",
            ".nickname",
            ".writer",
        ]) or "익명"

        body = _extract_text(comment_el, [
            ".comment-body",
            ".comment-content",
            ".reply-content",
            ".cmt-content",
        ])

        like_count = _extract_number(comment_el, [
            ".comment-like",
            ".reply-like",
            ".like-count",
        ])

        if body:
            comments.append(Comment(
                author=author,
                body=body,
                like_count=like_count,
            ))

    logger.info("aggag 댓글 파싱: %d건", len(comments))
    return comments


def _extract_text(
    soup: BeautifulSoup, selectors: List[str]
) -> str:
    """여러 CSS 셀렉터 중 첫 번째 매칭 요소의 텍스트 반환

    Args:
        soup: BeautifulSoup 객체
        selectors: 시도할 CSS 셀렉터 목록

    Returns:
        추출된 텍스트 (없으면 빈 문자열)
    """
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element.get_text(strip=True)
    return ""


def _extract_number(
    soup: BeautifulSoup, selectors: List[str]
) -> int:
    """여러 CSS 셀렉터 중 첫 번째 매칭 요소에서 숫자 추출

    Args:
        soup: BeautifulSoup 객체
        selectors: 시도할 CSS 셀렉터 목록

    Returns:
        추출된 숫자 (없으면 0)
    """
    import re

    text = _extract_text(soup, selectors)
    if text:
        numbers = re.findall(r"\d+", text.replace(",", ""))
        if numbers:
            return int(numbers[0])
    return 0


def _extract_post_id(url: str) -> str:
    """URL에서 게시글 ID 추출

    Args:
        url: 게시글 URL

    Returns:
        게시글 ID 문자열
    """
    import re
    from urllib.parse import urlparse, parse_qs

    # URL 쿼리 파라미터에서 ID 추출 시도
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    for key in ["id", "no", "idx", "seq", "document_srl"]:
        if key in params:
            return params[key][0]

    # URL 경로에서 숫자 ID 추출 시도
    numbers = re.findall(r"/(\d+)", parsed.path)
    if numbers:
        return numbers[-1]

    # 마지막 경로 세그먼트 사용
    path_parts = parsed.path.rstrip("/").split("/")
    if path_parts:
        return path_parts[-1]

    return url
