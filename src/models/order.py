from sqlalchemy import Column, DateTime, Integer, String, Text, event, inspect
from sqlalchemy.orm import Session, object_session
from sqlalchemy.sql import func

from src.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PAID")
    total_amount = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    request_fingerprint = Column(String(64), nullable=True)
    delivery_address = Column(Text, nullable=True)
    payment_method_snapshot = Column(Text, nullable=True)
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


@event.listens_for(Session, "after_flush")
def schedule_fulfill_on_delivery(session, _flush_context):
    pending = session.info.setdefault("fulfill_after_commit", set())
    for instance in session.dirty:
        if not isinstance(instance, Order) or instance.status != "DELIVERED":
            continue
        if inspect(instance).attrs.status.history.has_changes():
            pending.add(instance.id)


@event.listens_for(Session, "after_commit")
def trigger_fulfill_after_delivery_commit(session):
    order_ids = session.info.pop("fulfill_after_commit", set())
    if not order_ids:
        return
    bind = session.get_bind()
    from src.services.fulfill_service import FulfillService

    for order_id in order_ids:
        with Session(bind=bind) as fulfillment_session:
            FulfillService(fulfillment_session).trigger_fulfill(order_id)
