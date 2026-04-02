"""
YouTube 수집기 테스트

YouTubeCollector의 파싱 로직과 할당량 관리를 테스트한다.
"""

import pytest
from datetime import datetime

from shared.types import ContentItem, Comment
from collector.youtube.parser import (
    parse_search_result,
    parse_video_details,
    parse_comment,
    parse_comments_response,
)


class TestYouTubeParser:
    """YouTube API 응답 파서 테스트"""

    def test_parse_search_result(self):
        """검색 결과 파싱 — API 응답을 ContentItem으로 변환"""
        api_item = {
            "id": {"videoId": "test123"},
            "snippet": {
                "title": "테스트 영상 제목",
                "description": "테스트 설명",
                "channelId": "UCtest",
                "channelTitle": "테스트 채널",
                "publishedAt": "2026-04-01T00:00:00Z",
                "thumbnails": {
                    "high": {"url": "https://img.youtube.com/test/high.jpg"},
                    "default": {"url": "https://img.youtube.com/test/default.jpg"},
                },
            },
        }

        result = parse_search_result(api_item)

        assert isinstance(result, ContentItem)
        assert result.source == "youtube"
        assert result.source_id == "test123"
        assert result.title == "테스트 영상 제목"
        assert result.source_url == "https://www.youtube.com/watch?v=test123"
        assert result.metadata["channel_title"] == "테스트 채널"
        assert "high.jpg" in result.metadata["thumbnail_url"]

    def test_parse_video_details(self):
        """영상 상세 정보 병합"""
        item = ContentItem(
            source="youtube",
            source_url="https://www.youtube.com/watch?v=test123",
            source_id="test123",
            title="테스트",
        )

        video_data = {
            "statistics": {
                "viewCount": "50000",
                "likeCount": "1200",
                "commentCount": "300",
            },
            "snippet": {
                "description": "상세 설명",
                "categoryId": "22",
                "tags": ["태그1", "태그2"],
            },
            "contentDetails": {
                "duration": "PT10M30S",
            },
        }

        result = parse_video_details(item, video_data)

        assert result.view_count == 50000
        assert result.like_count == 1200
        assert result.comment_count == 300
        assert result.body == "상세 설명"
        assert result.metadata["tags"] == ["태그1", "태그2"]

    def test_parse_comment(self):
        """댓글 파싱"""
        api_item = {
            "snippet": {
                "topLevelComment": {
                    "snippet": {
                        "authorDisplayName": "사용자1",
                        "textDisplay": "정말 좋은 영상이네요!",
                        "likeCount": 15,
                    }
                }
            }
        }

        result = parse_comment(api_item)

        assert isinstance(result, Comment)
        assert result.author == "사용자1"
        assert result.body == "정말 좋은 영상이네요!"
        assert result.like_count == 15

    def test_parse_comments_response(self):
        """댓글 목록 파싱"""
        response = {
            "items": [
                {
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "authorDisplayName": "유저A",
                                "textDisplay": "댓글 1",
                                "likeCount": 5,
                            }
                        }
                    }
                },
                {
                    "snippet": {
                        "topLevelComment": {
                            "snippet": {
                                "authorDisplayName": "유저B",
                                "textDisplay": "댓글 2",
                                "likeCount": 3,
                            }
                        }
                    }
                },
            ]
        }

        result = parse_comments_response(response)

        assert len(result) == 2
        assert result[0].author == "유저A"
        assert result[1].body == "댓글 2"

    def test_parse_empty_response(self):
        """빈 응답 처리"""
        result = parse_comments_response({"items": []})
        assert result == []

        result = parse_comments_response({})
        assert result == []
