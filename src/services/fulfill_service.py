import logging

import httpx
from sqlalchemy.orm import Session

from src.models.order import Order, OrderItem
from src.services.b2b_client import b2b_client

logger = logging.getLogger(__name__)


class FulfillService:
    def __init__(self, db: Session):
        self.db = db

    def trigger_fulfill(self, order_id: str) -> dict:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        if order.status != "DELIVERED":
            return {"code": "INVALID_STATUS", "message": f"Order status is {order.status}, expected DELIVERED"}

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        fulfill_items = [{"sku_id": item.sku_id, "quantity": item.quantity} for item in items]
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/fulfill",
                    json={"order_id": order_id, "items": fulfill_items},
                    headers=b2b_client.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                return {"status": "fulfilled"}
        except Exception as exc:
            # DELIVERED is never rolled back: the next worker run can retry this idempotent B2B call.
            logger.error("Fulfill failed for order %s: %s", order_id, exc)
            return {"status": "retry_needed", "error": str(exc)}

    def retry_pending_fulfills(self) -> dict:
        orders = self.db.query(Order).filter(Order.status == "DELIVERED").all()
        retried = sum(self.trigger_fulfill(str(order.id)).get("status") == "fulfilled" for order in orders)
        return {"retried": retried, "total": len(orders)}
