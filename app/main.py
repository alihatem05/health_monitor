from fastapi import FastAPI, HTTPException, Depends
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Base
from app.database import engine, get_db
from app.scheduler import start_all_loops, start_service_loop, stop_service_loop, stop_all_loops, flush
from app.state import running_loops, last_known_status, pending_results
from app import crud
from app.schemas import ServiceCreate, Service, Result, Status
from app.log import log
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_all_loops()

    log("INFO", "Health Monitor Server has started running")

    yield

    await stop_all_loops()

    if pending_results:
        batch = pending_results.copy()
        pending_results.clear()
        await flush(batch)

app = FastAPI(title="Sentinel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/dashboard", StaticFiles(directory="static", html=True), name="dashboard")


@app.post("/services", response_model=Service)
async def create_service(service: ServiceCreate, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_service_by_url(db, service.url)
    if existing:
        service_id = str(existing.id)
        if service_id not in running_loops:
            await start_service_loop(existing)
        return existing

    new_service = await crud.create_service(
        db,
        name=service.name,
        url=service.url,
        check_interval_s=service.check_interval_s,
    )
    await start_service_loop(new_service)
    return new_service


@app.get("/services", response_model=list[Service])
async def list_services(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_services(db)


@app.delete("/services/{service_id}")
async def delete_service(service_id: str, db: AsyncSession = Depends(get_db)):
    await stop_service_loop(service_id)

    deleted = await crud.delete_service(db, service_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service not found")

    return {"deleted": True}


@app.get("/services/{service_id}/status", response_model=Status)
async def service_status(service_id: str):
    status = last_known_status.get(service_id)
    return Status(service_id=service_id, status=status)


@app.get("/services/{service_id}/history", response_model=list[Result])
async def service_history(service_id: str, db: AsyncSession = Depends(get_db)):
    return await crud.get_history(db, service_id)


@app.post("/services/stop-all")
async def stop_all_services():
    count = len(running_loops)
    await stop_all_loops()
    return {"stopped": count}


@app.get("/")
def root_route():
    return {"message": "Hello! :)"}