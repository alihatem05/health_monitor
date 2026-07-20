import asyncio

pending_results: list[dict] = []
last_known_status: dict[str, str] = {}
running_loops: dict[str, asyncio.Task] = {}
flusher_task = None