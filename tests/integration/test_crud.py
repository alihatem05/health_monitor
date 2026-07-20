from datetime import datetime, timedelta
import pytest
from app import crud


@pytest.mark.asyncio
async def test_create_service(setup_database, db_session):
    service = await crud.create_service(
        db_session,
        name="test-service",
        url="http://example.com",
        check_interval_s=10,
    )

    assert service.id is not None
    assert service.name == "test-service"
    assert service.url == "http://example.com"
    assert service.check_interval_s == 10


@pytest.mark.asyncio
async def test_get_service_by_url_found(setup_database, db_session):
    created = await crud.create_service(
        db_session,
        name="test-service",
        url="http://example.com",
        check_interval_s=10,
    )

    service = await crud.get_service_by_url(
        db_session,
        "http://example.com",
    )

    assert service is not None
    assert service.id == created.id
    assert service.name == "test-service"
    assert service.url == "http://example.com"


@pytest.mark.asyncio
async def test_get_service_by_url_not_found(setup_database, db_session):
    service = await crud.get_service_by_url(
        db_session,
        "http://does-not-exist.com",
    )

    assert service is None


@pytest.mark.asyncio
async def test_get_all_services(setup_database, db_session):
    service1 = await crud.create_service(
        db_session,
        name="service1",
        url="http://one.com",
        check_interval_s=10,
    )

    service2 = await crud.create_service(
        db_session,
        name="service2",
        url="http://two.com",
        check_interval_s=20,
    )

    services = await crud.get_all_services(db_session)

    assert len(services) == 2

    ids = {service.id for service in services}
    assert service1.id in ids
    assert service2.id in ids


@pytest.mark.asyncio
async def test_delete_service_success(setup_database, db_session):
    service = await crud.create_service(
        db_session,
        name="delete-me",
        url="http://delete.com",
        check_interval_s=10,
    )

    deleted = await crud.delete_service(
        db_session,
        service.id,
    )

    assert deleted is True

    fetched = await crud.get_service(
        db_session,
        service.id,
    )

    assert fetched is None


@pytest.mark.asyncio
async def test_delete_service_not_found(setup_database, db_session):
    deleted = await crud.delete_service(
        db_session,
        "00000000-0000-0000-0000-000000000000",
    )

    assert deleted is False


@pytest.mark.asyncio
async def test_get_history_ordering(setup_database, db_session):
    service = await crud.create_service(
        db_session,
        name="history-service",
        url="http://history.com",
        check_interval_s=10,
    )

    now = datetime.utcnow()

    await crud.save_check_results(
        db_session,
        [
            {
                "service_id": service.id,
                "status": "healthy",
                "rt_ms": 100,
                "error_message": None,
                "check_time": now - timedelta(minutes=2),
            },
            {
                "service_id": service.id,
                "status": "unhealthy",
                "rt_ms": 300,
                "error_message": "HTTP 500",
                "check_time": now,
            },
            {
                "service_id": service.id,
                "status": "healthy",
                "rt_ms": 120,
                "error_message": None,
                "check_time": now - timedelta(minutes=1),
            },
        ],
    )

    history = await crud.get_history(db_session, service.id)

    assert len(history) == 3

    assert history[0].check_time > history[1].check_time
    assert history[1].check_time > history[2].check_time

    assert history[0].status == "unhealthy"
    assert history[1].status == "healthy"
    assert history[2].status == "healthy"