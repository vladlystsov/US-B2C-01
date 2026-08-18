import uuid

import httpx
from sqlalchemy.orm import Session

from src.models.subscription import ProductSubscription
from src.services.b2b_client import b2b_client

VALID_NOTIFY_ON = ["BACK_IN_STOCK", "PRICE_DROP"]


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def subscribe(self, user_id: str, product_id: str, events: list[str]) -> dict:
        if not events:
            raise ValueError("events is required")
        invalid_events = [event for event in events if event not in VALID_NOTIFY_ON]
        if invalid_events:
            raise ValueError(f"Invalid event value: {invalid_events[0]}. Allowed: {', '.join(VALID_NOTIFY_ON)}")

        try:
            product = b2b_client.get_product_by_id(product_id)
        except httpx.HTTPStatusError as exc:
            return {"status": "not_found" if exc.response.status_code == 404 else "b2b_error"}
        except Exception:
            return {"status": "b2b_error"}
        if not product:
            return {"status": "not_found"}

        existing = self.db.query(ProductSubscription).filter(
            ProductSubscription.user_id == user_id, ProductSubscription.product_id == product_id
        ).first()
        if existing:
            return {"status": "duplicate"}

        subscription = ProductSubscription(
            id=str(uuid.uuid4()), user_id=user_id, product_id=product_id, notify_on=events
        )
        self.db.add(subscription)
        self.db.commit()
        return {"status": "created"}

    def unsubscribe(self, user_id: str, product_id: str) -> bool:
        subscription = self.db.query(ProductSubscription).filter(
            ProductSubscription.user_id == user_id, ProductSubscription.product_id == product_id
        ).first()
        if not subscription:
            return False
        self.db.delete(subscription)
        self.db.commit()
        return True
