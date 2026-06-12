from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from sqlalchemy.sql import func
from src.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PAID")
    total_amount = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    delivery_address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now(), nullable=False)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), nullable=False, index=True)
    sku_id = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=False)
    product_title = Column(String(255), nullable=False)
    sku_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    line_total = Column(Integer, nullable=False)
