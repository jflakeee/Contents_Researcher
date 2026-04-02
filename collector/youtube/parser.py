"""
YouTube API 응답 파서

YouTube Data API v3 응답을 ContentItem과 Comment로 변환한다.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from shared.constants import SOURCE_YOUTUBE
from shared.types import Comment, ContentItem


def parse_search_result(item: Dict[str, Any]) -> ContentItem:
    """검색 결과 항목을 ContentItem으로 변환

    Args:
        item: YouTube search.list API 응답의 개별 항목

    Returns:
        변환된 ContentItem (상세 정보는 별도 API 호출 필요)
    """
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId", "")

    return ContentItem(
        source=SOURCE_YOUTUBE,
        source_url=f"https://www.youtube.com/watch?v={video_id}",
        source_id=video_id,
        title=snippet.get("title", ""),
        body=snippet.get("description", ""),
        metadata={
            "channel_id": snippet.get("channelId", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "thumbnail_url": _get_best_thumbnail(snippet.get("thumbnails", {})),
            "published_at": snippet.get("publishedAt", ""),
        },
        collected_at=datetime.now(tz=timezone.utc),
    )


def parse_video_details(
    content_item: ContentItem, video_data: Dict[str, Any]
) -> ContentItem:
    """영상 상세 정보를 ContentItem에 병합

    Args:
        content_item: 기존 ContentItem (검색 결과에서 생성된 것)
        video_data: YouTube videos.list API 응답의 개별 항목

    Returns:
        상세 정보가 추가된 ContentItem
    """
    statistics = video_data.get("statistics", {})
    snippet = video_data.get("snippet", {})

    # 조회수, 좋아요수 업데이트
    content_item.view_count = int(statistics.get("viewCount", 0))
    content_item.like_count = int(statistics.get("likeCount", 0))
    content_item.comment_count = int(statistics.get("commentCount", 0))

    # 상세 설명 업데이트
    content_item.body = snippet.get("description", content_item.body)

    # 메타데이터 추가
    content_item.metadata.update({
        "category_id": snippet.get("categoryId", ""),
        "tags": snippet.get("tags", []),
        "duration": video_data.get("contentDetails", {}).get("duration", ""),
    })

    return content_item


def parse_comment(item: Dict[str, Any]) -> Comment:
    """댓글 스레드 항목을 Comment로 변환

    Args:
        item: YouTube commentThreads.list API 응답의 개별 항목

    Returns:
        변환된 Comment
    """
    snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})

    return Comment(
        author=snippet.get("authorDisplayName", ""),
        body=snippet.get("textDisplay", ""),
        like_count=int(snippet.get("likeCount", 0)),
    )


def parse_comments_response(response: Dict[str, Any]) -> List[Comment]:
    """댓글 API 응답 전체를 Comment 목록으로 변환

    Args:
        response: YouTube commentThreads.list API 전체 응답

    Returns:
        Comment 목록
    """
    items = response.get("items", [])
    return [parse_comment(item) for item in items]


def _get_best_thumbnail(thumbnails: Dict[str, Any]) -> str:
    """가장 고화질인 썸네일 URL 반환

    Args:
        thumbnails: YouTube 썸네일 딕셔너리

    Returns:
        썸네일 URL
    """
    # 우선순위: maxres > high > medium > default
    for quality in ["maxres", "high", "medium", "default"]:
        if quality in thumbnails:
            return thumbnails[quality].get("url", "")
    return ""
