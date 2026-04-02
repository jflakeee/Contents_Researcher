"""
aagag.com HTML 파서

aagag.com의 게시글 목록과 상세 페이지에서 데이터를 추출한다.
URL 패턴: /issue/?idx=숫자
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from shared.constants import SOURCE_AGGAG
from shared.types import Comment, ContentItem

logger = logging.getLogger(__name__)

# aagag.com 기본 URL
BASE_URL = "https://aagag.com"


def parse_post_list(html: str, base_url: str = BASE_URL) -> List[Dict[str, str]]:
    """게시글 목록 페이지에서 게시글 링크와 제목 추출

    Args:
        html: 게시글 목록 페이지 HTML
        base_url: 기본 URL

    Returns:
        [{"url": "...", "title": "...", "source_id": "..."}]
    """
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    seen = set()

    # aagag.com 패턴: a[href*="idx="] 태그
    for a_tag in soup.select('a[href*="idx="]'):
        href = a_tag.get("href", "")
        if not href:
            continue

        # idx 파라미터 추출
        idx_match = re.search(r'idx=(\d+)', href)
        if not idx_match:
            continue

        source_id = idx_match.group(1)
        if source_id in seen:
            continue
        seen.add(source_id)

        # 제목: a 태그 내 span.title 또는 a 태그 텍스트
        title_el = a_tag.select_one('span.title')
        if title_el:
            title = title_el.get_text(strip=True)
        else:
            title = a_tag.get_text(strip=True)

        # 제목에서 파일 크기/조회수 등 불필요한 접미사 제거
        title = re.sub(r'[\d.]+\s*[KMGT]?B\d+\d+.*$', '', title).strip()

        if not title:
            continue

        # 절대 URL 생성
        if href.startswith("/"):
            full_url = base_url.rstrip("/") + href
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = base_url.rstrip("/") + "/" + href

        posts.append({
            "url": full_url,
            "title": title,
            "source_id": source_id,
        })

    logger.info("aagag 게시글 목록 파싱: %d건", len(posts))
    return posts


def parse_post_detail(html: str, url: str, source_id: str) -> ContentItem:
    """게시글 상세 페이지에서 컨텐츠 데이터 추출

    Args:
        html: 게시글 상세 페이지 HTML
        url: 게시글 URL
        source_id: 게시글 idx

    Returns:
        파싱된 ContentItem
    """
    soup = BeautifulSoup(html, "html.parser")
    metadata: Dict[str, Any] = {}

    # 제목: h1 또는 span.title
    title = ""
    h1 = soup.select_one("h1")
    if h1:
        title = h1.get_text(strip=True)
    if not title:
        span_title = soup.select_one("span.title")
        if span_title:
            title = span_title.get_text(strip=True)
            # 파일 크기 등 접미사 제거
            title = re.sub(r'[\d.]+\s*[KMGT]?B\d+.*$', '', title).strip()

    # 본문: div.view_content 또는 div.content
    body = ""
    for sel in [".view_content", ".content", ".article", "#content"]:
        body_el = soup.select_one(sel)
        if body_el and len(body_el.get_text(strip=True)) > 10:
            body = body_el.get_text(strip=True)
            break

    # 조회수: .hit
    view_count = 0
    hit_el = soup.select_one(".hit")
    if hit_el:
        numbers = re.findall(r'\d+', hit_el.get_text().replace(",", ""))
        if numbers:
            view_count = int(numbers[0])

    # 좋아요: .good
    like_count = 0
    good_el = soup.select_one(".good")
    if good_el:
        numbers = re.findall(r'\d+', good_el.get_text().replace(",", ""))
        if numbers:
            like_count = int(numbers[0])

    # 댓글 수: .comment 영역 내 댓글 개수
    comment_els = soup.select(".icomment .cmt_memo, .comment .cmt_memo")
    comment_count = len(comment_els)

    return ContentItem(
        source=SOURCE_AGGAG,
        source_url=url,
        source_id=source_id,
        title=title or f"aagag #{source_id}",
        body=body,
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
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

    # aagag.com 댓글: .icomment 내부 .cmt_memo
    for cmt_el in soup.select(".icomment .cmt_memo, .comment .cmt_memo"):
        body = cmt_el.get_text(strip=True)
        if not body or len(body) < 2:
            continue

        # 작성자: 인접 요소에서 탐색
        author = ""
        parent = cmt_el.parent
        if parent:
            nick_el = parent.select_one(".nick, .nickname, .name")
            if nick_el:
                author = nick_el.get_text(strip=True)

        # 좋아요
        like_count = 0
        if parent:
            like_el = parent.select_one(".good, .like, .recommend")
            if like_el:
                nums = re.findall(r'\d+', like_el.get_text())
                if nums:
                    like_count = int(nums[0])

        comments.append(Comment(
            author=author or "익명",
            body=body,
            like_count=like_count,
        ))

    logger.info("aagag 댓글 파싱: %d건", len(comments))
    return comments
