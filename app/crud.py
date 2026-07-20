from app.models import Service, CheckResult
from app.log import log
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_service(db: AsyncSession, name: str, url: str, check_interval_s: int) -> Service:
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


async def get_all_services(db: AsyncSession) -> list[Service]:
    result = await db.execute(select(Service))
    return result.scalars().all()


async def get_service(db: AsyncSession, service_id: str) -> Service | None:
    return await db.get(Service, service_id)


async def delete_service(db: AsyncSession, service_id: str) -> bool:
    service = await db.get(Service, service_id)
    if service is None:
        log("DATABASE", f"Delete failed — service {service_id} not found")
        return False
    await db.delete(service)
    await db.commit()
    log("DATABASE", f"Deleted service '{service.name}' ({service_id})")
    return True


async def save_check_results(db: AsyncSession, batch: list[dict]) -> None:
    db.add_all([CheckResult(**item) for item in batch])
    await db.commit()


async def get_history(db: AsyncSession, service_id: str, limit: int = 50) -> list[CheckResult]:
    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.service_id == service_id)
        .order_by(CheckResult.check_time.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_service_by_url(db: AsyncSession, url: str) -> Service | None:
    result = await db.execute(select(Service).where(Service.url == url))
    return result.scalar_one_or_none()