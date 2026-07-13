import asyncio
from datetime import datetime
from app import state, crud
from app.checker import check_service
from app.models import Service
from app.config import FLUSH_INTERVAL
from app.log import log

async def check_loop(service: Service):
    service_id = str(service.id)
    while True:
        result = await check_service(service.url)

        state.pending_results.append({
            "service_id": service.id,
            "status": result["status"],
            "rt_ms": result["rt_ms"],
            "error_message": result["error_message"],
            "check_time": datetime.utcnow(),
        })

        old_status = state.last_known_status.get(service_id)
        new_status = result["status"]
        if old_status != new_status:
            state.last_known_status[service_id] = new_status
            handle_alert(service, old_status, new_status)

        await asyncio.sleep(service.check_interval_s)

def handle_alert(service: Service, old_status: str | None, new_status: str):
    if old_status is None:
        log("INFO", f"{service.name} first check: {new_status}")
    else:
        log("ALERT", f"{service.name} changed: {old_status} -> {new_status}")

async def flusher_loop():
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)
        if state.pending_results:
            batch = state.pending_results.copy()
            state.pending_results.clear()
            await crud.save_check_results(batch)
            log("DATABASE", f"Flushed {len(batch)} check result(s) to DB")

async def start_service_loop(service: Service):
    task = asyncio.create_task(check_loop(service))
    state.running_loops[str(service.id)] = task
    log("SCHEDULER", f"Started check loop for '{service.name}' ({service.id})")

async def stop_service_loop(service_id: str):
    task = state.running_loops.pop(service_id, None)
    if task:
        task.cancel()
        log("SCHEDULER", f"Stopped check loop for {service_id}")

async def start_all_loops():
    services = await crud.get_all_services()
    for service in services:
        await start_service_loop(service)
    asyncio.create_task(flusher_loop())
    log("SCHEDULER", f"Startup complete. {len(services)} service loop(s) running")

async def stop_all_loops():
    service_ids = list(state.running_loops.keys())
    for service_id in service_ids:
        await stop_service_loop(service_id)
    log("SCHEDULER", f"Stopped {len(service_ids)} service loop(s)")