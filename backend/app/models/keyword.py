"""
키워드 트렌드(KeywordTrend) 및 수집 작업(CollectionJob) 모델 정의.
키워드 빈도/감성 추이 및 크롤러 작업 이력을 저장한다.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KeywordTrend(Base):
    """일별 키워드 트렌드 집계 테이블."""

    __tablename__ = "keyword_trends"

    # 복합 기본 키: 날짜 + 키워드 + 출처
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 해당 날짜에 해당 키워드가 등장한 횟수
    count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 해당 키워드의 평균 감성 점수
    avg_sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)


class CollectionJob(Base):
    """크롤러/수집 작업 이력 테이블."""

    __tablename__ = "collection_jobs"

    # 기본 키
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 수집 대상 출처
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 작업 상태 (pending, running, completed, failed)
    status: Mapped[str | None] = mapped_column(
        String(20), default="pending", server_default="pending"
    )

    # 작업 시작 시각
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 작업 완료 시각
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 수집된 항목 수
    items_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # 에러 메시지 (실패 시)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 추가 메타데이터
    # JSON 객체로 저장 (SQLite 호환)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
