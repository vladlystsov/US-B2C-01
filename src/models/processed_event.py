from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from src.database import Base


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    idempotency_key = Column(String(255), primary_key=True)
    sender_service = Column(String(50), primary_key=True, default="b2b")
    event_type = Column(String(50), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
