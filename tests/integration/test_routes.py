import pytest
from app import crud


@pytest.mark.asyncio
async def test_create_service(setup_database, client):
    response = await client.post("/services", json={
        "name": "test-service",
        "url": "http://example.com",
        "check_interval_s": 10,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-service"
    assert data["url"] == "http://example.com"
    assert data["check_interval_s"] == 10
    assert "id" in data


@pytest.mark.asyncio
async def test_create_service_duplicate_url(setup_database, client, db_session):
    existing = await crud.create_service(
        db_session,
        name="original",
        url="http://duplicate.com",
        check_interval_s=10,
    )

    response = await client.post("/services", json={
        "name": "different-name",
        "url": "http://duplicate.com",
        "check_interval_s": 20,
    })

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(existing.id)
    assert data["name"] == "original"
    assert data["check_interval_s"] == 10

    all_services = await crud.get_all_services(db_session)
    matching = [s for s in all_services if s.url == "http://duplicate.com"]
    assert len(matching) == 1


@pytest.mark.asyncio
async def test_list_services(setup_database, client, db_session):
    await crud.create_service(
        db_session,
        name="svc",
        url="http://list-test.com",
        check_interval_s=10,
    )

    response = await client.get("/services")

    assert response.status_code == 200
    data = response.json()
    assert any(s["url"] == "http://list-test.com" for s in data)


@pytest.mark.asyncio
async def test_delete_service_success(setup_database, client, db_session):
    service = await crud.create_service(
        db_session,
        name="delete-me",
        url="http://delete-test.com",
        check_interval_s=10,
    )

    response = await client.delete(f"/services/{service.id}")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    fetched = await crud.get_service(db_session, service.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_service_not_found(setup_database, client):
    response = await client.delete("/services/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_service_status_no_checks_yet(setup_database, client, db_session):
    service = await crud.create_service(
        db_session,
        name="svc",
        url="http://status-test.com",
        check_interval_s=10,
    )

    response = await client.get(f"/services/{service.id}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] is None


@pytest.mark.asyncio
async def test_service_history_empty(setup_database, client, db_session):
    service = await crud.create_service(
        db_session,
        name="svc",
        url="http://history-test.com",
        check_interval_s=10,
    )

    response = await client.get(f"/services/{service.id}/history")

    assert response.status_code == 200
    assert response.json() == []