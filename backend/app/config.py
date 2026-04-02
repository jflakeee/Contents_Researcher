"""
애플리케이션 설정 모듈.
pydantic-settings 기반으로 환경 변수에서 설정값을 로드한다.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정 클래스."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 데이터베이스 연결 URL (SQLite + aiosqlite)
    DATABASE_URL: str = "sqlite+aiosqlite:///data/contents_researcher.db"

    # YouTube Data API 키
    YOUTUBE_API_KEY: str = ""

    # CORS 허용 오리진 목록
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # 스케줄러 타임존
    SCHEDULER_TIMEZONE: str = "Asia/Seoul"

    # 콘텐츠당 추출할 키워드 수
    KEYWORDS_PER_CONTENT: int = 15

    # 감성 분석 임계값 (양수/음수 판단 기준)
    SENTIMENT_THRESHOLD: float = 0.1

    # 기본 페이지 크기
    DEFAULT_PAGE_SIZE: int = 20


@lru_cache
def get_settings() -> Settings:
    """캐싱된 Settings 인스턴스를 반환한다."""
    return Settings()
