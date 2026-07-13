# dummy_service/main.py
import os
import random
import time
from fastapi import FastAPI, Response

app = FastAPI()

NAME = os.getenv("SERVICE_NAME", "dummy")
MODE = os.getenv("HEALTH_STATUS", "healthy")

@app.get("/health")
async def health():
    if MODE == "unhealthy":
        return Response(status_code=500)
    if MODE == "slow":
        time.sleep(3)
        return {"status": "ok", "name": NAME}
    if MODE == "flaky":
        if random.random() < 0.5:
            return Response(status_code=500)
        return {"status": "ok", "name": NAME}
    return {"status": "ok", "name": NAME}