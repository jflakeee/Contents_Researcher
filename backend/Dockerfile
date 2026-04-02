# =============================================================================
# Contents Researcher 백엔드 Dockerfile
# =============================================================================
# 빌드 컨텍스트: 프로젝트 루트 (docker-compose에서 context: . 사용)
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (pyproject.toml에서 추출)
RUN pip install --no-cache-dir \
    "fastapi[standard]>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "sqlalchemy[asyncio]>=2.0" \
    "asyncpg>=0.29" \
    "alembic>=1.14.0" \
    "pydantic-settings>=2.6.0" \
    "redis[hiredis]>=5.0" \
    "httpx>=0.27"

# 공유 모듈 복사
COPY shared/ /app/shared/

# 백엔드 코드 복사
COPY backend/app/ /app/app/
COPY backend/alembic/ /app/alembic/
COPY backend/alembic.ini /app/

# PYTHONPATH 설정 (shared 모듈 접근용)
ENV PYTHONPATH="/app"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
