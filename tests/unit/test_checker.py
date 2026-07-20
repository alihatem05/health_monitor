import pytest
import httpx
from unittest.mock import Mock, AsyncMock
from app.checker import check_service


@pytest.fixture
def fake_http(mocker):
    fake_client = AsyncMock()

    fake_context = AsyncMock()
    fake_context.__aenter__.return_value = fake_client

    mocker.patch(
        "app.checker.httpx.AsyncClient",
        return_value=fake_context
    )

    return fake_client


@pytest.mark.asyncio
async def test_check_service_200(fake_http):

    fake_response = Mock()
    fake_response.status_code = 200

    fake_http.get.return_value = fake_response

    result = await check_service(
        "http://localhost:8000",
        timeout=0.5
    )

    assert result["status"] == "healthy"
    assert result["rt_ms"] >= 0
    assert result["error_message"] is None

    fake_http.get.assert_awaited_once_with(
        "http://localhost:8000/health"
    )


@pytest.mark.asyncio
async def test_check_service_404(fake_http):

    fake_response = Mock()
    fake_response.status_code = 404

    fake_http.get.return_value = fake_response

    result = await check_service(
        "http://localhost:8000",
        timeout=0.5
    )

    assert result["status"] == "unhealthy"
    assert result["rt_ms"] >= 0
    assert result["error_message"] == "HTTP 404"

    fake_http.get.assert_awaited_once_with(
        "http://localhost:8000/health"
    )


@pytest.mark.asyncio
async def test_check_service_timeout(fake_http):

    fake_http.get.side_effect = httpx.TimeoutException("Request timed out")

    result = await check_service(
        "http://localhost:8000",
        timeout=0.5
    )

    assert result["status"] == "timeout"
    assert result["rt_ms"] is None
    assert result["error_message"] == "Request timed out"

    fake_http.get.assert_awaited_once_with(
        "http://localhost:8000/health"
    )


@pytest.mark.asyncio
async def test_check_service_connection_error(fake_http):

    fake_http.get.side_effect = httpx.ConnectError(
        "Connection refused"
    )

    result = await check_service(
        "http://localhost:8000",
        timeout=0.5
    )

    assert result["status"] == "unhealthy"
    assert result["rt_ms"] is None
    assert result["error_message"] == "Connection refused"

    fake_http.get.assert_awaited_once_with(
        "http://localhost:8000/health"
    )