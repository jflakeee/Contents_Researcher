"""
댓글(Comment) 모델 정의.
콘텐츠에 달린 댓글의 본문, 감성 분석 결과 등을 저장한다.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Comment(Base):
    """콘텐츠에 달린 댓글을 나타내는 ORM 모델."""

    __tablename__ = "comments"

    # 기본 키
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # 소속 콘텐츠 외래 키
    content_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 수집 시각
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 댓글 작성자
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 댓글 본문
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # 감성 분석 결과 (positive, negative, neutral)
    sentiment: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 감성 점수 (-1.0 ~ 1.0)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 좋아요 수
    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 콘텐츠 관계 (N:1)
    content: Mapped["Content"] = relationship(
        "Content", back_populates="comments"
    )


# 순환 참조 방지를 위해 하단에서 import
from app.models.content import Content  # noqa: E402, F401
