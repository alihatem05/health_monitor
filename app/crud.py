from app.database import async_session
from app.models import Service, CheckResult
from app.log import log
from sqlalchemy import select

async def create_service(name: str, url: str, check_interval_s: int) -> Service:
    async with async_session() as db:
        new_service = Service(
            name=name,
            url=url,
            check_interval_s=check_interval_s
        )
        db.add(new_service)
        await db.commit()
        await db.refresh(new_service)
        log("DATABASE", f"Created service '{name}' ({new_service.id}) -> {url}")
        return new_service

async def get_all_services() -> list[Service]:
    async with async_session() as db:
        result = await db.execute(select(Service))
        return result.scalars().all()

async def get_service(service_id: str) -> Service | None:
    async with async_session() as db:
        return await db.get(Service, service_id)

async def delete_service(service_id: str) -> bool:
    async with async_session() as db:
        service = await db.get(Service, service_id)
        if service is None:
            log("DATABASE", f"Delete failed — service {service_id} not found")
            return False
        await db.delete(service)
        await db.commit()
        log("DATABASE", f"Deleted service '{service.name}' ({service_id})")
        return True

async def save_check_results(batch: list[dict]) -> None:
    async with async_session() as db:
        db.add_all([CheckResult(**item) for item in batch])
        await db.commit()

async def get_history(service_id: str, limit: int = 50) -> list[CheckResult]:
    async with async_session() as db:
        result = await db.execute(
            select(CheckResult)
            .where(CheckResult.service_id == service_id)
            .order_by(CheckResult.check_time.desc())
            .limit(limit)
        )
        return result.scalars().all()