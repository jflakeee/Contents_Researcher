"""
aggag.com 수집기 테스트

AggagCollector의 HTML 파싱 로직을 테스트한다.
"""

import pytest

from shared.types import ContentItem, Comment
from collector.aggag.parser import (
    parse_post_list,
    parse_post_detail,
    parse_comments,
    _extract_post_id,
)


class TestAggagParser:
    """aggag.com HTML 파서 테스트"""

    def test_parse_post_list_with_article_tags(self):
        """article 태그가 있는 게시글 목록 파싱"""
        html = """
        <div class="board">
            <article>
                <a href="/post/123">첫 번째 게시글</a>
            </article>
            <article>
                <a href="/post/456">두 번째 게시글</a>
            </article>
        </div>
        """
        result = parse_post_list(html, "https://aggag.com")

        assert len(result) == 2
        assert result[0]["title"] == "첫 번째 게시글"
        assert result[0]["url"] == "https://aggag.com/post/123"
        assert result[0]["source_id"] == "123"

    def test_parse_post_detail(self):
        """게시글 상세 페이지 파싱"""
        html = """
        <html>
            <h1 class="post-title">테스트 게시글 제목</h1>
            <div class="post-content">게시글 본문 내용입니다.</div>
            <span class="view-count">조회 1,234</span>
            <span class="like-count">좋아요 56</span>
            <span class="post-date">2026-04-01</span>
            <span class="post-author">작성자명</span>
        </html>
        """
        result = parse_post_detail(html, "https://aggag.com/post/789", "789")

        assert isinstance(result, ContentItem)
        assert result.source == "aggag"
        assert result.source_id == "789"
        assert result.title == "테스트 게시글 제목"
        assert "본문 내용" in result.body
        assert result.view_count == 1234
        assert result.like_count == 56

    def test_parse_comments(self):
        """댓글 파싱"""
        html = """
        <div class="comment-list">
            <li class="comment-item">
                <span class="comment-author">댓글작성자1</span>
                <span class="comment-body">댓글 내용 1</span>
                <span class="comment-like">3</span>
            </li>
            <li class="comment-item">
                <span class="comment-author">댓글작성자2</span>
                <span class="comment-body">댓글 내용 2</span>
            </li>
        </div>
        """
        result = parse_comments(html)

        assert len(result) == 2
        assert result[0].author == "댓글작성자1"
        assert result[0].body == "댓글 내용 1"
        assert result[0].like_count == 3

    def test_parse_empty_comments(self):
        """댓글 없는 페이지"""
        html = "<div class='no-comments'>댓글이 없습니다.</div>"
        result = parse_comments(html)
        assert result == []

    def test_extract_post_id_from_path(self):
        """URL 경로에서 게시글 ID 추출"""
        assert _extract_post_id("https://aggag.com/post/12345") == "12345"

    def test_extract_post_id_from_query(self):
        """URL 쿼리 파라미터에서 게시글 ID 추출"""
        assert _extract_post_id("https://aggag.com/board?id=99") == "99"
        assert _extract_post_id("https://aggag.com/board?no=42") == "42"

    def test_parse_post_detail_missing_elements(self):
        """누락된 HTML 요소가 있는 게시글 상세"""
        html = "<html><body><h1>제목만 있음</h1></body></html>"
        result = parse_post_detail(html, "https://aggag.com/post/1", "1")

        assert result.title == "제목만 있음"
        assert result.view_count == 0
        assert result.like_count == 0
