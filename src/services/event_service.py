from sqlalchemy.orm import Session

from src.models.cart import CartItem
from src.models.processed_event import ProcessedEvent


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def handle_b2b_event(self, event: dict) -> dict:
        idempotency_key = event["idempotency_key"]
        existing = self.db.query(ProcessedEvent).filter(
            ProcessedEvent.idempotency_key == idempotency_key, ProcessedEvent.sender_service == "b2b"
        ).first()
        if existing:
            return {"status": "duplicate"}

        event_type = event["event_type"]
        payload = event.get("payload") or {}
        reason_by_type = {
            "PRODUCT_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_HARD_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_DELETED": "PRODUCT_DELETED",
            "SKU_OUT_OF_STOCK": "OUT_OF_STOCK",
        }
        if event_type in reason_by_type:
            sku_ids = payload.get("sku_ids") or ([payload["sku_id"]] if payload.get("sku_id") else [])
            if sku_ids:
                self.db.query(CartItem).filter(CartItem.sku_id.in_(sku_ids)).update(
                    {CartItem.unavailable_reason: reason_by_type[event_type]}, synchronize_session=False
                )

        self.db.add(ProcessedEvent(idempotency_key=idempotency_key, sender_service="b2b", event_type=event_type))
        self.db.commit()
        return {"status": "accepted"}
