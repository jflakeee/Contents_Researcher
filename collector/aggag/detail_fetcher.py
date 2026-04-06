"""
원본 사이트 상세 페이지 수집기

issuelink의 리다이렉트를 따라가 원본 커뮤니티 사이트에서
본문 텍스트, 이미지 URL, 댓글을 추출한다.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
REQUEST_TIMEOUT = 10.0


@dataclass
class DetailResult:
    """상세 페이지 수집 결과"""
    body: str = ""
    image_urls: List[str] = field(default_factory=list)
    comments: List[dict] = field(default_factory=list)  # [{"author": str, "body": str}]
    success: bool = False


async def fetch_detail(issuelink_url: str) -> DetailResult:
    """issuelink URL을 따라가 원본 사이트에서 상세 데이터 수집

    Args:
        issuelink_url: issuelink.co.kr의 게시글 URL

    Returns:
        DetailResult (본문, 이미지, 댓글)
    """
    result = DetailResult()

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ko-KR"},
            follow_redirects=True,
        ) as client:
            response = await client.get(issuelink_url)
            if response.status_code != 200:
                return result

            final_url = str(response.url)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # 사이트별 파싱 전략 선택
            if "theqoo.net" in final_url:
                _parse_theqoo(soup, result)
            elif "fmkorea.com" in final_url:
                _parse_fmkorea(soup, result)
            elif "ruliweb.com" in final_url:
                _parse_ruliweb(soup, result)
            elif "ppomppu.co.kr" in final_url:
                _parse_ppomppu(soup, result)
            elif "todayhumor.co.kr" in final_url:
                _parse_todayhumor(soup, result)
            elif "instiz.net" in final_url:
                _parse_instiz(soup, result)
            elif "bobae.co.kr" in final_url or "clien.net" in final_url:
                _parse_generic(soup, result)
            elif "inven.co.kr" in final_url:
                _parse_generic(soup, result)
            elif "slrclub.com" in final_url:
                _parse_generic(soup, result)
            else:
                _parse_generic(soup, result)

            result.success = True

    except Exception as e:
        logger.debug("상세 수집 실패 (%s): %s", issuelink_url[:60], e)

    return result


# === 사이트별 파서 ===

def _parse_theqoo(soup: BeautifulSoup, result: DetailResult) -> None:
    """더쿠 파싱"""
    _extract_body(soup, result, [".xe_content", ".rd_body", ".article-body"])
    _extract_images(soup, result, [".xe_content img", ".rd_body img"])
    _extract_comments(soup, result, [
        ".fdb_lst_ul li .xe_content",
        ".comment_content",
    ])


def _parse_fmkorea(soup: BeautifulSoup, result: DetailResult) -> None:
    """에펨코리아 파싱"""
    _extract_body(soup, result, [".xe_content", ".rd_body"])
    _extract_images(soup, result, [".xe_content img", ".rd_body img"])
    _extract_comments(soup, result, [
        ".fdb_lst_ul li .xe_content",
        ".comment_content",
    ])


def _parse_ruliweb(soup: BeautifulSoup, result: DetailResult) -> None:
    """루리웹 파싱"""
    _extract_body(soup, result, [".view_content", ".board_main_content"])
    _extract_images(soup, result, [".view_content img", ".board_main_content img"])
    _extract_comments(soup, result, [
        ".comment_element .text_wrapper",
        ".comment_view .text",
    ])


def _parse_ppomppu(soup: BeautifulSoup, result: DetailResult) -> None:
    """뽐뿌 파싱"""
    _extract_body(soup, result, [".han_proverb", ".board-contents"])
    _extract_images(soup, result, [".han_proverb img", ".board-contents img"])
    _extract_comments(soup, result, [".comment_line .comment"])


def _parse_todayhumor(soup: BeautifulSoup, result: DetailResult) -> None:
    """오늘의유머 파싱"""
    _extract_body(soup, result, [".viewContent", "#articleContent"])
    _extract_images(soup, result, [".viewContent img", "#articleContent img"])
    _extract_comments(soup, result, [".comment_content", ".memo_content"])


def _parse_instiz(soup: BeautifulSoup, result: DetailResult) -> None:
    """인스티즈 파싱"""
    _extract_body(soup, result, [".memo_content", ".xe_content"])
    _extract_images(soup, result, [".memo_content img", ".xe_content img"])
    _extract_comments(soup, result, [".comment .comment_content"])


def _parse_generic(soup: BeautifulSoup, result: DetailResult) -> None:
    """범용 파서 (알 수 없는 사이트)"""
    _extract_body(soup, result, [
        ".xe_content", ".rd_body", ".view_content", ".article-body",
        ".board-contents", "#content", "article", ".post-content",
    ])
    _extract_images(soup, result, [
        ".xe_content img", ".rd_body img", ".view_content img",
        ".article-body img", "article img",
    ])
    _extract_comments(soup, result, [
        ".fdb_lst_ul li .xe_content",
        ".comment_content", ".reply_content",
        ".cmt_content", ".comment .text",
    ])


# === 공통 추출 유틸리티 ===

def _extract_body(soup: BeautifulSoup, result: DetailResult, selectors: List[str]) -> None:
    """본문 텍스트 추출"""
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            if len(text) > 10:
                result.body = text[:5000]  # 최대 5000자
                return


def _extract_images(soup: BeautifulSoup, result: DetailResult, selectors: List[str]) -> None:
    """본문 내 이미지 URL 추출"""
    seen = set()
    for sel in selectors:
        for img in soup.select(sel):
            src = img.get("src", "") or img.get("data-src", "")
            if not src:
                continue
            # 절대 URL로 변환
            if src.startswith("//"):
                src = "https:" + src
            # 실제 이미지만 필터 (아이콘, 로고 제외)
            if not src.startswith("http"):
                continue
            if any(skip in src.lower() for skip in ["icon", "logo", "emoji", "button", "badge", "avatar"]):
                continue
            if src not in seen:
                seen.add(src)
                result.image_urls.append(src)


def _extract_comments(soup: BeautifulSoup, result: DetailResult, selectors: List[str]) -> None:
    """댓글 추출"""
    for sel in selectors:
        elements = soup.select(sel)
        if elements:
            for el in elements[:50]:  # 최대 50개 댓글
                text = el.get_text(strip=True)
                if text and len(text) >= 50:
                    # 작성자 추출 시도
                    parent = el.parent
                    author = ""
                    if parent:
                        nick = parent.select_one(".nickname, .nick, .member, .author")
                        if nick:
                            author = nick.get_text(strip=True)
                    result.comments.append({
                        "author": author or "",
                        "body": text[:500],
                    })
            return  # 첫 매칭 셀렉터에서 댓글을 찾으면 종료
