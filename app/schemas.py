import uuid
from datetime import datetime
from pydantic import BaseModel

class ServiceCreate(BaseModel):
    name: str
    url: str
    check_interval_s: int = 30

class Service(BaseModel):
    id: uuid.UUID
    name: str
    url: str
    check_interval_s: int
    created_at: datetime

    class Config:
        from_attributes = True

class Result(BaseModel):
    status: str
    rt_ms: float | None
    error_message: str | None
    check_time: datetime

    class Config:
        from_attributes = True

class Status(BaseModel):
    service_id: str
    status: str | None  