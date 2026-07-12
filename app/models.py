import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Service(Base):
    __tablename__ = "services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    check_interval_s = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship("CheckResult", back_populates="service")

class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"))
    status = Column(String)
    rt_ms = Column(Float, nullable=True)
    error_message = Column(String, nullable=True)
    check_time = Column(DateTime, default=datetime.utcnow)

    service = relationship("Service", back_populates="results")