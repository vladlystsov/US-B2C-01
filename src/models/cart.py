from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.sql import func
from src.database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    sku_id = Column(String(36), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unavailable_reason = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now(), nullable=False)
