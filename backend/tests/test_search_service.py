"""
SearchService 유닛 테스트.
DB 세션을 모킹하여 서비스 레이어의 비즈니스 로직을 검증한다.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.search import SearchRequest
from app.services.search_service import SearchService


def _make_search_mock_db(count=0, items=None):
    """검색용 Mock DB: execute가 2번 호출됨 (count + select)"""
    mock_db = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one.return_value = count

    select_result = MagicMock()
    select_result.scalars.return_value.all.return_value = items or []

    mock_db.execute = AsyncMock(side_effect=[count_result, select_result])
    return mock_db


@pytest.mark.asyncio
async def test_search_empty_result():
    """빈 DB에서 검색 시 빈 PaginatedResponse를 반환하는지 확인한다."""
    mock_db = _make_search_mock_db(count=0, items=[])
    request = SearchRequest(page=1, page_size=10)

    result = await SearchService.search(mock_db, request)

    assert result.total == 0
    assert result.items == []
    assert result.page == 1
    assert result.page_size == 10
    assert result.total_pages == 0


@pytest.mark.asyncio
async def test_search_with_query_filter():
    """query 파라미터가 있을 때 execute가 호출되는지 확인한다."""
    mock_db = _make_search_mock_db(count=0, items=[])
    request = SearchRequest(query="테스트", page=1, page_size=10)

    result = await SearchService.search(mock_db, request)

    # execute가 2번 호출되어야 함 (count + select)
    assert mock_db.execute.call_count == 2
    assert result.total == 0


@pytest.mark.asyncio
async def test_search_with_source_filter():
    """sources 필터가 있을 때 정상 동작하는지 확인한다."""
    mock_db = _make_search_mock_db(count=0, items=[])
    request = SearchRequest(sources=["youtube", "aggag"], page=1, page_size=20)

    result = await SearchService.search(mock_db, request)

    assert mock_db.execute.call_count == 2
    assert result.total == 0


@pytest.mark.asyncio
async def test_get_detail_not_found():
    """존재하지 않는 콘텐츠 조회 시 None을 반환하는지 확인한다."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await SearchService.get_detail(mock_db, content_id=99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_trending_empty():
    """빈 DB에서 트렌딩 조회 시 빈 리스트를 반환하는지 확인한다."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await SearchService.get_trending(mock_db, period="24h", limit=10)
    assert isinstance(result, list)
    assert len(result) == 0
