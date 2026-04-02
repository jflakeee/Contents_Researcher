"""
모든 ORM 모델을 한 곳에서 import할 수 있도록 한다.
Alembic 마이그레이션 등에서 Base.metadata에 모든 테이블이 등록되려면
이 모듈을 import해야 한다.
"""

from app.models.base import Base
from app.models.comment import Comment
from app.models.content import Content
from app.models.keyword import CollectionJob, KeywordTrend

__all__ = [
    "Base",
    "Content",
    "Comment",
    "KeywordTrend",
    "CollectionJob",
]
