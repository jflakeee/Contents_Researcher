"""
공통 데이터 타입 정의

수집기, 분석기, 백엔드에서 공유하는 데이터 클래스.
모든 모듈 간 데이터 교환은 이 타입들을 통해 이루어진다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Comment:
    """댓글 데이터"""

    # 작성자
    author: str
    # 댓글 본문
    body: str
    # 감성 분류 (positive, negative, neutral)
    sentiment: Optional[str] = None
    # 감성 점수 (-1.0 ~ 1.0)
    sentiment_score: Optional[float] = None
    # 좋아요 수
    like_count: int = 0


@dataclass
class ContentItem:
    """수집된 컨텐츠 데이터

    수집기에서 생성하고, 분석기에서 키워드/감성/중요도를 채운 뒤,
    백엔드에서 DB에 저장한다.
    """

    # 수집 출처 (youtube, aggag, instagram 등)
    source: str
    # 원본 URL
    source_url: str
    # 플랫폼 내 고유 ID
    source_id: str
    # 컨텐츠 제목
    title: str
    # 본문 (선택)
    body: Optional[str] = None
    # 본문 SHA-256 해시 (중복 체크용)
    body_hash: Optional[str] = None
    # 추출된 키워드 목록
    keywords: List[str] = field(default_factory=list)
    # 컨텐츠 유형 (informative=정보성, entertaining=흥미성)
    content_type: Optional[str] = None
    # 감성 분류 (positive, negative, neutral)
    sentiment: Optional[str] = None
    # 감성 점수 (-1.0 ~ 1.0)
    sentiment_score: Optional[float] = None
    # 중요도 점수 (0.0 ~ 10.0)
    importance_score: Optional[float] = None
    # 댓글 수
    comment_count: int = 0
    # 좋아요 수
    like_count: int = 0
    # 조회수
    view_count: int = 0
    # 본문 내 이미지 URL 목록
    image_urls: List[str] = field(default_factory=list)
    # 댓글 목록
    comments: List[Comment] = field(default_factory=list)
    # 플랫폼별 추가 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 수집 시각
    collected_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class SentimentResult:
    """감성 분석 결과"""

    # 분류 라벨 (positive, negative, neutral)
    label: str
    # 점수 (-1.0 ~ 1.0)
    score: float
    # 상세 비율 (예: {"positive": 0.65, "neutral": 0.25, "negative": 0.10})
    details: Optional[Dict[str, float]] = None


@dataclass
class CollectionResult:
    """수집 작업 결과"""

    # 수집 출처
    source: str
    # 수집된 컨텐츠 수
    collected_count: int = 0
    # 저장된 컨텐츠 수 (중복 제외)
    saved_count: int = 0
    # 오류 메시지 (실패 시)
    error_message: Optional[str] = None
    # 성공 여부
    success: bool = True
