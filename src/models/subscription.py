from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func
from src.database import Base


class ProductSubscription(Base):
    __tablename__ = "product_subscriptions"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    product_id = Column(String(36), nullable=False)
    notify_on = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
