from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.models import Base
from app.database import engine
from app.scheduler import start_all_loops, start_service_loop, stop_service_loop, stop_all_loops
from app.state import running_loops, last_known_status
from app.crud import (create_service as crud_create_service, get_all_services, delete_service as crud_delete_service, get_history, get_service_by_url)
from app.schemas import ServiceCreate, Service, Result, Status
from app.log import log
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_all_loops()

    log("INFO", "Health Monitor Server has started running")

    yield

    for task in running_loops.values():
        task.cancel()

    log("INFO", "Health Monitor Server has stopped running")

app = FastAPI(title="Sentinel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/dashboard", StaticFiles(directory="static", html=True), name="dashboard")

@app.post("/services", response_model=Service)
async def create_service(service: ServiceCreate):
    existing = await get_service_by_url(service.url)
    if existing:
        service_id = str(existing.id)
        if service_id not in running_loops:
            await start_service_loop(existing)
        return existing

    new_service = await crud_create_service(
        name=service.name,
        url=service.url,
        check_interval_s=service.check_interval_s,
    )
    await start_service_loop(new_service)
    return new_service

@app.get("/services", response_model=list[Service])
async def list_services():
    return await get_all_services()

@app.delete("/services/{service_id}")
async def delete_service(service_id: str):
    deleted = await crud_delete_service(service_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Service not found")
    await stop_service_loop(service_id)
    return {"deleted": True}

@app.get("/services/{service_id}/status", response_model=Status)
async def service_status(service_id: str):
    status = last_known_status.get(service_id)
    return Status(service_id=service_id, status=status)

@app.get("/services/{service_id}/history", response_model=list[Result])
async def service_history(service_id: str):
    return await get_history(service_id)


@app.post("/services/stop-all")
async def stop_all_services():
    count = len(running_loops)
    await stop_all_loops()
    return {"stopped": count}