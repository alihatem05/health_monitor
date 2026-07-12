import time
import httpx
from app.log import log

async def check_service(url: str, timeout: float = 5.0) -> dict:
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            api = url.rstrip("/") + "/health"
            resp = await client.get(api)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if resp.status_code == 200:
            return {"status": "healthy", "rt_ms": elapsed_ms, "error_message": None}
        else:
            log("ERROR", f"{url} returned HTTP {resp.status_code}")
            return {"status": "unhealthy", "rt_ms": elapsed_ms,
                     "error_message": f"HTTP {resp.status_code}"}

    except httpx.TimeoutException:
        log("ERROR", f"Timeout checking {url}")
        return {"status": "timeout", "rt_ms": None, "error_message": "Request timed out"}
    except Exception as e:
        log("ERROR", f"Failed checking {url}: {e}")
        return {"status": "unhealthy", "rt_ms": None, "error_message": str(e)}