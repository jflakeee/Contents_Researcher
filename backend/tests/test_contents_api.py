"""
콘텐츠 API 엔드포인트 통합 테스트.
AsyncMock으로 DB 세션을 모킹하여 API 계약을 검증한다.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.session import get_db


# DB 모킹 유틸리티
def _make_mock_db(execute_returns=None):
    """테스트용 Mock DB 세션 생성

    Args:
        execute_returns: execute() 호출 시 반환할 값 목록 또는 단일 값
    """
    mock_session = AsyncMock()

    if isinstance(execute_returns, list):
        mock_session.execute = AsyncMock(side_effect=execute_returns)
    elif execute_returns is not None:
        mock_session.execute = AsyncMock(return_value=execute_returns)

    return mock_session


def _mock_count_result(count: int):
    """count 쿼리 결과 Mock"""
    result = MagicMock()
    result.scalar_one.return_value = count
    return result


def _mock_scalars_result(items: list):
    """select 쿼리 결과 Mock (scalars().all())"""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_scalar_one_or_none(value):
    """scalar_one_or_none 결과 Mock"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.fixture
async def client():
    """테스트용 비동기 HTTP 클라이언트"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # 테스트 후 오버라이드 정리
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """루트 엔드포인트가 서비스 상태를 정상 반환하는지 확인"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Contents Researcher API"


@pytest.mark.asyncio
async def test_search_contents_empty(client):
    """빈 DB에서 검색 시 빈 결과 반환 확인"""
    mock_db = _make_mock_db(execute_returns=[
        _mock_count_result(0),
        _mock_scalars_result([]),
    ])

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override

    response = await client.post(
        "/api/v1/contents/search",
        json={"page": 1, "page_size": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_get_content_not_found(client):
    """존재하지 않는 콘텐츠 ID → 404 반환 확인"""
    mock_db = _make_mock_db(
        execute_returns=_mock_scalar_one_or_none(None)
    )

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override

    response = await client.get("/api/v1/contents/99999")

    assert response.status_code == 404
    data = response.json()
    assert "찾을 수 없습니다" in data["detail"]


@pytest.mark.asyncio
async def test_trending_contents_empty(client):
    """트렌딩 엔드포인트 빈 결과 반환 확인"""
    mock_db = _make_mock_db(
        execute_returns=_mock_scalars_result([])
    )

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override

    response = await client.get("/api/v1/contents/trending?period=24h&limit=10")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
