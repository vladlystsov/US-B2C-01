from sqlalchemy.orm import Session
from src.models.processed_event import ProcessedEvent
from src.models.cart import CartItem
import uuid


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def handle_product_event(self, payload: dict) -> dict:
        idempotency_key = payload.get("idempotency_key")
        event_type = payload.get("event")
        sku_ids = payload.get("sku_ids", [])

        existing = self.db.query(ProcessedEvent).filter(
            ProcessedEvent.idempotency_key == idempotency_key,
            ProcessedEvent.sender_service == "b2b"
        ).first()

        if existing:
            return {"status": "duplicate"}

        if event_type == "PRODUCT_BLOCKED":
            self._mark_cart_items_unavailable(sku_ids, "PRODUCT_BLOCKED")
        elif event_type == "PRODUCT_DELETED":
            self._mark_cart_items_unavailable(sku_ids, "PRODUCT_DELETED")
        elif event_type == "SKU_OUT_OF_STOCK":
            self._mark_cart_items_unavailable(sku_ids, "OUT_OF_STOCK")

        db_event = ProcessedEvent(
            idempotency_key=idempotency_key,
            sender_service="b2b",
            event_type=event_type
        )
        self.db.add(db_event)
        self.db.commit()

        return {"status": "accepted"}

    def _mark_cart_items_unavailable(self, sku_ids: list, reason: str):
        cart_items = self.db.query(CartItem).filter(
            CartItem.sku_id.in_(sku_ids)
        ).all()

        for item in cart_items:
            item.unavailable_reason = reason

        self.db.flush()
