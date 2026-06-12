from sqlalchemy.orm import Session
from src.models.subscription import ProductSubscription
import uuid


VALID_NOTIFY_ON = ["IN_STOCK", "PRICE_DOWN"]


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db

    def subscribe(self, user_id: str, product_id: str, notify_on: list) -> dict:
        if not notify_on:
            raise ValueError("notify_on is required")

        for value in notify_on:
            if value not in VALID_NOTIFY_ON:
                raise ValueError(f"Invalid notify_on value: {value}. Allowed: {', '.join(VALID_NOTIFY_ON)}")

        existing = self.db.query(ProductSubscription).filter(
            ProductSubscription.user_id == user_id,
            ProductSubscription.product_id == product_id
        ).first()

        if existing:
            return {"status": "duplicate", "created_at": str(existing.created_at)}

        sub = ProductSubscription(
            id=str(uuid.uuid4()),
            user_id=user_id,
            product_id=product_id,
            notify_on=notify_on
        )
        self.db.add(sub)
        self.db.commit()

        return {"status": "created", "created_at": str(sub.created_at)}

    def unsubscribe(self, user_id: str, product_id: str) -> bool:
        sub = self.db.query(ProductSubscription).filter(
            ProductSubscription.user_id == user_id,
            ProductSubscription.product_id == product_id
        ).first()

        if sub:
            self.db.delete(sub)
            self.db.commit()
            return True

        return False
