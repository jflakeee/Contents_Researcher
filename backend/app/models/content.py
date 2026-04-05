"""
콘텐츠(Content) 모델 정의.
수집된 콘텐츠의 메타데이터, 감성 분석 결과, 키워드 등을 저장한다.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Content(Base):
    """수집된 콘텐츠를 나타내는 ORM 모델."""

    __tablename__ = "contents"

    # 기본 키
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 수집 시각
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # 콘텐츠 출처 (youtube, naver_news, reddit 등)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 원본 URL
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    # 콘텐츠 제목
    title: Mapped[str] = mapped_column(Text, nullable=False)

    # 콘텐츠 본문
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 본문 해시 (중복 체크용, SHA-256)
    body_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 추출된 키워드 목록
    # JSON 배열로 저장 (SQLite 호환)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # 컨텐츠 유형 분류 (informative=정보성, entertaining=흥미성)
    content_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 감성 분석 결과 (positive, negative, neutral)
    sentiment: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 감성 점수 (-1.0 ~ 1.0)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 중요도 점수
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 댓글 수
    comment_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 좋아요 수
    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 조회수
    view_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 추가 메타데이터 (JSON)
    # JSON 객체로 저장 (SQLite 호환)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )

    # 댓글 관계 (1:N)
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="content", lazy="selectin"
    )


# 순환 참조 방지를 위해 하단에서 import
from app.models.comment import Comment  # noqa: E402, F401
