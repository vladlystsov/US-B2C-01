from __future__ import annotations

import uuid
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from src.models.order import Order, OrderItem
from src.services.b2b_client import b2b_client
from src.services.cart_service import CartService


class OrderService:
    def __init__(self, db: Session):
        self.db = db

    def create_order(self, user_id: str, request, idempotency_key: str) -> dict:
        existing = self.db.query(Order).filter(Order.idempotency_key == idempotency_key).first()
        if existing:
            return {"status": "existing", "order": self._format_order(existing)}

        cart = CartService(self.db).get_cart(user_id=user_id)
        cart_items = cart["items"]
        issues = []
        if not cart_items:
            issues.append({"sku_id": "", "type": "OUT_OF_STOCK", "message": "Cart is empty"})
        for item in cart_items:
            if not item["is_available"]:
                issues.append(
                    {
                        "sku_id": item["sku_id"],
                        "type": item.get("unavailable_reason") or "OUT_OF_STOCK",
                        "message": "SKU is no longer available",
                    }
                )

        if request.items_snapshot is not None:
            snapshot = {item.sku_id: (item.quantity, item.unit_price) for item in request.items_snapshot}
            actual = {item["sku_id"]: (item["quantity"], item["unit_price"]) for item in cart_items}
            if snapshot != actual:
                for sku_id in set(snapshot) | set(actual):
                    if snapshot.get(sku_id) != actual.get(sku_id):
                        issues.append(
                            {
                                "sku_id": sku_id,
                                "type": "PRICE_CHANGED",
                                "message": "Cart state differs from items_snapshot",
                            }
                        )

        if issues:
            return {"code": "CART_INVALID", "message": "Cart validation failed", "cart": cart, "issues": issues}

        order_id = str(uuid.uuid4())
        reserve_items = [{"sku_id": item["sku_id"], "quantity": item["quantity"]} for item in cart_items]
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/reserve",
                    json={"idempotency_key": idempotency_key, "order_id": order_id, "items": reserve_items},
                    headers=b2b_client.headers,
                    timeout=10.0,
                )
                if response.status_code == 409:
                    details = response.json()
                    return {
                        "code": "RESERVE_FAILED",
                        "message": "Не удалось зарезервировать товары",
                        "failed_items": details.get("failed_items") or details.get("details", {}).get("failed_items", []),
                    }
                response.raise_for_status()
        except Exception:
            return {"code": "B2B_UNAVAILABLE", "message": "B2B service unavailable"}

        subtotal = sum(item["unit_price"] * item["quantity"] for item in cart_items)
        order = Order(
            id=order_id,
            user_id=user_id,
            status="PAID",
            idempotency_key=idempotency_key,
            delivery_address=request.address_id,
            total_amount=subtotal,
        )
        self.db.add(order)
        order_items = []
        for cart_item in cart_items:
            order_item = OrderItem(
                id=str(uuid.uuid4()),
                order_id=order_id,
                sku_id=cart_item["sku_id"],
                product_id=cart_item["product_id"],
                product_title=cart_item["name"],
                sku_name=cart_item.get("sku_code") or "",
                quantity=cart_item["quantity"],
                unit_price=cart_item["unit_price"],
                line_total=cart_item["unit_price"] * cart_item["quantity"],
            )
            self.db.add(order_item)
            order_items.append(order_item)
        self.db.commit()
        return {
            "status": "created",
            "order": self._format_order(order, order_items, payment_method_id=request.payment_method_id, comment=request.comment),
        }

    def cancel_order(self, user_id: str, order_id: str, reason: str | None = None) -> dict:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        if not order:
            return {"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        if order.status not in ["CREATED", "PAID", "ASSEMBLING", "DELIVERING"]:
            return {
                "code": "CANCEL_NOT_ALLOWED",
                "message": f"Отмена невозможна: заказ в статусе {order.status}",
                "current_status": order.status,
            }

        items = self.db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        unreserve_items = [{"sku_id": item.sku_id, "quantity": item.quantity} for item in items]
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{b2b_client.base_url}/api/v1/inventory/unreserve",
                    json={"order_id": order_id, "items": unreserve_items},
                    headers=b2b_client.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
        except Exception:
            order.status = "CANCEL_PENDING"
            self.db.commit()
            return {"status": "pending", "order": self._format_order(order, items, cancel_reason=reason)}
        order.status = "CANCELLED"
        self.db.commit()
        return {"status": "cancelled", "order": self._format_order(order, items, cancel_reason=reason)}

    def get_order(self, user_id: str, order_id: str) -> dict | None:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        return self._format_order(order) if order else None

    def get_orders(self, user_id: str, limit: int = 20, offset: int = 0, status: str | None = None) -> dict:
        query = self.db.query(Order).filter(Order.user_id == user_id)
        if status:
            query = query.filter(Order.status == status)
        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
        return {
            "items": [self._format_order(order) for order in orders],
            "total_count": total,
            "limit": limit,
            "offset": offset,
        }

    def set_order_status(self, user_id: str, order_id: str, status: str) -> dict | None:
        order = self.db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
        if not order:
            return None
        previous = order.status
        order.status = status
        self.db.commit()
        if status == "DELIVERED" and previous != "DELIVERED":
            from src.services.fulfill_service import FulfillService
            FulfillService(self.db).trigger_fulfill(order_id)
        return self._format_order(order)

    def _format_order(
        self,
        order: Order,
        items: list[OrderItem] | None = None,
        payment_method_id: str | None = None,
        comment: str | None = None,
        cancel_reason: str | None = None,
    ) -> dict:
        if items is None:
            items = self.db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        formatted_items = [
            {
                "sku_id": item.sku_id,
                "product_id": item.product_id,
                "name": item.product_title,
                "sku_code": item.sku_name or None,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "image_url": None,
            }
            for item in items
        ]
        subtotal = sum(item["line_total"] for item in formatted_items)
        created_at = str(order.created_at) if order.created_at else None
        return {
            "id": order.id,
            "buyer_id": order.user_id,
            "status": order.status,
            "status_history": [{"status": "CREATED", "changed_at": created_at}, {"status": order.status, "changed_at": str(order.updated_at) if order.updated_at else created_at}],
            "items": formatted_items,
            "subtotal": subtotal,
            "delivery_cost": 0,
            "total": order.total_amount if order.total_amount is not None else subtotal,
            "address": {"id": order.delivery_address},
            "payment_method": {"id": payment_method_id} if payment_method_id else None,
            "comment": comment,
            "cancel_reason": cancel_reason,
            "created_at": created_at,
            "paid_at": created_at if order.status in {"PAID", "ASSEMBLING", "DELIVERING", "DELIVERED"} else None,
            "delivered_at": str(order.updated_at) if order.status == "DELIVERED" and order.updated_at else None,
        }
