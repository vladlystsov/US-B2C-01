from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.cart import CartItem
from src.models.processed_event import ProcessedEvent


class EventService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _event_reason(event_type: str, payload: dict) -> str | None:
        return payload.get("reason") or {
            "PRODUCT_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_HARD_BLOCKED": "PRODUCT_BLOCKED",
            "PRODUCT_DELETED": "PRODUCT_DELETED",
            "SKU_OUT_OF_STOCK": "OUT_OF_STOCK",
        }.get(event_type)

    def handle_b2b_event(self, event: dict) -> dict:
        """Atomically deduplicate an event and reconcile cart availability from B2B."""
        idempotency_key = event["idempotency_key"]
        event_type = event["event_type"]
        payload = event.get("payload") or {}

        # The composite primary key is the concurrency guard: flush before the
        # cart mutation, so a parallel delivery cannot apply side effects twice.
        try:
            self.db.add(
                ProcessedEvent(
                    idempotency_key=idempotency_key,
                    sender_service="b2b",
                    event_type=event_type,
                )
            )
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return {"status": "duplicate"}

        sku_ids = payload.get("sku_ids") or ([payload["sku_id"]] if payload.get("sku_id") else [])
        product_id = payload.get("product_id")

        if event_type == "SKU_BACK_IN_STOCK":
            query = self.db.query(CartItem)
            conditions = []
            if sku_ids:
                conditions.append(CartItem.sku_id.in_(sku_ids))
            if product_id and not sku_ids:
                # A product-only restore is intentionally limited to rows for that
                # product; each SKU's current quantity is still checked on GET cart.
                conditions.append(CartItem.product_id == product_id)
            if conditions:
                query.filter(or_(*conditions)).update({CartItem.unavailable_reason: None}, synchronize_session=False)
        else:
            reason = self._event_reason(event_type, payload)
            if reason:
                conditions = []
                if product_id:
                    conditions.append(CartItem.product_id == product_id)
                if sku_ids:
                    # Compatibility for already persisted rows from before product_id.
                    conditions.append(CartItem.sku_id.in_(sku_ids))
                if conditions:
                    self.db.query(CartItem).filter(or_(*conditions)).update(
                        {CartItem.unavailable_reason: reason}, synchronize_session=False
                    )

        self.db.commit()
        return {"status": "accepted"}
