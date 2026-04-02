"""
SQLAlchemy 선언적 베이스 클래스 정의.
모든 모델은 이 Base를 상속받아야 한다.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 ORM 모델의 공통 베이스 클래스."""
    pass
