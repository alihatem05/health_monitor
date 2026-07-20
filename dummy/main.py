import os
import random
import time
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/health")
async def health():
    NAME = os.getenv("SERVICE_NAME", "dummy")
    MODE = os.getenv("HEALTH_STATUS", "healthy")

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