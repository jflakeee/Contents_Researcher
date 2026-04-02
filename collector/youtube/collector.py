"""
YouTube 수집기

YouTube Data API v3를 사용하여 영상과 댓글을 수집한다.
API 할당량(일일 10,000 유닛)을 추적하여 초과를 방지한다.
"""

import logging
from datetime import datetime
from typing import List, Optional

from shared.constants import SOURCE_YOUTUBE
from shared.types import Comment, ContentItem
from collector.core.base import BaseCollector
from collector.youtube.parser import (
    parse_search_result,
    parse_video_details,
    parse_comments_response,
)

logger = logging.getLogger(__name__)

# API 호출별 할당량 비용 (유닛)
QUOTA_COST_SEARCH = 100
QUOTA_COST_VIDEOS = 1
QUOTA_COST_COMMENTS = 1
# 일일 할당량 한도
DAILY_QUOTA_LIMIT = 10000


class YouTubeCollector(BaseCollector):
    """YouTube 수집기

    YouTube Data API v3를 통해 영상 검색, 상세 조회, 댓글 수집을 수행한다.
    """

    source_name = SOURCE_YOUTUBE

    def __init__(self, api_key: str, max_results: int = 50):
        """초기화

        Args:
            api_key: YouTube Data API v3 키
            max_results: 검색당 최대 결과 수 (기본 50, API 최대값)
        """
        self._api_key = api_key
        self._max_results = min(max_results, 50)
        self._quota_used = 0
        self._service = None

    def _get_service(self):
        """YouTube API 서비스 객체 생성 (지연 초기화)"""
        if self._service is None:
            from googleapiclient.discovery import build
            self._service = build("youtube", "v3", developerKey=self._api_key)
        return self._service

    def _check_quota(self, cost: int) -> bool:
        """할당량 초과 여부 확인

        Args:
            cost: 소비할 할당량 유닛

        Returns:
            True면 호출 가능
        """
        if self._quota_used + cost > DAILY_QUOTA_LIMIT:
            logger.warning(
                "YouTube API 할당량 한도 근접: 사용=%d, 요청=%d, 한도=%d",
                self._quota_used,
                cost,
                DAILY_QUOTA_LIMIT,
            )
            return False
        return True

    def _consume_quota(self, cost: int) -> None:
        """할당량 소비 기록"""
        self._quota_used += cost

    async def collect(
        self,
        query: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ContentItem]:
        """YouTube 영상 검색 및 수집

        Args:
            query: 검색 키워드
            date_from: 검색 시작일
            date_to: 검색 종료일

        Returns:
            수집된 ContentItem 목록
        """
        if not self._check_quota(QUOTA_COST_SEARCH):
            logger.error("YouTube API 할당량 부족으로 검색 중단")
            return []

        service = self._get_service()

        # 검색 API 호출
        search_params = {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": self._max_results,
            "order": "relevance",
            "regionCode": "KR",
            "relevanceLanguage": "ko",
        }

        # 날짜 필터 (RFC 3339 형식)
        if date_from:
            search_params["publishedAfter"] = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
        if date_to:
            search_params["publishedBefore"] = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")

        response = service.search().list(**search_params).execute()
        self._consume_quota(QUOTA_COST_SEARCH)

        # 검색 결과 파싱
        items = [parse_search_result(item) for item in response.get("items", [])]
        logger.info("YouTube 검색 결과: %d건 (query='%s')", len(items), query)

        # 영상 상세 정보 일괄 조회
        if items:
            video_ids = [item.source_id for item in items]
            items = await self._fetch_video_details(items, video_ids)

        return items

    async def _fetch_video_details(
        self, items: List[ContentItem], video_ids: List[str]
    ) -> List[ContentItem]:
        """영상 상세 정보 일괄 조회

        Args:
            items: 기존 ContentItem 목록
            video_ids: 영상 ID 목록

        Returns:
            상세 정보가 추가된 ContentItem 목록
        """
        if not self._check_quota(QUOTA_COST_VIDEOS):
            return items

        service = self._get_service()

        # 최대 50개씩 배치 조회
        batch_size = 50
        for i in range(0, len(video_ids), batch_size):
            batch_ids = video_ids[i : i + batch_size]
            response = (
                service.videos()
                .list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(batch_ids),
                )
                .execute()
            )
            self._consume_quota(QUOTA_COST_VIDEOS)

            # 상세 정보 병합
            video_map = {
                v["id"]: v for v in response.get("items", [])
            }
            for item in items[i : i + batch_size]:
                if item.source_id in video_map:
                    parse_video_details(item, video_map[item.source_id])

        return items

    async def collect_comments(
        self, content_id: str, max_comments: int = 100
    ) -> List[Comment]:
        """영상 댓글 수집

        Args:
            content_id: YouTube 영상 ID
            max_comments: 최대 수집 댓글 수

        Returns:
            Comment 목록
        """
        if not self._check_quota(QUOTA_COST_COMMENTS):
            return []

        service = self._get_service()
        all_comments: List[Comment] = []
        next_page_token = None

        try:
            while len(all_comments) < max_comments:
                params = {
                    "videoId": content_id,
                    "part": "snippet",
                    "maxResults": min(100, max_comments - len(all_comments)),
                    "order": "relevance",
                    "textFormat": "plainText",
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                response = service.commentThreads().list(**params).execute()
                self._consume_quota(QUOTA_COST_COMMENTS)

                comments = parse_comments_response(response)
                all_comments.extend(comments)

                # 다음 페이지 확인
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

        except Exception as e:
            # 댓글 비활성화된 영상 등 예외 처리
            logger.warning(
                "YouTube 댓글 수집 실패 (video_id=%s): %s", content_id, str(e)
            )

        logger.info(
            "YouTube 댓글 수집: video_id=%s, %d건", content_id, len(all_comments)
        )
        return all_comments

    @property
    def quota_used(self) -> int:
        """현재 사용된 할당량"""
        return self._quota_used

    def reset_quota(self) -> None:
        """할당량 카운터 초기화 (일일 리셋 시 호출)"""
        self._quota_used = 0
