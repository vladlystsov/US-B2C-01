import uuid

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from src.database import Base


class PriceDropNotification(Base):
    """Persisted notification work created by a B2B PRICE_CHANGED event.

    Delivery (email/push) is outside this service, but a durable outbox record
    guarantees that every opted-in buyer can be handled by a notification worker.
    """

    __tablename__ = "price_drop_notifications"
    __table_args__ = (
        UniqueConstraint("event_idempotency_key", "subscription_id", name="uq_price_drop_event_subscription"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_idempotency_key = Column(String(64), nullable=False, index=True)
    subscription_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), nullable=False, index=True)
    sku_id = Column(String(36), nullable=False, index=True)
    old_price = Column(Integer, nullable=False)
    new_price = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
