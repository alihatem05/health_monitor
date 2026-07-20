import asyncio
import threading
import time
import uuid
import pytest
import uvicorn
from httpx import AsyncClient, ASGITransport
from asgi_lifespan import LifespanManager
from app.main import app
from dummy.main import app as dummy_app
import os


@pytest.fixture(scope="module")
def dummy_server():
    config = uvicorn.Config(
        dummy_app,
        host="127.0.0.1",
        port=9000,
        log_level="error",
    )

    server = uvicorn.Server(config)

    thread = threading.Thread(
        target=server.run,
        daemon=True,
    )

    thread.start()

    time.sleep(1)

    yield

    server.should_exit = True
    thread.join(timeout=5)


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _register_service(client, name="dummy", check_interval_s=1):
    # unique query string per call so each test gets a fresh service row
    # instead of reusing a stale one (and its stale history) from a
    # previous test/run that happened to register the same URL.
    unique_url = f"http://127.0.0.1:9000/health?t={uuid.uuid4().hex}"
    response = await client.post(
        "/services",
        json={
            "name": name,
            "url": unique_url,
            "check_interval_s": check_interval_s,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


async def _wait_for_history(client, service_id, timeout=8.0, interval=0.25, min_entries=1):
    deadline = time.time() + timeout
    history = []
    while time.time() < deadline:
        response = await client.get(f"/services/{service_id}/history")
        assert response.status_code == 200
        history = response.json()
        if len(history) >= min_entries:
            return history
        await asyncio.sleep(interval)
    pytest.fail(
        f"Only {len(history)} history entries for service {service_id} "
        f"within {timeout}s (expected >= {min_entries})"
    )


@pytest.mark.asyncio
async def test_e2e_healthy(dummy_server):
    os.environ["HEALTH_STATUS"] = "healthy"

    async with LifespanManager(app):
        async with _client() as client:
            service_id = await _register_service(client)

            history = await _wait_for_history(client, service_id)

            latest = history[-1]
            assert latest["status"] == "healthy"

            # clean up so this service doesn't get resurrected by
            # start_all_loops() on the next test's LifespanManager startup
            await client.delete(f"/services/{service_id}")


@pytest.mark.asyncio
async def test_e2e_unhealthy(dummy_server):
    os.environ["HEALTH_STATUS"] = "unhealthy"

    async with LifespanManager(app):
        async with _client() as client:
            service_id = await _register_service(client)

            history = await _wait_for_history(client, service_id)

            latest = history[-1]
            assert latest["status"] == "unhealthy"

            await client.delete(f"/services/{service_id}")


@pytest.mark.asyncio
async def test_e2e_slow(dummy_server):
    os.environ["HEALTH_STATUS"] = "slow"

    async with LifespanManager(app):
        async with _client() as client:
            service_id = await _register_service(client)

            history = await _wait_for_history(client, service_id, timeout=20.0)

            latest = history[-1]
            assert latest["status"] in ("healthy", "unhealthy", "timeout")

            await client.delete(f"/services/{service_id}")


@pytest.mark.asyncio
async def test_e2e_flaky(dummy_server):
    os.environ["HEALTH_STATUS"] = "flaky"

    async with LifespanManager(app):
        async with _client() as client:
            service_id = await _register_service(client)

            history = await _wait_for_history(
                client, service_id, timeout=20.0, min_entries=2
            )

            statuses = {entry["status"] for entry in history}
            assert statuses.issubset({"healthy", "unhealthy"})
            assert len(statuses) >= 1

            await client.delete(f"/services/{service_id}")